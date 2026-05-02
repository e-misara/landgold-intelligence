import json

DB_PATH = '/Users/GAC-A/landgold-agents/data/research/osb_database.json'

NEW_OSB: dict[str, list] = {
    "Marmara": [
        {"il":"İstanbul","osb_adi":"Topkapı Deri OSB","ilce":"Bağcılar","alan_ha":120,"durum":"faal","ihracat_milyon_usd":480,"sektor":"deri,hazır giyim","arsa_usd_m2":1600,"arsa_trend":"+8%","yatirim_notu":"B","tradia_score":74},
        {"il":"İstanbul","osb_adi":"Çobançeşme OSB","ilce":"Bahçelievler","alan_ha":95,"durum":"faal","ihracat_milyon_usd":320,"sektor":"tekstil,ambalaj","arsa_usd_m2":1400,"arsa_trend":"+7%","yatirim_notu":"B","tradia_score":71},
        {"il":"İstanbul","osb_adi":"İkitelli Deri OSB","ilce":"Başakşehir","alan_ha":180,"durum":"faal","ihracat_milyon_usd":680,"sektor":"deri,plastik","arsa_usd_m2":1100,"arsa_trend":"+9%","yatirim_notu":"B","tradia_score":73},
        {"il":"Bursa","osb_adi":"İnegöl OSB","ilce":"İnegöl","alan_ha":680,"durum":"faal","ihracat_milyon_usd":2800,"sektor":"mobilya,orman ürünleri","arsa_usd_m2":380,"arsa_trend":"+16%","yatirim_notu":"A","tradia_score":84},
        {"il":"Bursa","osb_adi":"Mustafakemalpaşa OSB","ilce":"Mustafakemalpaşa","alan_ha":320,"durum":"faal","ihracat_milyon_usd":680,"sektor":"gıda,tekstil","arsa_usd_m2":280,"arsa_trend":"+12%","yatirim_notu":"B","tradia_score":73},
        {"il":"Bursa","osb_adi":"Kestel OSB","ilce":"Kestel","alan_ha":220,"durum":"faal","ihracat_milyon_usd":480,"sektor":"metal,plastik","arsa_usd_m2":320,"arsa_trend":"+11%","yatirim_notu":"B","tradia_score":71},
        {"il":"Kocaeli","osb_adi":"Gebze 2. OSB","ilce":"Gebze","alan_ha":580,"durum":"faal","ihracat_milyon_usd":2800,"sektor":"kimya,plastik","arsa_usd_m2":460,"arsa_trend":"+14%","yatirim_notu":"A","tradia_score":83},
        {"il":"Kocaeli","osb_adi":"Kocaeli 2. OSB","ilce":"Körfez","alan_ha":480,"durum":"faal","ihracat_milyon_usd":2200,"sektor":"petrokimya,metal","arsa_usd_m2":420,"arsa_trend":"+16%","yatirim_notu":"A","tradia_score":82},
        {"il":"Kocaeli","osb_adi":"İzmit OSB","ilce":"İzmit","alan_ha":380,"durum":"faal","ihracat_milyon_usd":1800,"sektor":"kağıt,ambalaj","arsa_usd_m2":380,"arsa_trend":"+13%","yatirim_notu":"B","tradia_score":79},
        {"il":"Tekirdağ","osb_adi":"Hayrabolu OSB","ilce":"Hayrabolu","alan_ha":180,"durum":"faal","ihracat_milyon_usd":280,"sektor":"gıda,tekstil","arsa_usd_m2":100,"arsa_trend":"+12%","yatirim_notu":"C","tradia_score":68},
        {"il":"Tekirdağ","osb_adi":"Malkara OSB","ilce":"Malkara","alan_ha":160,"durum":"faal","ihracat_milyon_usd":180,"sektor":"gıda","arsa_usd_m2":90,"arsa_trend":"+10%","yatirim_notu":"C","tradia_score":64},
        {"il":"Balıkesir","osb_adi":"Gönen OSB","ilce":"Gönen","alan_ha":220,"durum":"faal","ihracat_milyon_usd":380,"sektor":"deri,tekstil","arsa_usd_m2":110,"arsa_trend":"+11%","yatirim_notu":"C","tradia_score":67},
        {"il":"Balıkesir","osb_adi":"Bandırma OSB","ilce":"Bandırma","alan_ha":480,"durum":"faal","ihracat_milyon_usd":1200,"sektor":"kimya,gübre,liman","arsa_usd_m2":160,"arsa_trend":"+14%","yatirim_notu":"B","tradia_score":75},
        {"il":"Çanakkale","osb_adi":"Çanakkale OSB","ilce":"Merkez","alan_ha":280,"durum":"faal","ihracat_milyon_usd":480,"sektor":"seramik,gıda","arsa_usd_m2":180,"arsa_trend":"+18%","yatirim_notu":"B","tradia_score":76},
        {"il":"Edirne","osb_adi":"Edirne OSB","ilce":"Merkez","alan_ha":380,"durum":"faal","ihracat_milyon_usd":680,"sektor":"tekstil,gıda","arsa_usd_m2":120,"arsa_trend":"+14%","yatirim_notu":"B","tradia_score":72},
        {"il":"Kırklareli","osb_adi":"Lüleburgaz OSB","ilce":"Lüleburgaz","alan_ha":320,"durum":"faal","ihracat_milyon_usd":580,"sektor":"tekstil,gıda,metal","arsa_usd_m2":130,"arsa_trend":"+13%","yatirim_notu":"B","tradia_score":73},
        {"il":"Sakarya","osb_adi":"Arifiye OSB","ilce":"Arifiye","alan_ha":280,"durum":"faal","ihracat_milyon_usd":980,"sektor":"otomotiv,plastik","arsa_usd_m2":200,"arsa_trend":"+13%","yatirim_notu":"B","tradia_score":76},
        {"il":"Sakarya","osb_adi":"Hendek OSB","ilce":"Hendek","alan_ha":220,"durum":"faal","ihracat_milyon_usd":480,"sektor":"metal,plastik","arsa_usd_m2":170,"arsa_trend":"+12%","yatirim_notu":"B","tradia_score":73},
        {"il":"Düzce","osb_adi":"Düzce OSB","ilce":"Merkez","alan_ha":380,"durum":"faal","ihracat_milyon_usd":680,"sektor":"orman ürünleri,plastik","arsa_usd_m2":160,"arsa_trend":"+13%","yatirim_notu":"B","tradia_score":73},
        {"il":"Bolu","osb_adi":"Bolu OSB","ilce":"Merkez","alan_ha":280,"durum":"faal","ihracat_milyon_usd":480,"sektor":"gıda,plastik,metal","arsa_usd_m2":150,"arsa_trend":"+12%","yatirim_notu":"B","tradia_score":71},
    ],
    "Ege": [
        {"il":"İzmir","osb_adi":"İzmir Serbest Bölge","ilce":"Gaziemir","alan_ha":320,"durum":"faal","ihracat_milyon_usd":2800,"sektor":"elektronik,makine,lojistik","arsa_usd_m2":580,"arsa_trend":"+16%","yatirim_notu":"A","tradia_score":86},
        {"il":"İzmir","osb_adi":"Menderes OSB","ilce":"Menderes","alan_ha":280,"durum":"faal","ihracat_milyon_usd":680,"sektor":"gıda,seramik","arsa_usd_m2":240,"arsa_trend":"+14%","yatirim_notu":"B","tradia_score":74},
        {"il":"İzmir","osb_adi":"Bergama OSB","ilce":"Bergama","alan_ha":180,"durum":"faal","ihracat_milyon_usd":280,"sektor":"gıda,tekstil","arsa_usd_m2":160,"arsa_trend":"+11%","yatirim_notu":"C","tradia_score":67},
        {"il":"Manisa","osb_adi":"Akhisar OSB","ilce":"Akhisar","alan_ha":380,"durum":"faal","ihracat_milyon_usd":980,"sektor":"zeytin,gıda,tekstil","arsa_usd_m2":140,"arsa_trend":"+12%","yatirim_notu":"B","tradia_score":73},
        {"il":"Manisa","osb_adi":"Salihli OSB","ilce":"Salihli","alan_ha":280,"durum":"faal","ihracat_milyon_usd":580,"sektor":"gıda,tekstil","arsa_usd_m2":130,"arsa_trend":"+11%","yatirim_notu":"C","tradia_score":70},
        {"il":"Denizli","osb_adi":"Çardak OSB","ilce":"Çardak","alan_ha":180,"durum":"faal","ihracat_milyon_usd":380,"sektor":"mermer,tekstil","arsa_usd_m2":120,"arsa_trend":"+10%","yatirim_notu":"C","tradia_score":66},
        {"il":"Aydın","osb_adi":"Nazilli OSB","ilce":"Nazilli","alan_ha":320,"durum":"faal","ihracat_milyon_usd":680,"sektor":"tekstil,boyama","arsa_usd_m2":140,"arsa_trend":"+12%","yatirim_notu":"C","tradia_score":69},
        {"il":"Aydın","osb_adi":"Söke OSB","ilce":"Söke","alan_ha":220,"durum":"faal","ihracat_milyon_usd":380,"sektor":"gıda,pamuk","arsa_usd_m2":130,"arsa_trend":"+11%","yatirim_notu":"C","tradia_score":67},
        {"il":"Muğla","osb_adi":"Milas OSB","ilce":"Milas","alan_ha":280,"durum":"faal","ihracat_milyon_usd":480,"sektor":"mermer,enerji","arsa_usd_m2":200,"arsa_trend":"+14%","yatirim_notu":"B","tradia_score":72},
        {"il":"Afyonkarahisar","osb_adi":"Dinar OSB","ilce":"Dinar","alan_ha":160,"durum":"faal","ihracat_milyon_usd":180,"sektor":"mermer,gıda","arsa_usd_m2":90,"arsa_trend":"+9%","yatirim_notu":"C","tradia_score":62},
        {"il":"Kütahya","osb_adi":"Tavşanlı OSB","ilce":"Tavşanlı","alan_ha":180,"durum":"faal","ihracat_milyon_usd":280,"sektor":"bor,seramik","arsa_usd_m2":100,"arsa_trend":"+10%","yatirim_notu":"C","tradia_score":64},
        {"il":"Uşak","osb_adi":"Eşme OSB","ilce":"Eşme","alan_ha":220,"durum":"faal","ihracat_milyon_usd":580,"sektor":"deri,tekstil","arsa_usd_m2":120,"arsa_trend":"+11%","yatirim_notu":"C","tradia_score":68},
    ],
    "Karadeniz": [
        {"il":"Samsun","osb_adi":"Samsun 2. OSB","ilce":"İlkadım","alan_ha":320,"durum":"faal","ihracat_milyon_usd":580,"sektor":"gıda,kimya","arsa_usd_m2":160,"arsa_trend":"+14%","yatirim_notu":"B","tradia_score":72},
        {"il":"Trabzon","osb_adi":"Araklı OSB","ilce":"Araklı","alan_ha":180,"durum":"faal","ihracat_milyon_usd":280,"sektor":"fındık,gıda","arsa_usd_m2":180,"arsa_trend":"+20%","yatirim_notu":"C","tradia_score":69},
        {"il":"Zonguldak","osb_adi":"Ereğli OSB","ilce":"Ereğli","alan_ha":420,"durum":"faal","ihracat_milyon_usd":1200,"sektor":"çelik,metal","arsa_usd_m2":160,"arsa_trend":"+12%","yatirim_notu":"B","tradia_score":73},
        {"il":"Bolu","osb_adi":"Gerede OSB","ilce":"Gerede","alan_ha":220,"durum":"faal","ihracat_milyon_usd":380,"sektor":"orman,plastik","arsa_usd_m2":130,"arsa_trend":"+11%","yatirim_notu":"C","tradia_score":67},
        {"il":"Kastamonu","osb_adi":"Taşköprü OSB","ilce":"Taşköprü","alan_ha":160,"durum":"faal","ihracat_milyon_usd":120,"sektor":"ahşap,gıda","arsa_usd_m2":80,"arsa_trend":"+8%","yatirim_notu":"C","tradia_score":58},
        {"il":"Sinop","osb_adi":"Sinop OSB","ilce":"Merkez","alan_ha":180,"durum":"faal","ihracat_milyon_usd":120,"sektor":"gıda,balıkçılık","arsa_usd_m2":110,"arsa_trend":"+10%","yatirim_notu":"C","tradia_score":60},
        {"il":"Amasya","osb_adi":"Amasya OSB","ilce":"Merkez","alan_ha":220,"durum":"faal","ihracat_milyon_usd":280,"sektor":"gıda,metal","arsa_usd_m2":110,"arsa_trend":"+10%","yatirim_notu":"C","tradia_score":62},
        {"il":"Tokat","osb_adi":"Tokat OSB","ilce":"Merkez","alan_ha":280,"durum":"faal","ihracat_milyon_usd":320,"sektor":"gıda,tekstil","arsa_usd_m2":100,"arsa_trend":"+10%","yatirim_notu":"C","tradia_score":61},
        {"il":"Çorum","osb_adi":"Çorum 2. OSB","ilce":"Merkez","alan_ha":280,"durum":"faal","ihracat_milyon_usd":380,"sektor":"metal,makine","arsa_usd_m2":120,"arsa_trend":"+11%","yatirim_notu":"C","tradia_score":65},
        {"il":"Bartın","osb_adi":"Bartın OSB","ilce":"Merkez","alan_ha":180,"durum":"faal","ihracat_milyon_usd":180,"sektor":"orman,ambalaj","arsa_usd_m2":100,"arsa_trend":"+9%","yatirim_notu":"C","tradia_score":59},
        {"il":"Karabük","osb_adi":"Safranbolu OSB","ilce":"Safranbolu","alan_ha":160,"durum":"faal","ihracat_milyon_usd":120,"sektor":"çelik,turizm","arsa_usd_m2":120,"arsa_trend":"+10%","yatirim_notu":"C","tradia_score":61},
    ],
    "İç Anadolu": [
        {"il":"Ankara","osb_adi":"Sincan OSB","ilce":"Sincan","alan_ha":1200,"durum":"faal","ihracat_milyon_usd":3200,"sektor":"savunma,makine","arsa_usd_m2":260,"arsa_trend":"+15%","yatirim_notu":"A","tradia_score":83},
        {"il":"Ankara","osb_adi":"Polatlı OSB","ilce":"Polatlı","alan_ha":480,"durum":"faal","ihracat_milyon_usd":680,"sektor":"savunma,gıda","arsa_usd_m2":180,"arsa_trend":"+12%","yatirim_notu":"B","tradia_score":74},
        {"il":"Konya","osb_adi":"Konya 3. OSB","ilce":"Karatay","alan_ha":800,"durum":"faal","ihracat_milyon_usd":1800,"sektor":"makine,metal","arsa_usd_m2":150,"arsa_trend":"+13%","yatirim_notu":"B","tradia_score":77},
        {"il":"Konya","osb_adi":"Seydişehir OSB","ilce":"Seydişehir","alan_ha":280,"durum":"faal","ihracat_milyon_usd":480,"sektor":"alüminyum,metal","arsa_usd_m2":120,"arsa_trend":"+11%","yatirim_notu":"B","tradia_score":71},
        {"il":"Eskişehir","osb_adi":"Eskişehir 2. OSB","ilce":"Tepebaşı","alan_ha":820,"durum":"faal","ihracat_milyon_usd":1800,"sektor":"demiryolu,makine","arsa_usd_m2":200,"arsa_trend":"+13%","yatirim_notu":"B","tradia_score":79},
        {"il":"Kayseri","osb_adi":"Kayseri 3. OSB","ilce":"Talas","alan_ha":680,"durum":"faal","ihracat_milyon_usd":1200,"sektor":"mobilya,gıda","arsa_usd_m2":130,"arsa_trend":"+12%","yatirim_notu":"B","tradia_score":74},
        {"il":"Nevşehir","osb_adi":"Nevşehir OSB","ilce":"Merkez","alan_ha":220,"durum":"faal","ihracat_milyon_usd":180,"sektor":"gıda,turizm malzemeleri","arsa_usd_m2":140,"arsa_trend":"+14%","yatirim_notu":"C","tradia_score":68},
        {"il":"Niğde","osb_adi":"Niğde OSB","ilce":"Merkez","alan_ha":280,"durum":"faal","ihracat_milyon_usd":380,"sektor":"gıda,plastik","arsa_usd_m2":110,"arsa_trend":"+11%","yatirim_notu":"C","tradia_score":65},
        {"il":"Aksaray","osb_adi":"Aksaray 2. OSB","ilce":"Merkez","alan_ha":320,"durum":"faal","ihracat_milyon_usd":680,"sektor":"otomotiv,metal","arsa_usd_m2":120,"arsa_trend":"+12%","yatirim_notu":"B","tradia_score":71},
        {"il":"Karaman","osb_adi":"Karaman OSB","ilce":"Merkez","alan_ha":380,"durum":"faal","ihracat_milyon_usd":580,"sektor":"gıda,tekstil","arsa_usd_m2":110,"arsa_trend":"+11%","yatirim_notu":"C","tradia_score":67},
        {"il":"Kırıkkale","osb_adi":"Kırıkkale 2. OSB","ilce":"Merkez","alan_ha":220,"durum":"faal","ihracat_milyon_usd":320,"sektor":"savunma,metal","arsa_usd_m2":140,"arsa_trend":"+12%","yatirim_notu":"B","tradia_score":69},
        {"il":"Yozgat","osb_adi":"Yozgat OSB","ilce":"Merkez","alan_ha":280,"durum":"faal","ihracat_milyon_usd":220,"sektor":"gıda,metal","arsa_usd_m2":90,"arsa_trend":"+9%","yatirim_notu":"C","tradia_score":60},
        {"il":"Sivas","osb_adi":"Sivas 2. OSB","ilce":"Merkez","alan_ha":380,"durum":"faal","ihracat_milyon_usd":380,"sektor":"çimento,gıda","arsa_usd_m2":90,"arsa_trend":"+10%","yatirim_notu":"C","tradia_score":62},
        {"il":"Kırşehir","osb_adi":"Kırşehir OSB","ilce":"Merkez","alan_ha":220,"durum":"faal","ihracat_milyon_usd":180,"sektor":"gıda,plastik","arsa_usd_m2":85,"arsa_trend":"+9%","yatirim_notu":"C","tradia_score":58},
    ],
    "Güneydoğu": [
        {"il":"Gaziantep","osb_adi":"Gaziantep 2. OSB","ilce":"Şahinbey","alan_ha":1800,"durum":"faal","ihracat_milyon_usd":8500,"sektor":"tekstil,plastik,metal","arsa_usd_m2":160,"arsa_trend":"+20%","yatirim_notu":"A","tradia_score":86},
        {"il":"Gaziantep","osb_adi":"Oğuzeli OSB","ilce":"Oğuzeli","alan_ha":380,"durum":"faal","ihracat_milyon_usd":980,"sektor":"gıda,plastik","arsa_usd_m2":110,"arsa_trend":"+14%","yatirim_notu":"B","tradia_score":73},
        {"il":"Adana","osb_adi":"Adana 2. OSB","ilce":"Yüreğir","alan_ha":980,"durum":"faal","ihracat_milyon_usd":2800,"sektor":"tekstil,gıda","arsa_usd_m2":140,"arsa_trend":"+13%","yatirim_notu":"B","tradia_score":78},
        {"il":"Mersin","osb_adi":"Mersin 2. OSB","ilce":"Mezitli","alan_ha":680,"durum":"faal","ihracat_milyon_usd":2200,"sektor":"kimya,plastik","arsa_usd_m2":160,"arsa_trend":"+16%","yatirim_notu":"B","tradia_score":79},
        {"il":"Kahramanmaraş","osb_adi":"Kahramanmaraş 2. OSB","ilce":"Türkoğlu","alan_ha":680,"durum":"faal","ihracat_milyon_usd":1800,"sektor":"tekstil,metal","arsa_usd_m2":120,"arsa_trend":"+12%","yatirim_notu":"B","tradia_score":74},
        {"il":"Hatay","osb_adi":"Antakya OSB","ilce":"Antakya","alan_ha":420,"durum":"faal","ihracat_milyon_usd":1200,"sektor":"gıda,metal","arsa_usd_m2":130,"arsa_trend":"+12%","yatirim_notu":"B","tradia_score":72},
        {"il":"Adıyaman","osb_adi":"Adıyaman OSB","ilce":"Merkez","alan_ha":320,"durum":"faal","ihracat_milyon_usd":480,"sektor":"tekstil,gıda","arsa_usd_m2":90,"arsa_trend":"+11%","yatirim_notu":"C","tradia_score":65},
        {"il":"Batman","osb_adi":"Batman OSB","ilce":"Merkez","alan_ha":280,"durum":"faal","ihracat_milyon_usd":380,"sektor":"petrol,plastik","arsa_usd_m2":85,"arsa_trend":"+10%","yatirim_notu":"C","tradia_score":62},
        {"il":"Osmaniye","osb_adi":"Osmaniye OSB","ilce":"Merkez","alan_ha":380,"durum":"faal","ihracat_milyon_usd":680,"sektor":"tekstil,gıda","arsa_usd_m2":110,"arsa_trend":"+11%","yatirim_notu":"C","tradia_score":67},
        {"il":"Şanlıurfa","osb_adi":"Şanlıurfa 2. OSB","ilce":"Haliliye","alan_ha":380,"durum":"faal","ihracat_milyon_usd":480,"sektor":"gıda,tekstil","arsa_usd_m2":90,"arsa_trend":"+12%","yatirim_notu":"C","tradia_score":66},
        {"il":"Diyarbakır","osb_adi":"Diyarbakır 2. OSB","ilce":"Kayapınar","alan_ha":420,"durum":"faal","ihracat_milyon_usd":480,"sektor":"gıda,plastik","arsa_usd_m2":85,"arsa_trend":"+11%","yatirim_notu":"C","tradia_score":64},
        {"il":"Mardin","osb_adi":"Mardin 2. OSB","ilce":"Kızıltepe","alan_ha":280,"durum":"faal","ihracat_milyon_usd":220,"sektor":"gıda,tekstil","arsa_usd_m2":75,"arsa_trend":"+10%","yatirim_notu":"C","tradia_score":60},
    ],
    "Doğu Anadolu": [
        {"il":"Erzurum","osb_adi":"Erzurum 2. OSB","ilce":"Palandöken","alan_ha":380,"durum":"faal","ihracat_milyon_usd":280,"sektor":"gıda,inşaat","arsa_usd_m2":85,"arsa_trend":"+9%","yatirim_notu":"C","tradia_score":59},
        {"il":"Malatya","osb_adi":"Malatya 2. OSB","ilce":"Battalgazi","alan_ha":480,"durum":"faal","ihracat_milyon_usd":480,"sektor":"gıda,tekstil","arsa_usd_m2":95,"arsa_trend":"+10%","yatirim_notu":"C","tradia_score":62},
        {"il":"Elazığ","osb_adi":"Elazığ 2. OSB","ilce":"Merkez","alan_ha":320,"durum":"faal","ihracat_milyon_usd":280,"sektor":"metal,gıda","arsa_usd_m2":80,"arsa_trend":"+9%","yatirim_notu":"C","tradia_score":58},
        {"il":"Van","osb_adi":"Van 2. OSB","ilce":"İpekyolu","alan_ha":280,"durum":"faal","ihracat_milyon_usd":180,"sektor":"gıda,tekstil","arsa_usd_m2":70,"arsa_trend":"+9%","yatirim_notu":"C","tradia_score":55},
        {"il":"Ağrı","osb_adi":"Ağrı OSB","ilce":"Merkez","alan_ha":220,"durum":"faal","ihracat_milyon_usd":120,"sektor":"gıda,inşaat","arsa_usd_m2":65,"arsa_trend":"+8%","yatirim_notu":"C","tradia_score":52},
        {"il":"Muş","osb_adi":"Muş OSB","ilce":"Merkez","alan_ha":180,"durum":"faal","ihracat_milyon_usd":80,"sektor":"gıda","arsa_usd_m2":60,"arsa_trend":"+8%","yatirim_notu":"C","tradia_score":50},
        {"il":"Bingöl","osb_adi":"Bingöl OSB","ilce":"Merkez","alan_ha":160,"durum":"faal","ihracat_milyon_usd":60,"sektor":"gıda,inşaat","arsa_usd_m2":60,"arsa_trend":"+7%","yatirim_notu":"C","tradia_score":49},
        {"il":"Kars","osb_adi":"Kars OSB","ilce":"Merkez","alan_ha":180,"durum":"faal","ihracat_milyon_usd":80,"sektor":"hayvancılık,gıda","arsa_usd_m2":65,"arsa_trend":"+8%","yatirim_notu":"C","tradia_score":51},
        {"il":"Iğdır","osb_adi":"Iğdır OSB","ilce":"Merkez","alan_ha":160,"durum":"faal","ihracat_milyon_usd":120,"sektor":"gıda,sınır ticareti","arsa_usd_m2":70,"arsa_trend":"+9%","yatirim_notu":"C","tradia_score":53},
        {"il":"Ardahan","osb_adi":"Ardahan OSB","ilce":"Merkez","alan_ha":120,"durum":"faal","ihracat_milyon_usd":40,"sektor":"hayvancılık,gıda","arsa_usd_m2":55,"arsa_trend":"+7%","yatirim_notu":"C","tradia_score":47},
        {"il":"Erzincan","osb_adi":"Erzincan 2. OSB","ilce":"Merkez","alan_ha":220,"durum":"faal","ihracat_milyon_usd":160,"sektor":"metal,gıda","arsa_usd_m2":75,"arsa_trend":"+9%","yatirim_notu":"C","tradia_score":55},
    ],
}

