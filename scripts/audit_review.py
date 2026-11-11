"""Standalone local helper to review and fill `reports/audit.csv` in the browser (`uv run python scripts/audit_review.py`).

Completely separate from the main read-only web site (`serve.py`): binds to 127.0.0.1:8011 and reads/writes only `reports/audit.csv`.
"""

from __future__ import annotations

import csv
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from unitn_net import config

AUDIT_CSV = config.REPORTS / "audit.csv"

HTML = """<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Validazione manuale · audit.csv</title>
<style>
  :root { color-scheme: light dark; --bg: #f5f5f7; --card: #fff; --fg: #1d1d1f; --muted: #6e6e73; --line: rgba(60,60,67,.16); --accent: #0071e3; }
  @media (prefers-color-scheme: dark) { :root { --bg: #000; --card: #1c1c1e; --fg: #f5f5f7; --muted: #a1a1a6; --line: rgba(235,235,245,.16); --accent: #2997ff; } }
  body { font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Inter", system-ui, sans-serif; background: var(--bg); color: var(--fg); max-width: 780px; margin: 28px auto; padding: 0 16px; }
  .card { background: var(--card); border: 1px solid var(--line); border-radius: 18px; padding: 18px 20px; margin: 14px 0; }
  .bar { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; }
  button { font: inherit; font-weight: 500; padding: 7px 15px; border-radius: 16px; border: 1px solid var(--line); background: var(--card); color: var(--fg); cursor: pointer; }
  button.on-yes { background: #1c6b32; color: #fff; border-color: #1c6b32; }
  button.on-no { background: #a3241b; color: #fff; border-color: #a3241b; }
  .badge { font-size: 12px; padding: 2px 9px; border-radius: 10px; border: 1px solid var(--line); color: var(--muted); }
  ul { padding-left: 18px; color: var(--muted); font-size: 13px; }
  a { color: var(--accent); }
</style></head><body>
<div class="bar"><h2 id="title" style="margin:0">Validazione audit.csv</h2><div id="filter"><button onclick="setFilter('todo')" id="f-todo">Da valutare</button> <button onclick="setFilter('all')" id="f-all">Tutte</button></div></div>
<div id="main" class="card"></div>
<script>
let rows = [], idx = 0, filter = 'todo';
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const link = (d, t) => d ? `<a href="https://doi.org/${encodeURI(d)}" target="_blank">${esc(t)}</a>` : esc(t);
function setFilter(f) { filter = f; render(); }
function evHtml(raw) {
  try {
    const ev = JSON.parse(raw || '{}');
    return Object.entries(ev).map(([l, v]) => {
      let items = [];
      if (l === 'sem') items = v.map(e => `${link(e.doi_a, e.a)} ↔ ${link(e.doi_b, e.b)} (${e.cos})`);
      else if (l === 'coauth') items = v.map(e => `${link(e.doi, e.title)} (${e.year || ''})`);
      else if (l === 'teach') items = [...(v.shared || []).map(s => `Corso comune: ${esc(s)}`), ...(v.courses || []).map(c => `${esc(c.a)} ↔ ${esc(c.b)} (${c.cos})`)];
      else if (l === 'field') items = [`SSD: ${esc(v.ssd_i || '-')} / ${esc(v.ssd_j || '-')}`];
      return items.length ? `<div><b>${esc(l)}</b><ul>${items.map(i => `<li>${i}</li>`).join('')}</ul></div>` : '';
    }).join('');
  } catch { return `<p>${esc(raw)}</p>`; }
}
function render() {
  const done = rows.filter(r => r.judgment === '1' || r.judgment === '0').length;
  const pos = rows.filter(r => r.judgment === '1').length;
  document.getElementById('title').textContent = `Validazione audit.csv · ${done}/${rows.length}` + (done ? ` (${Math.round(100*pos/done)}% = 1)` : '');
  const list = rows.map((r, i) => [r, i]).filter(([r]) => filter === 'all' || (r.judgment !== '1' && r.judgment !== '0')).map(([, i]) => i);
  if (list.length && !list.includes(idx)) idx = list[0];
  const p = list.indexOf(idx), r = list.length ? rows[idx] : null;
  const box = document.getElementById('main');
  if (!r) { box.innerHTML = '<p>Tutte le coppie sono state valutate.</p>'; return; }
  box.innerHTML = `<div class="bar"><h3 style="margin:0">${esc(r.person)} ↔ ${esc(r.neighbour)}</h3><span class="badge">#${idx+1}/${rows.length} · comp ${(100*(+r.composite||0)).toFixed(0)}%</span></div>` +
    `<div style="margin:10px 0">${evHtml(r.evidence)}</div>` +
    `<div class="bar"><div><button class="${r.judgment==='1'?'on-yes':''}" onclick="vote('1')">Sensato (1)</button> <button class="${r.judgment==='0'?'on-no':''}" onclick="vote('0')">Non sensato (0)</button> <button onclick="vote('')">Svuota</button></div>` +
    `<div><button ${p<=0?'disabled':''} onclick="idx=${list[p-1]};render()">← Prec</button> <button ${p>=list.length-1?'disabled':''} onclick="idx=${list[p+1]};render()">Succ →</button></div></div>`;
}
function vote(v) {
  fetch('/api', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({index:idx, judgment:v})})
    .then(r => r.json()).then(() => { rows[idx].judgment = v; render(); });
}
fetch('/api').then(r => r.json()).then(d => { rows = d.rows; render(); });
</script></body></html>"""


PORT = 8011
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}   # refuse other Host headers (DNS rebinding: the file lists real names)


class AuditHandler(BaseHTTPRequestHandler):
    def parse_request(self):
        if not super().parse_request():
            return False
        if (self.headers.get("Host") or "").lower() not in ALLOWED_HOSTS:
            self.send_error(403)
            return False
        return True

    def do_GET(self):
        if self.path == "/api":
            with AUDIT_CSV.open("r", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            raw = json.dumps({"rows": rows}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(raw)
        else:
            raw = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(raw)

    def do_POST(self):
        # JSON only: a page on another site cannot send this content type without a CORS preflight, which is never answered.
        if self.path != "/api" or not (self.headers.get("Content-Type") or "").startswith("application/json"):
            self.send_error(400)
            return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8"))
        value = str(body.get("judgment", "")).strip()
        with AUDIT_CSV.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            fields, rows = list(reader.fieldnames or []), list(reader)
        index = int(body.get("index", -1))
        if value not in ("1", "0", "") or not 0 <= index < len(rows):
            self.send_error(400)
            return
        rows[index]["judgment"] = value
        with AUDIT_CSV.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"Audit UI su http://127.0.0.1:{PORT}/  (file: {AUDIT_CSV})")
    HTTPServer(("127.0.0.1", PORT), AuditHandler).serve_forever()
