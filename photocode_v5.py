
from PIL import Image
import numpy as np
import os
import math
import zlib

# AK's PhotoCode 5.0

LONG_SIDE = 768
BLOCK = 8
STRENGTH = 60.0
REGION_COLS = 32
SYNC = bytes.fromhex("D3A59C7E")
HEADER_BYTES = 13

N = np.arange(8)
D = np.cos(
    (2 * N[:, None] + 1) * N[None, :] * math.pi / 16
)
D[:, 0] *= 1 / math.sqrt(2)
D *= 0.5


def dct(block):
    return D.T @ block @ D


def idct(coeff):
    return D @ coeff @ D.T


def canonical_size(image):
    w, h = image.size
    scale = LONG_SIDE / max(w, h)
    return max(8, round(w * scale)), max(8, round(h * scale))


def normalize_image(image):
    return image.resize(
        canonical_size(image),
        Image.Resampling.LANCZOS
    )


def to_gray(arr):
    return (
        0.299 * arr[:, :, 0]
        + 0.587 * arr[:, :, 1]
        + 0.114 * arr[:, :, 2]
    )


def bits_from_bytes(data):
    return np.unpackbits(
        np.frombuffer(data, dtype=np.uint8)
    ).astype(np.uint8).tolist()


def bytes_from_bits(bits):
    return np.packbits(
        np.asarray(bits, dtype=np.uint8)
    ).tobytes()


# Hamming (7,4)

def hamming_encode(n):
    d1 = (n >> 3) & 1
    d2 = (n >> 2) & 1
    d3 = (n >> 1) & 1
    d4 = n & 1

    p1 = d1 ^ d2 ^ d4
    p2 = d1 ^ d3 ^ d4
    p4 = d2 ^ d3 ^ d4

    return [p1, p2, d1, p4, d2, d3, d4]


def hamming_decode(bits):
    b = list(map(int, bits))

    s1 = b[0] ^ b[2] ^ b[4] ^ b[6]
    s2 = b[1] ^ b[2] ^ b[5] ^ b[6]
    s4 = b[3] ^ b[4] ^ b[5] ^ b[6]

    syndrome = s1 + 2 * s2 + 4 * s4

    if syndrome:
        b[syndrome - 1] ^= 1

    return (
        (b[2] << 3)
        | (b[4] << 2)
        | (b[5] << 1)
        | b[6]
    )


def encode_bytes(data):
    output = []

    for value in data:
        output.extend(hamming_encode(value >> 4))
        output.extend(hamming_encode(value & 15))

    return output


def decode_bytes(bits):
    if len(bits) % 14:
        return None

    output = bytearray()

    for i in range(0, len(bits), 14):
        high = hamming_decode(bits[i:i + 7])
        low = hamming_decode(bits[i + 7:i + 14])
        output.append((high << 4) | low)

    return bytes(output)


def embed_bit(block, bit):
    coeff = dct(block)

    target = STRENGTH if bit else -STRENGTH

    change = target - (
        coeff[2, 3] - coeff[3, 2]
    )

    coeff[2, 3] += change / 2
    coeff[3, 2] -= change / 2

    return idct(coeff)


# Read all aligned 8x8 blocks efficiently

def read_grid(gray, dx, dy):
    h, w = gray.shape

    rows = (h - dy) // BLOCK
    cols = (w - dx) // BLOCK

    if rows <= 0 or cols <= 0:
        return None

    cut = gray[
        dy:dy + rows * BLOCK,
        dx:dx + cols * BLOCK
    ]

    blocks = cut.reshape(
        rows, BLOCK, cols, BLOCK
    ).transpose(0, 2, 1, 3)

    coeff = np.einsum(
        "ij,rcjk,kl->rcil",
        D.T, blocks, D,
        optimize=True
    )

    return (
        coeff[:, :, 2, 3]
        - coeff[:, :, 3, 2] > 0
    ).astype(np.uint8)


def packet_for(message):
    data = message.encode("utf-8")

    if not data:
        raise ValueError("Message cannot be empty.")

    crc = zlib.crc32(data) & 0xFFFFFFFF

    packet = (
        b"AKPC5"
        + len(data).to_bytes(4, "big")
        + crc.to_bytes(4, "big")
        + data
    )

    return data, packet


# Three separate message locations

def region_starts(rows, cols):
    x = (cols - REGION_COLS) // 2

    return [
        (x, round(rows * fraction))
        for fraction in (0.13, 0.38, 0.63)
    ]


