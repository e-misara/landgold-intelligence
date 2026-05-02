const TURKEY_INVESTMENT_DATA = {
  // TURIZM
  "Antalya": {category:"turizm", score:92, trend:"+18%", highlights:["Mediterranean coast","5M tourists/year","Strong rental yield"], news:[]},
  "Muğla": {category:"turizm", score:88, trend:"+22%", highlights:["Bodrum, Marmaris, Fethiye","Luxury villa market","High foreign buyer demand"], news:[]},
  "İzmir": {category:"turizm", score:82, trend:"+15%", highlights:["Aegean coast","Growing expat community","Alsancak premium district"], news:[]},
  "Nevşehir": {category:"turizm", score:78, trend:"+31%", highlights:["Cappadocia tourism boom","Hotel & boutique investment","Airbnb high yields"], news:[]},
  "Trabzon": {category:"turizm", score:72, trend:"+28%", highlights:["Black Sea tourism","Gulf investor demand","Growing infrastructure"], news:[]},
  "Artvin": {category:"turizm", score:65, trend:"+12%", highlights:["Nature tourism","Low entry price","Long-term upside"], news:[]},

  // SANAYİ & LOJİSTİK
  "İstanbul": {category:"sanayi", score:95, trend:"+12%", highlights:["Financial hub","Europe's busiest airport","7 active listings"], news:[]},
  "Kocaeli": {category:"sanayi", score:90, trend:"+14%", highlights:["TEM & E-5 corridor","Major industrial zone","Ford, Toyota plants nearby"], news:[]},
  "Bursa": {category:"sanayi", score:87, trend:"+11%", highlights:["Automotive industry","OIZ zones","Strong rental market"], news:[]},
  "Gaziantep": {category:"sanayi", score:85, trend:"+19%", highlights:["Largest OIZ in Turkey","Textile & food export hub","Low land prices"], news:[]},
  "Mersin": {category:"sanayi", score:83, trend:"+16%", highlights:["Turkey's largest port","Free trade zone","Logistics investment"], news:[]},
  "İzmit": {category:"sanayi", score:80, trend:"+13%", highlights:["Petrochemical corridor","Highway access","Industrial demand"], news:[]},
  "Tekirdağ": {category:"sanayi", score:78, trend:"+10%", highlights:["Thrace industrial zone","EU trade route","Low cost per m²"], news:[]},
  "Sakarya": {category:"sanayi", score:76, trend:"+9%", highlights:["Automotive cluster","E-5 highway","Growing workforce"], news:[]},

  // TARIM & ARSA
  "Konya": {category:"tarim", score:80, trend:"+8%", highlights:["Largest agricultural land","Grain production hub","Low land prices"], news:[]},
  "Şanlıurfa": {category:"tarim", score:74, trend:"+15%", highlights:["GAP project region","Irrigation projects","Zoning upside potential"], news:[]},
  "Diyarbakır": {category:"tarim", score:68, trend:"+12%", highlights:["Agricultural land","Low entry prices","Infrastructure development"], news:[]},
  "Erzurum": {category:"tarim", score:62, trend:"+7%", highlights:["Eastern hub","Winter tourism potential","State investment"], news:[]},
  "Sivas": {category:"tarim", score:60, trend:"+6%", highlights:["Agricultural potential","Rail connection","Low competition"], news:[]},

  // KONUT & KENTSEL
  "Ankara": {category:"konut", score:85, trend:"+9%", highlights:["Capital city","Government district demand","Stable rental market"], news:[]},
  "Eskişehir": {category:"konut", score:78, trend:"+11%", highlights:["University city","Young population","Affordable entry"], news:[]},
  "Kayseri": {category:"konut", score:74, trend:"+8%", highlights:["Growing middle class","Industrial + residential mix","Low prices"], news:[]},
  "Adana": {category:"konut", score:72, trend:"+10%", highlights:["Southern hub","Population growth","Commercial development"], news:[]},

  // TEKNOLOJİ & YENİLİK
  "Ankara_tek": {category:"teknoloji", score:88, trend:"+13%", highlights:["ODTÜ Teknokent","Defense industry cluster","Startup ecosystem"], news:[]},
  "İstanbul_tek": {category:"teknoloji", score:90, trend:"+15%", highlights:["Maslak tech corridor","Startup hub","VC investment"], news:[]},
  "İzmir_tek": {category:"teknoloji", score:76, trend:"+18%", highlights:["Teknoloji geliştirme bölgesi","Smart city projects","Young talent"], news:[]},
};

