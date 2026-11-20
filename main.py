import os, io, json, time, threading
from datetime import datetime


def _ak_trace(stage):
    try:
        os.write(2, ("AKPC_TRACE:" + stage + "\n").encode())
    except Exception:
        pass

_ak_trace("PYTHON_ENTRY_REACHED")

_ak_trace("BEFORE_1_4")
from kivy.app import App
_ak_trace("AFTER_1_4")
_ak_trace("BEFORE_2_5")
from kivy.clock import Clock
_ak_trace("AFTER_2_5")
_ak_trace("BEFORE_3_6")
from kivy.metrics import dp, sp
_ak_trace("AFTER_3_6")
_ak_trace("BEFORE_4_7")
from kivy.core.window import Window
_ak_trace("AFTER_4_7")
_ak_trace("BEFORE_5_8")
from kivy.uix.screenmanager import ScreenManager, Screen
_ak_trace("AFTER_5_8")
_ak_trace("BEFORE_6_9")
from kivy.uix.boxlayout import BoxLayout
_ak_trace("AFTER_6_9")
_ak_trace("BEFORE_7_10")
from kivy.uix.gridlayout import GridLayout
_ak_trace("AFTER_7_10")
_ak_trace("BEFORE_8_11")
from kivy.uix.scrollview import ScrollView
_ak_trace("AFTER_8_11")
_ak_trace("BEFORE_9_12")
from kivy.uix.label import Label
_ak_trace("AFTER_9_12")
_ak_trace("BEFORE_10_13")
from kivy.uix.button import Button
_ak_trace("AFTER_10_13")
_ak_trace("BEFORE_11_14")
from kivy.uix.textinput import TextInput
_ak_trace("AFTER_11_14")
_ak_trace("BEFORE_12_15")
from kivy.uix.image import Image as KivyImage
_ak_trace("AFTER_12_15")
_ak_trace("BEFORE_13_16")
from kivy.graphics import Color, RoundedRectangle, Line
_ak_trace("AFTER_13_16")

# Native Android logging is initialized only after all Kivy imports.
_AK_ANDROID_LOG = None
try:
    from jnius import autoclass
    _AK_ANDROID_LOG = autoclass("android.util.Log")
    _AK_ANDROID_LOG.i("AKPhotoCode", "AKPC_NATIVE_TRACE_READY")
except Exception:
    _AK_ANDROID_LOG = None

def _ak_native_trace(stage):
    try:
        if _AK_ANDROID_LOG is not None:
            _AK_ANDROID_LOG.i("AKPhotoCode", "AKPC_TRACE:" + str(stage))
    except Exception:
        pass


BG = (0.008, 0.018, 0.043, 1)
PANEL = (0.018, 0.065, 0.11, 1)
PANEL2 = (0.025, 0.105, 0.17, 1)
CYAN = (0.0, 0.82, 1, 1)
WHITE = (0.9, 0.96, 1, 1)
MUTED = (0.48, 0.65, 0.76, 1)
GREEN = (0.12, 0.9, 0.6, 1)
RED = (1, 0.3, 0.36, 1)


class NeonButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = WHITE
        self.bold = True
        self.font_size = sp(15)
        with self.canvas.before:
            self.bg_color = Color(*PANEL2)
            self.bg_rect = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[dp(10)]
            )
            self.border_color = Color(*CYAN)
            self.border = Line(
                rounded_rectangle=(
                    self.x, self.y, self.width, self.height, dp(10)
                ), width=1.1
            )
        self.bind(pos=self.draw_shape, size=self.draw_shape)

    def draw_shape(self, *_):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border.rounded_rectangle = (
            self.x, self.y, self.width, self.height, dp(10)
        )


