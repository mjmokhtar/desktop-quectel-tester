"""
main.py — EC25-E AT Command Tester (PyQt5)

Jalankan:  python main.py
Port AT EC25 di Windows biasanya "Quectel USB AT Port" (COMx).
"""

import json
import os
import sys
from datetime import datetime

import serial.tools.list_ports
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont, QTextCursor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QComboBox, QPushButton, QLabel, QLineEdit, QTextEdit, QGroupBox, QScrollArea,
    QMessageBox, QFileDialog, QFormLayout, QSplitter, QCheckBox, QSizePolicy,
)

import commands as C
from parsers import parse_line
from serial_worker import SerialWorker

SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    "port": "", "baud": "115200", "apn": "internet",
    "host": "", "port_mqtt": "1883", "client_id": "AT-TESTER",
    "user": "", "pass": "", "topic": "test/topic",
}

# Warna log
CLR_TX   = QColor("#4fc3f7")   # biru
CLR_OK   = QColor("#81c784")   # hijau
CLR_ERR  = QColor("#e57373")   # merah
CLR_URC  = QColor("#ffb74d")   # oranye
CLR_INFO = QColor("#b0bec5")   # abu
CLR_RX   = QColor("#eeeeee")


class HelpDialog(QMessageBox):
    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Help — {item['label']}")
        self.setIcon(QMessageBox.Information)
        self.setText(f"<b>{item['cmd']}</b>")
        self.setInformativeText(item["help"])
        self.setStandardButtons(QMessageBox.Ok)
        self.setStyleSheet("QLabel{min-width:520px; font-family:Consolas,monospace;}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EC25-E AT Command Tester")
        self.resize(1200, 760)

        self.settings = self._load_settings()
        self.worker = SerialWorker()
        self.worker.line_received.connect(self.on_line)
        self.worker.prompt_received.connect(self.on_prompt)
        self.worker.error.connect(lambda m: self.log(m, CLR_ERR))
        self.worker.connected.connect(self.on_connected)

        self.pending_key = None          # preset yang sedang menunggu respons
        self.pending_wait = None
        self.pending_payload = None      # payload untuk dikirim setelah '>'
        self.buttons = {}                # key → QPushButton
        self._seq = []
        self._seq_running = False

        self._build_ui()
        self.refresh_ports()

    # ══════════════════════════════════════════════════════════════
    # UI
    # ══════════════════════════════════════════════════════════════
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        layout.addWidget(self._build_port_bar())

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_left_panel())
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([520, 680])
        layout.addWidget(splitter, 1)

    def _build_port_bar(self):
        box = QGroupBox("Port")
        h = QHBoxLayout(box)
        self.cb_port = QComboBox()
        self.cb_port.setMinimumWidth(320)
        self.cb_baud = QComboBox()
        self.cb_baud.addItems(["115200", "9600", "57600", "230400", "460800", "921600"])
        self.cb_baud.setCurrentText(self.settings["baud"])
        self.btn_refresh = QPushButton("Scan")
        self.btn_refresh.clicked.connect(self.refresh_ports)
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.clicked.connect(self.toggle_connect)
        self.lbl_state = QLabel("● Disconnected")
        self.lbl_state.setStyleSheet("color:#e57373; font-weight:bold;")
        h.addWidget(QLabel("Port:"))
        h.addWidget(self.cb_port)
        h.addWidget(QLabel("Baud:"))
        h.addWidget(self.cb_baud)
        h.addWidget(self.btn_refresh)
        h.addWidget(self.btn_connect)
        h.addWidget(self.lbl_state)
        h.addStretch()
        return box

    def _build_left_panel(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)

        # ── Settings ──
        gb = QGroupBox("Parameter (dipakai oleh preset)")
        f = QFormLayout(gb)
        self.ed = {}
        for key, label in [("apn", "APN"), ("host", "MQTT host"), ("port_mqtt", "MQTT port"),
                           ("client_id", "Client ID"), ("user", "User"), ("pass", "Password"),
                           ("topic", "Topic")]:
            e = QLineEdit(self.settings.get(key, ""))
            if key == "pass":
                e.setEchoMode(QLineEdit.Password)
            e.editingFinished.connect(self._save_settings)
            self.ed[key] = e
            f.addRow(label, e)
        v.addWidget(gb)

        # ── Preset buttons ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        iv = QVBoxLayout(inner)
        for title, items in C.GROUPS:
            g = QGroupBox(title)
            grid = QGridLayout(g)
            grid.setHorizontalSpacing(4)
            grid.setVerticalSpacing(4)
            for row, item in enumerate(items):
                btn = QPushButton(item["label"])
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                btn.setToolTip(item["cmd"])
                btn.clicked.connect(lambda _, k=item["key"]: self.send_preset(k))
                hb = QPushButton("?")
                hb.setFixedWidth(28)
                hb.clicked.connect(lambda _, it=item: HelpDialog(it, self).exec_())
                grid.addWidget(btn, row, 0)
                grid.addWidget(hb, row, 1)
                self.buttons[item["key"]] = btn
            iv.addWidget(g)
        iv.addStretch()
        scroll.setWidget(inner)
        v.addWidget(scroll, 1)

        # ── Run all ──
        h = QHBoxLayout()
        self.btn_runall = QPushButton("▶ Jalankan urutan firmware (1→5)")
        self.btn_runall.setToolTip("Kirim preset berurutan seperti lte_task di STM32, "
                                   "berhenti di command pertama yang gagal")
        self.btn_runall.clicked.connect(self.run_sequence)
        self.btn_reset = QPushButton("Reset warna")
        self.btn_reset.clicked.connect(self.reset_colors)
        h.addWidget(self.btn_runall, 1)
        h.addWidget(self.btn_reset)
        v.addLayout(h)
        return w

    def _build_right_panel(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)

        # ── Status hasil parse ──
        gb = QGroupBox("Status (hasil parse)")
        g = QGridLayout(gb)
        self.st = {}
        fields = [("net", "Network"), ("sig", "Signal"), ("op", "Operator / Band"),
                  ("ip", "PDP / IP"), ("gps", "GPS"), ("mqtt", "MQTT"), ("time", "Time")]
        for i, (k, lbl) in enumerate(fields):
            g.addWidget(QLabel(f"<b>{lbl}</b>"), i // 2, (i % 2) * 2)
            val = QLabel("—")
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            val.setMinimumWidth(240)
            self.st[k] = val
            g.addWidget(val, i // 2, (i % 2) * 2 + 1)
        v.addWidget(gb)

        # ── Log ──
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 10))
        self.log_view.setStyleSheet("background:#1e1e1e; color:#eee;")
        v.addWidget(self.log_view, 1)

        # ── Manual input ──
        h = QHBoxLayout()
        self.ed_cmd = QLineEdit()
        self.ed_cmd.setPlaceholderText("Ketik AT command manual, Enter untuk kirim")
        self.ed_cmd.setFont(QFont("Consolas", 10))
        self.ed_cmd.returnPressed.connect(self.send_manual)
        self.chk_crlf = QCheckBox("CR+LF")
        self.chk_crlf.setChecked(True)
        btn_send = QPushButton("Send")
        btn_send.clicked.connect(self.send_manual)
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.log_view.clear)
        btn_save = QPushButton("Save log")
        btn_save.clicked.connect(self.save_log)
        h.addWidget(self.ed_cmd, 1)
        h.addWidget(self.chk_crlf)
        h.addWidget(btn_send)
        h.addWidget(btn_clear)
        h.addWidget(btn_save)
        v.addLayout(h)
        return w

    # ══════════════════════════════════════════════════════════════
    # Port
    # ══════════════════════════════════════════════════════════════
    def refresh_ports(self):
        self.cb_port.clear()
        ports = sorted(serial.tools.list_ports.comports(), key=lambda p: p.device)
        pick = -1
        for i, p in enumerate(ports):
            desc = p.description or ""
            self.cb_port.addItem(f"{p.device}  —  {desc}", p.device)
            if p.device == self.settings["port"]:
                pick = i
            elif pick < 0 and "AT" in desc.upper() and "QUECTEL" in desc.upper():
                pick = i
        if pick >= 0:
            self.cb_port.setCurrentIndex(pick)
        if not ports:
            self.log("Tidak ada port serial. Cek driver Quectel di Device Manager.", CLR_ERR)

    def toggle_connect(self):
        if self.worker.is_open():
            self.worker.close()
            return
        port = self.cb_port.currentData()
        if not port:
            self.log("Pilih port dulu", CLR_ERR)
            return
        baud = int(self.cb_baud.currentText())
        if self.worker.open(port, baud):
            self.settings["port"], self.settings["baud"] = port, str(baud)
            self._save_settings()
            self.log(f"Terhubung {port} @ {baud}", CLR_INFO)

    def on_connected(self, ok):
        self.btn_connect.setText("Disconnect" if ok else "Connect")
        self.lbl_state.setText("● Connected" if ok else "● Disconnected")
        self.lbl_state.setStyleSheet(
            f"color:{'#81c784' if ok else '#e57373'}; font-weight:bold;")

    # ══════════════════════════════════════════════════════════════
    # Kirim
    # ══════════════════════════════════════════════════════════════
    def _settings_for_fill(self):
        return {"apn": self.ed["apn"].text(), "host": self.ed["host"].text(),
                "port": self.ed["port_mqtt"].text(), "client_id": self.ed["client_id"].text(),
                "user": self.ed["user"].text(), "pass": self.ed["pass"].text(),
                "topic": self.ed["topic"].text()}

    def send_manual(self):
        cmd = self.ed_cmd.text().strip()
        if not cmd:
            return
        self.pending_key = None
        self._tx(cmd, self.chk_crlf.isChecked())
        self.ed_cmd.clear()

    def send_preset(self, key):
        item = C.all_commands()[key]
        cmd = C.fill(item["cmd"], self._settings_for_fill())
        self.pending_key = key
        self.pending_wait = item["wait"]
        self.pending_payload = C.TEST_PAYLOAD if key == "qmtpubex" else None
        self.buttons[key].setStyleSheet("background:#455a64; color:white;")
        self._tx(cmd, True)

    def _tx(self, cmd, newline):
        if not self.worker.is_open():
            self.log("Port belum terhubung", CLR_ERR)
            return
        shown = cmd
        pw = self.ed["pass"].text()
        if pw and pw in shown:
            shown = shown.replace(pw, "****")
        self.log(f">> {shown}", CLR_TX)
        self.worker.write(cmd, newline)

    # ══════════════════════════════════════════════════════════════
    # Terima
    # ══════════════════════════════════════════════════════════════
    def on_prompt(self):
        self.log("<< >", CLR_OK)
        if self.pending_payload:
            self.log(f">> {self.pending_payload}", CLR_TX)
            self.worker.write(self.pending_payload, newline=False)
            self.pending_payload = None
            self.pending_wait = "+QMTPUBEX:"

    def on_line(self, line):
        color = CLR_RX
        up = line.upper()
        if line == "OK":
            color = CLR_OK
        elif "ERROR" in up:
            color = CLR_ERR
        elif line.startswith("+"):
            color = CLR_URC
        self.log(f"<< {line}", color)

        parsed = parse_line(line)
        if parsed:
            self._update_status(*parsed)

        # tandai tombol preset hijau/merah
        if self.pending_key:
            ok_hit = self.pending_wait and self.pending_wait in line
            fail = "ERROR" in up
            if parsed and "ok" in parsed[1]:
                ok_hit = parsed[1]["ok"]
                fail = not ok_hit
            if ok_hit or fail:
                btn = self.buttons[self.pending_key]
                btn.setStyleSheet("background:#2e7d32; color:white;" if ok_hit
                                  else "background:#c62828; color:white;")
                self.pending_key = None
                self._seq_step(ok_hit)

    def _update_status(self, kind, d):
        s = self.st
        if kind == "CEREG":
            s["net"].setText(f"{d['text']} (stat={d['stat']})")
            s["net"].setStyleSheet("color:#81c784" if d["ok"] else "color:#e57373")
        elif kind == "CSQ":
            cur = s["sig"].text()
            tail = cur.split("|", 1)[1] if "|" in cur else ""
            s["sig"].setText(f"RSSI {d['rssi']} ({d['dbm']} dBm) |{tail}")
        elif kind == "QCSQ":
            cur = s["sig"].text()
            head = cur.split("|", 1)[0] if "|" in cur else cur
            s["sig"].setText(f"{head}| RSRP {d['rsrp']}  SINR {d['sinr_db']:.0f} dB  RSRQ {d['rsrq']}")
        elif kind == "COPS":
            cur = s["op"].text()
            tail = cur.split("/", 1)[1] if "/" in cur else ""
            s["op"].setText(f"{d['operator']} /{tail}")
        elif kind == "QNWINFO":
            cur = s["op"].text()
            head = cur.split("/", 1)[0] if "/" in cur else cur
            s["op"].setText(f"{head}/ {d['band']}")
        elif kind == "QIACT":
            s["ip"].setText(f"ctx{d['ctx']} active, IP {d['ip']}")
            s["ip"].setStyleSheet("color:#81c784")
        elif kind == "QGPSLOC":
            s["gps"].setText(f"{d['lat']:.6f}, {d['lon']:.6f}  alt {d['alt']:.0f} m  "
                             f"sat {d['nsat']}  fix {d['fix']}D  hdop {d['hdop']}")
            s["gps"].setStyleSheet("color:#81c784")
        elif kind == "GGA":
            s["gps"].setText(f"satelit terlihat: {d['sat_in_view']}  (fix quality {d['fix_quality']})")
            s["gps"].setStyleSheet("color:#ffb74d")
        elif kind == "CME":
            code = d["code"]
            desc = C.CME_ERRORS.get(code, "lihat manual AT EC25")
            self.log(f"   ↳ CME {code}: {desc}", CLR_INFO)
            if code == "516":
                s["gps"].setText("belum fix (516) — tunggu…")
                s["gps"].setStyleSheet("color:#ffb74d")
        elif kind == "QMTOPEN":
            desc = C.QMTOPEN_RESULT.get(d["result"], "?")
            s["mqtt"].setText(f"open: {desc}")
            s["mqtt"].setStyleSheet("color:#81c784" if d["ok"] else "color:#e57373")
            if not d["ok"]:
                self.log(f"   ↳ QMTOPEN {d['result']}: {desc}", CLR_INFO)
        elif kind == "QMTCONN":
            if "ret" in d:
                desc = C.QMTCONN_RESULT.get(d["ret"], "?")
                s["mqtt"].setText(f"conn: {desc}")
                s["mqtt"].setStyleSheet("color:#81c784" if d["ok"] else "color:#e57373")
                if not d["ok"]:
                    self.log(f"   ↳ QMTCONN ret={d['ret']}: {desc}", CLR_INFO)
            else:
                state = {1: "initial", 2: "connecting", 3: "connected", 4: "disconnecting"}
                s["mqtt"].setText(f"state: {state.get(d['state'], d['state'])}")
        elif kind == "QMTPUB":
            s["mqtt"].setText("publish OK" if d["ok"] else f"publish gagal ({d['result']})")
            s["mqtt"].setStyleSheet("color:#81c784" if d["ok"] else "color:#e57373")
        elif kind == "QLTS":
            s["time"].setText(d["time"])
        elif kind == "QPING":
            if d["result"] == "0" and d["detail"].count(",") >= 3 and not d["detail"].startswith('"'):
                s["ip"].setText(s["ip"].text().split("  ping")[0] + "  ping OK")
            elif d["result"] != "0":
                self.log(f"   ↳ QPING {d['result']}: gagal (569 = timeout)", CLR_INFO)

    # ══════════════════════════════════════════════════════════════
    # Urutan otomatis
    # ══════════════════════════════════════════════════════════════
    SEQUENCE = ["at", "ate0", "cpin", "cereg", "csq", "qcsq", "cops", "qnwinfo",
                "qicsgp", "qiact", "qiactq", "gnsscfg", "outport", "qgps",
                "qmtopen", "qmtconn", "qmtpubex", "ctzu", "qlts"]

    def run_sequence(self):
        if not self.worker.is_open():
            self.log("Connect dulu", CLR_ERR)
            return
        self.reset_colors()
        self._seq = list(self.SEQUENCE)
        self._seq_running = True
        self.log("── Mulai urutan firmware ──", CLR_INFO)
        self._seq_next()

    def _seq_next(self):
        if not self._seq_running or not self._seq:
            self._seq_running = False
            self.log("── Urutan selesai ──", CLR_INFO)
            return
        key = self._seq.pop(0)
        self.send_preset(key)
        ms = 35000 if key == "qiact" else 12000     # QIACT bisa lama
        QTimer.singleShot(ms, lambda k=key: self._seq_timeout(k))

    def _seq_step(self, ok):
        """Dipanggil on_line setelah preset selesai (hijau/merah)."""
        if not self._seq_running:
            return
        if ok:
            QTimer.singleShot(300, self._seq_next)
        else:
            self._seq_running = False
            self.log("── Urutan berhenti: command gagal. Klik '?' di tombol merah. ──", CLR_ERR)

    def _seq_timeout(self, key):
        if self._seq_running and self.pending_key == key:
            self.buttons[key].setStyleSheet("background:#c62828; color:white;")
            self.log(f"── Timeout menunggu respons {key} ──", CLR_ERR)
            self.pending_key = None
            self._seq_running = False

    def reset_colors(self):
        for b in self.buttons.values():
            b.setStyleSheet("")
        for lbl in self.st.values():
            lbl.setText("—")
            lbl.setStyleSheet("")

    # ══════════════════════════════════════════════════════════════
    # Log & settings
    # ══════════════════════════════════════════════════════════════
    def log(self, text, color=CLR_RX):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_view.moveCursor(QTextCursor.End)
        self.log_view.setTextColor(CLR_INFO)
        self.log_view.insertPlainText(f"[{ts}] ")
        self.log_view.setTextColor(color)
        self.log_view.insertPlainText(text + "\n")
        self.log_view.moveCursor(QTextCursor.End)

    def save_log(self):
        fn, _ = QFileDialog.getSaveFileName(
            self, "Simpan log", f"ec25_log_{datetime.now():%Y%m%d_%H%M%S}.txt", "Text (*.txt)")
        if fn:
            with open(fn, "w", encoding="utf-8") as f:
                f.write(self.log_view.toPlainText())
            self.log(f"Log disimpan: {fn}", CLR_INFO)

    def _load_settings(self):
        s = dict(DEFAULT_SETTINGS)
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, encoding="utf-8") as f:
                    s.update(json.load(f))
            except (json.JSONDecodeError, OSError):
                pass
        return s

    def _save_settings(self):
        if hasattr(self, "ed"):
            for k, e in self.ed.items():
                self.settings[k] = e.text()
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except OSError:
            pass

    def closeEvent(self, ev):
        self._save_settings()
        if self.worker.is_open():
            self.worker.close()
        ev.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())