# vezir/ — Tradia Dış Cephesi

Bu klasör **Vezir** (gacbusiness) tarafından okunur.
Tradia'nın iç çalışma verisi `data/` klasöründedir — buraya taşınmaz.

## Dosyalar

| Dosya | Açıklama | Güncelleme |
|-------|----------|------------|
| `status.json` | Sistem durumu snapshot | Saatte 1 (idempotent) |
| `signals.jsonl` | Append-only event log | Her olayda |

## Kontrat

Bu klasörün şeması **TRADIA ↔ VEZİR ENTEGRASYON KONTRATI v1.1**
tarafından yönetilir.

- `status.json` schema_version: 1.0
- Tradia yazar, Vezir HTTP fetch ile okur
- İki sistem birbirinin dosyalarını YAZMAZ

## Güncelleme mekanizması

```
scripts/update_status.py   → vezir/status.json yazar (idempotent)
scripts/append_signal.py   → vezir/signals.jsonl'a satır ekler
.github/workflows/sync-vezir.yml → her saat 05'te çalışır
```