class PhotoCodeApp(App):
    # Load the NumPy-based V5 engine only when the user actually creates
    # or scans a PhotoCode. This keeps native NumPy initialization out of
    # the Android application startup path.
    def get_engine(self):
        if not hasattr(self, "_photocode_engine"):
            import importlib
            self._photocode_engine = importlib.import_module("photocode_v5")
        return self._photocode_engine

    def build(self):
        _ak_native_trace("BUILD_ENTERED")
        self.title = "AK PhotoCode"
        _ak_native_trace("BEFORE_WINDOW")
        Window.clearcolor = BG
        _ak_native_trace("AFTER_WINDOW")

        self.history_file = os.path.join(self.user_data_dir, "activity.json")
        self.saved_file = os.path.join(self.user_data_dir, "saved.json")
        _ak_native_trace("BEFORE_STORAGE")
        os.makedirs(self.user_data_dir, exist_ok=True)
        _ak_native_trace("AFTER_STORAGE")

        self.history = self.load_json(self.history_file, [])
        self.saved = self.load_json(self.saved_file, [])
        self.create_path = None
        self.scan_path = None
        self.last_saved_uri = None
        self.last_saved_path = None
        self.last_result = ""

        _ak_native_trace("BEFORE_SCREENMANAGER")
        self.sm = ScreenManager()
        _ak_native_trace("AFTER_SCREENMANAGER")
        self._built_screens = {"home"}
        _ak_native_trace("BEFORE_BUILD_HOME")
        self.build_home()
        _ak_native_trace("AFTER_BUILD_HOME")
        self.sm.current = "home"
        _ak_native_trace("BUILD_COMPLETE")
        return self.sm

    # ---------- STORAGE AND HISTORY ----------

    def load_json(self, path, default):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def write_json(self, path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def record(self, action, filename, status="Success"):
        self.history.insert(0, {
            "action": action,
            "filename": filename,
            "status": status,
            "time": datetime.now().strftime("%d %b %Y, %I:%M %p")
        })
        self.history = self.history[:100]
        self.write_json(self.history_file, self.history)

    # ---------- COMMON UI ----------

    def label(self, text, size=14, color=WHITE, height=48, bold=False):
        w = Label(
            text=text, font_size=sp(size), color=color, bold=bold,
            halign="left", valign="middle",
            size_hint_y=None, height=dp(height)
        )
        w.bind(size=lambda obj, val: setattr(obj, "text_size", (val[0], None)))
        return w

    def button(self, text, callback, height=52):
        b = NeonButton(text=text, size_hint_y=None, height=dp(height))
        b.bind(on_release=lambda *_: callback())
        return b

    def text_input(self, hint, multiline=False, height=52):
        return TextInput(
            hint_text=hint,
            multiline=multiline,
            size_hint_y=None,
            height=dp(height),
            background_normal="",
            background_active="",
            background_color=(0.015, 0.04, 0.075, 1),
            foreground_color=WHITE,
            hint_text_color=MUTED,
            cursor_color=CYAN,
            padding=dp(12)
        )

    def page(self, name, heading):
        screen = Screen(name=name)
        root = BoxLayout(
            orientation="vertical", padding=dp(14), spacing=dp(9)
        )

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(48), spacing=dp(8)
        )
        header.add_widget(self.button("‹ HOME", self.go_home, 42))
        header.add_widget(Label(
            text=heading, color=CYAN, bold=True, font_size=sp(18),
            halign="right"
        ))
        root.add_widget(header)

        scroll = ScrollView()
        body = BoxLayout(
            orientation="vertical", spacing=dp(11),
            padding=(dp(2), dp(5)), size_hint_y=None
        )
        body.bind(minimum_height=body.setter("height"))
        scroll.add_widget(body)
        root.add_widget(scroll)

        screen.add_widget(root)
        self.sm.add_widget(screen)
        return body

    def go_home(self):
        self.sm.current = "home"

    def open_page(self, name):
        if name not in self._built_screens:
            builders = {
                "create": self.build_create,
                "scan": self.build_scan,
                "recent": self.build_recent,
                "saved": self.build_saved,
                "settings": self.build_settings,
                "about": self.build_about,
            }
            builder = builders.get(name)
            if builder is None:
                raise ValueError("Unknown page: " + str(name))
            builder()
            self._built_screens.add(name)

        self.sm.current = name
        if name == "recent":
            self.refresh_recent()
        elif name == "saved":
            self.refresh_saved()

    # ---------- HOME DASHBOARD ----------

    def build_home(self):
        body = self.page("home", "AK PHOTO CODE")

        body.add_widget(self.label(
            "AK • PHOTO CODE 5 ENGINE  |  HOLOGRAPHIC INTERFACE",
            11, CYAN, 30, True
        ))
        body.add_widget(self.label(
            "Move Beyond QR Codes. Turn Your Personal Photos into Hidden Message Carriers.",
            20, WHITE, 125, True
        ))
        body.add_widget(self.label(
            "YOUR PHOTOS. YOUR HIDDEN MESSAGES.",
            12, MUTED, 32, True
        ))

        grid = GridLayout(
            cols=2, spacing=dp(10), size_hint_y=None
        )
        grid.bind(minimum_height=grid.setter("height"))

        choices = [
            ("✦  CREATE\nPHOTOCODE", "create"),
            ("⌕  SCAN\nPHOTOCODE", "scan"),
            ("◷  RECENT\nACTIVITY", "recent"),
            ("▣  SAVED\nPHOTOCODES", "saved"),
            ("⚙  SETTINGS", "settings"),
            ("ⓘ  ABOUT", "about")
        ]
        for text, target in choices:
            grid.add_widget(
                self.button(text, lambda t=target: self.open_page(t), 82)
            )
        body.add_widget(grid)

        body.add_widget(self.label(
            "PRIVATE MESSAGES • HIDDEN IN PHOTOS",
            12, CYAN, 40, True
        ))
        body.add_widget(self.label(
            "Create a PhotoCode, share it, and let another AK PhotoCode "
            "user recover the hidden message.",
            13, MUTED, 65
        ))

    # ---------- GALLERY AND IMAGE LOADING ----------

    def choose_image(self, purpose):
        def selected(paths):
            if not paths:
                return
            path = paths[0]
            if purpose == "create":
                self.create_path = path
                self.create_preview.text = "Selected: " + os.path.basename(path)
                self.show_preview(path, self.create_image_preview)
            else:
                self.scan_path = path
                self.scan_preview.text = "Selected: " + os.path.basename(path)
                self.show_preview(path, self.scan_image_preview)

        try:
            from plyer import filechooser
            filechooser.open_file(
                on_selection=selected,
                filters=["image"]
            )
        except Exception as e:
            self.set_status(purpose, "Gallery error: " + str(e), False)

    def load_image(self, path):
        from PIL import Image
        if path.startswith("content://"):
            from jnius import autoclass, jarray
            Activity = autoclass("org.kivy.android.PythonActivity")
            BAOS = autoclass("java.io.ByteArrayOutputStream")
            Uri = autoclass("android.net.Uri")
            activity = Activity.mActivity
            stream = activity.getContentResolver().openInputStream(
                Uri.parse(path)
            )
            if stream is None:
                raise RuntimeError("Unable to open selected image.")
            output = BAOS()
            buf = jarray("b", [0] * 32768)
            while True:
                count = stream.read(buf)
                if count == -1:
                    break
                output.write(buf, 0, count)
            stream.close()
            raw = bytes(output.toByteArray())
            return Image.open(io.BytesIO(raw)).convert("RGB")

        return Image.open(path).convert("RGB")

    def show_preview(self, path, widget):
        try:
            img = self.load_image(path)
            output = io.BytesIO()
            img.thumbnail((900, 900))
            img.save(output, format="PNG")
            output.seek(0)
            widget.texture = self.texture_from_bytes(output)
        except Exception:
            widget.texture = None

    def texture_from_bytes(self, stream):
        from kivy.core.image import Image as CoreImage
        return CoreImage(stream, ext="png").texture

    # ---------- CREATE PHOTOCODE ----------

    def build_create(self):
        body = self.page("create", "CREATE PHOTOCODE")

        body.add_widget(self.label(
            "Choose an image and enter the message to hide.",
            14, MUTED, 48
        ))
        body.add_widget(self.button(
            "SELECT PHOTO FROM GALLERY",
            lambda: self.choose_image("create")
        ))
        self.create_preview = self.label("No image selected", 13, CYAN, 38)
        body.add_widget(self.create_preview)

        self.create_image_preview = KivyImage(
            size_hint_y=None, height=dp(190), allow_stretch=True,
            keep_ratio=True
        )
        body.add_widget(self.create_image_preview)

        self.message_box = self.text_input(
            "Enter your private message...", True, 125
        )
        self.message_box.bind(text=self.update_counter)
        body.add_widget(self.message_box)

        self.counter = self.label(
            "Characters: 0  |  UTF-8 bytes: 0",
            12, CYAN, 30
        )
        body.add_widget(self.counter)

        self.create_status = self.label(
            "Ready to create PhotoCode.", 13, MUTED, 55
        )
        body.add_widget(self.create_status)

        body.add_widget(self.button(
            "GENERATE PHOTOCODE", self.generate
        ))
        body.add_widget(self.button(
            "SHARE LAST CREATED IMAGE", self.share_last_image
        ))

    def update_counter(self, *_):
        text = self.message_box.text
        self.counter.text = (
            "Characters: " + str(len(text)) +
            "  |  UTF-8 bytes: " + str(len(text.encode("utf-8")))
        )

    def generate(self):
        if not self.create_path:
            self.set_status("create", "Select a photo first.", False)
            return
        message = self.message_box.text.strip()
        if not message:
            self.set_status("create", "Enter a message first.", False)
            return

        self.create_status.text = "Encoding PhotoCode..."
        self.create_status.color = CYAN
        threading.Thread(
            target=self.generate_worker,
            args=(self.create_path, message),
            daemon=True
        ).start()

    def generate_worker(self, path, message):
        try:
            source = self.load_image(path)
            engine = self.get_engine()
            result, byte_count = engine.encode_image(source, message)
            output = io.BytesIO()
            result.save(output, format="JPEG", quality=95)
            data = output.getvalue()

            filename = "AK_PhotoCode_" + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            ) + ".jpg"

            saved = self.save_public_image(data, filename)
            if not saved:
                raise RuntimeError("Unable to save generated image.")

            Clock.schedule_once(
                lambda dt: self.generate_finished(
                    filename, byte_count, saved
                ), 0
            )
        except Exception as e:
            error = str(e)
            Clock.schedule_once(
                lambda dt: self.set_status("create", error, False), 0
            )

    def save_public_image(self, data, filename):
        # Android MediaStore: visible in Pictures/AK PhotoCode.
        try:
            from jnius import autoclass, jarray
            Activity = autoclass("org.kivy.android.PythonActivity")
            ContentValues = autoclass("android.content.ContentValues")
            MediaStore = autoclass("android.provider.MediaStore")
            activity = Activity.mActivity
            resolver = activity.getContentResolver()

            values = ContentValues()
            values.put("display_name", filename)
            values.put("mime_type", "image/jpeg")
            values.put("relative_path", "Pictures/AK PhotoCode")

            uri = resolver.insert(
                MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values
            )
            if uri is None:
                raise RuntimeError("MediaStore insert failed.")

            stream = resolver.openOutputStream(uri)
            if stream is None:
                raise RuntimeError("Unable to open output stream.")

            signed = jarray(
                "b", [b if b < 128 else b - 256 for b in data]
            )
            stream.write(signed)
            stream.flush()
            stream.close()
            return {"uri": str(uri.toString()), "path": None}
        except Exception:
            # Private-storage fallback, clearly identified in the UI.
            folder = os.path.join(self.user_data_dir, "PhotoCode")
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, filename)
            with open(path, "wb") as f:
                f.write(data)
            return {"uri": None, "path": path}

    def generate_finished(self, filename, byte_count, saved):
        self.last_saved_uri = saved.get("uri")
        self.last_saved_path = saved.get("path")

        item = {
            "filename": filename,
            "uri": self.last_saved_uri,
            "path": self.last_saved_path
        }
        self.saved.insert(0, item)
        self.saved = self.saved[:100]
        self.write_json(self.saved_file, self.saved)
        self.record("Created PhotoCode", filename)

        location = (
            "Pictures/AK PhotoCode"
            if self.last_saved_uri
            else "App private storage"
        )
        self.set_status(
            "create",
            "PhotoCode created successfully!\n"
            + str(byte_count) + " message bytes encoded.\n"
            + "Saved to: " + location,
            True
        )

    # ---------- SHARE IMAGE ----------

    def share_uri(self, uri):
        from jnius import autoclass
        Activity = autoclass("org.kivy.android.PythonActivity")
        Intent = autoclass("android.content.Intent")
        Uri = autoclass("android.net.Uri")
        activity = Activity.mActivity
        intent = Intent(Intent.ACTION_SEND)
        intent.setType("image/jpeg")
        intent.putExtra(Intent.EXTRA_STREAM, Uri.parse(uri))
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        chooser = Intent.createChooser(intent, "Share PhotoCode")
        activity.startActivity(chooser)

    def share_last_image(self):
        if not self.last_saved_uri:
            self.create_status.text = (
                "No shareable public image is available. "
                "A private-storage fallback cannot be shared directly."
            )
            return
        try:
            self.share_uri(self.last_saved_uri)
        except Exception as e:
            self.set_status("create", "Share failed: " + str(e), False)

    # ---------- SCAN PHOTOCODE ----------

    def build_scan(self):
        body = self.page("scan", "SCAN PHOTOCODE")

        body.add_widget(self.label(
            "Select a PhotoCode image to recover its hidden message.",
            14, MUTED, 55
        ))
        body.add_widget(self.button(
            "SELECT IMAGE FROM GALLERY",
            lambda: self.choose_image("scan")
        ))

        self.scan_preview = self.label("No image selected", 13, CYAN, 38)
        body.add_widget(self.scan_preview)

        self.scan_image_preview = KivyImage(
            size_hint_y=None, height=dp(190),
            allow_stretch=True, keep_ratio=True
        )
        body.add_widget(self.scan_image_preview)

        self.scan_status = self.label(
            "Ready to scan.", 13, MUTED, 55
        )
        body.add_widget(self.scan_status)

        body.add_widget(self.button(
            "SCAN AND DECODE", self.scan
        ))

        self.result_box = self.text_input(
            "Recovered message appears here...", True, 125
        )
        self.result_box.readonly = True
        body.add_widget(self.result_box)

        body.add_widget(self.button(
            "COPY RECOVERED MESSAGE", self.copy_result
        ))
        body.add_widget(self.button(
            "SHARE RECOVERED MESSAGE", self.share_text
        ))

    def scan(self):
        if not self.scan_path:
            self.set_status("scan", "Select an image first.", False)
            return

        self.result_box.text = ""
        self.scan_status.text = "Scanning and decoding..."
        self.scan_status.color = CYAN

        threading.Thread(
            target=self.scan_worker,
            args=(self.scan_path,),
            daemon=True
        ).start()

    def scan_worker(self, path):
        start = time.perf_counter()
        try:
            source = self.load_image(path)
            engine = self.get_engine()
            message = engine.decode_image(source)
            elapsed = time.perf_counter() - start
            Clock.schedule_once(
                lambda dt: self.scan_finished(
                    message, elapsed, path
                ), 0
            )
        except Exception as e:
            error = str(e)
            Clock.schedule_once(
                lambda dt: self.set_status("scan", error, False), 0
            )

    def scan_finished(self, message, elapsed, path):
        filename = os.path.basename(path)

        if message is None:
            self.result_box.text = ""
            self.set_status(
                "scan",
                "No valid PhotoCode detected.\n"
                "Try the original generated PhotoCode image.",
                False
            )
            self.record("Scan failed", filename, "No valid code")
            return

        self.last_result = message
        self.result_box.text = message
        self.set_status(
            "scan",
            "Message recovered successfully!\n"
            "Decode time: " + "{:.3f}".format(elapsed) + " seconds",
            True
        )
        self.record("Scanned PhotoCode", filename)

    def copy_result(self):
        if not self.result_box.text:
            self.set_status("scan", "No message to copy.", False)
            return
        try:
            from kivy.core.clipboard import Clipboard
            Clipboard.copy(self.result_box.text)
            self.set_status("scan", "Message copied.", True)
        except Exception as e:
            self.set_status("scan", "Copy failed: " + str(e), False)

    def share_text(self):
        if not self.result_box.text:
            self.set_status("scan", "No message to share.", False)
            return
        try:
            from jnius import autoclass
            Activity = autoclass("org.kivy.android.PythonActivity")
            Intent = autoclass("android.content.Intent")
            activity = Activity.mActivity
            intent = Intent(Intent.ACTION_SEND)
            intent.setType("text/plain")
            intent.putExtra(Intent.EXTRA_TEXT, self.result_box.text)
            activity.startActivity(
                Intent.createChooser(intent, "Share recovered message")
            )
        except Exception as e:
            self.set_status("scan", "Share failed: " + str(e), False)

    # ---------- RECENT ACTIVITY ----------

    def build_recent(self):
        self.recent_body = self.page("recent", "RECENT ACTIVITY")
        self.refresh_recent()

    def refresh_recent(self):
        body = self.recent_body
        body.clear_widgets()
        body.add_widget(self.label(
            "Your latest PhotoCode actions", 14, MUTED, 42
        ))

        if not self.history:
            body.add_widget(self.label(
                "No activity yet.", 14, MUTED, 55
            ))

        for item in self.history:
            body.add_widget(self.label(
                item.get("action", "") + "\n" +
                item.get("filename", "") + "\n" +
                item.get("time", "") + " • " +
                item.get("status", ""),
                13, WHITE, 82
            ))

        body.add_widget(self.button(
            "CLEAR ACTIVITY HISTORY", self.clear_history
        ))

    def clear_history(self):
        self.history = []
        self.write_json(self.history_file, [])
        # Refresh only when the lazy-loaded screen exists.
        if hasattr(self, "recent_body"):
            self.refresh_recent()

    # ---------- SAVED PHOTOCODES ----------

    def build_saved(self):
        self.saved_body = self.page("saved", "SAVED PHOTOCODES")
        self.refresh_saved()

    def refresh_saved(self):
        body = self.saved_body
        body.clear_widgets()
        body.add_widget(self.label(
            "Generated PhotoCode images", 14, MUTED, 42
        ))

        if not self.saved:
            body.add_widget(self.label(
                "No saved PhotoCodes yet.", 14, MUTED, 55
            ))

        for index, item in enumerate(self.saved):
            body.add_widget(self.label(
                item.get("filename", "PhotoCode"), 13, WHITE, 40
            ))
            row = BoxLayout(
                size_hint_y=None, height=dp(45), spacing=dp(7)
            )
            row.add_widget(self.button(
                "SCAN",
                lambda x=item: self.scan_saved(x),
                42
            ))
            row.add_widget(self.button(
                "SHARE",
                lambda x=item: self.share_saved(x),
                42
            ))
            row.add_widget(self.button(
                "REMOVE",
                lambda i=index: self.remove_saved(i),
                42
            ))
            body.add_widget(row)

    def scan_saved(self, item):
        self.scan_path = item.get("uri") or item.get("path")
        if not self.scan_path:
            return
        self.open_page("scan")
        self.scan_preview.text = item.get("filename", "Saved PhotoCode")
        self.scan()

    def share_saved(self, item):
        uri = item.get("uri")
        if not uri:
            self.saved_body.add_widget(self.label(
                "This image is in private app storage and cannot be "
                "shared directly by this version.",
                12, RED, 65
            ))
            return
        try:
            self.share_uri(uri)
        except Exception as e:
            self.saved_body.add_widget(self.label(
                "Share failed: " + str(e), 12, RED, 55
            ))

    def remove_saved(self, index):
        if 0 <= index < len(self.saved):
            self.saved.pop(index)
            self.write_json(self.saved_file, self.saved)
            self.refresh_saved()

    # ---------- SETTINGS ----------

    def build_settings(self):
        body = self.page("settings", "SETTINGS")
        body.add_widget(self.label(
            "APPLICATION SETTINGS", 17, CYAN, 45, True
        ))
        body.add_widget(self.label(
            "Engine: PhotoCode V5\n"
            "Interface: Dark holographic theme\n"
            "Image processing: On device\n"
            "Activity history: Local app storage\n"
            "Saved list: Local app storage",
            14, WHITE, 125
        ))
        body.add_widget(self.label(
            "Privacy: The activity log stores action names, filenames "
            "and timestamps. It does not store hidden message contents.",
            13, MUTED, 75
        ))
        body.add_widget(self.button(
            "CLEAR ACTIVITY HISTORY", self.clear_history
        ))
        body.add_widget(self.button(
            "OPEN SAVED PHOTOCODES", lambda: self.open_page("saved")
        ))
        body.add_widget(self.button(
            "BACK TO HOME", self.go_home
        ))

    # ---------- ABOUT ----------

    def build_about(self):
        body = self.page("about", "ABOUT AK PHOTO CODE")
        body.add_widget(self.label(
            "AK PHOTO CODE", 25, CYAN, 60, True
        ))
        body.add_widget(self.label(
            "Move Beyond QR Codes. Turn Your Personal Photos into Hidden Message Carriers.",
            16, WHITE, 110, True
        ))
        body.add_widget(self.label(
            "AK PhotoCode uses the PhotoCode V5 engine to encode "
            "messages into photographs and recover them from "
            "PhotoCode images.\n\n"
            "Created by AK-YASIR.\n\n"
            "Version: 1.0.0",
            14, MUTED, 145
        ))

    # ---------- STATUS ----------

    def set_status(self, page, message, success=True):
        color = GREEN if success else RED
        if page == "create":
            self.create_status.text = message
            self.create_status.color = color
        else:
            self.scan_status.text = message
            self.scan_status.color = color


if __name__ == "__main__":
    PhotoCodeApp().run()
