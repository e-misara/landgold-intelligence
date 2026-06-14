#!/usr/bin/env python3
"""
CC-Basın LOKAL SÜREKLİ MOTOR — B96 (anayasa v2.2 § BÖLÜM 5.5 ÇİFT-MOD KESİNTİSİZ TARAMA)

Bilgisayar AÇIKKEN devamlı çalışır — launchd KeepAlive=true ile çökerse yeniden başlar.
Bilgisayar kapanınca cloud GHA tier'lar baseline'ı sürdürür.

GUARDRAIL — feed'leri hammer'lamaz:
- Her feed için per-feed interval (yüksek-aktivite 4 dk · orta 15 dk · düşük 60 dk)
- Dedup md5(url)[:12] — cloud'la aynı havuz, çakışma YOK
- TUZAK-7: yalnız distinct yeni kayıt jsonl'a yazılır
- Akış log her döngü sonu: data/havuz/_akis_log.jsonl

Sinyal:
- SIGTERM/SIGINT → akış log son satır + temiz çıkış

Çalıştırma:
  python3 scripts/lokal_surekli_motor.py
  (launchd: ~/Library/LaunchAgents/com.tradia.ccbasin.pulse.plist KeepAlive=true)
"""
import os
import sys
import json
import re
import time
import signal
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAVUZ_HABER = os.path.join(BASE, 'data', 'havuz', 'haber')
HAVUZ_VALILIK = os.path.join(BASE, 'data', 'havuz', 'valilik')
AKIS_LOG = os.path.join(BASE, 'data', 'havuz', '_akis_log.jsonl')
STATE_FILE = os.path.join(BASE, 'data', 'havuz', '_lokal_state.json')

UA = 'Mozilla/5.0 (compatible; TradiaBasinLokal/2.0; +https://tradiaturkey.com)'
TR = timezone(timedelta(hours=3))


# ============================================================================
# FEED ENVANTERİ — interval saniye cinsinden (per-feed rate-limit guard)
# Yüksek-aktivite: 240 sn (4 dk)  ·  Orta: 900 sn (15 dk)  ·  Düşük: 3600 sn (60 dk)
# ============================================================================
FEEDS = [
    # Ulusal ajans + büyük gazete (haber_pulse_saatlik B94 ile aynı)
    {'id': 'aa_ekonomi', 'kategori': 'haber', 'tip': 'rss',
     'url': 'https://www.aa.com.tr/tr/rss/default?cat=ekonomi', 'interval': 900},
    {'id': 'hurriyet_ekonomi', 'kategori': 'haber', 'tip': 'rss',
     'url': 'https://www.hurriyet.com.tr/rss/ekonomi', 'interval': 240},
    {'id': 'milliyet_emlak', 'kategori': 'haber', 'tip': 'rss',
     'url': 'https://www.milliyet.com.tr/rss/rssNew/emlakRss.xml', 'interval': 900},
    {'id': 'sabah_ekonomi', 'kategori': 'haber', 'tip': 'rss',
     'url': 'https://www.sabah.com.tr/rss/ekonomi.xml', 'interval': 900},
    {'id': 'dunya_emlak', 'kategori': 'haber', 'tip': 'rss',
     'url': 'https://www.dunya.com/rss?icerik=emlak', 'interval': 900},
    {'id': 'cumhuriyet_ekonomi', 'kategori': 'haber', 'tip': 'rss',
     'url': 'https://www.cumhuriyet.com.tr/rss/3.xml', 'interval': 240},
    {'id': 'ntv_ekonomi', 'kategori': 'haber', 'tip': 'rss',
     'url': 'https://www.ntv.com.tr/ekonomi.rss', 'interval': 240},
    {'id': 'haberturk_ekonomi', 'kategori': 'haber', 'tip': 'rss',
     'url': 'https://www.haberturk.com/rss/kategori/ekonomi.xml', 'interval': 900},
    # Sektörel (yüksek yoğunluk B94 verisi)
    {'id': 'emlakkulisi', 'kategori': 'haber', 'tip': 'rss',
     'url': 'https://emlakkulisi.com/rss', 'interval': 240},
    {'id': 'arkitera', 'kategori': 'haber', 'tip': 'rss',
     'url': 'https://www.arkitera.com/feed/', 'interval': 240},
    # Resmî
    {'id': 'rg_anasayfa', 'kategori': 'haber', 'tip': 'sitemap_html',
     'url': 'https://www.resmigazete.gov.tr/', 'interval': 1800},
    {'id': 'toki_duyuru', 'kategori': 'haber', 'tip': 'sitemap_html',
     'url': 'https://www.toki.gov.tr/duyurular', 'interval': 1800},
    # Metro valilik (7 il — düşük; valilik genelde günde 1-2 duyuru)
    {'id': 'valilik_istanbul', 'kategori': 'valilik', 'tip': 'html_duyuru',
     'url': 'https://www.istanbul.gov.tr/duyurular', 'interval': 3600},
    {'id': 'valilik_ankara', 'kategori': 'valilik', 'tip': 'html_duyuru',
     'url': 'https://www.ankara.gov.tr/duyurular', 'interval': 3600},
    {'id': 'valilik_izmir', 'kategori': 'valilik', 'tip': 'html_duyuru',
     'url': 'https://www.izmir.gov.tr/duyurular', 'interval': 3600},
    {'id': 'valilik_bursa', 'kategori': 'valilik', 'tip': 'html_duyuru',
     'url': 'https://www.bursa.gov.tr/duyurular', 'interval': 3600},
    {'id': 'valilik_antalya', 'kategori': 'valilik', 'tip': 'html_duyuru',
     'url': 'https://www.antalya.gov.tr/duyurular', 'interval': 3600},
    {'id': 'valilik_kocaeli', 'kategori': 'valilik', 'tip': 'html_duyuru',
     'url': 'https://www.kocaeli.gov.tr/duyurular', 'interval': 3600},
    {'id': 'valilik_gaziantep', 'kategori': 'valilik', 'tip': 'html_duyuru',
     'url': 'https://www.gaziantep.gov.tr/duyurular', 'interval': 3600},
    # B97 ekleme — İBB sitemap (belediye katmanı, 6 SPA-gated illerden biri için kısmî kapsama)
    {'id': 'ibb_sitemap', 'kategori': 'haber', 'tip': 'sitemap_html',
     'url': 'https://www.ibb.istanbul/sitemap.xml', 'interval': 1800},
]

