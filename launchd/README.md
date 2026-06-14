# CC-Basın launchd Agents

macOS launchd plist dosyaları — yapısal versiyon kontrol için.

**Kanonik yer (çalışan kopya):** `~/Library/LaunchAgents/`

## Plistler

| Plist | Rol | Frekans | KeepAlive |
|---|---|---|---|
| `com.tradia.ccbasin.pulse.plist` | Lokal sürekli motor (B96) | her saniye döngü + per-feed interval | `true` |
| `com.tradia.ccbasin.saglik.plist` | Sağlık rutini (B98) | StartCalendarInterval 02:00 TR | `false` |

## Yükleme (Patron eylem)

```bash
# Repo'dan kanonik yere kopyala
cp launchd/com.tradia.ccbasin.pulse.plist ~/Library/LaunchAgents/
cp launchd/com.tradia.ccbasin.saglik.plist ~/Library/LaunchAgents/

# Yükle
launchctl load ~/Library/LaunchAgents/com.tradia.ccbasin.pulse.plist
launchctl load ~/Library/LaunchAgents/com.tradia.ccbasin.saglik.plist

# Durum
launchctl list | grep com.tradia.ccbasin
```

## Anayasa atfı

[[anayasa_basin v2.3]] § BÖLÜM 5.5 ÇİFT-MOD KESİNTİSİZ TARAMA + BÖLÜM 7 SAĞLIK RUTİNİ
