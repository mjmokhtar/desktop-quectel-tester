[🇮🇩 Bahasa Indonesia](README.md) | 🇬🇧 English

# Quectel EC25-E AT Command Tester

A Windows GUI for testing the **Quectel EC25-E** modem over USB (mini-PCIe adapter) before it is
attached to a microcontroller. The command presets follow the order of `lte_task` in the
[STM32F401CCUx-EC25E-GPS-IoT](https://github.com/mjmokhtar/STM32F401CCUx-EC25E-GPS-IoT) firmware —
if every button turns green in sequence, the firmware is guaranteed to work on this modem.

Features:
- 31 preset commands in 6 groups: Module Ready → Network Info → Internet (PDP) → GPS → MQTT → Time
- A **`?`** button on every command: function, response format, meaning of error codes
- Buttons turn **green / red** according to the result — including the `+QMTCONN`/`+QMTOPEN` result codes, not just `OK`
- **▶ Run firmware sequence** (labelled *Jalankan urutan firmware* in the app): sends all presets in order, stops at the first failure
- Parsed status panel: RSRP/SINR in dB, PDP IP, lat/lon/satellites, MQTT status
- `+CME ERROR` codes are explained automatically in the log (516, 504, 10, 11, …)
- MQTT test publish with automatic `>` prompt handling
- Manual command input, colored log with timestamps, save the log to `.txt`

---

## Download (no Python needed)

Get `quectel-at-tester.exe` from the **[Releases](../../releases/latest)** page.
A single portable file, no installation — put it in any folder and double-click.

> **Windows SmartScreen** will show *"Windows protected your PC"* because the exe is not
> signed. Click **More info → Run anyway**. This is normal for a small open-source app;
> the source is in this repo and can be run directly from Python (see below).

`settings.json` (last port, APN, broker host/user/password) is created in the same folder
as the exe.

### Quectel Driver

The exe does not include the driver. Before the modem appears as a COM port, install the
**Quectel Windows USB Driver** from [quectel.com/download-zone](https://www.quectel.com/download-zone)
(account required) or from your mini-PCIe adapter's vendor. Once installed, Device Manager → Ports
will show 4–5 ports:

| Name in Device Manager | Function |
|---|---|
| Quectel USB DM Port | diagnostics — do not use |
| Quectel USB NMEA Port | GPS NMEA stream |
| **Quectel USB AT Port** | **AT commands — pick this one** |
| Quectel USB Modem | PPP / alternative AT |

The tool automatically picks the port whose name contains "Quectel" and "AT".

---

## How to use

1. Plug in the modem, click **Scan** → pick *Quectel USB AT Port* → **Connect**.
2. Click the **`AT`** button — it must turn green. If there is no response: wrong port, or the modem has not
   booted yet (wait for the NET LED to blink, ~10 seconds after plugging in).
3. Fill in the **APN** and **MQTT** parameters in the left panel. They are saved automatically.
4. Click **▶ Run firmware sequence**. It stops at the first command that fails — its button turns
   red; click the **`?`** next to it for an explanation.
5. GPS: after `AT+QGPS=1`, wait 30–90 seconds **outdoors / near a window** with an active
   GNSS antenna attached, then click `AT+QGPSLOC=2` repeatedly until you get a fix. While it is still
   `516`, click **NMEA GGA** to see the number of visible satellites — if it stays at 0, the antenna
   has a problem.
6. MQTT: **Publish test** sends `{"device":"AT-TESTER","msg":"hello from EC25"}` to the topic
   you filled in. Check on the server:
   ```
   mosquitto_sub -h <host> -u <user> -P <pass> -t '<topic>' -v
   ```

Log colors: blue = TX, green = `OK`, red = `ERROR`, orange = `+XXX:` responses, gray =
tool notes. The password is never printed to the log.

---

## Run from source

```powershell
git clone https://github.com/mjmokhtar/desktop-quectel-tester.git
cd desktop-quectel-tester
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Dependencies: `pyserial`, `PyQt5`. Python 3.9+.

## Build the exe yourself

```powershell
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name quectel-at-tester `
    --hidden-import serial.tools.list_ports main.py
```

The result is in `dist\quectel-at-tester.exe`. Official releases are built automatically by GitHub Actions
(`.github/workflows/build.yml`) on every push of a `v*` tag.

---

## Structure

| File | Contents |
|---|---|
| `main.py` | main window, entry point |
| `serial_worker.py` | QThread port reader, `>` prompt detection |
| `commands.py` | command presets + help text (pure data) |
| `parsers.py` | response parsers for `+CSQ`, `+QCSQ`, `+QGPSLOC`, `+QIACT`, `+QMTCONN`, … → dict. Test: `python parsers.py` |
| `requirements.txt` | runtime dependencies |
| `.github/workflows/build.yml` | automatic exe build + release |

## Adding your own commands

Add one `dict(...)` to the appropriate group in `commands.py`:

```python
dict(key="qtemp", label="AT+QTEMP", cmd="AT+QTEMP", wait="+QTEMP:",
     help="Suhu modem.\n\nRespons: +QTEMP: <pa>,<xo>,<ambient> dalam °C"),
```

`wait` is the string that marks success (green button). The placeholders `{APN}`, `{HOST}`,
`{PORT}`, `{CLIENT}`, `{USER}`, `{PASS}`, `{TOPIC}` are filled in from the parameter panel.

> The `help` text in the example above is shown in Indonesian in the app's `?` popup; write it in whatever language you prefer.

## Note: EC25 vs EC600K

If you are coming from the EC600K (ASR chip): on the EC25, `AT+QINISTAT` returns a bitmask
(1/3/7), the field order of `+QCSQ` differs (`rssi,rsrp,sinr,rsrq`), and SINR is scaled 0–250
(dB = x/5 − 20). This tool already uses the EC25 format.

## License

MIT
