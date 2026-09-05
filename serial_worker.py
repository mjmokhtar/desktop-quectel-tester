"""
serial_worker.py — QThread pembaca port serial.
Membaca byte, memecah per baris, emit signal line_received(str).
Prompt '>' (tanpa newline, dari QMTPUBEX/QMTPUB) di-emit khusus lewat prompt_received.
"""

import time
import serial
from PyQt5.QtCore import QThread, pyqtSignal


class SerialWorker(QThread):
    line_received = pyqtSignal(str)
    prompt_received = pyqtSignal()
    error = pyqtSignal(str)
    connected = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ser = None
        self._running = False
        self._port = ""
        self._baud = 115200

    # ── kontrol dari main thread ──────────────────────────────────
    def open(self, port: str, baud: int) -> bool:
        try:
            self._ser = serial.Serial(port, baud, timeout=0.05)
        except serial.SerialException as e:
            self.error.emit(f"Gagal buka {port}: {e}")
            return False
        self._port, self._baud = port, baud
        self._running = True
        self.start()
        self.connected.emit(True)
        return True

    def close(self):
        self._running = False
        self.wait(500)
        if self._ser and self._ser.is_open:
            self._ser.close()
        self._ser = None
        self.connected.emit(False)

    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open

    def write(self, data: str, newline: bool = True):
        if not self.is_open():
            self.error.emit("Port belum terbuka")
            return
        try:
            self._ser.write(data.encode("utf-8") + (b"\r\n" if newline else b""))
        except serial.SerialException as e:
            self.error.emit(f"Gagal kirim: {e}")

    def write_raw(self, data: bytes):
        if self.is_open():
            self._ser.write(data)

    # ── loop baca ─────────────────────────────────────────────────
    def run(self):
        buf = b""
        while self._running and self._ser and self._ser.is_open:
            try:
                chunk = self._ser.read(256)
            except serial.SerialException as e:
                self.error.emit(f"Port terputus: {e}")
                self._running = False
                self.connected.emit(False)
                break
            if not chunk:
                # prompt '>' tidak diikuti newline — deteksi saat buffer diam
                if buf.strip() == b">":
                    self.prompt_received.emit()
                    buf = b""
                continue
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                text = line.decode("utf-8", errors="replace").strip("\r").strip()
                if text:
                    self.line_received.emit(text)
            time.sleep(0.005)