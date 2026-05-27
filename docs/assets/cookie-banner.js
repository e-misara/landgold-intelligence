/**
 * Tradia Cookie Banner — Sprint 7
 *
 * Minimum KVKK + GDPR uyumlu, analytics cookie YOK.
 * LocalStorage'a 1 yıllık 'tradia_cookie_consent' anahtarı yazar.
 *
 * Kullanım:
 *   <link rel="stylesheet" href="/assets/cookie-banner.css">
 *   <script defer src="/assets/cookie-banner.js"></script>
 *
 * Otomatik enjekte eder; HTML markup gerekmez.
 */

(function () {
  const STORAGE_KEY = 'tradia_cookie_consent';
  const VERSION = '1.0';

  // Var olan onay kontrolü
  function hasConsent() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return false;
      const parsed = JSON.parse(raw);
      if (parsed.version !== VERSION) return false;
      const expiresAt = new Date(parsed.expires_at);
      return expiresAt > new Date();
    } catch { return false; }
  }

  // Onay kaydet (1 yıl)
  function saveConsent(accepted) {
    const expires = new Date();
    expires.setFullYear(expires.getFullYear() + 1);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      version: VERSION,
      accepted,
      accepted_at: new Date().toISOString(),
      expires_at: expires.toISOString(),
    }));
  }

  // Dil tespiti (URL path'inden)
  function getLang() {
    const path = window.location.pathname;
    if (path.startsWith('/tr/')) return 'tr';
    if (path.startsWith('/en/')) return 'en';
    if (path.startsWith('/ru/')) return 'ru';
    if (path.startsWith('/de/')) return 'de';
    if (path.startsWith('/ar/')) return 'ar';
    if (path.startsWith('/fa/')) return 'fa';
    if (path.startsWith('/zh/')) return 'zh';
    // varsayılan: HTML lang attribute'una bak
    const htmlLang = (document.documentElement.lang || 'tr').slice(0, 2);
    return ['tr', 'en', 'ru', 'de'].includes(htmlLang) ? htmlLang : 'tr';
  }

  const I18N = {
    tr: {
      text:    'Bu site teknik amaçlı (oturum + tercihler) çerez kullanır. Pazarlama veya izleme çerezi yok.',
      privacy: 'Gizlilik',
      accept:  'Kabul et',
      reject:  'Sadece zorunlu',
      privacy_url: '/privacy.html',
    },
    en: {
      text:    'This site uses essential cookies only (session + preferences). No marketing or tracking cookies.',
      privacy: 'Privacy',
      accept:  'Accept',
      reject:  'Essentials only',
      privacy_url: '/en/privacy.html',
    },
    ru: {
      text:    'Этот сайт использует только технические cookie (сессия + настройки). Маркетинговые или отслеживающие cookie не используются.',
      privacy: 'Конфиденциальность',
      accept:  'Принять',
      reject:  'Только необходимые',
      privacy_url: '/ru/privacy.html',
    },
    de: {
      text:    'Diese Website verwendet nur technische Cookies (Sitzung + Einstellungen). Keine Marketing- oder Tracking-Cookies.',
      privacy: 'Datenschutz',
      accept:  'Akzeptieren',
      reject:  'Nur notwendige',
      privacy_url: '/de/privacy.html',
    },
  };

  // Banner enjekte
  function showBanner() {
    const lang = getLang();
    const t = I18N[lang] || I18N.tr;

    const banner = document.createElement('div');
    banner.className = 'tradia-cookie-banner show';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Cookie consent');
    banner.innerHTML = `
      <div class="tcb-text">
        <strong>🍪</strong> ${t.text}
        <a href="${t.privacy_url}">${t.privacy}</a>
      </div>
      <div class="tcb-actions">
        <button class="tcb-secondary" data-action="reject">${t.reject}</button>
        <button data-action="accept">${t.accept}</button>
      </div>
    `;
    document.body.appendChild(banner);

    banner.addEventListener('click', e => {
      const action = e.target?.dataset?.action;
      if (action) {
        saveConsent(action === 'accept');
        banner.remove();
      }
    });
  }

  // DOM hazır olduğunda kontrol
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { if (!hasConsent()) showBanner(); });
  } else {
    if (!hasConsent()) showBanner();
  }

  // Diğer scriptlerin sorgu için global API
  window.tradiaCookie = {
    hasConsent,
    get: () => { try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'); } catch { return null; } },
    revoke: () => { localStorage.removeItem(STORAGE_KEY); location.reload(); },
  };
})();
