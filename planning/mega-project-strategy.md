# Tradia — Ücretsiz Mega Proje Stratejisi
## İmplementasyon Planı

**Hazırlayan:** Claude Code  
**Tarih:** 2026-05-02  
**Durum:** Boss onayı bekliyor  
**Scope:** Plan yaz — kod yok

---

## 1. Hangi Ajanlar Yeniden Yapılandırılacak

### 1.1 ResearchAgent — BÜYÜK REFACTOR

ResearchAgent şu an 8 Marmara projesiyle sınırlı ve SEARCH_SOURCES'ın 2/5'i dead.

**Yapılacaklar:**

**a) MEGA_PROJECTS hardcode → projects/mega-projects.json'dan oku**  
Şu an projeler `research_agent.py` içinde class variable olarak hardcoded. Yeni yapıda:
```
projects/mega-projects.json  ←  tek kaynak
ResearchAgent                ←  dosyayı okur, dinamik
```
Bu sayede kod değişikliği yapmadan proje eklenebilir.

**b) SEARCH_SOURCES güncelleme**  
Kaynak doğrulama sonuçları (bugün test edildi):

| Kaynak | URL | Durum | Aksiyon |
|---|---|---|---|
| Haberturk RSS | `haberturk.com/rss` | Bilinmiyor | Test et |
| Sabah Ekonomi | `sabah.com.tr/rss/ekonomi.xml` | ✅ Çalışıyor | Koru |
| Dunya.com RSS | `dunya.com/rss` | Bilinmiyor | Test et |
| emlakkulisi.com | `emlakkulisi.com/rss` | ❌ 403 | Kaldır |
| propertymag.com.tr | `propertymag.com.tr/feed` | ❌ SSL | Kaldır |
| AA Genel | `aa.com.tr/tr/rss/defaultcat=guncel` | ✅ 302→OK | Ekle |
| Hürriyet Ekonomi | `hurriyet.com.tr/rss/ekonomi` | ✅ 200 | Ekle |
| TOKİ RSS | `toki.gov.tr/rss` | ❌ 404 | HTML scrape planla |
| UAB RSS | `uab.gov.tr/rss` | ❌ 404 | HTML scrape planla |
| CSB haberler | `csb.gov.tr/haberler` | ❌ 404 | HTML scrape planla |

**c) Keyword filter güçlendirme**  
Şu an proje bazlı keyword match. Eklenecek global property keywords:
```
["imar planı", "kamulaştırma", "yap-sat", "konut projesi", 
 "arsa tahsisi", "müteahhit", "inşaat ruhsatı", "kentsel dönüşüm",
 "rezidans", "AVM projesi", "lojistik merkez", "serbest bölge"]
```

**d) "Türkiye geneli" mod ekle**  
Şu an sadece Marmara projelerini araştırıyor. Antalya (Şehir Hastanesi), Ankara-İzmir HSR, Çanakkale Köprüsü için Türkiye geneli mod gerekli.

---

### 1.2 NewsAgent — KAYNAK DEĞİŞİMİ

**Kaldırılacaklar:** (genel ekonomi, property-specific değil)
- Hürriyet Ekonomi (genel)
- Milliyet Ekonomi (genel)  
- Sabah Ekonomi (genel)

**Eklenecekler:** (property/infrastructure odaklı)
```python
{"name": "AA Ekonomi", "url": "https://www.aa.com.tr/tr/rss/defaultcat=ekonomi", "type": "rss", "language": "tr"},
{"name": "AA Altyapı", "url": "https://www.aa.com.tr/tr/rss/defaultcat=altyapi", "type": "rss", "language": "tr"},
{"name": "Sabah Ekonomi XML", "url": "https://www.sabah.com.tr/rss/ekonomi.xml", "type": "rss", "language": "tr"},
{"name": "Hürriyet Ekonomi", "url": "https://www.hurriyet.com.tr/rss/ekonomi", "type": "rss", "language": "tr"},
{"name": "Dünya Gazetesi", "url": "https://www.dunya.com/rss", "type": "rss", "language": "tr"},
{"name": "Daily Sabah Economy", "url": "https://www.dailysabah.com/feeds/economy", "type": "rss", "language": "en"},
{"name": "Daily Sabah Business", "url": "https://www.dailysabah.com/feeds/business", "type": "rss", "language": "en"},
{"name": "Arnavutköy Belediyesi", "url": "https://www.arnavutkoy.bel.tr/rss", "type": "rss", "language": "tr"},
{"name": "İBB Haberler", "url": "https://www.ibb.istanbul/rss.xml", "type": "rss", "language": "tr"},
```