ANAHTAR_KELIMELER = [
    'konut', 'emlak', 'imar', 'kentsel donusum', 'kentsel dönüşüm', 'arsa',
    'mahalle', 'belediye', 'ihale', 'plan', 'park', 'toki', 'gayrimenkul',
    'inşaat', 'insaat', 'meclis', 'altyapı', 'altyapi', 'osb', 'metro',
    'köprü', 'kopru', 'doğalgaz', 'dogalgaz', 'satış', 'satis', 'tapu',
    'yapı', 'yapi', 'fiyat', 'kira', 'müteahhit', 'muteahhit', 'çed', 'ced',
    'taşınmaz', 'tasinmaz', 'duyuru', 'genelge', 'karar',
]

STOP = False


def _signal_handler(signum, frame):
    global STOP
    STOP = True
    print(f"[motor] SIGNAL {signum} — temiz kapanıyor...", flush=True)


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


def now_tr():
    return datetime.now(TR)


def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), None
    except Exception as e:
        return None, str(e)[:80]


def parse_rss(b):
    if not b:
        return []
    try:
        import feedparser
        d = feedparser.parse(b)
        out = []
        for e in d.entries:
            t = (e.get('title') or '').strip()
            l = (e.get('link') or '').strip()
            tar = (e.get('published') or e.get('updated') or '').strip()
            if t and l:
                out.append({'baslik': t, 'url': l, 'tarih': tar})
        return out
    except Exception:
        return []


def parse_sitemap_html(b):
    if not b:
        return []
    txt = b.decode('utf-8', errors='replace')
    matches = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{15,250})</a>', txt)
    out, seen = [], set()
    for url, baslik in matches:
        baslik = re.sub(r'\s+', ' ', baslik).strip()
        if not (15 <= len(baslik) <= 250) or url in seen:
            continue
        seen.add(url)
        out.append({'baslik': baslik, 'url': url, 'tarih': ''})
        if len(out) >= 50:
            break
    return out


def parse_html_duyuru(b, base_url):
    if not b:
        return []
    txt = b.decode('utf-8', errors='replace')
    matches = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{15,250})</a>', txt)
    out, seen = [], set()
    for url, baslik in matches:
        baslik = re.sub(r'\s+', ' ', baslik).strip()
        if not (15 <= len(baslik) <= 250) or url in seen:
            continue
        seen.add(url)
        if url.startswith('/'):
            url = base_url.rstrip('/').rsplit('/', 1)[0] + url
        elif not url.startswith('http'):
            continue
        out.append({'baslik': baslik, 'url': url, 'tarih': ''})
        if len(out) >= 60:
            break
    return out


def relevant(baslik):
    if not baslik:
        return False
    low = baslik.lower()
    return any(k in low for k in ANAHTAR_KELIMELER)


def kisaltma(baslik, maxk=6):
    if not baslik:
        return ''
    k = baslik.split()
    return baslik if len(k) <= maxk else ' '.join(k[:maxk]) + '...'


def url_hash(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()[:12]


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'son_fetch': {}, 'dedup_seen': []}


