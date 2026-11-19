"""Deterministic synthetic data for the Account Takeover Detection example.

Run: python3 data/generate_data.py
Writes CSVs to data/ and the Snowflake load script to sql/02_data.sql.
Everything is invented. IP addresses come from private (10.x) and documentation
(198.51.100.x, 203.0.113.x) ranges. The same seed always yields the same data.

Timeline: baseline 2026-09-01 .. 2026-10-01, detection window 2026-10-02 .. 2026-11-01.
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA, SQL = ROOT / "data", ROOT / "sql"
START = datetime(2026, 9, 1)
WINDOW_START = datetime(2026, 10, 2)
AS_OF = datetime(2026, 11, 1)
rng = random.Random(20261119)

HOME_CITIES = [  # city, country, lat, lon
    ("New York", "US", 40.7128, -74.0060), ("Chicago", "US", 41.8781, -87.6298),
    ("Charlotte", "US", 35.2271, -80.8431), ("Atlanta", "US", 33.7490, -84.3880),
    ("Dallas", "US", 32.7767, -96.7970), ("Denver", "US", 39.7392, -104.9903),
    ("Phoenix", "US", 33.4484, -112.0740), ("Seattle", "US", 47.6062, -122.3321),
    ("Boston", "US", 42.3601, -71.0589), ("Miami", "US", 25.7617, -80.1918),
    ("Minneapolis", "US", 44.9778, -93.2650), ("San Diego", "US", 32.7157, -117.1611),
]
FOREIGN_CITIES = [
    ("London", "GB", 51.5074, -0.1278), ("Lagos", "NG", 6.5244, 3.3792),
    ("Bucharest", "RO", 44.4268, 26.1025), ("Manila", "PH", 14.5995, 120.9842),
    ("Sao Paulo", "BR", -23.5505, -46.6333), ("Jakarta", "ID", -6.2088, 106.8456),
    ("Toronto", "CA", 43.6532, -79.3832), ("Mexico City", "MX", 19.4326, -99.1332),
]
FIRST = ["Avery", "Jordan", "Riley", "Morgan", "Casey", "Quinn", "Taylor", "Jamie", "Rowan", "Skyler",
         "Harper", "Emerson", "Finley", "Reese", "Dakota", "Hayden", "Parker", "Sage", "Blake", "Cameron"]
LAST = ["Alder", "Brook", "Calder", "Dunmore", "Ellery", "Fairbanks", "Garrow", "Hollis", "Ingram", "Juniper",
        "Kestrel", "Linwood", "Marlow", "Northam", "Oakes", "Penrose", "Quill", "Redfern", "Stroud", "Thorne"]
SEGMENTS = ["Retail", "Retail", "Retail", "Premier", "Small Business"]


class Ids:
    def __init__(self):
        self.n = {"E": 0, "C": 0, "T": 0, "S": 0}

    def next(self, p):
        self.n[p] += 1
        return f"{p}{self.n[p]:07d}"


ids = Ids()
identity, changes, txns = [], [], []


def ts(t):
    return t.strftime("%Y-%m-%d %H:%M:%S")


def ev(cust, t, etype, ip, device, city, session=""):
    identity.append({"event_id": ids.next("E"), "customer_id": cust["customer_id"], "event_ts": ts(t),
                     "event_type": etype, "ip_address": ip, "device_id": device, "city": city[0],
                     "country": city[1], "latitude": city[2], "longitude": city[3], "session_id": session})


def login(cust, t, ip, device, city):
    s = ids.next("S")
    ev(cust, t, "LOGIN_SUCCESS", ip, device, city, s)
    return s


def change(cust, t, ctype, session="", payee=""):
    changes.append({"change_id": ids.next("C"), "customer_id": cust["customer_id"], "change_ts": ts(t),
                    "change_type": ctype, "payee_id": payee, "session_id": session})


def pay(cust, t, amount, payee, session=""):
    txns.append({"txn_id": ids.next("T"), "customer_id": cust["customer_id"], "txn_ts": ts(t),
                 "amount": int(amount), "payee_id": payee, "session_id": session})


def rand_time(lo, hi):
    return lo + timedelta(seconds=rng.randint(0, int((hi - lo).total_seconds())))


def normal_amount():
    return max(15, int(rng.lognormvariate(4.6, 0.7)))  # median about $100


def build():
    customers = []
    for i in range(1, 1501):
        city = rng.choice(HOME_CITIES)
        customers.append({
            "customer_id": f"CU{i:05d}", "customer_name": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
            "segment": rng.choice(SEGMENTS), "home_city": city[0], "home_country": city[1],
            "_city": city, "_ip": f"10.{20 + i // 250}.{i % 250}.{rng.randint(2, 250)}",
            "_devices": [f"DV{i:05d}{k}" for k in range(rng.choice([1, 1, 2]))],
            "_payees": [f"PY{i:05d}{k}" for k in range(3)], "confirmed_ato": False, "_story": "",
        })

    # Normal behaviour for everyone, both periods.
    for c in customers:
        for p in c["_payees"]:
            change(c, rand_time(START, START + timedelta(days=5)), "PAYEE_ADDED", payee=p)
        t = START + timedelta(hours=rng.randint(6, 60))
        while t < AS_OF - timedelta(hours=2):
            dev = rng.choice(c["_devices"])
            if rng.random() < 0.06:
                ev(c, t - timedelta(seconds=rng.randint(20, 90)), "LOGIN_FAIL", c["_ip"], dev, c["_city"])
            s = login(c, t, c["_ip"], dev, c["_city"])
            if rng.random() < 0.4:
                pay(c, t + timedelta(minutes=rng.randint(1, 20)), normal_amount(), rng.choice(c["_payees"]), s)
            t += timedelta(hours=rng.randint(30, 110), seconds=rng.randint(0, 3599))
        if rng.random() < 0.03:
            change(c, rand_time(START, AS_OF - timedelta(days=1)), rng.choice(["PASSWORD_RESET", "EMAIL_CHANGE"]))

    pool = customers[:]
    rng.shuffle(pool)
    take = lambda n: [pool.pop() for _ in range(n)]  # noqa: E731

    def when(c):
        return rand_time(WINDOW_START + timedelta(days=1), AS_OF - timedelta(days=1, hours=6))

    # A: full takeover chain from a new device abroad (15).
    for c in take(15):
        c["confirmed_ato"], c["_story"] = True, "Full takeover chain"
        t, city = when(c), rng.choice(FOREIGN_CITIES[:6])
        # A recent genuine login at home makes the foreign login physically impossible.
        login(c, t - timedelta(hours=rng.randint(2, 5)), c["_ip"], c["_devices"][0], c["_city"])
        ip = f"203.0.113.{rng.randint(2, 250)}"
        s = login(c, t, ip, f"DVX{c['customer_id'][2:]}", city)
        change(c, t + timedelta(minutes=rng.randint(2, 8)), "PASSWORD_RESET", s)
        payee = f"PYX{c['customer_id'][2:]}"
        change(c, t + timedelta(minutes=rng.randint(10, 30)), "PAYEE_ADDED", s, payee)
        pay(c, t + timedelta(minutes=rng.randint(35, 120)), rng.randint(2500, 9500), payee, s)

    # B: MFA fatigue then payee and transfer from a domestic new device (8).
    for c in take(8):
        c["confirmed_ato"], c["_story"] = True, "MFA fatigue"
        t, city = when(c), rng.choice(HOME_CITIES)
        ip, dev = f"198.51.100.{rng.randint(2, 250)}", f"DVX{c['customer_id'][2:]}"
        for k in range(rng.randint(6, 9)):
            ev(c, t + timedelta(seconds=40 * k + rng.randint(0, 20)), "MFA_DENY", ip, dev, city)
        ev(c, t + timedelta(minutes=7), "MFA_APPROVE", ip, dev, city)
        s = login(c, t + timedelta(minutes=7, seconds=30), ip, dev, city)
        payee = f"PYX{c['customer_id'][2:]}"
        change(c, t + timedelta(minutes=12), "PAYEE_ADDED", s, payee)
        pay(c, t + timedelta(minutes=rng.randint(15, 50)), rng.randint(1800, 6000), payee, s)

    # C: credential stuffing from two attacker IPs; a few logins succeed (8 victims).
    victims = take(8)
    for camp, ip in enumerate(["198.51.100.77", "203.0.113.199"]):
        t0 = rand_time(WINDOW_START + timedelta(days=3), AS_OF - timedelta(days=4))
        tried = take(22) + victims[camp * 4:(camp + 1) * 4]
        for c in tried:
            ev(c, t0 + timedelta(seconds=rng.randint(0, 3000)), "LOGIN_FAIL", ip, "DVBOT", FOREIGN_CITIES[2 + camp])
        for c in victims[camp * 4:(camp + 1) * 4]:
            c["confirmed_ato"], c["_story"] = True, "Credential stuffing"
            t = t0 + timedelta(minutes=rng.randint(60, 240))
            s = login(c, t, ip, "DVBOT", FOREIGN_CITIES[2 + camp])
            change(c, t + timedelta(minutes=3), "PHONE_CHANGE", s)
            payee = f"PYX{c['customer_id'][2:]}"
            change(c, t + timedelta(minutes=9), "PAYEE_ADDED", s, payee)
            pay(c, t + timedelta(minutes=rng.randint(12, 90)), rng.randint(900, 4000), payee, s)

    # D: stolen session token used abroad on the customer's own device (9).
    for c in take(9):
        c["confirmed_ato"], c["_story"] = True, "Session hijack"
        t = when(c)
        login(c, t, c["_ip"], c["_devices"][0], c["_city"])
        city = rng.choice(FOREIGN_CITIES[:6])
        s = login(c, t + timedelta(minutes=rng.randint(20, 70)), f"203.0.113.{rng.randint(2, 250)}",
                  c["_devices"][0], city)
        change(c, t + timedelta(minutes=80), "EMAIL_CHANGE", s)

    # Decoys: legitimate activity that looks suspicious.
    for c in take(25):  # travellers; 10 buy a local phone abroad
        c["_story"] = "Legitimate travel"
        t, city = when(c), rng.choice(FOREIGN_CITIES)
        new_phone = len([x for x in customers if x["_story"] == "Legitimate travel"]) <= 10
        dev = f"DVT{c['customer_id'][2:]}" if new_phone else c["_devices"][0]
        login(c, t - timedelta(hours=rng.randint(14, 30)), c["_ip"], c["_devices"][0], c["_city"])
        s = login(c, t, f"198.51.100.{rng.randint(2, 250)}", dev, city)
        pay(c, t + timedelta(minutes=rng.randint(2, 30)), normal_amount(), rng.choice(c["_payees"]), s)
    for c in take(15):  # new phone, then pays a new contractor the same day
        c["_story"] = "Legitimate new phone and payee"
        t = when(c)
        s = login(c, t, c["_ip"], c["_devices"][0], c["_city"])
        change(c, t + timedelta(minutes=2), "PHONE_CHANGE", s)
        payee = f"PYN{c['customer_id'][2:]}"
        change(c, t + timedelta(hours=rng.randint(1, 6)), "PAYEE_ADDED", "", payee)
        pay(c, t + timedelta(hours=rng.randint(7, 20)), rng.randint(150, 900), payee)
    for c in take(20):  # one large legitimate purchase
        c["_story"] = "Legitimate large payment"
        t = when(c)
        s = login(c, t, c["_ip"], c["_devices"][0], c["_city"])
        pay(c, t + timedelta(minutes=5), rng.randint(1500, 7000), c["_payees"][0], s)
    for c in take(6):  # corporate VPN exits abroad
        c["_story"] = "Legitimate VPN"
        t = when(c)
        login(c, t, c["_ip"], c["_devices"][0], c["_city"])
        login(c, t + timedelta(minutes=rng.randint(15, 45)), f"198.51.100.{rng.randint(2, 250)}",
              c["_devices"][0], FOREIGN_CITIES[0])
    for c in take(5):  # a couple of accidental MFA denials, below the threshold
        c["_story"] = "Legitimate MFA denials"
        t = when(c)
        for k in range(rng.randint(2, 3)):
            ev(c, t + timedelta(seconds=30 * k), "MFA_DENY", c["_ip"], c["_devices"][0], c["_city"])
        ev(c, t + timedelta(minutes=2), "MFA_APPROVE", c["_ip"], c["_devices"][0], c["_city"])
        login(c, t + timedelta(minutes=2, seconds=20), c["_ip"], c["_devices"][0], c["_city"])
    return customers


def write_csv(name, rows, cols):
    with open(DATA / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def sql_val(v, kind):
    if v == "" or v is None:
        return "NULL"
    if kind == "ts":
        return f"'{v}'::TIMESTAMP_NTZ"
    if kind == "num":
        return str(v)
    if kind == "bool":
        return "TRUE" if v else "FALSE"
    return "'" + str(v).replace("'", "''") + "'"


def inserts(table, rows, cols):
    out = []
    names = [c for c, _ in cols]
    for i in range(0, len(rows), 1000):
        vals = ["(" + ", ".join(sql_val(r[c], k) for c, k in cols) + ")" for r in rows[i:i + 1000]]
        out.append(f"INSERT INTO {table} ({', '.join(names)}) VALUES\n" + ",\n".join(vals) + ";")
    return "\n\n".join(out)


COLS = {
    "customers": [("customer_id", "s"), ("customer_name", "s"), ("segment", "s"), ("home_city", "s"),
                  ("home_country", "s"), ("confirmed_ato", "bool")],
    "identity_events": [("event_id", "s"), ("customer_id", "s"), ("event_ts", "ts"), ("event_type", "s"),
                        ("ip_address", "s"), ("device_id", "s"), ("city", "s"), ("country", "s"),
                        ("latitude", "num"), ("longitude", "num"), ("session_id", "s")],
    "account_changes": [("change_id", "s"), ("customer_id", "s"), ("change_ts", "ts"), ("change_type", "s"),
                        ("payee_id", "s"), ("session_id", "s")],
    "transactions": [("txn_id", "s"), ("customer_id", "s"), ("txn_ts", "ts"), ("amount", "num"),
                     ("payee_id", "s"), ("session_id", "s")],
}


def main():
    customers = build()
    tables = {"customers": customers,
              "identity_events": sorted(identity, key=lambda r: (r["event_ts"], r["event_id"])),
              "account_changes": sorted(changes, key=lambda r: (r["change_ts"], r["change_id"])),
              "transactions": sorted(txns, key=lambda r: (r["txn_ts"], r["txn_id"]))}
    for name, rows in tables.items():
        write_csv(f"{name}.csv", rows, [c for c, _ in COLS[name]])
    parts = ["-- Generated by data/generate_data.py. Synthetic data only.",
             "USE ROLE ATO_DEMO_ROLE;", "USE WAREHOUSE ATO_DEMO_WH;", "USE SCHEMA ACCOUNT_TAKEOVER.DATA;"]
    parts += [inserts(n.upper(), rows, COLS[n]) for n, rows in tables.items()]
    (SQL / "02_data.sql").write_text("\n\n".join(parts) + "\n")
    stories = {}
    for c in customers:
        if c["_story"]:
            stories[c["_story"]] = stories.get(c["_story"], 0) + 1
    print({k: len(v) for k, v in tables.items()}, stories)


if __name__ == "__main__":
    main()
