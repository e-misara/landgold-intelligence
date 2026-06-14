#!/usr/bin/env python3
"""
CC-Basın Piyasa Monitör Aylık — B93 (B87 borcu kapatıldı, anayasa v2.0 § BÖLÜM 5)

4 YEŞİL kanal (B87 keşfi):
  1. TCMB Konut Fiyat Endeksi (aylık PDF)
  2. GYODER yayınlar (çeyreklik)
  3. TÜİK veri portalı (URL keşif borcu — şimdilik ana sayfa probe)
  4. İstanbul Valiliği — Mevzuat + ÇED duyuruları (olay-bazlı)

Disiplin:
- $0
- Lane HAM: indirme + dosya hash + URL audit, yorum YOK
- Telif ≤6 kelime + atıf
- V53 ≥2 primer (her kanal kendi içinde primer)
"""
import os
import json
import re
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAVUZ_DIR = os.path.join(BASE, 'data', 'havuz', 'piyasa')
AUDIT_DIR = os.path.join(BASE, 'data', 'audit')

UA = 'Mozilla/5.0 (compatible; TradiaBasinPiyasa/2.0)'

KANALLAR = [
    {
        'id': 'tcmb_kfe',
        'kaynak': 'TCMB Konut Fiyat Endeksi',
        'tip': 'html_link_pdf',
        'url': 'https://www.tcmb.gov.tr/wps/wcm/connect/tr/tcmb+tr/main+menu/istatistikler/'
               'reel+sektor+istatistikleri/konut+fiyat+endeksi',
        'pdf_pattern': r'\.pdf"',
    },
    {
        'id': 'gyoder_yayinlar',
        'kaynak': 'GYODER Yayınlar',
        'tip': 'html_link_index',
        'url': 'https://www.gyoder.org.tr/yayinlar',
        'link_pattern': r'/yayinlar/onizleme/\d+',
    },
    {
        'id': 'tuik_veri_portali',
        'kaynak': 'TÜİK Veri Portalı (probe)',
        'tip': 'html_probe',
        'url': 'https://veriportali.tuik.gov.tr/',
    },
    {
        'id': 'istanbul_ced',
        'kaynak': 'İstanbul Valiliği ÇED Duyuruları',
        'tip': 'html_link_index',
        'url': 'https://www.istanbul.gov.tr/ced-duyurulari',
        'link_pattern': r'<a[^>]+href="([^"]+)"[^>]*>([^<]{15,250})</a>',
    },
    {
        'id': 'istanbul_kararlar',
        'kaynak': 'İstanbul Valiliği Genelge/Karar',
        'tip': 'html_link_index',
        'url': 'https://www.istanbul.gov.tr/genelgeler-ve-kararlar',
        'link_pattern': r'<a[^>]+href="([^"]+)"[^>]*>([^<]{15,250})</a>',
    },
]


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def parse_html_link_pdf(b, base_url):
    if not b:
        return []
    txt = b.decode('utf-8', errors='replace')
    pdfs = re.findall(r'href="([^"]+\.pdf)"', txt)
    out = []
    seen = set()
    for u in pdfs:
        if u in seen:
            continue
        seen.add(u)
        if u.startswith('/'):
            u = 'https://www.tcmb.gov.tr' + u
        elif not u.startswith('http'):
            continue
        out.append({'url': u, 'baslik': u.rsplit('/', 1)[-1]})
    return out


def parse_html_link_pattern(b, pattern):
    if not b:
        return []
    txt = b.decode('utf-8', errors='replace')
    # Eğer pattern bir <a> tag yakalıyorsa baslik+url, değilse sadece url
    if '<a' in pattern.lower() or 'href' in pattern.lower():
        matches = re.findall(pattern, txt)
        out = []
        seen = set()
        for m in matches:
            if isinstance(m, tuple):
                url, baslik = m[0], re.sub(r'\s+', ' ', m[1]).strip()
            else:
                url, baslik = m, ''
            if url in seen:
                continue
            seen.add(url)
            out.append({'url': url, 'baslik': baslik})
            if len(out) >= 40:
                break
        return out
    else:
        urls = re.findall(pattern, txt)
        out = []
        seen = set()
        for u in urls:
            if u in seen:
                continue
            seen.add(u)
            out.append({'url': u, 'baslik': ''})
        return out


