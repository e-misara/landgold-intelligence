#!/usr/bin/env python3
"""
Tradia Primer Monitör Günlük Cron Script — B66

İki primer kanalı günlük tarar, delta tespit eder, log + audit dosyası üretir:
1. Bursa BBB imar plan değişiklikleri (HTML statik)
2. İBB Strapi meclis-kararlari (JSON API, sort=tarih:desc)

Çalıştırma:
  python3 scripts/primer_monitor_gunluk.py

Crontab önerisi (her gün 09:00):
  0 9 * * * cd /Users/GAC-A/landgold-agents && /usr/bin/python3 scripts/primer_monitor_gunluk.py >> /Users/GAC-A/Desktop/tradia/logs/primer_cron.log 2>&1

Çıktı:
  data/audit/primer_monitor_YYYY-MM-DD.json
  /Users/GAC-A/Desktop/tradia/logs/primer_cron.log (cron çıktı + delta uyarısı)
"""
import os
import sys
import re
import json
import urllib.request
import urllib.error
from datetime import datetime

BASE = '/Users/GAC-A/landgold-agents'
LOG_DIR = '/Users/GAC-A/Desktop/tradia/logs/primer_monitor'

BURSA_BBB_URL = 'https://www.bursa.bel.tr/imar_plan_degisiklikleri'
# B77: webapi.ibb.istanbul ÖLÜ (4 sprint HTTP 000); data.ibb.gov.tr CKAN açık veri portalı yeni kanal
IBB_CKAN_URL = 'https://data.ibb.gov.tr/api/3/action/package_list'
CSB_HABER_URL = 'https://www.csb.gov.tr/haberler'
CSB_DUYURU_URL = 'https://www.csb.gov.tr/duyurular'
BDDK_MEVZUAT_URL = 'https://www.bddk.org.tr/Mevzuat'
BDDK_GUNCEL_URL = 'https://www.bddk.org.tr/Duyuru/Liste/197'

UA = 'Mozilla/5.0 (compatible; TradiaPrimerMonitor/1.0)'


def fetch(url, timeout=15):
    """HTTP GET — None on error."""
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        return None


def parse_bursa_bbb(html_bytes):
    """Askıdaki imar planlarını listele."""
    if not html_bytes:
        return []
    txt = html_bytes.decode('utf-8', errors='replace')
    satirlar = re.findall(r'<(?:td|li|p)[^>]*>([^<]{30,400})</(?:td|li|p)>', txt)
    planlar = []
    for s in satirlar:
        if any(k in s.lower() for k in ['1/1000', '1/5000', '1/500', 'imar', 'plan', 'askı', 'onay']):
            metin = re.sub(r'[ \t\n]+', ' ', s).strip()
            if 30 <= len(metin) <= 400:
                planlar.append(metin)
    return planlar


def parse_ibb_ckan(json_bytes):
    """İBB CKAN açık veri portalı dataset listesi — Tradia-relevant filtre."""
    if not json_bytes:
        return []
    try:
        d = json.loads(json_bytes)
    except Exception:
        return []
    if not d.get('success'):
        return []
    pkgs = d.get('result', [])
    tradia_anahtar = ['imar', 'meclis', 'karar', 'plan', 'konut', 'yatirim', 'arsa', 'mahalle', 'bina', 'iski']
    bulgular = []
    for slug in pkgs:
        if any(k in slug.lower() for k in tradia_anahtar):
            bulgular.append({'slug': slug, 'kaynak': 'data.ibb.gov.tr CKAN'})
    return bulgular


BDDK_TRADIA_RELEVANT_YUKSEK = [
    'konut kredi', 'konut kredisi', 'gayrimenkul teminat', 'mortgage', 'ipotek',
    'yapılandırma', 'gayrimenkul', 'tasarruf finansman', 'faktoring', 'sermaye yeterlilik'
]
BDDK_TRADIA_RELEVANT_ORTA = [
    'kredi kartı', 'tüketici kredi', 'banka risk', 'kredi limit',
    'bankacılık kanun', 'banka kart'
]


