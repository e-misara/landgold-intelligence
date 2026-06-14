#!/usr/bin/env python3
"""
CC-Basın 81-İl Valilik Pulse — B94 (anayasa v2.0 § BÖLÜM 5)

81 valilik resmî duyuru sayfası tarayıcı.
Pattern doğrulandı (B94 probe): https://www.<il>.gov.tr/duyurular → 79/81 OK.

Tiered frekans:
  --tier metro       7 yüksek-aktivite il (yarım-günlük)
  --tier buyuksehir  16 ek büyükşehir (günlük)
  --tier kalan       58 kalan il (günlük batch — sabah)
  --tier hepsi       81 il (default — günlük dispatch)

Disiplin:
- $0 (public repo + GHA sınırsız)
- Lane HAM: yorum/skor YOK, başlık + URL + tarih
- KVKK: kişi adı çekilmez
- Telif ≤6 kelime (kısaltma)
- TUZAK-7: dedup md5(url)[:12]

Çıktı:
  data/havuz/valilik/YYYY-MM-DD/<tier>_HH.jsonl
  data/audit/valilik_pulse_<tier>_YYYY-MM-DD.json
"""
import os
import sys
import json
import re
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAVUZ_DIR = os.path.join(BASE, 'data', 'havuz', 'valilik')
AUDIT_DIR = os.path.join(BASE, 'data', 'audit')

UA = 'Mozilla/5.0 (compatible; TradiaBasinValilik/2.0; +https://tradiaturkey.com)'

# 81 il — TÜİK plaka kod sıralı, slug normalize
TUM_ILLER = [
    'adana', 'adiyaman', 'afyonkarahisar', 'agri', 'aksaray', 'amasya',
    'ankara', 'antalya', 'ardahan', 'artvin', 'aydin', 'balikesir',
    'bartin', 'batman', 'bayburt', 'bilecik', 'bingol', 'bitlis',
    'bolu', 'burdur', 'bursa', 'canakkale', 'cankiri', 'corum',
    'denizli', 'diyarbakir', 'duzce', 'edirne', 'elazig', 'erzincan',
    'erzurum', 'eskisehir', 'gaziantep', 'giresun', 'gumushane', 'hakkari',
    'hatay', 'igdir', 'isparta', 'istanbul', 'izmir', 'kahramanmaras',
    'karabuk', 'karaman', 'kars', 'kastamonu', 'kayseri', 'kilis',
    'kirikkale', 'kirklareli', 'kirsehir', 'kocaeli', 'konya', 'kutahya',
    'malatya', 'manisa', 'mardin', 'mersin', 'mugla', 'mus',
    'nevsehir', 'nigde', 'ordu', 'osmaniye', 'rize', 'sakarya',
    'samsun', 'sanliurfa', 'siirt', 'sinop', 'sirnak', 'sivas',
    'tekirdag', 'tokat', 'trabzon', 'tunceli', 'usak', 'van',
    'yalova', 'yozgat', 'zonguldak',
]

# Tier 1: yüksek-aktivite metropol (yarım-günlük)
TIER_METRO = ['istanbul', 'ankara', 'izmir', 'bursa', 'antalya', 'kocaeli', 'gaziantep']

# Tier 2: kalan büyükşehir (günlük)
TIER_BUYUKSEHIR_KALAN = [
    'adana', 'aydin', 'balikesir', 'denizli', 'diyarbakir', 'erzurum',
    'eskisehir', 'hatay', 'kahramanmaras', 'kayseri', 'konya', 'malatya',
    'manisa', 'mardin', 'mersin', 'mugla', 'ordu', 'sakarya', 'samsun',
    'sanliurfa', 'tekirdag', 'trabzon', 'van',
]

ANAHTAR_KELIMELER = [
    'konut', 'emlak', 'imar', 'kentsel donusum', 'kentsel dönüşüm', 'arsa',
    'mahalle', 'belediye', 'ihale', 'plan', 'park', 'toki', 'gayrimenkul',
    'inşaat', 'insaat', 'meclis', 'altyapı', 'altyapi', 'osb', 'metro',
    'köprü', 'kopru', 'doğalgaz', 'dogalgaz', 'satış', 'satis', 'tapu',
    'yapı', 'yapi', 'çed', 'ced', 'duyuru', 'genelge', 'karar',
    'taşınmaz', 'tasinmaz', 'milli emlak', 'devlet ihale',
]


def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def parse_duyurular(html, il, base_url):
    """Valilik /duyurular sayfasından başlık + URL çek."""
    if not html:
        return []
    txt = html.decode('utf-8', errors='replace')
    # Kullanılan pattern: <a href=...>başlık</a> ve title attribute
    matches = re.findall(
        r'<a[^>]+href="([^"]+)"[^>]*>([^<]{15,250})</a>', txt
    )
    out = []
    seen = set()
    for url, baslik in matches:
        baslik = re.sub(r'\s+', ' ', baslik).strip()
        if not (15 <= len(baslik) <= 250):
            continue
        if url in seen:
            continue
        seen.add(url)
        # Relative URL ise base'e ek
        if url.startswith('/'):
            url = base_url.rstrip('/') + url
        elif not url.startswith('http'):
            continue
        out.append({'baslik': baslik, 'url': url})
        if len(out) >= 80:
            break
    return out