def encode_image(image, message):
    image = normalize_image(image.convert("RGB"))

    arr = np.asarray(image, dtype=np.float64).copy()

    gray = to_gray(arr)
    original = gray.copy()

    h, w = gray.shape
    rows = h // BLOCK
    cols = w // BLOCK

    data, packet = packet_for(message)

    coded = bits_from_bytes(SYNC) + encode_bytes(packet)

    region_rows = math.ceil(len(coded) / REGION_COLS)

    starts = region_starts(rows, cols)

    gaps = [
        starts[i + 1][1] - starts[i][1]
        for i in range(len(starts) - 1)
    ]

    safe_rows = min(
        gaps + [rows - starts[-1][1]]
    ) if starts else 0

    if (
        cols < REGION_COLS
        or region_rows > safe_rows
        or any(y + region_rows > rows for _, y in starts)
    ):
        max_bytes = max(
            0,
            (REGION_COLS * safe_rows - 32) // 14
            - HEADER_BYTES
        )

        raise ValueError(
            "Message too long or image too small. "
            "Maximum message bytes: " + str(max_bytes)
        )

    if len(coded) > REGION_COLS * region_rows:
        raise ValueError("Capacity error.")

    for x0, y0 in starts:
        for i, bit in enumerate(coded):
            rr = y0 + i // REGION_COLS
            cc = x0 + i % REGION_COLS

            r = rr * BLOCK
            c = cc * BLOCK

            gray[
                r:r + BLOCK,
                c:c + BLOCK
            ] = embed_bit(
                gray[r:r + BLOCK, c:c + BLOCK],
                bit
            )

    difference = gray - original

    result = arr + difference[:, :, None]
    result = np.clip(result, 0, 255).astype(np.uint8)

    return Image.fromarray(result), len(data)


# Search for synchronization marker and recover packet

def try_grid(bits):
    rows, cols = bits.shape

    if cols < REGION_COLS:
        return None

    syncbits = np.array(
        bits_from_bytes(SYNC),
        dtype=np.uint8
    )

    center = (cols - REGION_COLS) // 2

    x_candidates = range(
        max(0, center - 2),
        min(cols - REGION_COLS, center + 2) + 1
    )

    for fraction in (0.13, 0.38, 0.63):
        expected = round(rows * fraction)

        y_candidates = range(
            max(0, expected - 8),
            min(rows - 1, expected + 8) + 1
        )

        for y0 in y_candidates:
            for x0 in x_candidates:

                flat = bits[
                    y0:, x0:x0 + REGION_COLS
                ].reshape(-1)

                if len(flat) < 32:
                    continue

                if np.count_nonzero(
                    flat[:32] != syncbits
                ) > 3:
                    continue

                header_coded = flat[
                    32:32 + HEADER_BYTES * 14
                ]

                if len(header_coded) < HEADER_BYTES * 14:
                    continue

                header = decode_bytes(
                    header_coded.tolist()
                )

                if header is None or header[:5] != b"AKPC5":
                    continue

                length = int.from_bytes(
                    header[5:9], "big"
                )

                if length <= 0 or length > 2000:
                    continue

                total_bits = (
                    32 + (HEADER_BYTES + length) * 14
                )

                if len(flat) < total_bits:
                    continue

                packet = decode_bytes(
                    flat[32:total_bits].tolist()
                )

                if packet is None or packet[:5] != b"AKPC5":
                    continue

                got_length = int.from_bytes(
                    packet[5:9], "big"
                )

                if got_length != length:
                    continue

                data = packet[13:13 + length]

                crc = int.from_bytes(
                    packet[9:13], "big"
                )

                if len(data) != length:
                    continue

                if (zlib.crc32(data) & 0xFFFFFFFF) != crc:
                    continue

                try:
                    return data.decode("utf-8")
                except UnicodeDecodeError:
                    continue

    return None


def decode_image(image):
    # Native pixels first for crops.
    # Canonical scaling second for resized copies.

    candidates = [image.convert("RGB")]

    normalized = normalize_image(image.convert("RGB"))

    if normalized.size != image.size:
        candidates.append(normalized)

    for candidate in candidates:
        arr = np.asarray(candidate, dtype=np.float64)
        gray = to_gray(arr)

        for dy in range(BLOCK):
            for dx in range(BLOCK):
                grid = read_grid(gray, dx, dy)

                if grid is None:
                    continue

                message = try_grid(grid)

                if message is not None:
                    return message

    return None


def main():
    print("\n===== AK's PhotoCode 5.0 =====")
    print("1. Create PhotoCode")
    print("2. Scan PhotoCode")

    choice = input("Choose option: ").strip()

    if choice == "1":
        path = input("Original image path: ").strip()
        message = input("Secret message: ")

        if not os.path.isfile(path):
            print("Image file not found.")
            return

        try:
            with Image.open(path) as im:
                output_image, size = encode_image(im, message)

            output = (
                os.path.splitext(path)[0]
                + "_photocode_v5.png"
            )

            output_image.save(output)

            print("PhotoCode 5.0 created:", output)
            print("Normalized dimensions:", output_image.size)
            print("Message bytes:", size)
            print("Copies: 3")
            print("Hamming (7,4): Enabled")
            print("CRC32: Enabled")
            print("Synchronization search: Enabled")

        except Exception as e:
            print("Encoding error:", str(e))

    elif choice == "2":
        path = input("PhotoCode image path: ").strip()

        if not os.path.isfile(path):
            print("Image file not found.")
            return

        try:
            with Image.open(path) as im:
                message = decode_image(im)

            if message is None:
                print("No valid PhotoCode V5 found.")
            else:
                print("HIDDEN MESSAGE:", message)
                print("CRC32: Verified")
                print("PhotoCode V5 decoded successfully!")

        except Exception as e:
            print("Decoding error:", str(e))

    else:
        print("Invalid option.")


if __name__ == "__main__":
    main()
