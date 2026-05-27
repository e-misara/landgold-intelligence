/**
 * Tradia Lead Admin Dashboard — Cloudflare Worker
 *
 * Endpoint:
 *   GET /admin/leads          — son 24h/7d/30d count + dil/tip dağılımı
 *   GET /admin/leads/export   — JSON dump (Bearer auth)
 *   GET /admin/yorumlar       — son yorumlar mahalle bazlı
 *   GET /admin                — basit HTML dashboard (Bearer auth)
 *
 * Bindings (wrangler.toml):
 *   DB         D1 binding (lead-handler ile aynı DB)
 *   ADMIN_KEY  Bearer token (X-Admin-Key veya Authorization: Bearer)
 *
 * Routes (wrangler.toml):
 *   tradiaturkey.com/admin/*  → bu worker
 *
 * NOT: lead-handler.js'in YANINDA çalışır. Ayrı worker olarak deploy edilir
 * ya da lead-handler içine merge edilir (tercih: ayrı, prod izolasyon).
 */

function unauth(origin) {
  return json({ ok: false, err: 'unauthorized' }, 401, origin);
}

function corsHeaders(origin) {
  return {
    'Access-Control-Allow-Origin': origin || '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Admin-Key',
    'Access-Control-Max-Age': '86400',
  };
}

function json(data, status = 200, origin) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders(origin) },
  });
}

function checkAuth(req, env) {
  const xKey = req.headers.get('X-Admin-Key');
  const auth = req.headers.get('Authorization');
  const bearer = auth?.startsWith('Bearer ') ? auth.slice(7) : null;
  return (xKey && xKey === env.ADMIN_KEY) || (bearer && bearer === env.ADMIN_KEY);
}

// ─── Endpoints ────────────────────────────────────────────────

async function statsHandler(req, env) {
  const since24 = "datetime('now','-24 hours')";
  const since7  = "datetime('now','-7 days')";
  const since30 = "datetime('now','-30 days')";

  const [c24, c7, c30, dil, tip, ilTop, mahTop, yorum24] = await Promise.all([
    env.DB.prepare(`SELECT COUNT(*) AS n FROM leads WHERE ts >= ${since24}`).first(),
    env.DB.prepare(`SELECT COUNT(*) AS n FROM leads WHERE ts >= ${since7}`).first(),
    env.DB.prepare(`SELECT COUNT(*) AS n FROM leads WHERE ts >= ${since30}`).first(),
    env.DB.prepare(`SELECT dil, COUNT(*) AS n FROM leads WHERE ts >= ${since30} GROUP BY dil ORDER BY n DESC`).all(),
    env.DB.prepare(`SELECT tip, COUNT(*) AS n FROM leads WHERE ts >= ${since30} GROUP BY tip ORDER BY n DESC`).all(),
    env.DB.prepare(`SELECT il, COUNT(*) AS n FROM leads WHERE il IS NOT NULL AND ts >= ${since30} GROUP BY il ORDER BY n DESC LIMIT 10`).all(),
    env.DB.prepare(`SELECT mahalle, COUNT(*) AS n FROM leads WHERE mahalle IS NOT NULL AND ts >= ${since30} GROUP BY mahalle ORDER BY n DESC LIMIT 15`).all(),
    env.DB.prepare(`SELECT COUNT(*) AS n FROM comments WHERE ts >= ${since24}`).first(),
  ]);

  return {
    counts: {
      leads_24h: c24.n,
      leads_7d:  c7.n,
      leads_30d: c30.n,
      yorumlar_24h: yorum24.n,
    },
    dil_30d: dil.results,
    tip_30d: tip.results,
    il_top10_30d:      ilTop.results,
    mahalle_top15_30d: mahTop.results,
  };
}

async function exportHandler(env, limit = 1000) {
  const rows = await env.DB.prepare(
    `SELECT id, ts, tip, dil, email, ad, il, mahalle, kaynak, kvkk_onay
       FROM leads
       ORDER BY ts DESC
       LIMIT ?`
  ).bind(limit).all();
  return rows.results;
}

async function yorumlarHandler(env) {
  const rows = await env.DB.prepare(
    `SELECT id, ts, mahalle_slug, il, ilce, trend, substr(body, 1, 200) AS body
       FROM comments
       ORDER BY ts DESC
       LIMIT 100`
  ).all();
  return rows.results;
}

// ─── Mini HTML Dashboard ──────────────────────────────────────

