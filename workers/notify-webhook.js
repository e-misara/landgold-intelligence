/**
 * Tradia Lead Notify — Telegram / Email Webhook
 *
 * Bu modül lead-handler.js'in çağırdığı `notify()` fonksiyonunu kapsar.
 * lead-handler.js içinde `env.NOTIFY_WEBHOOK` URL'ine basit POST atılıyor;
 * burada Telegram Bot API + Cloudflare Email Routing alternatifleri.
 *
 * KVKK NOTU: Lead'in kendisine hiçbir e-posta gönderilmez (Ahmet'in
 * raporu manuel hazırlamasını bekler). Bu webhook YALNIZCA Ahmet'i
 * yeni lead konusunda uyarır.
 *
 * Kullanım — wrangler.toml içine secret:
 *   wrangler secret put NOTIFY_WEBHOOK
 *     → "tg:BOT_TOKEN:CHAT_ID"  (Telegram için)
 *     → "email:webhook_url"     (Email için)
 *     → boş bırakılırsa hiç gönderim olmaz
 */

// ─── Telegram Bot API ─────────────────────────────────────────

async function notifyTelegram(botToken, chatId, lead) {
  const text = [
    `🔔 *Yeni Tradia Lead*`,
    `Tip: ${lead.tip}`,
    `Dil: ${lead.dil}`,
    `Email: \`${lead.email}\``,
    lead.ad     ? `Ad: ${lead.ad}` : '',
    lead.il     ? `İl: ${lead.il}` : '',
    lead.mahalle? `Mahalle: ${lead.mahalle}` : '',
    `Kaynak: ${lead.kaynak || 'web'}`,
    `ID: ${lead.id}`,
    `Tarih: ${lead.ts}`,
  ].filter(Boolean).join('\n');

  const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: 'Markdown',
      disable_web_page_preview: true,
    }),
  });
  return r.ok;
}

// ─── Cloudflare Email Routing (Workers Email API) ────────────

async function notifyEmail(env, lead) {
  if (!env.SEND_EMAIL || !env.NOTIFY_EMAIL_TO) return false;

  const subject = `[Tradia] Yeni lead — ${lead.tip} · ${lead.email}`;
  const body = [
    `Yeni Tradia lead alındı.`,
    ``,
    `Tip: ${lead.tip}`,
    `Dil: ${lead.dil}`,
    `Email: ${lead.email}`,
    lead.ad     ? `Ad: ${lead.ad}` : '',
    lead.il     ? `İl: ${lead.il}` : '',
    lead.mahalle? `Mahalle: ${lead.mahalle}` : '',
    `Kaynak: ${lead.kaynak || 'web'}`,
    `ID: ${lead.id}`,
    `Tarih: ${lead.ts}`,
    ``,
    `KVKK: Lead kişisel veri taşır, sadece Ahmet'e yönlendirilmiştir.`,
    `Erişim: https://tradiaturkey.com/admin (Bearer auth)`,
  ].filter(Boolean).join('\n');

  // Cloudflare Email Workers (mailchannels) örnek istek:
  return await fetch('https://api.mailchannels.net/tx/v1/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      personalizations: [{ to: [{ email: env.NOTIFY_EMAIL_TO }] }],
      from: { email: 'noreply@tradiaturkey.com', name: 'Tradia Lead Bot' },
      subject,
      content: [{ type: 'text/plain', value: body }],
    }),
  }).then(r => r.ok).catch(() => false);
}

// ─── Ana notify() — lead-handler içinde çağrılır ──────────────
//
// lead-handler.js'in en altına şu satırı eklemen yeterli (zaten env.NOTIFY_WEBHOOK
// ile basit POST yapıyor; daha zengin notify için lead-handler.js notify() çağrısını
// aşağıdaki fonksiyona yönlendir):
//
//   import { notify } from './notify-webhook.js';
//   ...
//   ctx.waitUntil(notify(env, leadKaydi));

export async function notify(env, lead) {
  const wh = env.NOTIFY_WEBHOOK;
  if (!wh) return;

  // tg:BOT_TOKEN:CHAT_ID  formatı
  if (wh.startsWith('tg:')) {
    const [, botToken, chatId] = wh.split(':');
    if (botToken && chatId) {
      return notifyTelegram(botToken, chatId, lead);
    }
  }
  // email modu (env.SEND_EMAIL=true + env.NOTIFY_EMAIL_TO=...)
  if (wh.startsWith('email:')) {
    return notifyEmail(env, lead);
  }
  // generic webhook (Slack/Discord/Make.com)
  return fetch(wh, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: `Yeni Tradia lead: ${lead.tip} (${lead.dil}) · ${lead.email} · ${lead.il || ''}`,
      lead,
    }),
  }).then(r => r.ok).catch(() => false);
}

// ─── Standalone test (CLI'dan değil, wrangler dev içinden) ────
//
//   POST /notify-test  → mock lead ile webhook tetiklenir
//
export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    if (req.method === 'POST' && url.pathname === '/notify-test') {
      if (req.headers.get('X-Admin-Key') !== env.ADMIN_KEY) {
        return new Response('unauthorized', { status: 401 });
      }
      const mock = {
        id: 0, tip: 'rapor', dil: 'tr',
        email: 'test@example.com', il: 'İstanbul', mahalle: 'Arnavutköy',
        kaynak: 'notify_test', ts: new Date().toISOString(),
      };
      const ok = await notify(env, mock);
      return new Response(JSON.stringify({ ok, mock }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      });
    }
    return new Response('Tradia Notify Webhook — use /notify-test', { status: 200 });
  },
};
