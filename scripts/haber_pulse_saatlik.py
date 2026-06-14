#!/usr/bin/env python3
"""
CC-Basın Saatlik Haber Pulse — B93 (anayasa_basin v2.0 § BÖLÜM 5)

Ulusal ajans + büyük gazete + sektörel RSS/sitemap kaynaklarını saatlik tarar.
HAM ingest, sentez Analiz şeridinde. Append-only havuz.

Disiplin:
- $0 (urllib + feedparser stdlib + requirements)
- Lane HAM: yorum/skor üretmez
- KVKK: kişi adı çekilmez (başlık + URL + tarih + kaynak)
- Telif ≤6 kelime: BAŞLIK 6 kelimeyi geçerse kısaltılır + "..."
- V36 etiket: havuz delta = "Δ X distinct yeni"
- TUZAK-7: dedup anahtarı (kaynak + url_hash)

Çıktı:
  data/havuz/haber/YYYY-MM-DD/HH.jsonl      — saatlik snapshot append-only
  data/audit/haber_pulse_YYYY-MM-DD.json    — günlük durum (TUZAK-3 ÜÇLÜ kanıt audit)
"""
import os
import json
import re
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAVUZ_DIR = os.path.join(BASE, 'data', 'havuz', 'haber')
AUDIT_DIR = os.path.join(BASE, 'data', 'audit')

UA = 'Mozilla/5.0 (compatible; TradiaBasinPulse/2.0; +https://tradiaturkey.com)'

# ============================================================================
# KAYNAK ENVANTERİ (B93 başlangıç — V53 ≥2 primer, TR-only, $0)
# Hepsi RSS veya sitemap.xml — saatlik ucuz fetch
# ============================================================================
KAYNAKLAR = [
    # Ulusal ajans
    {'id': 'aa_ekonomi', 'kaynak': 'AA Ekonomi', 'tip': 'rss',
     'url': 'https://www.aa.com.tr/tr/rss/default?cat=ekonomi'},
    # iha kaldırıldı (B94): 403 bot koruma

    # Büyük gazete ekonomi/emlak (B94 düzeltme)
    {'id': 'hurriyet_ekonomi', 'kaynak': 'Hürriyet Ekonomi', 'tip': 'rss',
     'url': 'https://www.hurriyet.com.tr/rss/ekonomi'},
    {'id': 'milliyet_emlak', 'kaynak': 'Milliyet Emlak', 'tip': 'rss',
     'url': 'https://www.milliyet.com.tr/rss/rssNew/emlakRss.xml'},
    {'id': 'sabah_ekonomi', 'kaynak': 'Sabah Ekonomi', 'tip': 'rss',
     'url': 'https://www.sabah.com.tr/rss/ekonomi.xml'},
    {'id': 'dunya_emlak', 'kaynak': 'Dünya Gazetesi Emlak', 'tip': 'rss',
     'url': 'https://www.dunya.com/rss?icerik=emlak'},
    # B94 YENİ büyük gazete
    {'id': 'cumhuriyet_ekonomi', 'kaynak': 'Cumhuriyet Ekonomi', 'tip': 'rss',
     'url': 'https://www.cumhuriyet.com.tr/rss/3.xml'},
    {'id': 'ntv_ekonomi', 'kaynak': 'NTV Ekonomi', 'tip': 'rss',
     'url': 'https://www.ntv.com.tr/ekonomi.rss'},
    {'id': 'haberturk_ekonomi', 'kaynak': 'Habertürk Ekonomi', 'tip': 'rss',
     'url': 'https://www.haberturk.com/rss/kategori/ekonomi.xml'},

    # Sektörel
    {'id': 'emlakkulisi', 'kaynak': 'Emlak Kulisi', 'tip': 'rss',
     'url': 'https://emlakkulisi.com/rss'},
    # insaattime kaldırıldı (B94): SSL sertifika hatası
    {'id': 'arkitera', 'kaynak': 'Arkitera', 'tip': 'rss',
     'url': 'https://www.arkitera.com/feed/'},

    # Resmî
    {'id': 'rg_anasayfa', 'kaynak': 'Resmî Gazete Ana', 'tip': 'sitemap_html',
     'url': 'https://www.resmigazete.gov.tr/'},
    {'id': 'toki_duyuru', 'kaynak': 'TOKİ Duyuru', 'tip': 'sitemap_html',
     'url': 'https://www.toki.gov.tr/duyurular'},
]

ANAHTAR_KELIMELER = [
    'konut', 'emlak', 'imar', 'kentsel donusum', 'kentsel dönüşüm', 'arsa',
    'mahalle', 'belediye', 'ihale', 'plan', 'park', 'toki', 'gayrimenkul',
    'inşaat', 'insaat', 'meclis', 'altyapı', 'altyapi', 'osb', 'metro',
    'köprü', 'kopru', 'doğalgaz', 'dogalgaz', 'satış', 'satis', 'tapu',
    'yapı', 'yapi', 'fiyat', 'kira', 'müteahhit', 'muteahhit', 'çed',
]


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def parse_rss(b):
    """RSS/Atom parser — başlık + link + pubdate çek."""
    if not b:
        return []
    try:
        import feedparser
        d = feedparser.parse(b)
        out = []
        for e in d.entries:
            baslik = (e.get('title') or '').strip()
            link = (e.get('link') or '').strip()
            tarih = (e.get('published') or e.get('updated') or '').strip()
            if baslik and link:
                out.append({'baslik': baslik, 'url': link, 'tarih': tarih})
        return out
    except Exception:
        return []