def save_state(s):
    # dedup_seen son 5000'ile sınırla — disk şişme önleme
    s['dedup_seen'] = s['dedup_seen'][-5000:]
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


def havuz_yaz(feed, kayitlar, now):
    """Havuza append-only yaz. Cloud ile aynı yapı — dedup md5 üzerinden."""
    if not kayitlar:
        return
    tarih_str = now.strftime('%Y-%m-%d')
    saat_str = now.strftime('%H')
    kat = feed['kategori']
    if kat == 'haber':
        gun_dir = os.path.join(HAVUZ_HABER, tarih_str)
        dosya = os.path.join(gun_dir, f'{saat_str}.jsonl')
    elif kat == 'valilik':
        gun_dir = os.path.join(HAVUZ_VALILIK, tarih_str)
        dosya = os.path.join(gun_dir, f'lokal_{saat_str}.jsonl')
    else:
        return
    os.makedirs(gun_dir, exist_ok=True)
    with open(dosya, 'a', encoding='utf-8') as f:
        for r in kayitlar:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')


def akis_log(satir):
    os.makedirs(os.path.dirname(AKIS_LOG), exist_ok=True)
    with open(AKIS_LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(satir, ensure_ascii=False) + '\n')


def feed_process(feed, state):
    """Bir feed'i işle — interval ihlali varsa SKIP, yoksa fetch+dedup+yaz."""
    now = now_tr()
    son_ts = state['son_fetch'].get(feed['id'])
    if son_ts:
        try:
            son = datetime.fromisoformat(son_ts)
            if (now - son).total_seconds() < feed['interval']:
                return {'skip': True}
        except Exception:
            pass

    state['son_fetch'][feed['id']] = now.isoformat()

    b, err = fetch(feed['url'])
    if err:
        return {'feed': feed['id'], 'err': err, 'fetch': 0, 'rel': 0, 'yeni': 0}

    if feed['tip'] == 'rss':
        kayitlar = parse_rss(b)
    elif feed['tip'] == 'sitemap_html':
        kayitlar = parse_sitemap_html(b)
    elif feed['tip'] == 'html_duyuru':
        kayitlar = parse_html_duyuru(b, feed['url'])
    else:
        kayitlar = []

    rel = [k for k in kayitlar if relevant(k['baslik'])]
    dedup_set = set(state['dedup_seen'])
    yeni = []
    for k in rel:
        h = url_hash(k['url'])
        if h in dedup_set:
            continue
        dedup_set.add(h)
        state['dedup_seen'].append(h)
        yeni.append({
            'feed_id': feed['id'],
            'kategori': feed['kategori'],
            'kaynak': feed.get('kaynak') or feed['id'],
            'baslik_kisa': kisaltma(k['baslik']),
            'url': k['url'],
            'tarih_pub': k.get('tarih', ''),
            'url_hash': h,
            'fetch_ts': now.isoformat(),
            'mod': 'lokal',
        })

    havuz_yaz(feed, yeni, now)
    return {
        'feed': feed['id'],
        'fetch': len(kayitlar),
        'rel': len(rel),
        'yeni': len(yeni),
        'err': None,
    }


def main():
    print(f"[motor] B96 LOKAL SÜREKLİ MOTOR başlatıldı — {now_tr().isoformat()}", flush=True)
    print(f"[motor] {len(FEEDS)} feed · KeepAlive=launchd · dedup={STATE_FILE}", flush=True)
    state = load_state()

    dongu = 0
    while not STOP:
        dongu += 1
        sonuc = []
        for feed in FEEDS:
            if STOP:
                break
            try:
                r = feed_process(feed, state)
                if not r.get('skip'):
                    sonuc.append(r)
            except Exception as e:
                sonuc.append({'feed': feed['id'], 'err': str(e)[:60],
                              'fetch': 0, 'rel': 0, 'yeni': 0})

        if sonuc:
            toplam_yeni = sum(r['yeni'] for r in sonuc)
            satir = {
                'ts': now_tr().isoformat(),
                'dongu': dongu,
                'islenen_feed': len(sonuc),
                'toplam_yeni_distinct': toplam_yeni,
                'detay': sonuc,
            }
            akis_log(satir)
            save_state(state)
            print(f"[motor] döngü {dongu} · işlenen {len(sonuc)} feed · yeni {toplam_yeni} distinct",
                  flush=True)

        # Sleep — kısa, ama feed interval'ları işin doğal düzenleyicisi
        # 30 sn döngü turu — her feed kendi interval'ında işleniyor
        for _ in range(30):
            if STOP:
                break
            time.sleep(1)

    save_state(state)
    print(f"[motor] döngü sonu {dongu} · temiz çıkış {now_tr().isoformat()}", flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