**classify_item keyword güncellemesi:**  
`critical` tipi için: "imar planı değişikliği", "kamulaştırma kararı", "arsa tahsisi", "proje ihalesi"  
`opportunity` tipi için: "kentsel dönüşüm", "konut projesi", "mega proje duyurusu", "inşaat başlıyor"

---

### 1.3 PropertyAgent — DEĞİŞMİYOR (şimdilik)

PropertyAgent'ın canlı kaynak sorunu (403/404) bu stratejinin kapsamı dışında. Mega proje stratejisi önce **bilgi katmanını** (news + research) düzeltir. Mülk verisi ayrı roadmap.

---

### 1.4 CEOAgent — KÜÇÜK GÜNCELLEME

`evaluate_priorities` metoduna yeni kural:
- `research` ajanından "critical_impact" haberi gelirse → `escalate_research` aksiyonu
- Bu aksiyonu briefing'de öne çıkar: "Mega proje güzergahında imar değişikliği tespit edildi"

---

## 2. Hangi Veri Kaynakları Eklenecek

### 2.1 RSS (Otomatik — Kod Değişikliği)

Çalışan ve property-relevant RSS feed'leri:

| # | Kaynak | URL | İçerik | Durum |
|---|---|---|---|---|
| 1 | AA Ekonomi | `aa.com.tr/tr/rss/defaultcat=ekonomi` | Genel ekonomi + altyapı | ✅ Test OK |
| 2 | Sabah Ekonomi XML | `sabah.com.tr/rss/ekonomi.xml` | Ekonomi | ✅ Çalışıyor |
| 3 | Hürriyet Ekonomi | `hurriyet.com.tr/rss/ekonomi` | Ekonomi | ✅ 200 OK |
| 4 | Dünya Gazetesi | `dunya.com/rss` | İş dünyası | Test gerekli |
| 5 | Daily Sabah Economy | `dailysabah.com/feeds/economy` | EN ekonomi | ✅ Çalışıyor |
| 6 | Daily Sabah Business | `dailysabah.com/feeds/business` | EN iş | ✅ Çalışıyor |
| 7 | İBB Haberler | `ibb.istanbul/rss.xml` | İBB projeleri | ✅ Eklendi |
| 8 | Arnavutköy Belediyesi | `arnavutkoy.bel.tr/rss` | Kanal güzergahı | ✅ Eklendi |

### 2.2 HTML Scraping (Planlı — Geliştirme Gerekli)

RSS'i olmayan ama kritik devlet kaynakları. Bunlar için `research_agent.py`'a HTML parser eklenmeli:

| Kaynak | URL | Yöntem | Öncelik |
|---|---|---|---|
| TOKİ Duyurular | `toki.gov.tr/haberler` | BeautifulSoup | Yüksek |
| Ulaştırma Bakanlığı | `uab.gov.tr/haberler` | BeautifulSoup | Yüksek |
| Çevre Bakanlığı | `csb.gov.tr/haberler` | BeautifulSoup | Orta |
| Tapu Kadastro | `tkgm.gov.tr/tr/icerik/duyurular` | BeautifulSoup | Orta |
| TUIK Fiyat Endeksi | `tuik.gov.tr/dinamik` | JSON API | Orta |

### 2.3 Manuel JSON (Anında — projects/mega-projects.json)

10 proje için temel veri elle girilecek. Canlı haber eşleştirmesi otomatik yapılacak.

---

## 3. mega-projects.json Yapısı (Detay)