def url_hash(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()[:12]


def main():
    now = datetime.now(timezone(timedelta(hours=3)))
    tarih_str = now.strftime('%Y-%m-%d')
    ay_str = now.strftime('%Y-%m')

    havuz_ay_dir = os.path.join(HAVUZ_DIR, ay_str)
    os.makedirs(havuz_ay_dir, exist_ok=True)
    os.makedirs(AUDIT_DIR, exist_ok=True)
    havuz_dosya = os.path.join(havuz_ay_dir, f'{tarih_str}.jsonl')

    # Önceki dedup (ay boyu)
    onceki_hash = set()
    for fn in sorted(os.listdir(havuz_ay_dir)) if os.path.exists(havuz_ay_dir) else []:
        if not fn.endswith('.jsonl'):
            continue
        with open(os.path.join(havuz_ay_dir, fn), encoding='utf-8') as f:
            for line in f:
                try:
                    r = json.loads(line)
                    onceki_hash.add(r.get('url_hash', ''))
                except Exception:
                    pass

    rapor = {
        '_meta': 'CC-Basın Piyasa Monitör Aylık (anayasa v2.0)',
        'tarih': tarih_str,
        'ay': ay_str,
        'calistirma_zamani': now.isoformat(),
        'kanallar': [],
        'toplam_yeni_distinct': 0,
        'havuz_dosya': havuz_dosya,
    }

    yeni_kayitlar = []

    for kanal in KANALLAR:
        b = fetch(kanal['url'])
        if kanal['tip'] == 'html_link_pdf':
            kayitlar = parse_html_link_pdf(b, kanal['url'])
        elif kanal['tip'] == 'html_link_index':
            kayitlar = parse_html_link_pattern(b, kanal['link_pattern'])
        else:  # html_probe — sadece erişim doğrulama
            kayitlar = []
            if b:
                kayitlar.append({'url': kanal['url'], 'baslik': 'erişim_ok'})

        yeni = []
        for k in kayitlar:
            h = url_hash(k['url'])
            if h in onceki_hash:
                continue
            onceki_hash.add(h)
            yeni.append({
                'kanal_id': kanal['id'],
                'kaynak': kanal['kaynak'],
                'baslik': k['baslik'][:200],
                'url': k['url'],
                'url_hash': h,
                'fetch_ts': now.isoformat(),
            })

        yeni_kayitlar.extend(yeni)
        rapor['kanallar'].append({
            'id': kanal['id'],
            'kaynak': kanal['kaynak'],
            'fetch_ok': b is not None,
            'fetch_sayisi': len(kayitlar),
            'yeni_distinct': len(yeni),
        })
        rapor['toplam_yeni_distinct'] += len(yeni)

    if yeni_kayitlar:
        with open(havuz_dosya, 'a', encoding='utf-8') as f:
            for r in yeni_kayitlar:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')

    audit_dosya = os.path.join(AUDIT_DIR, f'piyasa_monitor_{ay_str}.json')
    onceki = {}
    if os.path.exists(audit_dosya):
        try:
            with open(audit_dosya, encoding='utf-8') as f:
                onceki = json.load(f)
        except Exception:
            pass
    if 'gunluk_log' not in onceki:
        onceki = {'_meta': rapor['_meta'], 'ay': ay_str, 'gunluk_log': []}
    onceki['gunluk_log'].append({
        'tarih': tarih_str,
        'toplam_yeni_distinct': rapor['toplam_yeni_distinct'],
        'kanallar': rapor['kanallar'],
        'havuz_dosya': havuz_dosya,
    })
    with open(audit_dosya, 'w', encoding='utf-8') as f:
        json.dump(onceki, f, ensure_ascii=False, indent=2)

    print(f"[piyasa_monitor] {tarih_str} — yeni distinct {rapor['toplam_yeni_distinct']}")
    print(f"[piyasa_monitor] havuz: {havuz_dosya}")
    print(f"[piyasa_monitor] audit: {audit_dosya}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
