#!/usr/bin/python3
# SPDX-License-Identifier: MIT

import io
import threading
import subprocess

import serial
import PIL.Image
import PIL.ImageOps

from phomemo.print_p12 import header, print_image, tape_feed, preprocess_image, DummySerial
from phomemo.render_label import cairo_context_init, render_text, crop_rendered_text, calc_y_offset

_printer_lock = threading.Lock()


class PrinterConnection:
    """Manages serial port state and provides print/render methods."""

    def __init__(self):
        self.port_path = None
        self.dots = 96
        self._serial = None

    def configure(self, port_path, dots=96):
        self.close()
        self.port_path = port_path
        self.dots = dots

    def _get_port(self):
        if not self.port_path:
            raise RuntimeError("Printer port not configured")
        if self.port_path == "dummy":
            return DummySerial(self.dots)
        if self._serial is None or not self._serial.is_open:
            self._serial = serial.Serial(self.port_path, timeout=10)
        return self._serial

    def close(self):
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None

    def render_text_to_image(self, text, font="", font_size=0, font_weight="NORMAL",
                             font_slant="NORMAL", margin=8, offset=0):
        """Render text to a PIL Image ready for printing.

        Replicates the flow from render_label.py main() lines 101-121.
        """
        surface_w = 32767
        surface_h = self.dots - margin

        if font_size == 0:
            font_size = surface_h

        cr = cairo_context_init(surface_w, surface_h, font, font_size, font_slant, font_weight)
        render_text(cr, text)
        cropped = crop_rendered_text(cr, text)
        y_offset = calc_y_offset(cr, text, font, font_size)
        y_offset -= offset

        resized = PIL.Image.new('1', cropped.size, 0)
        resized.paste(cropped, (0, y_offset))
        rot = resized.rotate(270, expand=True)

        return rot

    def prepare_uploaded_image(self, image_bytes):
        """Convert uploaded image bytes to a print-ready PIL Image.

        Reimplements preprocess_image logic with corrected crop() call.
        """
        width = self.dots
        with PIL.Image.open(io.BytesIO(image_bytes)) as src:
            src_w, src_h = src.size
            if src_w > width:
                resized = src.crop((0, 0, width, src_h))
            elif src_w < width:
                resized = PIL.Image.new('1', (width, src_h), 1)
                resized.paste(src, (width - src_w, 0))
            else:
                resized = src.copy()
            return PIL.ImageOps.invert(resized.convert("RGB")).convert("1")

    def print_label(self, image):
        """Thread-safe print: header, print_image, tape_feed."""
        with _printer_lock:
            port = self._get_port()
            header(port)
            print_image(port, image)
            tape_feed(port)

    @staticmethod
    def list_fonts():
        """List available system font family names using fc-list."""
        try:
            result = subprocess.run(
                ["fc-list", "--format", "%{family}\n"],
                capture_output=True, text=True, timeout=10
            )
            raw = result.stdout.strip().split("\n")
            # fc-list may return "Family1,Family2" for aliases; take first
            families = set()
            for line in raw:
                if line.strip():
                    families.add(line.strip().split(",")[0].strip())
            return sorted(families)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return ["sans-serif", "serif", "monospace"]
