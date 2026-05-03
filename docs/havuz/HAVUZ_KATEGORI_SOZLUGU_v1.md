# TRADIA HAVUZ KATEGORİ SÖZLÜĞÜ v1.0

**Versiyon:** 1.0  
**Tarih:** 3 Mayıs 2026  
**Kullanım:** `agents/news_classifier.py` sistem promptu referansı

---

## Genel Kurallar

- Her haber tek bir birincil kategoriye atanır
- Gayrimenkul/inşaat/imar konusu değilse → **BELIRSIZ**
- Ağırlık puanı 0-10 arası tam sayı
- Etki gecikmesi fiyat/talep yansımasına kadar geçen tipik süre

---

## Kategoriler

---

### 1. imar-degisikligi

- **Ağırlık aralığı:** 3-9
- **Etki gecikmesi:** 3-18 ay
- **Etki tipi:** Karma

**Alt-kategoriler:**
- `yogunluk-artisi` (KAKS/TAKS artışı) — ağırlık 6-8
- `yogunluk-azalisi` (KAKS/TAKS azalışı) — ağırlık 6-8 (negatif yön)
- `kullanim-degisikligi` (konuttan ticariye vb.) — ağırlık 4-6
- `plan-iptali` — ağırlık 7-9 (negatif)
- `yeni-imar-plani` — ağırlık 5-7

**Örnekler:**
- "Lapseki Cumhuriyet Mah. emsal 1.20'den 1.50'ye çıkarıldı"
- "Şişli'de 5 parselde imar değişikliği onaylandı"
- "Kadıköy Moda bölgesi TAKS değeri 0.40'dan 0.30'a düşürüldü"

---

### 2. ulasim-iyilestirme

- **Ağırlık aralığı:** 5-10
- **Etki gecikmesi:** 6-36 ay (açılış anında ani etki)
- **Etki tipi:** pozitif-talep

**Alt-kategoriler:**
- `metro-hat` — ağırlık 8-10
- `yol-otoyol` — ağırlık 6-8
- `kopru-gecis` — ağırlık 7-9
- `havalimani` — ağırlık 8-10
- `acilis` (mevcut projenin açılışı) — ağırlık 7-9
- `ihale` (inşaat başlamadı) — ağırlık 5-7

**Örnekler:**
- "M11 Gayrettepe-Havalimanı Metrosu açıldı"
- "Kuzey Marmara Otoyolu 3. etap ihalesi sonuçlandı"

---

### 3. saglik-tesisi

- **Ağırlık aralığı:** 4-8
- **Etki gecikmesi:** 12-48 ay
- **Etki tipi:** pozitif-talep

**Alt-kategoriler:**
- `sehir-hastanesi` — ağırlık 7-9
- `klinik-poliklinik` — ağırlık 4-6
- `acilis` — ağırlık 6-8
- `ihale` — ağırlık 4-6

**Örnekler:**
- "Etlik Şehir Hastanesi açıldı, 3.578 yatak kapasiteli"
- "Bursa Nilüfer'e yeni devlet hastanesi yapılacak"

---

### 4. egitim-tesisi

- **Ağırlık aralığı:** 3-6
- **Etki gecikmesi:** 12-60 ay
- **Etki tipi:** pozitif-talep

**Alt-kategoriler:**
- `universite-kampus` — ağırlık 5-7
- `ilkogretim-lise` — ağırlık 3-5
- `acilis` — ağırlık 5-6
- `ihale` — ağırlık 3-5

**Örnekler:**
- "Teknopark İstanbul yanına yeni üniversite kampüsü"
- "Kurtköy'de 48 derslikli okul ihalesi yapılıyor"

---

### 5. sanayi-yatirim

- **Ağırlık aralığı:** 5-9
- **Etki gecikmesi:** 12-60 ay
- **Etki tipi:** pozitif-talep (çevre konut/ticari için)

**Alt-kategoriler:**
- `fabrika-tesis` — ağırlık 7-9
- `osb-genisleme` — ağırlık 6-8
- `ar-ge-merkezi` — ağırlık 5-7
- `lojistik-depo` — ağırlık 4-6

**Örnekler:**
- "Ford Otosan Yeniköy'e 2 milyar Euro'luk EV hattı"
- "İzmir Kemalpaşa OSB 300 hektar genişliyor"

---

### 6. turizm-yatirim

- **Ağırlık aralığı:** 4-8
- **Etki gecikmesi:** 12-48 ay
- **Etki tipi:** pozitif-talep (ikinci konut, kira geliri)

**Alt-kategoriler:**
- `otel-resort` — ağırlık 5-8
- `marina-yat` — ağırlık 5-7
- `kruvaziyer` — ağırlık 4-6
- `kültür-turizm` — ağırlık 4-6

**Örnekler:**
- "Bodrum'a 500 odalı lüks resort onaylandı"
- "Çeşme Altın Yüzük Projesi ihalesi tamamlandı"

---

### 7. kamulastirma

- **Ağırlık aralığı:** 6-10
- **Etki gecikmesi:** 0-6 ay (ani etki)
- **Etki tipi:** negatif-arz-arttirici (piyasaya zorunlu çıkış)