```json
{
  "version": "1.0",
  "last_updated": "2026-05-02",
  "maintainer": "Tradia Research Team",
  "projects": [
    {
      "id": "kanal-istanbul",
      "name": "Kanal İstanbul",
      "name_en": "Istanbul Canal",
      "type": "infrastructure",
      "category": "waterway",
      "status": "planned",
      "announced": "2011-04-27",
      "expected_start": "2023-01",
      "expected_completion": "2030",
      "budget_usd_bn": 15,
      "route_description": "Küçükçekmece Gölü — Karadeniz, 45km",
      "regions": ["Istanbul"],
      "districts": ["Küçükçekmece", "Avcılar", "Başakşehir", "Arnavutköy"],
      "impact_radius_km": 15,
      "value_increase_estimate_pct": {"low": 50, "high": 130},
      "keywords_tr": ["kanal istanbul", "yenişehir imar", "sazlıbosna", "kanal güzergah", "kanal marmara"],
      "keywords_en": ["istanbul canal", "canal project istanbul", "new istanbul waterway"],
      "sources": [
        {"name": "UAB Açıklaması", "url": "https://www.uab.gov.tr/", "date": "2021"},
        {"name": "AA Haber", "url": "https://www.aa.com.tr/", "date": "2021"}
      ],
      "tradia_score": 92,
      "tradia_notes": "Güzergah üzerindeki arsa fiyatları 2023'te %40 arttı. Arnavutköy ve Küçükçekmece ilçeleri birincil hedef.",
      "active": true
    }
  ]
}
```

**Alan açıklamaları:**
- `status`: `planned` / `under_construction` / `completed` / `cancelled`
- `category`: `waterway` / `airport` / `hospital` / `highway` / `bridge` / `railway` / `urban_renewal`
- `value_increase_estimate_pct`: Basın açıklaması veya araştırma bazlı tahmin aralığı
- `sources`: Sadece resmi veya AA/Reuters haberleri — spekülatif kaynak yok
- `tradia_score`: ResearchAgent'ın yatırım önemi skoru (0-100)
- `active`: False yapılınca sistem bu projeyi izlemeyi bırakır

---

## 4. Site'a Nasıl Yansıyacak

### Mevcut Durum

```
data/reports/news_report_*.json   →  docs/index.html #lg-news-feed
data/reports/property_report_*.json  →  docs/index.html #lg-property-feed
```

### Yeni: Mega Proje Bölümü

`docs/index.html`'e yeni bir section eklenecek: `#mega-projects`

```
projects/mega-projects.json      →  (statik, her deploy'da okunur)
data/research/{id}_{date}.json   →  CEO briefing → deploy → #mega-projects
```

**Site template (örnek kart):**

```html
<div class="mega-project-card" data-score="92">
  <span class="project-status planned">PLANNED</span>
  <h3>Kanal İstanbul</h3>
  <p class="route">Küçükçekmece → Karadeniz, 45km</p>
  <div class="districts">
    <span>Küçükçekmece</span><span>Başakşehir</span><span>Arnavutköy</span>
  </div>
  <div class="impact">
    <span class="value-up">+50–130% tahmini değer artışı</span>
    <span class="radius">15km etki yarıçapı</span>
  </div>
  <div class="latest-news">Son haber: [ResearchAgent'tan çekilen son item]</div>
  <div class="tradia-score">Tradia Score: 92/100</div>
</div>
```

**CSS class sistemi:**
- `.project-status.planned` → sarı badge
- `.project-status.under_construction` → turuncu badge  
- `.project-status.completed` → yeşil badge

`deploy_to_site.py`'a `inject_mega_projects()` fonksiyonu eklenecek.

---

## 5. İlk 10 Proje — Manuel Veri Toplama Planı

Her proje için 1 saat araştırma. Boss veya asistan tarafından yapılabilir.

### Veri Kaynağı Hiyerarşisi (önem sırasıyla)
1. **Resmi hükümet açıklaması** (uab.gov.tr, toki.gov.tr, csb.gov.tr)
2. **Anadolu Ajansı haberi** (aa.com.tr — birincil haber ajansı)
3. **Cumhurbaşkanlığı duyurusu** (tccb.gov.tr)
4. **Wikipedia TR** (kronoloji için)
5. **Hürriyet/Sabah** (ikincil)

### Proje Listesi ve Durum

