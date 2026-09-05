"""
commands.py — daftar preset AT command + teks help.
Murni data, tidak ada logic Qt. Urutan grup mengikuti lte_task di firmware STM32.

Placeholder di cmd diisi dari settings saat runtime:
  {APN} {HOST} {PORT} {CLIENT} {USER} {PASS} {TOPIC} {LEN}
"""

# Kode error umum — dipakai di help dan di highlight log
CME_ERRORS = {
    "504": "GNSS sudah menyala (bukan error fatal, lanjut saja)",
    "505": "GNSS belum menyala — kirim AT+QGPS=1 dulu",
    "516": "Belum ada fix. Normal 30–90 detik setelah QGPS=1 di luar ruangan; "
           "di dalam ruangan bisa tidak pernah fix",
    "10":  "SIM tidak terdeteksi — cek slot/arah SIM",
    "11":  "SIM minta PIN — matikan PIN di HP dulu",
    "13":  "SIM gagal / rusak",
    "30":  "Tidak ada layanan jaringan — cek antena LTE dan sinyal",
}

QMTCONN_RESULT = {
    "0": "Diterima",
    "1": "Versi protokol MQTT ditolak broker",
    "2": "Client ID ditolak (duplikat / tidak valid)",
    "3": "Server tidak tersedia",
    "4": "Username / password salah",
    "5": "Tidak diotorisasi",
}

QMTOPEN_RESULT = {
    "0":  "Network terbuka",
    "-1": "Gagal buka network — cek PDP aktif (AT+QIACT?) dan port 1883 terbuka di server",
    "1":  "Parameter salah",
    "2":  "Identifier MQTT sudah dipakai",
    "3":  "Gagal aktivasi PDP",
    "4":  "Gagal resolve DNS (host pakai nama, bukan IP?)",
    "5":  "Network disconnect",
}

