#!/usr/bin/env python3
"""
CC-Basın Haber Sınıflandırıcı v1.0 — B98 (anayasa v2.2 § BÖLÜM 1 ŞERİT — sınıflar evet, sentez DEĞİL)

GİRİŞ: bir havuz kaydı (dict)
  {kaynak_id, kaynak, baslik_kisa, url, tarih_pub, url_hash, fetch_ts, ...}

ÇIKIŞ: aynı kayıt + 'siniflar' alanı
  {
    ...,
    'siniflar': {
      'version': 'v1.0',         # KESİN ŞEMA — değişirse versiyon bump
      'iller': ['istanbul', ...], # TR-slug — boş liste OK
      'ilceler': ['<il>/<ilce>'], # TR-slug — boş liste OK
      'kategoriler': [...],       # KESİN ENUM — aşağıda KATEGORI_ENUM
      'kazanan_firma_aday': str veya None,
    }
  }

KESİN KATEGORI ENUM (B98 sözleşme — yeni kategori eklemek versiyon bump şart):
- ihale_sonuc
- imar_degisikligi
- mega_proje
- banka_finans
- gentrifikasyon
- altyapi
- diger

ESKİ FIELD-MISMATCH TUZAK (TUZAK-8): Bu schema KONTRAT. Tüketici (CC-İhale arşivi, CC-Analiz Cross-Hat) bu alanlara güvenir. Yeni alan eklemek için 'version' bump + tüketicilere bildirim ŞART.

Disiplin:
- Lane HAM: sınıflar evet, yorum/skor/sentez HAYIR
- $0 (TR keyword, dış API YOK)
- KVKK: kazanan_firma_aday yalnız 'firma' (tüzel kişi) açık-kaynakta ise döner; şahıs YOK
"""
import re

SCHEMA_VERSION = 'v1.0'

# ============================================================================
# 81 İL SLUG SÖZLÜĞÜ — başlıkta geçişi ararken normalize
# ============================================================================
IL_SLUG = {
    'adana': 'adana', 'adıyaman': 'adiyaman', 'adiyaman': 'adiyaman',
    'afyon': 'afyonkarahisar', 'afyonkarahisar': 'afyonkarahisar',
    'ağrı': 'agri', 'agri': 'agri',
    'aksaray': 'aksaray', 'amasya': 'amasya',
    'ankara': 'ankara', 'antalya': 'antalya',
    'ardahan': 'ardahan', 'artvin': 'artvin',
    'aydın': 'aydin', 'aydin': 'aydin',
    'balıkesir': 'balikesir', 'balikesir': 'balikesir',
    'bartın': 'bartin', 'bartin': 'bartin',
    'batman': 'batman', 'bayburt': 'bayburt',
    'bilecik': 'bilecik', 'bingöl': 'bingol', 'bingol': 'bingol',
    'bitlis': 'bitlis', 'bolu': 'bolu', 'burdur': 'burdur',
    'bursa': 'bursa', 'çanakkale': 'canakkale', 'canakkale': 'canakkale',
    'çankırı': 'cankiri', 'cankiri': 'cankiri',
    'çorum': 'corum', 'corum': 'corum',
    'denizli': 'denizli', 'diyarbakır': 'diyarbakir', 'diyarbakir': 'diyarbakir',
    'düzce': 'duzce', 'duzce': 'duzce',
    'edirne': 'edirne', 'elazığ': 'elazig', 'elazig': 'elazig',
    'erzincan': 'erzincan', 'erzurum': 'erzurum',
    'eskişehir': 'eskisehir', 'eskisehir': 'eskisehir',
    'gaziantep': 'gaziantep', 'giresun': 'giresun',
    'gümüşhane': 'gumushane', 'gumushane': 'gumushane',
    'hakkari': 'hakkari', 'hatay': 'hatay',
    'iğdır': 'igdir', 'igdir': 'igdir',
    'isparta': 'isparta', 'istanbul': 'istanbul', 'i̇stanbul': 'istanbul',
    'izmir': 'izmir', 'i̇zmir': 'izmir',
    'kahramanmaraş': 'kahramanmaras', 'kahramanmaras': 'kahramanmaras',
    'k.maraş': 'kahramanmaras', 'k.maras': 'kahramanmaras',
    'karabük': 'karabuk', 'karabuk': 'karabuk',
    'karaman': 'karaman', 'kars': 'kars', 'kastamonu': 'kastamonu',
    'kayseri': 'kayseri', 'kilis': 'kilis',
    'kırıkkale': 'kirikkale', 'kirikkale': 'kirikkale',
    'kırklareli': 'kirklareli', 'kirklareli': 'kirklareli',
    'kırşehir': 'kirsehir', 'kirsehir': 'kirsehir',
    'kocaeli': 'kocaeli', 'konya': 'konya',
    'kütahya': 'kutahya', 'kutahya': 'kutahya',
    'malatya': 'malatya', 'manisa': 'manisa',
    'mardin': 'mardin', 'mersin': 'mersin',
    'muğla': 'mugla', 'mugla': 'mugla',
    'muş': 'mus', 'mus': 'mus',
    'nevşehir': 'nevsehir', 'nevsehir': 'nevsehir',
    'niğde': 'nigde', 'nigde': 'nigde',
    'ordu': 'ordu', 'osmaniye': 'osmaniye', 'rize': 'rize',
    'sakarya': 'sakarya', 'samsun': 'samsun',
    'şanlıurfa': 'sanliurfa', 'sanliurfa': 'sanliurfa', 's.urfa': 'sanliurfa',
    'siirt': 'siirt', 'sinop': 'sinop',
    'şırnak': 'sirnak', 'sirnak': 'sirnak',
    'sivas': 'sivas', 'tekirdağ': 'tekirdag', 'tekirdag': 'tekirdag',
    'tokat': 'tokat', 'trabzon': 'trabzon',
    'tunceli': 'tunceli', 'uşak': 'usak', 'usak': 'usak',
    'van': 'van', 'yalova': 'yalova', 'yozgat': 'yozgat',
    'zonguldak': 'zonguldak',
}

