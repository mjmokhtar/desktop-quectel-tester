# Quectel EC25-E AT Command Tester

🇮🇩 Bahasa Indonesia | [🇬🇧 English](README.en.md)

GUI Windows untuk menguji modem **Quectel EC25-E** lewat USB (adaptor mini-PCIe) sebelum
dipasang ke mikrokontroler. Preset command mengikuti urutan `lte_task` di firmware
[STM32F401CCUx-EC25E-GPS-IoT](https://github.com/mjmokhtar/STM32F401CCUx-EC25E-GPS-IoT) —
kalau semua tombol hijau berurutan, firmware dipastikan jalan di modem ini.

Fitur:
- Preset 31 command dalam 6 grup: Module Ready → Network Info → Internet (PDP) → GPS → MQTT → Time
- Tombol **`?`** di tiap command: fungsi, format respons, arti kode error
- Tombol berubah **hijau / merah** sesuai hasil — termasuk kode hasil `+QMTCONN`/`+QMTOPEN`, bukan cuma `OK`
- **▶ Jalankan urutan firmware**: kirim semua preset berurutan, berhenti di yang pertama gagal
- Panel status hasil parse: RSRP/SINR dalam dB, IP PDP, lat/lon/satelit, status MQTT
- Kode `+CME ERROR` dijelaskan otomatis di log (516, 504, 10, 11, …)
- Publish MQTT test dengan handling prompt `>` otomatis
- Input command manual, log berwarna dengan timestamp, simpan log ke `.txt`

---

## Download (tanpa Python)

Ambil `quectel-at-tester.exe` dari halaman **[Releases](../../releases/latest)**.
Satu file, portable, tidak perlu install — taruh di folder mana saja lalu klik dua kali.

> **Windows SmartScreen** akan menampilkan *"Windows protected your PC"* karena exe tidak
> ditandatangani. Klik **More info → Run anyway**. Ini normal untuk aplikasi open-source kecil;
> source-nya ada di repo ini dan bisa dijalankan langsung dari Python (lihat bawah).

`settings.json` (port terakhir, APN, host/user/password broker) dibuat di folder yang sama
dengan exe.

### Driver Quectel

Exe tidak membawa driver. Sebelum modem muncul sebagai COM port, instal
**Quectel Windows USB Driver** dari [quectel.com/download-zone](https://www.quectel.com/download-zone)
(butuh akun) atau dari vendor adaptor mini-PCIe-mu. Setelah terpasang, Device Manager → Ports
akan menampilkan 4–5 port:

| Nama di Device Manager | Fungsi |
|---|---|
| Quectel USB DM Port | diagnostik — jangan dipakai |
| Quectel USB NMEA Port | stream NMEA GPS |
| **Quectel USB AT Port** | **AT command — pilih ini** |
| Quectel USB Modem | PPP / AT alternatif |

Tool otomatis memilih port yang namanya mengandung "Quectel" dan "AT".

---

## Cara pakai

1. Colok modem, klik **Scan** → pilih *Quectel USB AT Port* → **Connect**.
2. Klik tombol **`AT`** — harus hijau. Kalau tidak ada respons: port salah, atau modem belum
   boot (tunggu LED NET kedip, ±10 detik setelah colok).
3. Isi **APN** dan parameter **MQTT** di panel kiri. Tersimpan otomatis.
4. Klik **▶ Jalankan urutan firmware**. Berhenti di command pertama yang gagal — tombolnya
   merah, klik **`?`** di sebelahnya untuk penjelasan.
5. GPS: setelah `AT+QGPS=1`, tunggu 30–90 detik **di luar ruangan / dekat jendela** dengan
   antena GNSS aktif terpasang, lalu klik `AT+QGPSLOC=2` berulang sampai fix. Saat masih
   `516`, klik **NMEA GGA** untuk lihat jumlah satelit yang terlihat — kalau 0 terus, antena
   bermasalah.
6. MQTT: **Publish test** mengirim `{"device":"AT-TESTER","msg":"hello from EC25"}` ke topic
   yang diisi. Cek di server:
   ```
   mosquitto_sub -h <host> -u <user> -P <pass> -t '<topic>' -v
   ```

Warna log: biru = TX, hijau = `OK`, merah = `ERROR`, oranye = respons `+XXX:`, abu =
keterangan tool. Password tidak pernah dicetak ke log.

---

## Jalan dari source

```powershell
git clone https://github.com/mjmokhtar/desktop-quectel-tester.git
cd desktop-quectel-tester
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Dependency: `pyserial`, `PyQt5`. Python 3.9+.

## Build exe sendiri

```powershell
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name quectel-at-tester `
    --hidden-import serial.tools.list_ports main.py
```

Hasil di `dist\quectel-at-tester.exe`. Release resmi dibuild otomatis oleh GitHub Actions
(`.github/workflows/build.yml`) setiap push tag `v*`.

---

## Struktur

| File | Isi |
|---|---|
| `main.py` | window utama, entry point |
| `serial_worker.py` | QThread pembaca port, deteksi prompt `>` |
| `commands.py` | preset command + teks help (murni data) |
| `parsers.py` | parser respons `+CSQ`, `+QCSQ`, `+QGPSLOC`, `+QIACT`, `+QMTCONN`, … → dict. Tes: `python parsers.py` |
| `requirements.txt` | dependency runtime |
| `.github/workflows/build.yml` | build exe + release otomatis |

## Menambah command sendiri

Tambahkan satu `dict(...)` ke grup yang sesuai di `commands.py`:

```python
dict(key="qtemp", label="AT+QTEMP", cmd="AT+QTEMP", wait="+QTEMP:",
     help="Suhu modem.\n\nRespons: +QTEMP: <pa>,<xo>,<ambient> dalam °C"),
```

`wait` adalah string yang menandai sukses (tombol hijau). Placeholder `{APN}`, `{HOST}`,
`{PORT}`, `{CLIENT}`, `{USER}`, `{PASS}`, `{TOPIC}` diisi dari panel parameter.

## Catatan EC25 vs EC600K

Kalau kau datang dari EC600K (chip ASR): `AT+QINISTAT` di EC25 mengembalikan bitmask
(1/3/7), urutan field `+QCSQ` berbeda (`rssi,rsrp,sinr,rsrq`), dan SINR berskala 0–250
(dB = x/5 − 20). Tool ini sudah memakai format EC25.

## Lisensi

MIT
