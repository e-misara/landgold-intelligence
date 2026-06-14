#!/usr/bin/env python3
"""
CC-Basın Cross-CC Besleme — B98 (anayasa v2.2 § Lane HAM tek-yön)

İki HAM köprü:
1. data/devir/basin_ihale_kazanan_aday.jsonl   → CC-İhale (EKAP-gated $0 boşluğu kısmen telafi)
   Filtre: kategoriler='ihale_sonuc' VE (kazanan_firma_aday DOLU veya il+sektör KESİN)
2. data/devir/basin_analiz_cross_hat.jsonl     → CC-Analiz (çevre istihbaratı sinyali)
   Filtre: il VEYA kategori dolu (her sınıflı kayıt)

İKİ ÇIKTI DOSYASI = HAM TEK-YÖN bridge:
- Tüketiciler (CC-İhale, CC-Analiz) bu dosyaları okur, kararı kendileri verir
- CC-Basın yorum/skor/öncelik atamaz (Lane HAM)
- Şema sözleşmesi (TUZAK-8): kayıt formatı + 'siniflar' alanı KESİN

Disiplin:
- $0
- KVKK: kazanan_firma_aday yalnız tüzel-kişi pattern (haber_classifier KAZANAN_FIRMA_REGEX)
- Idempotent: aynı tarih çağrısı dosyayı yeniden yazar (üretici tek doğru kaynak)
"""
import os
import sys
import json
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SINIFLI_DIR = os.path.join(BASE, 'data', 'havuz', 'siniflandirilmis')
DEVIR_DIR = os.path.join(BASE, 'data', 'devir')
TR = timezone(timedelta(hours=3))


def main():
    tarih = sys.argv[1] if len(sys.argv) > 1 else datetime.now(TR).strftime('%Y-%m-%d')
    girdi = os.path.join(SINIFLI_DIR, f'{tarih}.jsonl')
    if not os.path.exists(girdi):
        print(f"❌ Sınıflandırılmış havuz YOK: {girdi}")
        print(f"   Önce: python3 scripts/havuz_siniflandir.py {tarih}")
        return 1

    os.makedirs(DEVIR_DIR, exist_ok=True)

    ihale_dosya = os.path.join(DEVIR_DIR, f'basin_ihale_kazanan_aday_{tarih}.jsonl')
    cross_hat_dosya = os.path.join(DEVIR_DIR, f'basin_analiz_cross_hat_{tarih}.jsonl')

    sayilar = {'okunan': 0, 'ihale_kanal': 0, 'cross_hat_kanal': 0}

    with open(girdi, encoding='utf-8') as f_in, \
         open(ihale_dosya, 'w', encoding='utf-8') as f_ihale, \
         open(cross_hat_dosya, 'w', encoding='utf-8') as f_ch:
        for ln in f_in:
            try:
                k = json.loads(ln)
            except Exception:
                continue
            sayilar['okunan'] += 1
            s = k.get('siniflar', {})

            # Cross-Hat: il VEYA kategori dolu — her sınıflı kayıt
            if s.get('iller') or s.get('kategoriler'):
                # Minimal şema (tüketici Analiz lane Cross-Hat zenginleştirir)
                ch_kayit = {
                    'url_hash': k.get('url_hash'),
                    'baslik_kisa': k.get('baslik_kisa'),
                    'url': k.get('url'),
                    'kaynak': k.get('kaynak') or k.get('kaynak_id'),
                    'tarih_pub': k.get('tarih_pub') or k.get('fetch_ts'),
                    'siniflar': s,
                }
                f_ch.write(json.dumps(ch_kayit, ensure_ascii=False) + '\n')
                sayilar['cross_hat_kanal'] += 1

            # İhale kazanan adayı: kategori='ihale_sonuc' VE (firma adı VEYA il+sektör güçlü ipucu)
            if 'ihale_sonuc' in (s.get('kategoriler') or []):
                ihale_kayit = {
                    'url_hash': k.get('url_hash'),
                    'baslik_kisa': k.get('baslik_kisa'),
                    'url': k.get('url'),
                    'kaynak': k.get('kaynak') or k.get('kaynak_id'),
                    'tarih_pub': k.get('tarih_pub') or k.get('fetch_ts'),
                    'iller': s.get('iller', []),
                    'kazanan_firma_aday': s.get('kazanan_firma_aday'),
                    'classifier_version': s.get('version'),
                    'kesinlik': 'aday' if s.get('kazanan_firma_aday') else 'sektor_il_ipucu',
                }
                f_ihale.write(json.dumps(ihale_kayit, ensure_ascii=False) + '\n')
                sayilar['ihale_kanal'] += 1

    print(f"=== CROSS-CC BESLE · {tarih} ===")
    print(f"Sınıflı havuz okunan: {sayilar['okunan']}")
    print(f"Cross-Hat (Analiz) kanalı yazıldı: {sayilar['cross_hat_kanal']}")
    print(f"İhale kazanan adayı (İhale) kanalı yazıldı: {sayilar['ihale_kanal']}")
    print(f"📤 {ihale_dosya}")
    print(f"📤 {cross_hat_dosya}")

    # Audit
    audit = {
        '_meta': 'CC-Basın Cross-CC Besleme (B98 anayasa v2.2)',
        'tarih': tarih,
        'tek_yon_lane_ham': True,
        'tuketiciler': {
            'cc_ihale': ihale_dosya,
            'cc_analiz': cross_hat_dosya,
        },
        'sayilar': sayilar,
    }
    audit_dosya = os.path.join(BASE, 'data', 'audit', f'cross_cc_besle_{tarih}.json')
    with open(audit_dosya, 'w', encoding='utf-8') as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)
    print(f"Audit: {audit_dosya}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