def parse_bddk(html_bytes):
    """BDDK Mevzuat + Güncel Duyurular sayfasından link + başlık + Tradia-relevant filtre."""
    if not html_bytes:
        return []
    try:
        txt = html_bytes.decode('utf-8', errors='replace')
    except Exception:
        return []
    # /Mevzuat/Liste/* veya /Duyuru/Liste/* veya /Duyuru/Detay/* linkleri
    pattern = re.compile(r'href="(/(?:Mevzuat|Duyuru)/[^"]+)"[^>]*>([^<]{8,250})</a>', re.I)
    bulgular = []
    seen_url = set()
    for m in pattern.finditer(txt):
        url = m.group(1).strip()
        baslik = re.sub(r'[ \t\n]+', ' ', m.group(2)).strip()
        # HTML entity decode (basit)
        baslik = baslik.replace('&#252;', 'ü').replace('&#231;', 'ç').replace('&#246;', 'ö').replace('&#214;','Ö').replace('&#220;','Ü')
        if url in seen_url:
            continue
        seen_url.add(url)
        baslik_lower = baslik.lower()
        if any(k in baslik_lower for k in BDDK_TRADIA_RELEVANT_YUKSEK):
            tradia_skor = 'YÜKSEK'
        elif any(k in baslik_lower for k in BDDK_TRADIA_RELEVANT_ORTA):
            tradia_skor = 'ORTA'
        else:
            tradia_skor = 'İLGİSİZ'
        bulgular.append({
            'url': 'https://www.bddk.org.tr' + url,
            'baslik': baslik[:200],
            'tradia_skor': tradia_skor
        })
    return bulgular


def parse_csb(html_bytes):
    """ÇŞB haberler + duyurular sayfasından başlık + URL çek."""
    if not html_bytes:
        return []
    try:
        txt = html_bytes.decode('utf-8', errors='replace')
    except Exception:
        return []
    # /haberler/[slug] linkleri başlıkla
    pattern = re.compile(r'href="(https?://(?:www\.)?csb\.gov\.tr/(?:haberler|duyurular)/[^"]+)"[^>]*>([^<]{10,250})</a>', re.I)
    bulgular = []
    seen_url = set()
    for m in pattern.finditer(txt):
        url = m.group(1).strip()
        baslik = re.sub(r'[ \t\n]+', ' ', m.group(2)).strip()
        if url in seen_url:
            continue
        seen_url.add(url)
        bulgular.append({'url': url, 'baslik': baslik[:200]})
    return bulgular


def load_onceki(today_iso):
    """Bir önceki günün audit dosyasını yükle (varsa)."""
    # Bugünden önceki en yakın audit dosyasını ara
    audit_dir = os.path.join(BASE, 'data', 'audit')
    if not os.path.isdir(audit_dir):
        return None
    candidates = sorted([
        f for f in os.listdir(audit_dir)
        if f.startswith('primer_monitor_') and f.endswith('.json') and f < f'primer_monitor_{today_iso}.json'
    ], reverse=True)
    if not candidates:
        return None
    try:
        with open(os.path.join(audit_dir, candidates[0])) as fh:
            return json.load(fh)
    except Exception:
        return None


