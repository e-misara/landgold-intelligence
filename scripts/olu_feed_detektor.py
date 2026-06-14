#!/usr/bin/env python3
"""
CC-Basın Ölü-Feed Detektör — B97 (anayasa v2.2 § BÖLÜM 5.5 + RATE-LIMIT GUARD)

_akis_log.jsonl son N döngüsünü tarar — sürekli hata veren feed'leri "ölü" işaretler.

Kural:
- Son N=10 döngüde, bir feed her seferinde err verirse → DUR-damga (ölü)
- Son N=20 döngüde, bir feed hiç yeni distinct üretmediyse → KURU işareti (kontrol et)
- Output: data/audit/olu_feed_raporu.json + stdout V16 SERT durum

Disiplin:
- $0 (yalnız local log okur)
- Lane HAM (kararı raporlar, otomatik silmez — Patron onayı)
- V16 SERT: kuru ≠ ölü, ayrı işaret
"""
import os
import json
import sys
from datetime import datetime, timezone, timedelta
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AKIS_LOG = os.path.join(BASE, 'data', 'havuz', '_akis_log.jsonl')
RAPOR = os.path.join(BASE, 'data', 'audit', 'olu_feed_raporu.json')

TR = timezone(timedelta(hours=3))
N_OLU = 10       # son K döngü tamamı err = ölü
N_KURU = 20      # son K döngü hiç yeni distinct = kuru


def main():
    if not os.path.exists(AKIS_LOG):
        print(f"❌ Akış log YOK: {AKIS_LOG}")
        return 1

    donguler = []
    with open(AKIS_LOG, encoding='utf-8') as f:
        for ln in f:
            try:
                donguler.append(json.loads(ln))
            except Exception:
                pass

    if not donguler:
        print("❌ Akış log boş")
        return 1

    print(f"=== ÖLÜ-FEED DETEKTÖR (B97, v2.2) ===")
    print(f"Toplam döngü: {len(donguler)}")
    print(f"İlk: {donguler[0]['ts'][:19]}")
    print(f"Son: {donguler[-1]['ts'][:19]}")

    # Feed bazlı son N döngü detayı
    son_n_olu = donguler[-N_OLU:]
    son_n_kuru = donguler[-N_KURU:]

    # Tüm feed'ler
    tum_feed = set()
    for d in donguler:
        for detay in d.get('detay', []):
            tum_feed.add(detay['feed'])

    olu_listesi = []
    kuru_listesi = []
    saglikli_listesi = []
    yetersiz_veri = []

    for fid in sorted(tum_feed):
        # Son N_OLU döngüde işlenme + err sayısı
        islenme_olu = 0
        err_olu = 0
        for d in son_n_olu:
            for detay in d.get('detay', []):
                if detay['feed'] == fid:
                    islenme_olu += 1
                    if detay.get('err'):
                        err_olu += 1

        # Son N_KURU döngüde yeni distinct + relevant + fetch toplamı
        # B98 DÜZELTME: salt 'yeni=0' yanıltıcı (dedup sebebiyle olabilir);
        # KURU = 'relevant=0 hiç tradia-anahtarı yakalanmamış' VE 'fetch>0'
        yeni_kuru = 0
        islenme_kuru = 0
        rel_kuru = 0
        fetch_kuru = 0
        for d in son_n_kuru:
            for detay in d.get('detay', []):
                if detay['feed'] == fid:
                    islenme_kuru += 1
                    yeni_kuru += detay.get('yeni', 0)
                    rel_kuru += detay.get('rel', 0)
                    fetch_kuru += detay.get('fetch', 0)

        durum = {
            'feed': fid,
            'islenme_son_olu': islenme_olu,
            'err_son_olu': err_olu,
            'islenme_son_kuru': islenme_kuru,
            'fetch_son_kuru': fetch_kuru,
            'relevant_son_kuru': rel_kuru,
            'yeni_distinct_son_kuru': yeni_kuru,
        }

        # Karar — sıra önemli (ölü en sert)
        if islenme_olu < 3:
            yetersiz_veri.append(durum)
        elif islenme_olu >= 3 and err_olu == islenme_olu:
            durum['damga'] = 'OLU'
            durum['neden'] = f'Son {islenme_olu} işlenmenin hepsi err'
            olu_listesi.append(durum)
        elif islenme_kuru >= 5 and fetch_kuru > 0 and rel_kuru == 0:
            durum['damga'] = 'KURU'
            durum['neden'] = f'Son {islenme_kuru} işlenmede fetch={fetch_kuru} ama relevant=0 (Tradia-anahtar yakalanmıyor)'
            kuru_listesi.append(durum)
        else:
            durum['damga'] = 'SAGLIKLI'
            saglikli_listesi.append(durum)

    print()
    print(f"🟢 SAĞLIKLI: {len(saglikli_listesi)} feed")
    print(f"🟡 KURU (≥{N_KURU} işlenmede 0 yeni): {len(kuru_listesi)}")
    for d in kuru_listesi:
        print(f"   - {d['feed']:25s} işlenme={d['islenme_son_kuru']} yeni=0")
    print(f"🔴 ÖLÜ (son ≥3 işlenme tamamı err): {len(olu_listesi)}")
    for d in olu_listesi:
        print(f"   - {d['feed']:25s} err={d['err_son_olu']}/{d['islenme_son_olu']}")
    print(f"⚪ YETERSİZ VERİ (<3 işlenme): {len(yetersiz_veri)}")

    rapor = {
        '_meta': 'CC-Basın Ölü-Feed Detektör (B97 anayasa v2.2)',
        'ts': datetime.now(TR).isoformat(),
        'toplam_dongu': len(donguler),
        'aralik_ts': {
            'ilk': donguler[0]['ts'],
            'son': donguler[-1]['ts'],
        },
        'feed_sayilari': {
            'saglikli': len(saglikli_listesi),
            'kuru': len(kuru_listesi),
            'olu': len(olu_listesi),
            'yetersiz_veri': len(yetersiz_veri),
        },
        'olu_feed': olu_listesi,
        'kuru_feed': kuru_listesi,
        'saglikli_feed': saglikli_listesi,
        'yetersiz_veri': yetersiz_veri,
    }

    os.makedirs(os.path.dirname(RAPOR), exist_ok=True)
    with open(RAPOR, 'w', encoding='utf-8') as f:
        json.dump(rapor, f, ensure_ascii=False, indent=2)
    print(f"\n[rapor] {RAPOR}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