KATEGORI_ENUM = {
    'ihale_sonuc': {
        'pos': ['ihale.{0,40}(sonuçland|tamamland|kazand|verildi|aldı|sonucu açıkland)',
                'ihalesini.{0,40}kazand', 'ihalesini.{0,40}aldı',
                'kazanan firma', 'üstlendi.{0,8}şirket',
                'müteahhit.{0,5}olarak', 'projeyi.{0,40}üstlendi',
                '(GYO|İnşaat|İnş\\.|Yapı|Holding|A\\.Ş\\.).{0,15}(kazand|üstlendi|aldı)'],
        'neg': ['ihale ilanı', 'ihale takvimi', 'ihale çıkacak', 'ihale açıklan', 'ihale gerçekleş'],
    },
    'imar_degisikligi': {
        'pos': ['imar.{0,5}plan(ı|ları|ında|ında)', '1/1000', '1/5000',
                'plan değişikliği', 'plan değişiklikleri', 'imar değişikliği',
                'askıya çıkarıldı', 'meclis.{0,15}(plan|imar|onay)',
                'koruma amaçlı imar', 'nazım imar plan'],
        'neg': [],
    },
    'mega_proje': {
        'pos': ['mega proje', 'milyar.{0,5}TL.{0,15}proje', 'milyar dolar',
                'kanal istanbul', 'havalimanı', '3.köprü', 'üçüncü köprü',
                'avrasya tüneli', 'osb proje', 'şehir hastanesi', 'metroya',
                'metro hattı', 'yüksek hızlı tren', 'YHT', 'tüp geçit'],
        'neg': [],
    },
    'banka_finans': {
        'pos': ['konut.{0,5}kredi', 'kredi faiz', 'mortgage', 'banka.{0,15}konut',
                'BDDK', 'TCMB.{0,8}faiz', 'enflasyon.{0,8}(rapor|tahmin)',
                'borsa.{0,8}gayrimenkul', 'gyo halka arz'],
        'neg': [],
    },
    'gentrifikasyon': {
        'pos': ['kentsel dönüşüm', 'rezerv yapı', 'soylulaştırma',
                'tarihi.{0,8}mahalle.{0,8}(dönüşüm|proje)', 'rant.{0,8}artış',
                'mahalle.{0,5}yıkım', 'apartman.{0,5}dönüş'],
        'neg': [],
    },
    'altyapi': {
        'pos': ['altyapı', 'doğalgaz hattı', 'içme suyu', 'kanalizasyon',
                'arıtma tesisi', 'baraj.{0,8}sulama', 'sulama projesi',
                'ulaşım altyapı', 'köprü.{0,8}yapım', 'tünel.{0,8}yapım',
                'enerji nakil', 'trafo merkezi', 'EYAS', 'OSB altyapı'],
        'neg': [],
    },
}

