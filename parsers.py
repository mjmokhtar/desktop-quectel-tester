"""
parsers.py — ubah baris respons EC25 menjadi dict yang enak ditampilkan.
Tidak ada dependency. Setiap fungsi menerima satu baris (str), mengembalikan
dict atau None kalau baris bukan respons yang dimaksud.

parse_line(line) mencoba semua parser dan mengembalikan (jenis, dict) atau None.
"""

import re


def parse_csq(line: str):
    m = re.match(r"\+CSQ:\s*(\d+),(\d+)", line)
    if not m:
        return None
    rssi = int(m.group(1))
    dbm = None if rssi == 99 else -113 + 2 * rssi
    return {"rssi": rssi, "dbm": dbm}


def parse_qcsq(line: str):
    # EC25: +QCSQ: "LTE",<rssi>,<rsrp>,<sinr>,<rsrq>
    m = re.match(r'\+QCSQ:\s*"(\w+)",(-?\d+),(-?\d+),(-?\d+),(-?\d+)', line)
    if not m:
        return None
    sinr_raw = int(m.group(4))
    return {
        "mode": m.group(1),
        "rssi": int(m.group(2)),
        "rsrp": int(m.group(3)),
        "sinr_raw": sinr_raw,
        "sinr_db": sinr_raw / 5 - 20,
        "rsrq": int(m.group(5)),
    }


def parse_cereg(line: str):
    m = re.match(r"\+CEREG:\s*(\d+),(\d+)", line)
    if not m:
        return None
    stat = int(m.group(2))
    text = {0: "not searching", 1: "registered (home)", 2: "searching",
            3: "denied", 4: "unknown", 5: "registered (roaming)"}.get(stat, "?")
    return {"stat": stat, "text": text, "ok": stat in (1, 5)}


def parse_cops(line: str):
    m = re.match(r'\+COPS:\s*\d+,\d+,"([^"]*)",?(\d*)', line)
    if not m:
        return None
    return {"operator": m.group(1), "act": m.group(2)}


def parse_qnwinfo(line: str):
    m = re.match(r'\+QNWINFO:\s*"([^"]*)","([^"]*)","([^"]*)",(\d+)', line)
    if not m:
        return None
    return {"act": m.group(1), "plmn": m.group(2), "band": m.group(3), "channel": int(m.group(4))}


def parse_qiact(line: str):
    m = re.match(r'\+QIACT:\s*(\d+),(\d+),(\d+),"([^"]*)"', line)
    if not m:
        return None
    return {"ctx": int(m.group(1)), "state": int(m.group(2)), "ip": m.group(4)}


def parse_qgpsloc(line: str):
    # +QGPSLOC: <utc>,<lat>,<lon>,<hdop>,<alt>,<fix>,<cog>,<spkm>,<spkn>,<date>,<nsat>
    if not line.startswith("+QGPSLOC:"):
        return None
    f = line.split(":", 1)[1].strip().split(",")
    if len(f) < 11:
        return None
    try:
        return {
            "utc": f[0], "lat": float(f[1]), "lon": float(f[2]),
            "hdop": float(f[3]), "alt": float(f[4]), "fix": int(f[5]),
            "cog": float(f[6]) if f[6] else 0.0,
            "spkm": float(f[7]), "spkn": float(f[8]),
            "date": f[9], "nsat": int(f[10]),
        }
    except ValueError:
        return None


def parse_gga(line: str):
    # +QGPSGNMEA: $GPGGA,hhmmss,lat,N,lon,E,fix,nsat,hdop,alt,M,...
    if "$GPGGA" not in line and "$GNGGA" not in line:
        return None
    f = line.split("$", 1)[1].split(",")
    if len(f) < 8:
        return None
    return {"fix_quality": f[6], "sat_in_view": f[7]}


def parse_qmtopen(line: str):
    m = re.match(r"\+QMTOPEN:\s*(\d+),(-?\d+)", line)
    if not m:
        return None
    return {"client": int(m.group(1)), "result": m.group(2), "ok": m.group(2) == "0"}


def parse_qmtconn(line: str):
    m = re.match(r"\+QMTCONN:\s*(\d+),(\d+)(?:,(\d+))?", line)
    if not m:
        return None
    if m.group(3) is None:          # jawaban AT+QMTCONN? → status
        return {"client": int(m.group(1)), "state": int(m.group(2))}
    return {"client": int(m.group(1)), "result": int(m.group(2)),
            "ret": m.group(3), "ok": m.group(2) == "0" and m.group(3) == "0"}


def parse_qmtpub(line: str):
    m = re.match(r"\+QMTPUB(?:EX)?:\s*(\d+),(\d+),(\d+)", line)
    if not m:
        return None
    return {"client": int(m.group(1)), "msgid": int(m.group(2)),
            "result": int(m.group(3)), "ok": m.group(3) == "0"}


def parse_qlts(line: str):
    m = re.match(r'\+QLTS:\s*"([^"]*)"', line)
    if not m:
        return None
    return {"time": m.group(1)}


def parse_cme(line: str):
    m = re.match(r"\+CME ERROR:\s*(\d+)", line)
    if not m:
        return None
    return {"code": m.group(1)}


def parse_qping(line: str):
    m = re.match(r"\+QPING:\s*(\d+)(?:,(.*))?", line)
    if not m:
        return None
    return {"result": m.group(1), "detail": m.group(2) or ""}


PARSERS = [
    ("CSQ",     parse_csq),
    ("QCSQ",    parse_qcsq),
    ("CEREG",   parse_cereg),
    ("COPS",    parse_cops),
    ("QNWINFO", parse_qnwinfo),
    ("QIACT",   parse_qiact),
    ("QGPSLOC", parse_qgpsloc),
    ("GGA",     parse_gga),
    ("QMTOPEN", parse_qmtopen),
    ("QMTCONN", parse_qmtconn),
    ("QMTPUB",  parse_qmtpub),
    ("QLTS",    parse_qlts),
    ("CME",     parse_cme),
    ("QPING",   parse_qping),
]


def parse_line(line: str):
    """Coba semua parser. Return (jenis, dict) atau None."""
    line = line.strip()
    if not line.startswith("+") and "$G" not in line:
        return None
    for name, fn in PARSERS:
        r = fn(line)
        if r is not None:
            return name, r
    return None


if __name__ == "__main__":
    # tes cepat: python parsers.py
    samples = [
        "+CSQ: 24,99",
        '+QCSQ: "LTE",-65,-92,160,-10',
        "+CEREG: 0,1",
        '+COPS: 0,0,"INDOSATOOREDOO",7',
        '+QNWINFO: "FDD LTE","51001","LTE BAND 3",1350',
        '+QIACT: 1,1,1,"10.82.117.204"',
        "+QGPSLOC: 021241.000,-6.200912,106.816682,0.9,18.4,3,0.00,0.3,0.2,030926,09",
        "+QMTOPEN: 0,0",
        "+QMTCONN: 0,0,4",
        "+QMTPUBEX: 0,0,0",
        '+QLTS: "2026/09/05,09:12:41+28,0"',
        "+CME ERROR: 516",
    ]
    for s in samples:
        print(f"{s:75} → {parse_line(s)}")