| # | Proje | Kategori | Durum | Tahmini Bütçe | Etki İlleri |
|---|---|---|---|---|---|
| 1 | **Kanal İstanbul** | Su yolu | Planlandı | $15bn | İstanbul |
| 2 | **3. Havalimanı Genişleme** | Havalimanı | İnşaat | $10bn+ | İstanbul |
| 3 | **Marmaray Uzatması** | Demiryolu | Aktif | $3bn | İstanbul, Kocaeli |
| 4 | **Başakşehir Şehir Hastanesi** | Hastane | Tamamlandı (2020) | $1.8bn | İstanbul |
| 5 | **Çamlıca Camii Çevresi** | Kentsel dönüşüm | Aktif | — | İstanbul |
| 6 | **İzmit-Gebze Körfez Geçişi** | Köprü/tünel | Aktif | $3bn | Kocaeli |
| 7 | **Çanakkale 1915 Köprüsü** | Köprü | Tamamlandı (2022) | $3.2bn | Çanakkale, Balıkesir |
| 8 | **Çamlıca TV Kulesi** | İletişim/kentsel | Tamamlandı (2021) | — | İstanbul |
| 9 | **Ankara–İzmir Hızlı Tren** | Demiryolu | İnşaat | $12bn | Ankara, İzmir, Afyon |
| 10 | **Antalya Şehir Hastanesi** | Hastane | İnşaat | $800mn | Antalya |

### Toplama Formatı (Her Proje için Doldurulacak)

```
Proje: ___
Kaynak URL: ___
Duyuru tarihi: ___
Bütçe: ___
Tamamlanma: ___
Güzergah/konum detayı: ___
Etki ilçeleri: ___
Değer artışı tahmini (kaynak): ___
keywords_tr: ___
keywords_en: ___
```

### Öneri: Veri Toplama Sırası

**Faz 1 (bugün, 2 saat):** Projeler 1, 2, 4 — bunlar zaten kısmen sistemde.  
**Faz 2 (yarın, 3 saat):** Projeler 6, 7, 9 — köprü/tren, Türkiye geneli.  
**Faz 3 (2 gün):** Projeler 3, 5, 8, 10 — detay araştırma.

---

## 6. Tahmini Süre

### Implementasyon Roadmap

```
GÜN 1 (3-4 saat)
├── projects/mega-projects.json oluştur (10 proje, manuel veri)
├── ResearchAgent.MEGA_PROJECTS → JSON'dan oku
└── ResearchAgent.SEARCH_SOURCES güncelle (dead'leri kaldır, yenileri ekle)

GÜN 2 (4-5 saat)
├── NewsAgent SOURCES güncelle (genel → property-specific)
├── classify_item keyword'lerini güçlendir
└── research_agent.py HTML scraper ekle (TOKİ, UAB sayfaları için)

GÜN 3 (3-4 saat)
├── deploy_to_site.py → inject_mega_projects() ekle
├── docs/index.html → #mega-projects section ekle + CSS
└── CEO briefing → research raporu entegrasyonu

GÜN 4 (2-3 saat)
├── Uçtan uca test (watchdog → orchestrator → research → deploy → site)
└── 10 projeyi izlemeye al, ilk raporu üret
```

**Toplam:** 12-16 saat aktif geliştirme + 6 saat manuel veri toplama

### Başarı Kriterleri

- [ ] `projects/mega-projects.json` 10 proje, tüm alanlar dolu
- [ ] ResearchAgent saatlik çalışıyor, her proje için haber tarıyor
- [ ] NewsAgent günlük en az 3 property-specific haber üretiyor (şu an: 0)
- [ ] Site'da `#mega-projects` section 10 kart gösteriyor
- [ ] Cron deploy saatlik siteyi güncelliyor (bugün doğrulandı ✅)
- [ ] "mega proje" keyword'ü data tabanında 0 → en az 20 eşleşme

---

## Sonraki Adım

1. Boss bu planı onaylar
2. `projects/mega-projects.json` ile başlanır (10 proje veri girişi)
3. ResearchAgent güncellemesi
4. NewsAgent kaynak değişikliği
5. Site entegrasyonu

**Toplam beklenen süre:** 3-4 gün (paralel çalışırsak 2 gün)