# Kazanan firma adayı — TR pattern: "XYZ İnş. kazandı / üstlendi"
KAZANAN_FIRMA_REGEX = re.compile(
    r'([A-ZÇĞİÖŞÜ][A-Za-zçğıöşüÇĞİÖŞÜ\.\& ]{2,40}?(?:İnşaat|İnş\.|Yapı|GYO|Holding|A\.Ş\.|Ltd\.|San\.|Ti̇c\.))[\s.,]{0,10}'
    r'(?:ihale.{0,5}aldı|kazandı|üstlendi|firma olarak seçildi)',
    re.IGNORECASE
)


def normalize_text(t):
    return re.sub(r'\s+', ' ', (t or '')).strip().lower()


def iller_bul(metin_low):
    """Metinde geçen 81 il slug'larını bul — set'e dönüştür, sırala."""
    bulunan = set()
    for kelime, slug in IL_SLUG.items():
        if not kelime:
            continue
        # Kelime sınırı: önce/sonra harf-olmayan
        if re.search(r'(?:^|[^a-zçğıöşüâî])' + re.escape(kelime) + r'(?:[^a-zçğıöşüâî]|$)',
                     metin_low):
            bulunan.add(slug)
    return sorted(bulunan)


def kategori_bul(metin_low):
    """KATEGORI_ENUM üzerinden pos pattern eşleşmesi — neg varsa düşür."""
    kategoriler = []
    for kat, kurallar in KATEGORI_ENUM.items():
        eslesme = False
        for p in kurallar['pos']:
            if re.search(p, metin_low, re.IGNORECASE):
                eslesme = True
                break
        if not eslesme:
            continue
        # Neg pattern (yalan-pozitif önleme)
        neg_var = False
        for n in kurallar['neg']:
            if re.search(n, metin_low, re.IGNORECASE):
                neg_var = True
                break
        if neg_var:
            continue
        kategoriler.append(kat)
    return kategoriler


def kazanan_firma_aday(metin):
    """İhale-sonuç kategori için firma adayı — yoksa None."""
    m = KAZANAN_FIRMA_REGEX.search(metin or '')
    if m:
        ad = m.group(1).strip()
        # KVKK: sadece tüzel-kişi pattern (İnş./GYO/Holding gibi sonek şart, regex zaten gerekli)
        return ad[:60]
    return None


def siniflandir(kayit):
    """Mevcut kayda 'siniflar' alanını ekle.

    Args:
        kayit: dict, en az 'baslik_kisa' ve 'url' alanları olmalı
    Returns:
        kayit (aynı obje, in-place değiştirildi)
    """
    baslik = kayit.get('baslik_kisa') or ''
    metin_low = normalize_text(baslik)

    iller = iller_bul(metin_low)
    kategoriler = kategori_bul(metin_low)

    # İlçeler şu an için ARTIRMA YOK — başlıkta mahalle/ilçe geçişi
    # tek seferlik tarama maliyetli + yalan-pozitif yüksek (B99 enrichment lane)
    ilceler = []

    kazanan = None
    if 'ihale_sonuc' in kategoriler:
        kazanan = kazanan_firma_aday(baslik)

    kayit['siniflar'] = {
        'version': SCHEMA_VERSION,
        'iller': iller,
        'ilceler': ilceler,
        'kategoriler': kategoriler,
        'kazanan_firma_aday': kazanan,
    }
    return kayit


if __name__ == '__main__':
    # Hızlı self-test
    ornek = [
        {'baslik_kisa': 'Bakan Kurum: Kentsel dönüşüm Türkiye\'de tercih...',
         'url': 'https://www.aa.com.tr/...'},
        {'baslik_kisa': 'İstanbul Sarıyer\'de 1/1000 imar planı askıya çıkarıldı',
         'url': 'x'},
        {'baslik_kisa': 'Ankara Eryaman metro hattı ihalesini ABC İnş. kazandı',
         'url': 'y'},
        {'baslik_kisa': 'TCMB faiz kararı 50 baz puan indi konut kredisi etkilenecek',
         'url': 'z'},
    ]
    import json
    for o in ornek:
        siniflandir(o)
        print(json.dumps(o['siniflar'], ensure_ascii=False))