# Load existing
with open(DB_PATH, encoding='utf-8') as f:
    db = json.load(f)

# Append and count new entries
added_total = 0
for region, new_entries in NEW_OSB.items():
    before = len(db['regions'][region]['osb_list'])
    db['regions'][region]['osb_list'].extend(new_entries)
    after = len(db['regions'][region]['osb_list'])
    added_total += len(new_entries)

db['metadata']['last_updated'] = '2026-05-03'

# Save back
with open(DB_PATH, 'w', encoding='utf-8') as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

# Report
grand_total = sum(len(r['osb_list']) for r in db['regions'].values())
print(f"Added {added_total} new OSBs — total now: {grand_total} across {len(db['regions'])} regions")
print()
for region, data in db['regions'].items():
    osbs = data['osb_list']
    top = sorted(osbs, key=lambda x: x['tradia_score'], reverse=True)[:3]
    grades = {'A': 0, 'B': 0, 'C': 0}
    for o in osbs:
        grades[o['yatirim_notu']] = grades.get(o['yatirim_notu'], 0) + 1
    grade_str = '  '.join(f"{g}:{c}" for g, c in grades.items() if c)
    print(f"{region:<15} {len(osbs):>3} OSB   [{grade_str}]")
    for o in top:
        print(f"  {o['tradia_score']}/100  {o['il']:<14} {o['osb_adi']:<30} {o['arsa_usd_m2']:>5}$/m²  {o['arsa_trend']}")
