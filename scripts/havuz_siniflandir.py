#!/usr/bin/env python3
"""
CC-Basın Havuz Sınıflandırıcı — B98 (anayasa v2.2 § BÖLÜM 1 — sınıflar, sentez DEĞİL)

Günlük tarama:
- data/havuz/<kanal>/.../<saat>.jsonl tüm kayıtları okur
- haber_classifier.siniflandir() uygular
- data/havuz/siniflandirilmis/YYYY-MM-DD.jsonl YAZAR (idempotent — aynı gün yeniden yazılır)

KESİN ŞEMA (TUZAK-8 önleme):
  Her satır = kayıt + 'siniflar' alanı (haber_classifier.SCHEMA_VERSION)
  Aynı url_hash mükerrer = SON yazılanı kabul (dedup tek dosya scope)

Disiplin:
- Lane HAM: sentez/öneri YOK
- $0
- TUZAK-7: distinct url_hash kontrolü
"""
import os
import sys
import json
import glob
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SINIFLI_DIR = os.path.join(BASE, 'data', 'havuz', 'siniflandirilmis')
TR = timezone(timedelta(hours=3))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from haber_classifier import siniflandir, SCHEMA_VERSION


def gun_havuz_dosyalari(tarih_str):
    """Belirli tarih için havuz dosyalarını döndür."""
    desenler = [
        os.path.join(BASE, 'data', 'havuz', 'haber', tarih_str, '*.jsonl'),
        os.path.join(BASE, 'data', 'havuz', 'valilik', tarih_str, '*.jsonl'),
    ]
    dosyalar = []
    for d in desenler:
        dosyalar.extend(glob.glob(d))
    return dosyalar


def main():
    tarih = sys.argv[1] if len(sys.argv) > 1 else datetime.now(TR).strftime('%Y-%m-%d')
    dosyalar = gun_havuz_dosyalari(tarih)
    if not dosyalar:
        print(f"❌ {tarih} için havuz dosyası YOK")
        return 1

    print(f"=== HAVUZ SINIFLANDIR · {tarih} · classifier {SCHEMA_VERSION} ===")
    print(f"Dosya: {len(dosyalar)}")

    os.makedirs(SINIFLI_DIR, exist_ok=True)
    cikti_dosya = os.path.join(SINIFLI_DIR, f'{tarih}.jsonl')

    # Önceki gün sınıflı dosya varsa dedup için url_hash setini al
    yazilan_hash = set()
    if os.path.exists(cikti_dosya):
        # Idempotent: silip yeniden yaz
        os.remove(cikti_dosya)

    istatistik = {
        'toplam_okunan': 0,
        'distinct_yazilan': 0,
        'kategori_dolu': 0,
        'il_dolu': 0,
        'kategori_dagilim': {},
        'il_dagilim': {},
        'kazanan_firma_dolu': 0,
    }

    with open(cikti_dosya, 'w', encoding='utf-8') as out:
        for d in dosyalar:
            with open(d, encoding='utf-8') as fh:
                for ln in fh:
                    try:
                        k = json.loads(ln)
                    except Exception:
                        continue
                    istatistik['toplam_okunan'] += 1
                    h = k.get('url_hash', '')
                    if h in yazilan_hash:
                        continue
                    yazilan_hash.add(h)
                    siniflandir(k)
                    out.write(json.dumps(k, ensure_ascii=False) + '\n')
                    istatistik['distinct_yazilan'] += 1
                    s = k['siniflar']
                    if s['iller']:
                        istatistik['il_dolu'] += 1
                        for il in s['iller']:
                            istatistik['il_dagilim'][il] = istatistik['il_dagilim'].get(il, 0) + 1
                    if s['kategoriler']:
                        istatistik['kategori_dolu'] += 1
                        for kat in s['kategoriler']:
                            istatistik['kategori_dagilim'][kat] = istatistik['kategori_dagilim'].get(kat, 0) + 1
                    if s.get('kazanan_firma_aday'):
                        istatistik['kazanan_firma_dolu'] += 1

    print(f"Okunan ham: {istatistik['toplam_okunan']}")
    print(f"Distinct yazılan: {istatistik['distinct_yazilan']}")
    print(f"İl etiketli: {istatistik['il_dolu']}")
    print(f"Kategori etiketli: {istatistik['kategori_dolu']}")
    print(f"Kazanan firma adayı: {istatistik['kazanan_firma_dolu']}")
    print(f"Çıktı: {cikti_dosya}")

    # Audit
    audit = {
        '_meta': 'CC-Basın Havuz Sınıflandırıcı (B98 anayasa v2.2)',
        'tarih': tarih,
        'classifier_version': SCHEMA_VERSION,
        'cikti_dosya': cikti_dosya,
        'istatistik': istatistik,
    }
    audit_dosya = os.path.join(BASE, 'data', 'audit', f'havuz_siniflandir_{tarih}.json')
    with open(audit_dosya, 'w', encoding='utf-8') as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)
    print(f"Audit: {audit_dosya}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
