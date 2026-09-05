# EC25-E AT Command Tester

GUI PyQt5 untuk menguji modem Quectel EC25-E lewat USB (adaptor mini-PCIe) sebelum
dipasang ke STM32. Preset command mengikuti urutan `lte_task` di firmware
[STM32F401CCUx-EC25E-GPS-IoT](../) — kalau semua tombol hijau berurutan, firmware
dipastikan jalan di modem ini.

## Setup (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Port yang dipakai: **Quectel USB AT Port** (butuh driver Quectel). Tool auto-pilih
port yang deskripsinya mengandung "Quectel" + "AT".

## Pakai

1. Connect → tombol `AT` harus hijau. Kalau tidak: port salah / modem belum boot.
2. Isi APN, host/user/pass broker di panel kiri (tersimpan ke `settings.json`).
3. Klik `▶ Jalankan urutan firmware` — berhenti di command pertama yang gagal,
   tombolnya merah, klik `?` di sebelahnya untuk penjelasan + kode error.
4. GPS: setelah `AT+QGPS=1`, tunggu 30–90 detik di luar ruangan, klik `AT+QGPSLOC=2`
   berulang sampai fix. Saat `516`, klik `NMEA GGA` untuk lihat jumlah satelit.

Warna log: biru = TX, hijau = OK, merah = ERROR, oranye = respons `+XXX:`.
Password tidak pernah dicetak ke log.

## File

| File | Isi |
|---|---|
| `main.py` | window utama |
| `serial_worker.py` | QThread pembaca port, deteksi prompt `>` |
| `commands.py` | preset + teks help (data) |
| `parsers.py` | `+CSQ`, `+QCSQ`, `+QGPSLOC`, `+QIACT`, `+QMTCONN`… → dict. Tes: `python parsers.py` |
| `settings.json` | dibuat otomatis, di `.gitignore` (berisi password broker) |