def relevant(baslik):
    if not baslik:
        return False
    low = baslik.lower()
    return any(k in low for k in ANAHTAR_KELIMELER)


def kisaltma(baslik, max_kelime=6):
    if not baslik:
        return ''
    kelimeler = baslik.split()
    if len(kelimeler) <= max_kelime:
        return baslik
    return ' '.join(kelimeler[:max_kelime]) + '...'


def url_hash(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()[:12]


def secim_tier(tier):
    if tier == 'metro':
        return TIER_METRO
    if tier == 'buyuksehir':
        return TIER_BUYUKSEHIR_KALAN
    if tier == 'kalan':
        return [il for il in TUM_ILLER if il not in TIER_METRO and il not in TIER_BUYUKSEHIR_KALAN]
    if tier == 'hepsi':
        return TUM_ILLER
    raise SystemExit(f'Bilinmeyen tier: {tier}')


def main():
    tier = sys.argv[1] if len(sys.argv) > 1 else 'hepsi'
    iller = secim_tier(tier)

    now = datetime.now(timezone(timedelta(hours=3)))
    tarih_str = now.strftime('%Y-%m-%d')
    saat_str = now.strftime('%H')

    havuz_gun_dir = os.path.join(HAVUZ_DIR, tarih_str)
    os.makedirs(havuz_gun_dir, exist_ok=True)
    os.makedirs(AUDIT_DIR, exist_ok=True)
    havuz_dosya = os.path.join(havuz_gun_dir, f'{tier}_{saat_str}.jsonl')

    # Dedup (gün boyu — tier'lar arası dedup için)
    onceki_hash = set()
    for fn in sorted(os.listdir(havuz_gun_dir)):
        if not fn.endswith('.jsonl'):
            continue
        with open(os.path.join(havuz_gun_dir, fn), encoding='utf-8') as f:
            for line in f:
                try:
                    r = json.loads(line)
                    onceki_hash.add(r.get('url_hash', ''))
                except Exception:
                    pass

    rapor = {
        '_meta': 'CC-Basın Valilik 81-il Pulse (anayasa v2.0)',
        'tier': tier,
        'tarih': tarih_str,
        'saat': saat_str,
        'calistirma_zamani': now.isoformat(),
        'il_sayisi': len(iller),
        'il_durum': [],
        'toplam_relevant': 0,
        'toplam_yeni_distinct': 0,
        'havuz_dosya': havuz_dosya,
    }

    yeni_kayitlar = []

    for il in iller:
        base = f'https://www.{il}.gov.tr'
        url = base + '/duyurular'
        b = fetch(url)
        kayitlar = parse_duyurular(b, il, base) if b else []
        relevant_kayitlar = [k for k in kayitlar if relevant(k['baslik'])]

        yeni = []
        for k in relevant_kayitlar:
            h = url_hash(k['url'])
            if h in onceki_hash:
                continue
            onceki_hash.add(h)
            yeni.append({
                'il': il,
                'kaynak': f'{il}.gov.tr/duyurular',
                'baslik_kisa': kisaltma(k['baslik']),
                'url': k['url'],
                'url_hash': h,
                'fetch_ts': now.isoformat(),
            })

        yeni_kayitlar.extend(yeni)
        rapor['il_durum'].append({
            'il': il,
            'fetch_ok': b is not None,
            'fetch_sayisi': len(kayitlar),
            'relevant': len(relevant_kayitlar),
            'yeni_distinct': len(yeni),
        })
        rapor['toplam_relevant'] += len(relevant_kayitlar)
        rapor['toplam_yeni_distinct'] += len(yeni)

    if yeni_kayitlar:
        with open(havuz_dosya, 'a', encoding='utf-8') as f:
            for r in yeni_kayitlar:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')

    audit_dosya = os.path.join(AUDIT_DIR, f'valilik_pulse_{tier}_{tarih_str}.json')
    with open(audit_dosya, 'w', encoding='utf-8') as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)

    aktif = sum(1 for x in rapor['il_durum'] if x['fetch_ok'])
    print(f"[valilik_pulse {tier}] {tarih_str} {saat_str}:00 — "
          f"{aktif}/{len(iller)} il aktif · "
          f"relevant {rapor['toplam_relevant']} · "
          f"yeni distinct {rapor['toplam_yeni_distinct']}")
    print(f"[valilik_pulse {tier}] havuz: {havuz_dosya}")
    print(f"[valilik_pulse {tier}] audit: {audit_dosya}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