**Alt-kategoriler:**
- `acil-kamulastirma` — ağırlık 8-10
- `uzlasma-kamulastirma` — ağırlık 6-8
- `iptal` (kamulaştırma iptali) — ağırlık 6-8 (pozitif yön)

**Örnekler:**
- "Kanal İstanbul güzergahı Arnavutköy'de 450 parsel kamulaştırılıyor"
- "Resmi Gazete: Tekirdağ-Çorlu OSB için 12 parsel acele kamulaştırma"

---

### 8. ihale-ilani

- **Ağırlık aralığı:** 3-7
- **Etki gecikmesi:** 6-24 ay
- **Etki tipi:** pozitif-talep (altyapı/kamu inşaatı başlıyor)

**Alt-kategoriler:**
- `kamu-bina` — ağırlık 3-5
- `altyapi` — ağırlık 5-7
- `kentsel-donusum` — ağırlık 6-8
- `aoc-yikimi` (yıkım ihalesi) — ağırlık 5-7

**Örnekler:**
- "TOKİ Pendik'te 1200 konutluk proje ihalesi açtı"
- "Başakşehir kaymakamlık binası ihalesi KİK'te"

---

### 9. donusum-ilani

- **Ağırlık aralığı:** 5-9
- **Etki gecikmesi:** 12-60 ay
- **Etki tipi:** Karma

**Alt-kategoriler:**
- `kentsel-donusum` — ağırlık 7-9
- `riskli-alan` — ağırlık 7-9
- `tarihi-alan` — ağırlık 5-7

**Örnekler:**
- "Bağcılar Fevzi Çakmak Mahallesi riskli alan ilan edildi"
- "İzmir Konak tarihi çarşı kentsel dönüşüm kararnamesi"

---

### 10. yabanci-satis

- **Ağırlık aralığı:** 2-6
- **Etki gecikmesi:** 0-6 ay
- **Etki tipi:** pozitif-talep

**Alt-kategoriler:**
- `istatistik-artis` — ağırlık 3-5
- `istatistik-azalis` — ağırlık 3-5
- `politika-degisikligi` (yabancıya satış mevzuatı) — ağırlık 5-7

**Örnekler:**
- "TÜİK: Nisan'da yabancıya konut satışı %24 arttı"
- "Körfez alıcıları İstanbul yerine Antalya tercih ediyor"

---

### 11. mega-proje

- **Ağırlık aralığı:** 7-10
- **Etki gecikmesi:** 12-120 ay
- **Etki tipi:** pozitif-talep

**Alt-kategoriler:**
- `onay-karari` — ağırlık 8-10
- `ihale` — ağırlık 7-9
- `acilis` — ağırlık 8-10
- `iptal-askiya-alma` — ağırlık 8-10 (negatif)

**Örnekler:**
- "Kanal İstanbul güzergahı kesinleşti"
- "3. Havalimanı 3. pist inşaatı başladı"
- "Kuzey Marmara Otoyolu Sakarya kavşağı açıldı"

---

### 12. dogal-afet

- **Ağırlık aralığı:** 5-10
- **Etki gecikmesi:** 0-3 ay (ani)
- **Etki tipi:** negatif-talep

**Alt-kategoriler:**
- `deprem` — ağırlık 7-10
- `sel-taskin` — ağırlık 5-8
- `yangin` — ağırlık 5-8
- `heyelan` — ağırlık 5-7

**Örnekler:**
- "Düzce'de 5.1 büyüklüğünde deprem, 30 binada hasar"
- "İzmir Torbalı'da sanayi bölgesinde büyük yangın"

---

### 13. ekonomik-karar

- **Ağırlık aralığı:** 3-8
- **Etki gecikmesi:** 0-12 ay
- **Etki tipi:** Karma

**Alt-kategoriler:**
- `faiz-degisikligi` — ağırlık 6-8
- `enflasyon-verisi` — ağırlık 4-6
- `doviz-kuru` — ağırlık 4-6
- `kredi-kolayligi` — ağırlık 5-7

**Örnekler:**
- "TCMB faizi 250 baz puan artırdı"
- "Konut kredisi faizleri %3.5'e geriledi"

---

### 14. sosyal-tesis

- **Ağırlık aralığı:** 2-5
- **Etki gecikmesi:** 12-60 ay
- **Etki tipi:** pozitif-talep (mahalle prestiji)

**Alt-kategoriler:**
- `park-meydan` — ağırlık 2-4
- `spor-tesisi` — ağırlık 3-5
- `kültür-merkezi` — ağırlık 3-5
- `ibadet-yeri` — ağırlık 2-4

**Örnekler:**
- "Esenyurt'a 50.000 m² millet bahçesi açıldı"
- "Gaziosmanpaşa yeni spor kompleksi ihalesi"

---

### 15. yatirim-tesvik

- **Ağırlık aralığı:** 4-8
- **Etki gecikmesi:** 6-24 ay
- **Etki tipi:** pozitif-talep