// Province to category mapping for all 81 provinces
const PROVINCE_CATEGORIES = {
  "Adana": "konut", "Adıyaman": "tarim", "Afyonkarahisar": "tarim",
  "Ağrı": "tarim", "Amasya": "tarim", "Ankara": "teknoloji",
  "Antalya": "turizm", "Artvin": "turizm", "Aydın": "turizm",
  "Balıkesir": "konut", "Bilecik": "sanayi", "Bingöl": "tarim",
  "Bitlis": "tarim", "Bolu": "turizm", "Burdur": "tarim",
  "Bursa": "sanayi", "Çanakkale": "turizm", "Çankırı": "tarim",
  "Çorum": "tarim", "Denizli": "sanayi", "Diyarbakır": "tarim",
  "Edirne": "tarim", "Elazığ": "tarim", "Erzincan": "tarim",
  "Erzurum": "tarim", "Eskişehir": "konut", "Gaziantep": "sanayi",
  "Giresun": "turizm", "Gümüşhane": "tarim", "Hakkari": "tarim",
  "Hatay": "konut", "Isparta": "tarim", "İçel": "turizm",
  "İstanbul": "sanayi", "İzmir": "turizm", "Kars": "tarim",
  "Kastamonu": "tarim", "Kayseri": "konut", "Kırklareli": "tarim",
  "Kırşehir": "tarim", "Kocaeli": "sanayi", "Konya": "tarim",
  "Kütahya": "tarim", "Malatya": "tarim", "Manisa": "sanayi",
  "Kahramanmaraş": "sanayi", "Mardin": "tarim", "Muğla": "turizm",
  "Muş": "tarim", "Nevşehir": "turizm", "Niğde": "tarim",
  "Ordu": "turizm", "Rize": "turizm", "Sakarya": "sanayi",
  "Samsun": "konut", "Siirt": "tarim", "Sinop": "turizm",
  "Sivas": "tarim", "Tekirdağ": "sanayi", "Tokat": "tarim",
  "Trabzon": "turizm", "Tunceli": "tarim", "Şanlıurfa": "tarim",
  "Uşak": "sanayi", "Van": "tarim", "Yozgat": "tarim",
  "Zonguldak": "sanayi", "Aksaray": "tarim", "Bayburt": "tarim",
  "Karaman": "tarim", "Kırıkkale": "sanayi", "Batman": "tarim",
  "Şırnak": "tarim", "Bartın": "turizm", "Ardahan": "tarim",
  "Iğdır": "tarim", "Yalova": "konut", "Karabük": "sanayi",
  "Kilis": "tarim", "Osmaniye": "sanayi", "Düzce": "sanayi",
  "Mersin": "sanayi"
};

const CATEGORY_COLORS = {
  "turizm":    {fill: "rgba(59,130,246,0.25)",  stroke: "rgba(59,130,246,0.6)",  hover: "rgba(59,130,246,0.45)",  label: "Tourism",     color: "#3B82F6"},
  "sanayi":    {fill: "rgba(249,115,22,0.25)",  stroke: "rgba(249,115,22,0.6)",  hover: "rgba(249,115,22,0.45)",  label: "Industrial",  color: "#F97316"},
  "tarim":     {fill: "rgba(34,197,94,0.25)",   stroke: "rgba(34,197,94,0.6)",   hover: "rgba(34,197,94,0.45)",   label: "Agriculture", color: "#22C55E"},
  "konut":     {fill: "rgba(168,85,247,0.25)",  stroke: "rgba(168,85,247,0.6)",  hover: "rgba(168,85,247,0.45)",  label: "Residential", color: "#A855F7"},
  "teknoloji": {fill: "rgba(234,179,8,0.25)",   stroke: "rgba(234,179,8,0.6)",   hover: "rgba(234,179,8,0.45)",   label: "Technology",  color: "#EAB308"},
  "lojistik":  {fill: "rgba(236,72,153,0.25)",  stroke: "rgba(236,72,153,0.6)",  hover: "rgba(236,72,153,0.45)",  label: "Logistics",   color: "#EC4899"}
};