def main():
    bugun = datetime.now().strftime('%Y-%m-%d')
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(os.path.join(BASE, 'data', 'audit'), exist_ok=True)

    bursa_bytes = fetch(BURSA_BBB_URL)
    ibb_ckan_bytes = fetch(IBB_CKAN_URL)
    csb_haber_bytes = fetch(CSB_HABER_URL)
    csb_duyuru_bytes = fetch(CSB_DUYURU_URL)
    bddk_mevzuat_bytes = fetch(BDDK_MEVZUAT_URL)
    bddk_guncel_bytes = fetch(BDDK_GUNCEL_URL)

    bursa_planlar = parse_bursa_bbb(bursa_bytes)
    ibb_ckan_datasetler = parse_ibb_ckan(ibb_ckan_bytes)
    csb_haberler = parse_csb(csb_haber_bytes)
    csb_duyurular = parse_csb(csb_duyuru_bytes)
    bddk_mevzuat = parse_bddk(bddk_mevzuat_bytes)
    bddk_guncel = parse_bddk(bddk_guncel_bytes)

    # Önceki gün ile delta
    onceki = load_onceki(bugun)
    delta = {
        'bursa_yeni_plan': [],
        'bursa_kaldirilan_plan': [],
        'ibb_yeni_karar': [],
        'csb_yeni_haber': [],
        'csb_yeni_duyuru': [],
        'bddk_yeni_mevzuat': [],
        'bddk_yeni_guncel': [],
    }
    if onceki:
        onceki_bursa = set(onceki.get('bursa_bbb', {}).get('planlar', []))
        bugun_bursa = set(bursa_planlar)
        delta['bursa_yeni_plan'] = sorted(bugun_bursa - onceki_bursa)
        delta['bursa_kaldirilan_plan'] = sorted(onceki_bursa - bugun_bursa)
        onceki_ibb_ckan = {x.get('slug') for x in onceki.get('ibb_ckan', {}).get('datasetler', [])}
        bugun_ibb_ckan = {x['slug'] for x in ibb_ckan_datasetler}
        yeni_ckan = bugun_ibb_ckan - onceki_ibb_ckan
        delta['ibb_yeni_karar'] = [x for x in ibb_ckan_datasetler if x['slug'] in yeni_ckan]
        # ÇŞB delta
        onceki_csb_h = {x.get('url') for x in onceki.get('csb_haberler', {}).get('liste', [])}
        bugun_csb_h = {h['url'] for h in csb_haberler}
        delta['csb_yeni_haber'] = [h for h in csb_haberler if h['url'] not in onceki_csb_h]
        onceki_csb_d = {x.get('url') for x in onceki.get('csb_duyurular', {}).get('liste', [])}
        delta['csb_yeni_duyuru'] = [h for h in csb_duyurular if h['url'] not in onceki_csb_d]
        onceki_bddk_m = {x.get('url') for x in onceki.get('bddk_mevzuat', {}).get('liste', [])}
        delta['bddk_yeni_mevzuat'] = [h for h in bddk_mevzuat if h['url'] not in onceki_bddk_m]
        onceki_bddk_g = {x.get('url') for x in onceki.get('bddk_guncel', {}).get('liste', [])}
        delta['bddk_yeni_guncel'] = [h for h in bddk_guncel if h['url'] not in onceki_bddk_g]

    cikti = {
        '_meta': 'Tradia Primer Monitör Günlük Çıktı',
        'tarih': bugun,
        'calistirma_zamani': datetime.now().isoformat(),
        'bursa_bbb': {
            'url': BURSA_BBB_URL,
            'fetch_ok': bursa_bytes is not None,
            'plan_sayisi': len(bursa_planlar),
            'planlar': bursa_planlar,
            'akpinor_aski_durumu': any('Akpınar Mahallesi 1050 Konutlar' in p for p in bursa_planlar)
        },
        'ibb_ckan': {
            'url': IBB_CKAN_URL,
            'fetch_ok': ibb_ckan_bytes is not None,
            'dataset_sayisi_tradia_relevant': len(ibb_ckan_datasetler),
            'datasetler': ibb_ckan_datasetler,
            '_b77_not': 'webapi.ibb.istanbul ÖLÜ kabul (4 sprint HTTP 000); data.ibb.gov.tr CKAN açık veri portalı'
        },
        'csb_haberler': {
            'url': CSB_HABER_URL,
            'fetch_ok': csb_haber_bytes is not None,
            'liste_sayisi': len(csb_haberler),
            'liste': csb_haberler
        },
        'csb_duyurular': {
            'url': CSB_DUYURU_URL,
            'fetch_ok': csb_duyuru_bytes is not None,
            'liste_sayisi': len(csb_duyurular),
            'liste': csb_duyurular
        },
        'bddk_mevzuat': {
            'url': BDDK_MEVZUAT_URL,
            'fetch_ok': bddk_mevzuat_bytes is not None,
            'liste_sayisi': len(bddk_mevzuat),
            'liste': bddk_mevzuat
        },
        'bddk_guncel': {
            'url': BDDK_GUNCEL_URL,
            'fetch_ok': bddk_guncel_bytes is not None,
            'liste_sayisi': len(bddk_guncel),
            'liste': bddk_guncel
        },
        'delta_b_onceki_gun': delta
    }

    out_path = os.path.join(BASE, 'data', 'audit', f'primer_monitor_{bugun}.json')
    with open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(cikti, fh, ensure_ascii=False, indent=2)

    # Cron log özet
    print(f'[{bugun}] Primer monitör çalıştı')
    print(f'  Bursa BBB: {len(bursa_planlar)} plan (Akpınar askı: {cikti["bursa_bbb"]["akpinor_aski_durumu"]})')
    print(f'  İBB CKAN: {len(ibb_ckan_datasetler)} Tradia-relevant dataset (webapi.ibb.istanbul ölü)')
    print(f'  ÇŞB haberler: {len(csb_haberler)} link')
    print(f'  ÇŞB duyurular: {len(csb_duyurular)} link')
    bddk_m_yuksek = [b for b in bddk_mevzuat if b.get('tradia_skor') == 'YÜKSEK']
    bddk_m_orta = [b for b in bddk_mevzuat if b.get('tradia_skor') == 'ORTA']
    bddk_g_yuksek = [b for b in bddk_guncel if b.get('tradia_skor') == 'YÜKSEK']
    bddk_g_orta = [b for b in bddk_guncel if b.get('tradia_skor') == 'ORTA']
    print(f'  BDDK mevzuat: {len(bddk_mevzuat)} link (YÜKSEK {len(bddk_m_yuksek)} / ORTA {len(bddk_m_orta)})')
    print(f'  BDDK güncel: {len(bddk_guncel)} link (YÜKSEK {len(bddk_g_yuksek)} / ORTA {len(bddk_g_orta)})')
    for b in bddk_m_yuksek[:3] + bddk_g_yuksek[:3]:
        print(f'    ⭐ {b["baslik"][:120]}')
    if delta['bursa_yeni_plan']:
        print(f'  ⭐ Bursa YENİ plan: {len(delta["bursa_yeni_plan"])}')
        for p in delta['bursa_yeni_plan'][:3]:
            print(f'    - {p[:180]}')
    if delta['bursa_kaldirilan_plan']:
        print(f'  ⚠ Bursa kaldırılan: {len(delta["bursa_kaldirilan_plan"])}')
    if delta['ibb_yeni_karar']:
        print(f'  ⭐ İBB CKAN YENİ dataset: {len(delta["ibb_yeni_karar"])}')
        for k in delta['ibb_yeni_karar'][:3]:
            print(f'    - {k.get("slug", "?")[:140]}')
    if delta['csb_yeni_haber']:
        print(f'  ⭐ ÇŞB YENİ haber: {len(delta["csb_yeni_haber"])}')
        for h in delta['csb_yeni_haber'][:3]:
            print(f'    - {h["baslik"][:160]}')
    if delta['csb_yeni_duyuru']:
        print(f'  ⭐ ÇŞB YENİ duyuru: {len(delta["csb_yeni_duyuru"])}')
        for h in delta['csb_yeni_duyuru'][:3]:
            print(f'    - {h["baslik"][:160]}')
    print(f'  Çıktı: {out_path}')


if __name__ == '__main__':
    main()
