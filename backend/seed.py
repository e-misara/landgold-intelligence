"""Run once: python -m backend.seed"""
from backend.db import get_conn, init_db

SIGNALS = [
    ("municipality_zoning_change",    "Konya",   "Karatay ilçesi imar planı revizyonu — tarım → ticari",         78, 1),
    ("highway_extension",             "Ankara",  "Kuzey Çevre Yolu 42 km uzatma projesi ihaleye çıktı",          85, 1),
    ("airport_expansion",             "İzmir",   "Adnan Menderes 3. pist genişlemesi DHMI onayı alındı",         70, 1),
    ("industrial_zone_declaration",   "Bursa",   "OSB sınırı 1,200 dönüm genişletme kararnamesi imzalandı",      90, 1),
    ("tourism_incentive_zone",        "Antalya", "Kemer-Beldibi turizm teşvik bölgesi ilanı TBMM'de onaylandı", 65, 1),
    ("infrastructure_project_nearby", "Mersin",  "Liman genişlemesi — 3. konteyner terminali ihalesi açıldı",    80, 1),
]

def seed():
    init_db()
    with get_conn() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM gov_signals").fetchone()[0]
        if existing:
            print(f"Already seeded ({existing} signals). Skipping.")
            return
        conn.executemany(
            "INSERT INTO gov_signals (signal_type, region, description, confidence_pct, active) VALUES (?,?,?,?,?)",
            SIGNALS,
        )
    print(f"Seeded {len(SIGNALS)} gov signals.")

if __name__ == "__main__":
    seed()