// Historical news archive
const NEWS_ARCHIVE = [
  {
    date: "2024-11-15",
    title: "Turkey Lifts Property Purchase Restrictions for Gulf Investors",
    summary: "Turkey streamlined foreign property acquisition rules, reducing bureaucratic barriers for investors from UAE, Saudi Arabia and Qatar. Processing time cut from 90 to 30 days.",
    impact: "Direct boost for Gulf investor appetite — expect increased demand in Istanbul and Antalya premium segments.",
    type: "opportunity", score: 90, province: "İstanbul"
  },
  {
    date: "2024-10-03",
    title: "Istanbul Canal Project: New Zoning Approvals Released",
    summary: "Turkish government released updated zoning maps along the Istanbul Canal corridor, opening 2,400 hectares to mixed-use development.",
    impact: "Land parcels along the canal route expected to appreciate 40-60% within 24 months as construction begins.",
    type: "opportunity", score: 88, province: "İstanbul"
  },
  {
    date: "2024-09-20",
    title: "VAT on New Property Sales Reduced to 1% for Foreign Buyers",
    summary: "Turkish Revenue Administration confirmed reduced VAT rate of 1% on first-time residential purchases by foreign nationals, down from 18%.",
    impact: "Significant cost reduction for international buyers — increased purchasing power expected to drive 15-20% volume uptick in Istanbul, Antalya and Izmir.",
    type: "opportunity", score: 85, province: "İstanbul"
  },
  {
    date: "2024-08-30",
    title: "Antalya Breaks Foreign Buyer Records for Third Consecutive Year",
    summary: "Antalya province recorded 18,400 foreign property sales in H1 2024, surpassing Istanbul for the first time in residential transactions.",
    impact: "Coastal rental yield compression risk in prime Antalya zones; secondary coastal districts offer better entry points now.",
    type: "opportunity", score: 82, province: "Antalya"
  },
  {
    date: "2024-08-14",
    title: "Cappadocia Boutique Hotel Sector Sees 31% YoY Price Growth",
    summary: "Cave hotel and boutique property values in Nevşehir's Göreme and Ürgüp districts jumped 31% year-on-year, driven by record domestic and international tourism.",
    impact: "Hospitality-zoned parcels in Cappadocia remain one of Turkey's highest-yielding short-term rental plays for foreign investors.",
    type: "opportunity", score: 80, province: "Nevşehir"
  },
  {
    date: "2024-07-22",
    title: "Mersin Free Trade Zone Expanded — 400 New Industrial Plots Available",
    summary: "The Turkish government approved expansion of Mersin Free Trade Zone, releasing 400 industrial plots with 15-year tax exemption status.",
    impact: "Industrial land in Mersin FTZ offers zero corporate tax for 15 years — compelling case for logistics and manufacturing investors.",
    type: "opportunity", score: 83, province: "Mersin"
  },
  {
    date: "2024-06-10",
    title: "Turkish Central Bank Holds Rate — TRY Stabilizes Against USD",
    summary: "TCMB held benchmark rate at 50% in June meeting, signaling confidence in disinflation path. TRY/USD stabilized in 32-33 range through Q2.",
    impact: "Currency stability reduces FX risk for USD-denominated property investors — entry timing window improving for dollar-holding buyers.",
    type: "neutral", score: 60, province: "İstanbul"
  },
  {
    date: "2024-05-18",
    title: "Gaziantep OIZ: Turkey's Largest Industrial Zone Opens Phase 3",
    summary: "Gaziantep Organized Industrial Zone Phase 3 officially opened, adding 850 hectares of industrial land with full infrastructure and utilities.",
    impact: "Gaziantep industrial land prices still 40% below Istanbul equivalents — strong value play for investors targeting manufacturing tenants.",
    type: "opportunity", score: 79, province: "Gaziantep"
  }
];