function htmlDashboard(stats, origin) {
  const rows = (arr, key, val) => arr.map(r => `<tr><td>${r[key] ?? '—'}</td><td>${r[val]}</td></tr>`).join('');
  return `<!doctype html>
<html lang="tr"><head>
<meta charset="utf-8"><title>Tradia · Lead Admin</title>
<style>
  body { font-family: -apple-system, "Segoe UI", Arial; background:#0a0e1a; color:#e2e8f0; padding:28px; margin:0; }
  h1 { font-size:22px; margin:0 0 14px; color:#fff; }
  h2 { font-size:14px; margin:24px 0 8px; color:#fbbf24; text-transform:uppercase; letter-spacing:0.08em; }
  .grid { display:grid; grid-template-columns:repeat(4, 1fr); gap:12px; }
  .card { background:#111827; border:1px solid #1f2937; border-radius:8px; padding:14px; }
  .card .lbl { font-size:11px; color:#94a3b8; text-transform:uppercase; }
  .card .big { font-size:28px; color:#fbbf24; font-weight:700; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  td, th { padding:6px 10px; border-bottom:1px solid #1f2937; text-align:left; }
  th { color:#94a3b8; font-weight:600; text-transform:uppercase; font-size:10px; letter-spacing:0.06em; }
  .twocol { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-top:14px; }
  a { color:#fbbf24; text-decoration:none; }
  .meta { font-size:11px; color:#64748b; margin-top:14px; }
</style></head><body>
<h1>Tradia · Lead Admin Dashboard</h1>
<div class="grid">
  <div class="card"><div class="lbl">Son 24h Lead</div><div class="big">${stats.counts.leads_24h}</div></div>
  <div class="card"><div class="lbl">Son 7 gün Lead</div><div class="big">${stats.counts.leads_7d}</div></div>
  <div class="card"><div class="lbl">Son 30 gün Lead</div><div class="big">${stats.counts.leads_30d}</div></div>
  <div class="card"><div class="lbl">24h Yorum</div><div class="big">${stats.counts.yorumlar_24h}</div></div>
</div>

<h2>Son 30 gün — Dil Dağılımı</h2>
<table><thead><tr><th>Dil</th><th>Adet</th></tr></thead><tbody>${rows(stats.dil_30d, 'dil', 'n')}</tbody></table>

<h2>Son 30 gün — Tip Dağılımı</h2>
<table><thead><tr><th>Tip</th><th>Adet</th></tr></thead><tbody>${rows(stats.tip_30d, 'tip', 'n')}</tbody></table>

<div class="twocol">
  <div>
    <h2>Top 10 İl (30g)</h2>
    <table><thead><tr><th>İl</th><th>Adet</th></tr></thead><tbody>${rows(stats.il_top10_30d, 'il', 'n')}</tbody></table>
  </div>
  <div>
    <h2>Top 15 Mahalle (30g)</h2>
    <table><thead><tr><th>Mahalle</th><th>Adet</th></tr></thead><tbody>${rows(stats.mahalle_top15_30d, 'mahalle', 'n')}</tbody></table>
  </div>
</div>

<div class="meta">
  Export: <a href="/admin/leads/export">JSON dump</a> · <a href="/admin/yorumlar">Yorumlar</a><br>
  ${new Date().toISOString()} · Tradia Admin · Bearer auth aktif.
</div>
</body></html>`;
}

// ─── Router ───────────────────────────────────────────────────

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const origin = req.headers.get('Origin') || 'https://tradiaturkey.com';

    if (req.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders(origin) });
    }

    if (!checkAuth(req, env)) return unauth(origin);

    try {
      if (url.pathname === '/admin' || url.pathname === '/admin/') {
        const stats = await statsHandler(req, env);
        return new Response(htmlDashboard(stats, origin), {
          headers: { 'Content-Type': 'text/html; charset=utf-8', ...corsHeaders(origin) },
        });
      }
      if (url.pathname === '/admin/leads') {
        const stats = await statsHandler(req, env);
        return json(stats, 200, origin);
      }
      if (url.pathname === '/admin/leads/export') {
        const limit = parseInt(url.searchParams.get('limit') || '1000', 10);
        const data = await exportHandler(env, Math.min(limit, 10000));
        return json({ count: data.length, leads: data }, 200, origin);
      }
      if (url.pathname === '/admin/yorumlar') {
        const data = await yorumlarHandler(env);
        return json({ count: data.length, yorumlar: data }, 200, origin);
      }
      return json({ ok: false, err: 'not_found' }, 404, origin);
    } catch (e) {
      return json({ ok: false, err: 'internal', detail: e.message }, 500, origin);
    }
  },
};