**Alt-kategoriler:**
- `osb-tesvik` — ağırlık 5-7
- `serbest-bolge` — ağırlık 5-7
- `vergi-muafiyeti` — ağırlık 4-6
- `bölge-sinifi-degisikligi` — ağırlık 6-8

**Örnekler:**
- "Malatya 5. bölge teşvikine alındı"
- "Samsun serbest bölgede 3 yeni arazi tahsisi"

---

### 16. yargi-karari

- **Ağırlık aralığı:** 5-10
- **Etki gecikmesi:** 0-12 ay
- **Etki tipi:** Karma

**Alt-kategoriler:**
- `imar-plan-iptali` — ağırlık 7-9 (negatif)
- `kamulaştirma-iptali` — ağırlık 6-8 (pozitif)
- `proje-durdurma` — ağırlık 6-9 (negatif)
- `hak-tanima` — ağırlık 4-6

**Örnekler:**
- "Danıştay Maslak 1453 imar planını iptal etti"
- "AYM: Kanal İstanbul kararı Anayasa'ya aykırı değil"

---

### 17. dogal-olay

- **Ağırlık aralığı:** 2-5
- **Etki gecikmesi:** 0-3 ay
- **Etki tipi:** Karma

**Alt-kategoriler:**
- `iklim-degisikligi` — ağırlık 3-5
- `su-kaynaklari` — ağırlık 3-5
- `cevre-etki` — ağırlık 2-4

**Örnekler:**
- "İstanbul barajları doluluk oranı %28'e düştü"
- "Marmara Denizi deniz salyası uyarısı"

---

### 18. vergi-harc-degisikligi

- **Ağırlık aralığı:** 4-8
- **Etki gecikmesi:** 0-6 ay
- **Etki tipi:** Karma

**Alt-kategoriler:**
- `tapu-harci` — ağırlık 5-7
- `emlak-vergisi` — ağırlık 4-6
- `kira-stopaj` — ağırlık 4-6
- `kdv-degisikligi` — ağırlık 5-7

**Örnekler:**
- "Yüksek değerli konutlarda %3 tapu harcı uygulaması başlıyor"
- "İkinci el konut satışında KDV %20'ye çıktı"

---

### 19. demografik-haber

- **Ağırlık aralığı:** 2-5
- **Etki gecikmesi:** 12-60 ay
- **Etki tipi:** pozitif-talep veya negatif-talep

**Alt-kategoriler:**
- `nufus-artisi` — ağırlık 3-5
- `nufus-azalisi` — ağırlık 3-5
- `goc-hareketi` — ağırlık 3-5

**Örnekler:**
- "Bolu'ya sanayi göçü: 5 yılda nüfus %12 arttı"
- "Doğu Anadolu'dan batıya göç hızlanıyor"

---

### 20. guvenlik-suc

- **Ağırlık aralığı:** 2-6
- **Etki gecikmesi:** 0-12 ay
- **Etki tipi:** negatif-talep

**Alt-kategoriler:**
- `organize-suc` — ağırlık 4-6
- `terör-olay` — ağırlık 5-7
- `artan-suç-oranı` — ağırlık 3-5

**Örnekler:**
- "Güngören'de organize suç operasyonu: mahalle güvenlik algısı etkisi"
- "Karaköy-Taksim bölgesinde artan taciz olayları turizmi etkiliyor"

---

### 21. BELIRSIZ *(özel kod)*

- Kategori atanamadığında kullanılır
- Gayrimenkul ile ilgisi olmayan her haber için
- **Ağırlık:** 0
- **Etki:** notr

---

## Hızlı Referans Tablosu

| # | Kod | Ağırlık Aralığı | Tipik Gecikme |
|---|-----|----------------|---------------|
| 1 | imar-degisikligi | 3-9 | 3-18 ay |
| 2 | ulasim-iyilestirme | 5-10 | 6-36 ay |
| 3 | saglik-tesisi | 4-8 | 12-48 ay |
| 4 | egitim-tesisi | 3-6 | 12-60 ay |
| 5 | sanayi-yatirim | 5-9 | 12-60 ay |
| 6 | turizm-yatirim | 4-8 | 12-48 ay |
| 7 | kamulastirma | 6-10 | 0-6 ay |
| 8 | ihale-ilani | 3-7 | 6-24 ay |
| 9 | donusum-ilani | 5-9 | 12-60 ay |
| 10 | yabanci-satis | 2-6 | 0-6 ay |
| 11 | mega-proje | 7-10 | 12-120 ay |
| 12 | dogal-afet | 5-10 | 0-3 ay |
| 13 | ekonomik-karar | 3-8 | 0-12 ay |
| 14 | sosyal-tesis | 2-5 | 12-60 ay |
| 15 | yatirim-tesvik | 4-8 | 6-24 ay |
| 16 | yargi-karari | 5-10 | 0-12 ay |
| 17 | dogal-olay | 2-5 | 0-3 ay |
| 18 | vergi-harc-degisikligi | 4-8 | 0-6 ay |
| 19 | demografik-haber | 2-5 | 12-60 ay |
| 20 | guvenlik-suc | 2-6 | 0-12 ay |
| 21 | BELIRSIZ | 0 | — |
