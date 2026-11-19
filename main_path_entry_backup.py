import os
from PIL import Image
import photocode_v5 as engine
from plyer import filechooser

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window

Window.clearcolor = (0.035, 0.045, 0.07, 1)


class PhotoCodeApp(App):

    def build(self):
        self.image_path = None

        root = BoxLayout(
            orientation="vertical",
            padding=25,
            spacing=18
        )

        root.add_widget(Label(
            text="[b]AK's PhotoCode[/b]",
            markup=True,
            font_size="30sp",
            size_hint_y=None,
            height=85
        ))

        root.add_widget(Label(
            text="Your photograph. Your hidden message.",
            font_size="15sp",
            size_hint_y=None,
            height=45
        ))

        self.status = Label(
            text="Choose a PhotoCode image to begin.",
            font_size="15sp",
            size_hint_y=None,
            height=65
        )
        root.add_widget(self.status)

        choose = Button(
            text="CHOOSE PHOTO FROM GALLERY",
            size_hint_y=None,
            height=65
        )
        choose.bind(on_release=self.choose_image)
        root.add_widget(choose)

        self.scan_button = Button(
            text="SCAN PHOTO CODE",
            size_hint_y=None,
            height=65,
            disabled=True
        )
        self.scan_button.bind(on_release=self.scan_image)
        root.add_widget(self.scan_button)

        self.result = Label(
            text="Decoded message will appear here.",
            font_size="18sp",
            halign="center",
            valign="middle"
        )
        root.add_widget(self.result)

        again = Button(
            text="SCAN ANOTHER IMAGE",
            size_hint_y=None,
            height=55
        )
        again.bind(on_release=self.reset)
        root.add_widget(again)

        return root

    def choose_image(self, instance):
        self.status.text = "Opening gallery..."
        try:
            filechooser.open_file(
                on_selection=self.on_image_selected,
                filters=["image"]
            )
        except Exception as error:
            self.status.text = "Picker error: " + str(error)

    def on_image_selected(self, selection):
        if not selection:
            self.status.text = "No image selected."
            return

        self.image_path = selection[0]
        self.status.text = "Selected: " + os.path.basename(
            self.image_path
        )
        self.scan_button.disabled = False
        self.result.text = "Ready to scan!"

    def scan_image(self, instance):
        if not self.image_path:
            return

        self.status.text = "Scanning photograph..."
        self.result.text = "Please wait..."

        try:
            with Image.open(self.image_path) as img:
                img.load()
                message = engine.decode_image(img)

            if message is None:
                self.result.text = "No valid PhotoCode found."
            else:
                if isinstance(message, bytes):
                    message = message.decode(
                        "utf-8", errors="replace"
                    )

                self.result.text = (
                    "[b]DECODED MESSAGE[/b]\n\n" + message
                )
                self.result.markup = True
                self.status.text = "PhotoCode successfully scanned!"

        except Exception as error:
            self.result.text = "Scan error: " + str(error)

    def reset(self, instance):
        self.image_path = None
        self.scan_button.disabled = True
        self.status.text = "Choose another PhotoCode image."
        self.result.text = "Ready for another scan."


if __name__ == "__main__":
    PhotoCodeApp().run()