def parse_sitemap_html(b):
    """HTML link tarayıcı (sitemap.xml yoksa son haberler)."""
    if not b:
        return []
    txt = b.decode('utf-8', errors='replace')
    matches = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{15,200})</a>', txt)
    out = []
    seen = set()
    for url, baslik in matches:
        baslik = re.sub(r'\s+', ' ', baslik).strip()
        if not (15 <= len(baslik) <= 200):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append({'baslik': baslik, 'url': url, 'tarih': ''})
        if len(out) >= 50:
            break
    return out


def relevant(baslik):
    """Tradia-relevant filtre — başlık anahtar kelime taraması."""
    if not baslik:
        return False
    low = baslik.lower()
    return any(k in low for k in ANAHTAR_KELIMELER)


def kisaltma(baslik, max_kelime=6):
    """Telif ≤6 kelime — başlık kısaltma + ...

    Not: Bu KAYNAK kısaltması değil, BİZİM havuzumuza yazdığımız özet.
    Orijinal URL korunur, atıf format zorunlu.
    """
    if not baslik:
        return ''
    kelimeler = baslik.split()
    if len(kelimeler) <= max_kelime:
        return baslik
    return ' '.join(kelimeler[:max_kelime]) + '...'


def url_hash(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()[:12]


def main():
    now = datetime.now(timezone(timedelta(hours=3)))  # TR = UTC+3
    tarih_str = now.strftime('%Y-%m-%d')
    saat_str = now.strftime('%H')

    havuz_gun_dir = os.path.join(HAVUZ_DIR, tarih_str)
    os.makedirs(havuz_gun_dir, exist_ok=True)
    os.makedirs(AUDIT_DIR, exist_ok=True)
    havuz_dosya = os.path.join(havuz_gun_dir, f'{saat_str}.jsonl')

    # Önceki dedup havuzu (sadece bugün — saatlik hızlı dedup)
    onceki_hash = set()
    if os.path.exists(havuz_gun_dir):
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
        '_meta': 'CC-Basın Saatlik Haber Pulse (anayasa v2.0)',
        'tarih': tarih_str,
        'saat': saat_str,
        'calistirma_zamani': now.isoformat(),
        'kaynaklar': [],
        'toplam_fetch': 0,
        'toplam_relevant': 0,
        'toplam_yeni_distinct': 0,
        'havuz_dosya': havuz_dosya,
    }

    yeni_kayitlar = []

    for kaynak in KAYNAKLAR:
        b = fetch(kaynak['url'])
        if kaynak['tip'] == 'rss':
            kayitlar = parse_rss(b)
        else:
            kayitlar = parse_sitemap_html(b)

        relevant_kayitlar = [k for k in kayitlar if relevant(k['baslik'])]
        yeni = []
        for k in relevant_kayitlar:
            h = url_hash(k['url'])
            if h in onceki_hash:
                continue
            onceki_hash.add(h)
            yeni.append({
                'kaynak_id': kaynak['id'],
                'kaynak': kaynak['kaynak'],
                'baslik_kisa': kisaltma(k['baslik']),
                'url': k['url'],
                'tarih_pub': k['tarih'],
                'url_hash': h,
                'fetch_ts': now.isoformat(),
            })

        yeni_kayitlar.extend(yeni)
        rapor['kaynaklar'].append({
            'id': kaynak['id'],
            'kaynak': kaynak['kaynak'],
            'fetch_ok': b is not None,
            'fetch_sayisi': len(kayitlar),
            'relevant': len(relevant_kayitlar),
            'yeni_distinct': len(yeni),
        })
        rapor['toplam_fetch'] += len(kayitlar)
        rapor['toplam_relevant'] += len(relevant_kayitlar)
        rapor['toplam_yeni_distinct'] += len(yeni)

    # Havuz append (TUZAK-7 — distinct yeni sadece)
    if yeni_kayitlar:
        with open(havuz_dosya, 'a', encoding='utf-8') as f:
            for r in yeni_kayitlar:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')

    # Audit (günlük — saatlik üzerine yazılır, toplam günlük durum)
    audit_dosya = os.path.join(AUDIT_DIR, f'haber_pulse_{tarih_str}.json')
    onceki_audit = {}
    if os.path.exists(audit_dosya):
        try:
            with open(audit_dosya, encoding='utf-8') as f:
                onceki_audit = json.load(f)
        except Exception:
            pass
    if 'saatlik_log' not in onceki_audit:
        onceki_audit = {'_meta': rapor['_meta'], 'tarih': tarih_str, 'saatlik_log': []}
    onceki_audit['saatlik_log'].append({
        'saat': saat_str,
        'toplam_fetch': rapor['toplam_fetch'],
        'toplam_relevant': rapor['toplam_relevant'],
        'toplam_yeni_distinct': rapor['toplam_yeni_distinct'],
        'kaynak_durum': rapor['kaynaklar'],
        'havuz_dosya': havuz_dosya,
    })
    with open(audit_dosya, 'w', encoding='utf-8') as f:
        json.dump(onceki_audit, f, ensure_ascii=False, indent=2)

    print(f"[haber_pulse] {tarih_str} {saat_str}:00 — "
          f"fetch {rapor['toplam_fetch']} / relevant {rapor['toplam_relevant']} / "
          f"yeni distinct {rapor['toplam_yeni_distinct']}")
    print(f"[haber_pulse] havuz: {havuz_dosya}")
    print(f"[haber_pulse] audit: {audit_dosya}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