# Setiap grup: (judul, [ {key, label, cmd, wait, help}, ... ])
GROUPS = [
    ("1. Module Ready", [
        dict(key="at", label="AT", cmd="AT", wait="OK",
             help="Cek modem hidup dan port benar.\n\n"
                  "Respons: OK\n\n"
                  "Kalau tidak ada respons sama sekali: port yang dipilih bukan AT Port "
                  "(coba port lain), baud salah, atau modem belum boot (LED NET belum kedip)."),
        dict(key="ate0", label="ATE0", cmd="ATE0", wait="OK",
             help="Matikan echo. Setelah ini modem tidak mengulang command yang kita kirim.\n\n"
                  "Firmware STM32 mengirim ini agar parser tidak bingung."),
        dict(key="ati", label="ATI", cmd="ATI", wait="OK",
             help="Identitas modem: Quectel / EC25 / Revision.\n\n"
                  "Respons contoh:\n  Quectel\n  EC25\n  Revision: EC25EFAR06A11M4G\n\n"
                  "Revision penting: firmware lama (< R06) mungkin tidak support QMTPUBEX."),
        dict(key="cpin", label="AT+CPIN?", cmd="AT+CPIN?", wait="READY",
             help="Status SIM.\n\n"
                  "Respons: +CPIN: READY\n\n"
                  "+CPIN: SIM PIN → SIM diproteksi PIN, matikan dulu.\n"
                  "+CME ERROR: 10 → SIM tidak terdeteksi."),
        dict(key="cereg", label="AT+CEREG?", cmd="AT+CEREG?", wait="+CEREG:",
             help="Registrasi LTE.\n\n"
                  "Respons: +CEREG: <n>,<stat>\n"
                  "  stat 1 = registered home ✔\n"
                  "  stat 5 = registered roaming ✔\n"
                  "  stat 2 = masih mencari → tunggu\n"
                  "  stat 0 = tidak mencari → antena/SIM bermasalah\n"
                  "  stat 3 = ditolak jaringan\n\n"
                  "Firmware STM32 menunggu ini sampai 60 detik."),
    ]),
    ("2. Network Info", [
        dict(key="csq", label="AT+CSQ", cmd="AT+CSQ", wait="+CSQ:",
             help="Kekuatan sinyal (RSSI).\n\n"
                  "Respons: +CSQ: <rssi>,<ber>\n"
                  "  rssi 0–31 → dBm = -113 + 2×rssi\n"
                  "  99 = tidak diketahui / tidak ada sinyal\n\n"
                  "Bagus: > 15. Buruk: < 8."),
        dict(key="qcsq", label="AT+QCSQ", cmd="AT+QCSQ", wait="+QCSQ:",
             help="Kualitas sinyal LTE detail.\n\n"
                  "Respons EC25: +QCSQ: \"LTE\",<rssi>,<rsrp>,<sinr>,<rsrq>\n"
                  "  rsrp: -80 bagus, -100 cukup, -110 buruk (dBm)\n"
                  "  sinr: nilai mentah 0–250 → dB = sinr/5 − 20\n"
                  "        > 10 dB bagus, < 0 dB buruk\n\n"
                  "PERHATIAN: urutan field EC25 BERBEDA dari EC600K."),
        dict(key="cops", label="AT+COPS?", cmd="AT+COPS?", wait="+COPS:",
             help="Operator yang sedang dipakai.\n\n"
                  "Respons: +COPS: 0,0,\"INDOSATOOREDOO\",7\n"
                  "  angka terakhir 7 = LTE"),
        dict(key="qnwinfo", label="AT+QNWINFO", cmd="AT+QNWINFO", wait="+QNWINFO:",
             help="Teknologi + band aktif.\n\n"
                  "Respons: +QNWINFO: \"FDD LTE\",\"51001\",\"LTE BAND 3\",1350"),
    ]),
    ("3. Internet (PDP)", [
        dict(key="qicsgp", label="Set APN", cmd='AT+QICSGP=1,1,"{APN}","","",1', wait="OK",
             help="Set APN ke context 1.\n\n"
                  "Format: AT+QICSGP=<ctx>,<type>,\"<apn>\",\"<user>\",\"<pass>\",<auth>\n"
                  "  type 1 = IPv4\n\n"
                  "APN umum Indonesia: internet (Telkomsel/Indosat/XL/Tri), "
                  "indosatgprs, 3gprs. Salah APN → QIACT gagal."),
        dict(key="qiact", label="AT+QIACT=1", cmd="AT+QIACT=1", wait="OK",
             help="Aktifkan PDP context 1 (dapat IP dari operator).\n\n"
                  "Bisa sampai 30 detik. Respons: OK\n\n"
                  "ERROR kalau sudah aktif dari sebelumnya — cek dengan AT+QIACT?."),
        dict(key="qiactq", label="AT+QIACT?", cmd="AT+QIACT?", wait="OK",
             help="Cek PDP aktif dan IP-nya.\n\n"
                  "Respons: +QIACT: 1,1,1,\"10.82.117.204\"\n\n"
                  "Kalau hanya OK tanpa +QIACT → PDP belum aktif, ulangi AT+QIACT=1."),
        dict(key="qideact", label="AT+QIDEACT=1", cmd="AT+QIDEACT=1", wait="OK",
             help="Matikan PDP context 1. Untuk tes ulang dari nol."),
        dict(key="qping", label="Ping 8.8.8.8", cmd='AT+QPING=1,"8.8.8.8",4,3', wait="+QPING: 0,4",
             help="Bukti internet benar-benar jalan.\n\n"
                  "Respons: +QPING: 0,\"8.8.8.8\",32,54,255 (×3)\n"
                  "         +QPING: 0,4,3,0,54,66,58   ← ringkasan\n\n"
                  "+QPING: 569 = timeout → PDP aktif tapi tidak ada rute keluar."),
    ]),
    ("4. GPS", [
        dict(key="gnsscfg", label="GNSS config", cmd='AT+QGPSCFG="gnssconfig",1', wait="OK",
             help="Pilih konstelasi: 1 = GPS + GLONASS (default, paling cepat fix di Asia)."),
        dict(key="outport", label="NMEA off", cmd='AT+QGPSCFG="outport","none"', wait="OK",
             help="Matikan stream NMEA otomatis. Firmware STM32 pakai ini supaya UART1 "
                  "tidak dibanjiri kalimat NMEA.\n\n"
                  "Untuk tes di PC bisa pilih \"usbnmea\" → NMEA muncul di port NMEA."),
        dict(key="qgps", label="AT+QGPS=1", cmd="AT+QGPS=1", wait="OK",
             help="Nyalakan GNSS.\n\n"
                  "Respons: OK\n"
                  "+CME ERROR: 504 = sudah nyala, aman.\n\n"
                  "Setelah ini tunggu 30–90 detik di luar ruangan, lalu AT+QGPSLOC=2."),
        dict(key="qgpsq", label="AT+QGPS?", cmd="AT+QGPS?", wait="+QGPS:",
             help="Status GNSS. +QGPS: 1 = nyala, 0 = mati."),
        dict(key="qgpsloc", label="AT+QGPSLOC=2", cmd="AT+QGPSLOC=2", wait="+QGPSLOC:",
             help="Ambil posisi. Mode 2 = lat/lon derajat desimal.\n\n"
                  "Respons: +QGPSLOC: <utc>,<lat>,<lon>,<hdop>,<alt>,<fix>,<cog>,<spkm>,<spkn>,<date>,<nsat>\n\n"
                  "+CME ERROR: 516 = belum fix. Tunggu dan ulangi.\n"
                  "Fix > 5 menit tidak dapat → antena GNSS pasif/tidak ada, atau di dalam ruangan."),
        dict(key="gga", label="NMEA GGA", cmd='AT+QGPSGNMEA="GGA"', wait="+QGPSGNMEA:",
             help="Ambil satu kalimat NMEA GGA. Berguna saat 516: field ke-7 = jumlah satelit "
                  "yang terlihat. Kalau 0 terus → antena bermasalah."),
        dict(key="qgpsend", label="AT+QGPSEND", cmd="AT+QGPSEND", wait="OK",
             help="Matikan GNSS."),
    ]),
    ("5. MQTT", [
        dict(key="qmtdisc", label="AT+QMTDISC=0", cmd="AT+QMTDISC=0", wait="+QMTDISC:",
             help="Putus sesi MQTT lama. ERROR kalau belum ada sesi — normal."),
        dict(key="qmtclose", label="AT+QMTCLOSE=0", cmd="AT+QMTCLOSE=0", wait="OK",
             help="Tutup koneksi network MQTT lama. ERROR kalau belum ada — normal."),
        dict(key="recvmode", label="QMTCFG recv/mode", cmd='AT+QMTCFG="recv/mode",0,0,1', wait="OK",
             help="Mode penerimaan URC. ERROR di firmware lama — firmware STM32 akan skip, "
                  "bukan fatal."),
        dict(key="qmtopen", label="Open broker", cmd='AT+QMTOPEN=0,"{HOST}",{PORT}', wait="+QMTOPEN:",
             help="Buka TCP ke broker.\n\n"
                  "Respons: +QMTOPEN: 0,<result>\n" +
                  "\n".join(f"  {k:>3} = {v}" for k, v in QMTOPEN_RESULT.items()) +
                  "\n\nHarus PDP aktif dulu (grup 3)."),
        dict(key="qmtconn", label="Connect", cmd='AT+QMTCONN=0,"{CLIENT}","{USER}","{PASS}"',
             wait="+QMTCONN:",
             help="CONNECT ke broker dengan client ID + user/pass.\n\n"
                  "Respons: +QMTCONN: 0,0,<ret>\n" +
                  "\n".join(f"  {k} = {v}" for k, v in QMTCONN_RESULT.items())),
        dict(key="qmtpubex", label="Publish test", cmd='AT+QMTPUBEX=0,0,0,0,"{TOPIC}",{LEN}',
             wait=">",
             help="Publish payload. Modem balas '>' lalu kita kirim payload sepanjang {LEN} byte.\n\n"
                  "Tool ini otomatis mengirim payload test setelah '>'.\n"
                  "Respons akhir: +QMTPUBEX: 0,0,0\n\n"
                  "ERROR langsung → firmware tidak support QMTPUBEX, pakai QMTPUB (Ctrl-Z)."),
        dict(key="qmtstat", label="AT+QMTCONN?", cmd="AT+QMTCONN?", wait="+QMTCONN:",
             help="Status koneksi MQTT.\n  +QMTCONN: 0,3 = connected\n  0,1 = initial\n  0,4 = disconnecting"),
    ]),
    ("6. Time", [
        dict(key="ctzu", label="AT+CTZU=1", cmd="AT+CTZU=1", wait="OK",
             help="Auto update timezone dari jaringan."),
        dict(key="qlts", label="AT+QLTS=2", cmd="AT+QLTS=2", wait="+QLTS:",
             help="Jam jaringan seluler.\n\nRespons: +QLTS: \"2026/09/05,09:12:41+28,0\"\n"
                  "  +28 = offset timezone dalam kuarter jam (28/4 = +7 WIB)"),
    ]),
]

# Payload contoh untuk tombol Publish test
TEST_PAYLOAD = '{"device":"AT-TESTER","msg":"hello from EC25"}'


def all_commands():
    """Flatten GROUPS → dict key → item."""
    return {item["key"]: item for _, items in GROUPS for item in items}


def fill(cmd: str, settings: dict) -> str:
    """Isi placeholder {APN} dst dari settings."""
    return cmd.format(
        APN=settings.get("apn", "internet"),
        HOST=settings.get("host", ""),
        PORT=settings.get("port", "1883"),
        CLIENT=settings.get("client_id", "AT-TESTER"),
        USER=settings.get("user", ""),
        PASS=settings.get("pass", ""),
        TOPIC=settings.get("topic", "test/topic"),
        LEN=len(TEST_PAYLOAD),
    )