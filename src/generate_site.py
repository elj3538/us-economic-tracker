"""米国経済指標トラッカーの静的サイト（dist/index.html および dist/data/*.json）を生成するモジュール。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.indicators_def import CATEGORY_GUIDES, CATEGORY_ORDER, FOMC_EVENTS

JST = timezone(timedelta(hours=9))


def generate_site(
    indicators: list[dict[str, Any]],
    econ_summary: dict[str, Any],
    market_cards: list[dict[str, Any]],
    failures: list[str],
    dist_dir: Path,
) -> Path:
    dist_dir.mkdir(parents=True, exist_ok=True)
    data_dir = dist_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    now_jst = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")

    # 1. JSONデータ出力（クライアントfetch & ポータル連携用）
    market_payload = {"generated_at": now_jst, "items": market_cards}
    (data_dir / "market.json").write_text(json.dumps(market_payload, ensure_ascii=False), encoding="utf-8")

    # ブラウザ軽量化のため全指標のpointsは最大600点に間引き（日次は週次サンプリング＋直近60営業日）
    slim_indicators: list[dict[str, Any]] = []
    for ind in indicators:
        pts = ind.get("points", [])
        if ind["frequency"] == "daily" and len(pts) > 360:
            older = pts[:-90][::5]
            recent = pts[-90:]
            pts_out = older + recent
        else:
            pts_out = pts[-360:]
        slim = {k: v for k, v in ind.items() if k != "points"}
        slim["points"] = pts_out
        slim_indicators.append(slim)

    ind_payload = {
        "generated_at": now_jst,
        "indicator_count": len(slim_indicators),
        "failures": failures,
        "category_order": CATEGORY_ORDER,
        "category_guides": CATEGORY_GUIDES,
        "econ_summary": econ_summary,
        "indicators": slim_indicators,
    }
    (data_dir / "indicators.json").write_text(json.dumps(ind_payload, ensure_ascii=False), encoding="utf-8")
    (data_dir / "events.json").write_text(
        json.dumps({"generated_at": now_jst, "events": FOMC_EVENTS}, ensure_ascii=False),
        encoding="utf-8",
    )

    # ポータル連携用の軽量サマリー
    by_id = {x["id"]: x for x in indicators}
    def _pick(iid: str) -> str:
        st = by_id.get(iid, {}).get("stats", {})
        v = st.get("latest")
        u = by_id.get(iid, {}).get("unit", "")
        if v is None:
            return "―"
        d = by_id.get(iid, {}).get("digits", 1)
        return f"{v:.{d}f}{u}"

    portal_summary = {
        "generated_at": now_jst,
        "indicator_count": len(indicators),
        "regime": econ_summary["regime"],
        "regime_level": econ_summary["regime_level"],
        "counts": econ_summary["counts"],
        "highlights": [
            {"label": "CPI", "value": _pick("cpi_yoy_us")},
            {"label": "失業率", "value": _pick("unemployment_rate_us")},
            {"label": "米10年金利", "value": _pick("treasury_10y_us")},
        ],
    }
    (dist_dir / "summary.json").write_text(json.dumps(portal_summary, ensure_ascii=False), encoding="utf-8")

    # 2. index.html 生成（データ埋め込み＋fetchフォールバック不要でローカル直接閲覧も高速）
    bundle_json = json.dumps(
        {
            "generated_at": now_jst,
            "market": market_cards,
            "econ_summary": econ_summary,
            "category_order": CATEGORY_ORDER,
            "category_guides": CATEGORY_GUIDES,
            "indicators": slim_indicators,
            "events": FOMC_EVENTS,
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>米国経済指標トラッカー（38指標・FRED自動更新）</title>
<style>
:root {{
  --bg: #f5f7fb; --surface: #ffffff; --border: #dfe5ef; --text: #162032; --muted: #5d6b82;
  --accent: #1d5fd6; --accent-soft: #eaf1ff;
  --good: #137333; --good-bg: #e6f6ec;
  --warn: #b06000; --warn-bg: #fef3e2;
  --bad: #c5221f; --bad-bg: #fde8e8;
}}
body.dark {{
  --bg: #0d131c; --surface: #161f2e; --border: #273449; --text: #e8eef7; --muted: #98a6be;
  --accent: #5e9bff; --accent-soft: #1b2a44;
  --good: #6ee79c; --good-bg: #123122;
  --warn: #fbbf24; --warn-bg: #36280d;
  --bad: #f87171; --bad-bg: #3b1719;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Hiragino Kaku Gothic ProN", sans-serif;
  background: var(--bg); color: var(--text); font-size: 14px; line-height: 1.55;
}}
a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.hub-bar {{
  background: #0f172a; color: #e2e8f0; padding: 7px 14px;
  display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 12px; border-bottom: 1px solid #1e293b;
}}
.hub-bar a {{
  color: #cbd5e1; padding: 4px 10px; border-radius: 6px; text-decoration: none; font-weight: 600; white-space: nowrap;
}}
.hub-bar a:hover {{ background: #1e293b; color: #fff; }}
.hub-bar a.hub-active {{ background: #2563eb; color: #fff; }}
.hub-bar .spacer {{ margin-left: auto; }}
.hub-bar button {{
  background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px; padding: 3px 9px; cursor: pointer; font-size: 12px;
}}
.wrap {{ max-width: 1380px; margin: 0 auto; padding: 16px 16px 70px; }}
header {{
  display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px;
  margin-bottom: 14px; border-bottom: 1px solid var(--border); padding-bottom: 10px;
}}
h1 {{ margin: 0; font-size: 21px; }}
.meta {{ font-size: 12px; color: var(--muted); }}
.sec-title {{ font-size: 15px; font-weight: 700; margin: 18px 0 10px; display: flex; align-items: center; gap: 8px; }}
.mkt-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(195px, 1fr)); gap: 10px;
}}
.mkt-card {{
  background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 11px 12px;
}}
.mkt-card .lbl {{ font-size: 11.5px; color: var(--muted); }}
.mkt-card .val {{ font-size: 20px; font-weight: 800; margin: 2px 0; }}
.mkt-card .chg {{ font-size: 12px; font-weight: 600; }}
.pos {{ color: var(--good); }}
.neg {{ color: var(--bad); }}
.summary-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; margin-top: 10px;
}}
.card {{
  background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px;
}}
.regime-badge {{
  display: inline-block; padding: 4px 12px; border-radius: 999px; font-weight: 700; font-size: 13px;
}}
.lvl-good {{ background: var(--good-bg); color: var(--good); }}
.lvl-warn {{ background: var(--warn-bg); color: var(--warn); }}
.lvl-bad {{ background: var(--bad-bg); color: var(--bad); }}
.check-list {{ list-style: none; padding: 0; margin: 8px 0 0; font-size: 12.5px; }}
.check-list li {{ display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px dashed var(--border); gap: 8px; }}
.pill-row {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
.pill {{
  font-size: 11.5px; padding: 3px 8px; border-radius: 6px; border: 1px solid var(--border);
  background: var(--bg); cursor: pointer;
}}
.pill:hover {{ border-color: var(--accent); }}
.controls {{
  display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 16px 0 12px;
}}
.tab-btn {{
  padding: 6px 12px; border: 1px solid var(--border); border-radius: 999px;
  background: var(--surface); color: var(--text); cursor: pointer; font-size: 12.5px; font-weight: 600;
}}
.tab-btn.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
.controls input[type=text] {{
  padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px;
  background: var(--surface); color: var(--text); min-width: 220px; font-size: 13px;
}}
.btn {{
  padding: 6px 11px; border: 1px solid var(--border); border-radius: 6px;
  background: var(--surface); color: var(--text); cursor: pointer; font-size: 12.5px;
}}
.btn-primary {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
.ind-grid {{
  display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 12px;
}}
.ind-card {{
  background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 13px;
  display: flex; flex-direction: column; gap: 6px; cursor: pointer; transition: border-color .15s, transform .12s;
}}
.ind-card:hover {{ border-color: var(--accent); transform: translateY(-1px); }}
.ind-top {{ display: flex; justify-content: space-between; align-items: center; gap: 6px; }}
.cat-tag {{ font-size: 10.5px; padding: 2px 7px; border-radius: 4px; background: var(--accent-soft); color: var(--accent); font-weight: 600; }}
.tr-tag {{ font-size: 10.5px; padding: 2px 7px; border-radius: 4px; font-weight: 700; }}
.tr-improving {{ background: var(--good-bg); color: var(--good); }}
.tr-worsening {{ background: var(--bad-bg); color: var(--bad); }}
.tr-neutral {{ background: var(--bg); color: var(--muted); }}
.ind-val {{ font-size: 22px; font-weight: 800; }}
.ind-sub {{ font-size: 11.5px; color: var(--muted); display: flex; justify-content: space-between; flex-wrap: wrap; gap: 4px; }}
.ind-actions {{ display: flex; justify-content: space-between; align-items: center; font-size: 12px; margin-top: 2px; }}
.star-btn {{ background: none; border: none; cursor: pointer; font-size: 15px; padding: 0 4px; color: var(--muted); }}
.star-btn.on {{ color: #f59e0b; }}
.modal-bg {{
  position: fixed; inset: 0; background: rgba(0,0,0,0.55); display: none;
  justify-content: center; align-items: center; z-index: 200; padding: 16px;
}}
.modal-bg.open {{ display: flex; }}
.modal {{
  background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
  max-width: 820px; width: 100%; max-height: 90vh; overflow-y: auto; padding: 18px 20px;
}}
.range-btns {{ display: flex; gap: 6px; margin: 8px 0; }}
.range-btns button {{ padding: 4px 10px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); color: var(--text); cursor: pointer; font-size: 12px; }}
.range-btns button.active {{ background: var(--accent); color: #fff; border-color: var(--accent); }}
details.panel {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; margin-top: 18px; }}
details.panel > summary {{ cursor: pointer; font-weight: 700; font-size: 14px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; margin-top: 8px; }}
th, td {{ padding: 6px 8px; border-bottom: 1px solid var(--border); text-align: left; }}
th {{ color: var(--muted); background: var(--bg); }}
</style>
</head>
<body>
<div class="hub-bar">
  <a href="https://elj3538.github.io/">🏠 ポータル</a>
  <a href="https://elj3538.github.io/us-long-screener/">🇺🇸 米国10年保有</a>
  <a href="https://elj3538.github.io/us-dividend-screener/">🇺🇸 米国配当株</a>
  <a href="https://elj3538.github.io/jp-long-screener/">🇯🇵 日本10年保有</a>
  <a href="https://elj3538.github.io/jp-dividend-screener/">🇯🇵 日本配当株</a>
  <a href="https://elj3538.github.io/us-economic-tracker/" class="hub-active">📊 米国経済指標</a>
  <a href="https://elj3538.github.io/jp-economic-tracker/">🗾 日本経済指標</a>
  <span class="spacer"></span>
  <button onclick="toggleDark()">🌙 ダーク切替</button>
</div>

<div class="wrap">
  <header>
    <div>
      <h1>📊 米国経済指標トラッカー</h1>
      <div class="meta">FRED（セントルイス連銀）公開データより全{len(slim_indicators)}指標を自動取得・毎日更新 ｜ 生成: {now_jst}</div>
    </div>
    <div style="display:flex;gap:8px;align-items:center;">
      <button class="btn btn-primary" id="btn-compare" onclick="openCompareModal()">📈 選択2指標を比較 (<span id="cmp-cnt">0</span>/2)</button>
      <button class="btn" onclick="clearCompare()">比較クリア</button>
    </div>
  </header>

  <div class="sec-title">💹 主要マーケット（直近60営業日推移）</div>
  <div class="mkt-grid" id="mkt-grid"></div>

  <div class="sec-title">🧭 米国経済状況サマリー ＆ 景気シグナル</div>
  <div class="summary-grid" id="summary-grid"></div>

  <div class="controls">
    <div id="cat-tabs" style="display:flex;flex-wrap:wrap;gap:6px;"></div>
    <input type="text" id="q" placeholder="指標名・解説・FRED IDで検索..." oninput="renderCards()">
    <select id="trend-filter" class="btn" onchange="renderCards()">
      <option value="all">トレンド: すべて</option>
      <option value="improving">改善のみ</option>
      <option value="worsening">悪化のみ</option>
      <option value="imp3">最重要（★★★）のみ</option>
    </select>
  </div>
  <div id="cat-guide" style="font-size:12px;color:var(--muted);margin-bottom:10px;"></div>
  <div class="ind-grid" id="ind-grid"></div>

  <details class="panel">
    <summary>📅 FOMC・FRB 主要イベントスケジュール（2026〜2027年）</summary>
    <table>
      <thead><tr><th>日付</th><th>種別</th><th>イベント</th><th>備考</th></tr></thead>
      <tbody id="ev-body"></tbody>
    </table>
  </details>
</div>

<!-- 詳細モーダル -->
<div class="modal-bg" id="detail-modal" onclick="if(event.target===this)closeDetail()">
  <div class="modal">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
      <h2 id="m-title" style="margin:0;font-size:18px;"></h2>
      <button class="btn" onclick="closeDetail()">✕ 閉じる</button>
    </div>
    <div id="m-meta" style="font-size:12px;color:var(--muted);margin:4px 0 8px;"></div>
    <div class="range-btns" id="m-ranges"></div>
    <div id="m-chart"></div>
    <p id="m-desc" style="font-size:13px;margin:10px 0;"></p>
    <div id="m-stats" style="font-size:12.5px;background:var(--bg);padding:10px;border-radius:8px;"></div>
    <div style="margin-top:10px;font-size:12px;"><a id="m-fred-link" href="#" target="_blank" rel="noopener">FRED公式ページで原データを見る ↗</a></div>
  </div>
</div>

<!-- 2指標比較モーダル -->
<div class="modal-bg" id="cmp-modal" onclick="if(event.target===this)closeCompare()">
  <div class="modal">
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <h2 style="margin:0;font-size:18px;">📈 2指標 推移比較（zスコア正規化オーバーレイ）</h2>
      <button class="btn" onclick="closeCompare()">✕ 閉じる</button>
    </div>
    <div id="cmp-legend" style="font-size:13px;margin:8px 0;"></div>
    <div id="cmp-chart"></div>
  </div>
</div>

<script>
const BUNDLE = {bundle_json};
const LS_FAV = "us_econ_favs";
const LS_DARK = "us_econ_dark";

let activeCat = "ALL";
let favs = new Set(JSON.parse(localStorage.getItem(LS_FAV) || "[]"));
let cmpIds = [];
let currentModalInd = null;
let currentRange = "5Y";

function toggleDark() {{
  document.body.classList.toggle("dark");
  localStorage.setItem(LS_DARK, document.body.classList.contains("dark") ? "1" : "0");
}}
if (localStorage.getItem(LS_DARK) === "1") document.body.classList.add("dark");

function fmtVal(v, d=1, unit="") {{
  if (v === null || v === undefined) return "―";
  return Number(v).toLocaleString("ja-JP", {{minimumFractionDigits: d, maximumFractionDigits: d}}) + unit;
}}

function sparkSvg(vals, w=170, h=42, color="var(--accent)") {{
  if (!vals || vals.length < 2) return "";
  const mn = Math.min(...vals), mx = Math.max(...vals);
  const sp = mx > mn ? mx - mn : 1;
  const pts = vals.map((v, i) => {{
    const x = 3 + (w - 6) * (i / (vals.length - 1));
    const y = h - 4 - (h - 8) * ((v - mn) / sp);
    return `${{x.toFixed(1)}},${{y.toFixed(1)}}`;
  }}).join(" ");
  return `<svg viewBox="0 0 ${{w}} ${{h}}" style="width:100%;height:${{h}}px;display:block;"><polyline fill="none" stroke="${{color}}" stroke-width="1.8" points="${{pts}}"/></svg>`;
}}

function renderMarket() {{
  const box = document.getElementById("mkt-grid");
  box.innerHTML = BUNDLE.market.map(m => {{
    const cls = (m.change || 0) >= 0 ? "pos" : "neg";
    const sign = (m.change || 0) > 0 ? "+" : "";
    const chgStr = m.change !== null ? `${{sign}}${{m.change.toFixed(m.digits > 1 ? 2 : 1)}} (${{sign}}${{m.change_pct ?? 0}}%)` : "―";
    return `<div class="mkt-card">
      <div class="lbl">${{m.label}} <span style="float:right;">${{m.date || ""}}</span></div>
      <div class="val">${{fmtVal(m.latest, m.digits, m.unit)}}</div>
      <div class="chg ${{cls}}">${{chgStr}}</div>
      ${{sparkSvg(m.spark, 180, 38)}}
    </div>`;
  }}).join("");
}}

function renderSummary() {{
  const s = BUNDLE.econ_summary;
  const c = s.counts;
  const box = document.getElementById("summary-grid");
  box.innerHTML = `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <strong>全体判定</strong>
        <span class="regime-badge lvl-${{s.regime_level}}">${{s.regime}}</span>
      </div>
      <div style="display:flex;gap:10px;margin:10px 0;font-size:13px;">
        <span class="tr-tag tr-improving">改善 ${{c.improving}}</span>
        <span class="tr-tag tr-worsening">悪化 ${{c.worsening}}</span>
        <span class="tr-tag tr-neutral">横ばい ${{c.neutral}}</span>
      </div>
      <div style="font-size:12px;color:var(--muted);">景気後退警戒チェック（点灯: ${{s.alert_count}}項目）</div>
      <ul class="check-list">
        ${{s.recession_checks.map(x => `<li><span>${{x.alert ? "🔴" : "🟢"}} ${{x.name}}</span><strong>${{x.value}}</strong></li>`).join("")}}
      </ul>
    </div>
    <div class="card">
      <strong>⚡ zスコア急変アラート（過去5年比 ±1.5σ超）</strong>
      <div class="pill-row">
        ${{(s.z_alerts.length ? s.z_alerts : []).map(x => `<span class="pill" onclick="openDetail('${{x.id}}')">${{x.shortName}} (z=${{x.zscore > 0 ? "+" : ""}}${{x.zscore}})</span>`).join("") || "<span style='color:var(--muted);font-size:12px;'>現在大きな異常値なし</span>"}}
      </div>
      <div style="margin-top:12px;"><strong>🔄 トレンド転換シグナル</strong></div>
      <div class="pill-row">
        ${{(s.turning_signals.length ? s.turning_signals : []).map(x => `<span class="pill" onclick="openDetail('${{x.id}}')">${{x.shortName}}</span>`).join("") || "<span style='color:var(--muted);font-size:12px;'>該当なし</span>"}}
      </div>
      <div style="margin-top:12px;"><strong>🌱 追い風・回復チェック</strong></div>
      <ul class="check-list">
        ${{s.recovery_checks.map(x => `<li><span>${{x.ok ? "✅" : "➖"}} ${{x.name}}</span><strong>${{x.value}}</strong></li>`).join("")}}
      </ul>
    </div>
  `;
}}

function renderTabs() {{
  const tabs = [["ALL", "すべて (" + BUNDLE.indicators.length + ")"], ...BUNDLE.category_order.map(c => [c, c]), ["FAV", "★ お気に入り"]];
  document.getElementById("cat-tabs").innerHTML = tabs.map(([k, lbl]) =>
    `<button class="tab-btn ${{activeCat === k ? "active" : ""}}" onclick="setCat('${{k}}')">${{lbl}}</button>`
  ).join("");
  document.getElementById("cat-guide").textContent = BUNDLE.category_guides[activeCat] || "全38指標を表示しています。カードをクリックすると詳細チャートが開きます。";
}}

function setCat(c) {{
  activeCat = c;
  renderTabs();
  renderCards();
}}

function toggleFav(ev, id) {{
  ev.stopPropagation();
  if (favs.has(id)) favs.delete(id); else favs.add(id);
  localStorage.setItem(LS_FAV, JSON.stringify([...favs]));
  renderCards();
}}

function toggleCompare(ev, id) {{
  ev.stopPropagation();
  if (cmpIds.includes(id)) cmpIds = cmpIds.filter(x => x !== id);
  else if (cmpIds.length < 2) cmpIds.push(id);
  else {{ cmpIds.shift(); cmpIds.push(id); }}
  document.getElementById("cmp-cnt").textContent = cmpIds.length;
  renderCards();
}}
function clearCompare() {{
  cmpIds = [];
  document.getElementById("cmp-cnt").textContent = "0";
  renderCards();
}}

function renderCards() {{
  const q = document.getElementById("q").value.trim().toLowerCase();
  const tf = document.getElementById("trend-filter").value;
  const list = BUNDLE.indicators.filter(x => {{
    if (activeCat === "FAV" && !favs.has(x.id)) return false;
    if (activeCat !== "ALL" && activeCat !== "FAV" && x.category !== activeCat) return false;
    if (tf === "improving" && x.stats.trend !== "improving") return false;
    if (tf === "worsening" && x.stats.trend !== "worsening") return false;
    if (tf === "imp3" && x.importance < 3) return false;
    if (q) {{
      const hay = (x.name + " " + x.shortName + " " + x.description + " " + x.fred_id + " " + x.category).toLowerCase();
      if (!hay.includes(q)) return false;
    }}
    return true;
  }});

  document.getElementById("ind-grid").innerHTML = list.map(x => {{
    const st = x.stats || {{}};
    const d3 = st.diff_3m;
    const d3Str = d3 !== null && d3 !== undefined ? `3M: ${{d3 > 0 ? "+" : ""}}${{d3.toFixed(x.digits > 1 ? 2 : 1)}}` : "";
    const zStr = st.zscore !== null && st.zscore !== undefined ? `z: ${{st.zscore > 0 ? "+" : ""}}${{st.zscore}}` : "";
    const recentVals = (x.points || []).slice(-36).map(p => p.value);
    const stars = "★".repeat(x.importance || 1);
    const isCmp = cmpIds.includes(x.id);
    return `<div class="ind-card" onclick="openDetail('${{x.id}}')">
      <div class="ind-top">
        <span class="cat-tag">${{x.category}}</span>
        <span style="font-size:11px;color:#f59e0b;">${{stars}}</span>
        <span class="tr-tag tr-${{st.trend || 'neutral'}}">${{st.trend_label || '横ばい'}}</span>
      </div>
      <div style="font-weight:700;font-size:14px;">${{x.shortName}}</div>
      <div class="ind-val">${{fmtVal(st.latest, x.digits, x.unit)}}</div>
      <div class="ind-sub"><span>${{st.date || "―"}}</span><span>${{d3Str}} / ${{zStr}}</span></div>
      ${{sparkSvg(recentVals, 250, 40)}}
      <div class="ind-actions">
        <button class="star-btn ${{favs.has(x.id) ? 'on' : ''}}" onclick="toggleFav(event,'${{x.id}}')" title="お気に入り">★</button>
        <label onclick="event.stopPropagation()" style="font-size:11.5px;color:var(--muted);cursor:pointer;">
          <input type="checkbox" ${{isCmp ? "checked" : ""}} onchange="toggleCompare(event,'${{x.id}}')"> 比較に追加
        </label>
      </div>
    </div>`;
  }}).join("") || `<p style="color:var(--muted);">該当する指標がありません。</p>`;
}}

function openDetail(id) {{
  currentModalInd = BUNDLE.indicators.find(x => x.id === id);
  if (!currentModalInd) return;
  document.getElementById("m-title").textContent = currentModalInd.name;
  document.getElementById("m-meta").textContent = `${{currentModalInd.category}} ｜ FRED: ${{currentModalInd.fred_id}} ｜ 頻度: ${{currentModalInd.frequency}} ｜ 最新日: ${{currentModalInd.stats.date || "―"}}`;
  document.getElementById("m-desc").textContent = currentModalInd.description;
  document.getElementById("m-fred-link").href = currentModalInd.source_url;
  const st = currentModalInd.stats;
  document.getElementById("m-stats").innerHTML = `
    最新値: <strong>${{fmtVal(st.latest, currentModalInd.digits, currentModalInd.unit)}}</strong> ／
    前回値: <strong>${{fmtVal(st.prev, currentModalInd.digits, currentModalInd.unit)}}</strong> ／
    3か月変化: <strong>${{st.diff_3m !== null ? (st.diff_3m > 0 ? "+" : "") + st.diff_3m : "―"}}</strong> ／
    過去5年平均: <strong>${{fmtVal(st.mean_5y, currentModalInd.digits, currentModalInd.unit)}}</strong> ／
    zスコア: <strong>${{st.zscore}}</strong>
  `;
  renderDetailChart();
  document.getElementById("detail-modal").classList.add("open");
}}
function closeDetail() {{ document.getElementById("detail-modal").classList.remove("open"); }}

function setRange(r) {{ currentRange = r; renderDetailChart(); }}
function renderDetailChart() {{
  document.getElementById("m-ranges").innerHTML = ["1Y","3Y","5Y","10Y","ALL"].map(r =>
    `<button class="${{currentRange === r ? "active" : ""}}" onclick="setRange('${{r}}')">${{r}}</button>`
  ).join("");
  const allPts = currentModalInd.points || [];
  let pts = allPts;
  if (currentRange !== "ALL" && allPts.length) {{
    const yrs = Number(currentRange.replace("Y",""));
    const lastD = new Date(allPts[allPts.length - 1].date);
    const cut = new Date(lastD); cut.setFullYear(cut.getFullYear() - yrs);
    pts = allPts.filter(p => new Date(p.date) >= cut);
  }}
  if (pts.length < 2) {{ document.getElementById("m-chart").innerHTML = "<p>データ不足</p>"; return; }}
  const w = 740, h = 240, pad = 36;
  const vals = pts.map(p => p.value);
  let mn = Math.min(...vals), mx = Math.max(...vals);
  if (currentModalInd.ref_line !== null && currentModalInd.ref_line !== undefined) {{
    mn = Math.min(mn, currentModalInd.ref_line);
    mx = Math.max(mx, currentModalInd.ref_line);
  }}
  const sp = mx > mn ? mx - mn : 1;
  const poly = pts.map((p, i) => {{
    const x = pad + (w - pad * 2) * (i / (pts.length - 1));
    const y = h - pad - (h - pad * 2) * ((p.value - mn) / sp);
    return `${{x.toFixed(1)}},${{y.toFixed(1)}}`;
  }}).join(" ");
  let refSvg = "";
  if (currentModalInd.ref_line !== null && currentModalInd.ref_line !== undefined) {{
    const ry = h - pad - (h - pad * 2) * ((currentModalInd.ref_line - mn) / sp);
    refSvg = `<line x1="${{pad}}" y1="${{ry.toFixed(1)}}" x2="${{w-pad}}" y2="${{ry.toFixed(1)}}" stroke="var(--warn)" stroke-dasharray="4 4"/>
              <text x="${{w-pad}}" y="${{(ry-4).toFixed(1)}}" font-size="10" fill="var(--warn)" text-anchor="end">目安 ${{currentModalInd.ref_line}}${{currentModalInd.unit}}</text>`;
  }}
  document.getElementById("m-chart").innerHTML = `<svg viewBox="0 0 ${{w}} ${{h}}" style="width:100%;height:auto;background:var(--bg);border-radius:8px;">
    <line x1="${{pad}}" y1="${{h-pad}}" x2="${{w-pad}}" y2="${{h-pad}}" stroke="var(--border)"/>
    ${{refSvg}}
    <polyline fill="none" stroke="var(--accent)" stroke-width="2.2" points="${{poly}}"/>
    <text x="${{pad}}" y="18" font-size="11" fill="var(--muted)">最大 ${{fmtVal(mx, currentModalInd.digits, currentModalInd.unit)}}</text>
    <text x="${{w-pad}}" y="18" font-size="11" fill="var(--text)" text-anchor="end">最新 ${{fmtVal(vals[vals.length-1], currentModalInd.digits, currentModalInd.unit)}}</text>
    <text x="${{pad}}" y="${{h-10}}" font-size="10" fill="var(--muted)">${{pts[0].date}}（最小 ${{fmtVal(mn, currentModalInd.digits, currentModalInd.unit)}}）</text>
    <text x="${{w-pad}}" y="${{h-10}}" font-size="10" fill="var(--muted)" text-anchor="end">${{pts[pts.length-1].date}}</text>
  </svg>`;
}}

function openCompareModal() {{
  if (cmpIds.length < 2) {{ alert("比較する指標を2つチェックしてください。"); return; }}
  const a = BUNDLE.indicators.find(x => x.id === cmpIds[0]);
  const b = BUNDLE.indicators.find(x => x.id === cmpIds[1]);
  document.getElementById("cmp-legend").innerHTML = `<span style="color:#2563eb;font-weight:700;">━ ${{a.shortName}}</span>　vs　<span style="color:#dc2626;font-weight:700;">━ ${{b.shortName}}</span>（直近5年をzスコア正規化）`;
  const norm = ind => {{
    const pts = (ind.points || []).slice(-60);
    const vs = pts.map(p => p.value);
    const mu = vs.reduce((s,v)=>s+v,0)/vs.length;
    const sd = Math.sqrt(vs.reduce((s,v)=>s+(v-mu)**2,0)/vs.length) || 1;
    return pts.map(p => ({{date: p.date, z: (p.value - mu)/sd}}));
  }};
  const na = norm(a), nb = norm(b);
  const w = 740, h = 240, pad = 34;
  const allZ = [...na.map(p=>p.z), ...nb.map(p=>p.z)];
  const mn = Math.min(...allZ, -2), mx = Math.max(...allZ, 2), sp = mx - mn || 1;
  const toPoly = arr => arr.map((p,i) => `${{(pad+(w-pad*2)*(i/Math.max(1,arr.length-1))).toFixed(1)}},${{(h-pad-(h-pad*2)*((p.z-mn)/sp)).toFixed(1)}}`).join(" ");
  document.getElementById("cmp-chart").innerHTML = `<svg viewBox="0 0 ${{w}} ${{h}}" style="width:100%;height:auto;background:var(--bg);border-radius:8px;">
    <line x1="${{pad}}" y1="${{(h-pad-(h-pad*2)*((0-mn)/sp)).toFixed(1)}}" x2="${{w-pad}}" y2="${{(h-pad-(h-pad*2)*((0-mn)/sp)).toFixed(1)}}" stroke="var(--border)" stroke-dasharray="3 3"/>
    <polyline fill="none" stroke="#2563eb" stroke-width="2" points="${{toPoly(na)}}"/>
    <polyline fill="none" stroke="#dc2626" stroke-width="2" points="${{toPoly(nb)}}"/>
  </svg>`;
  document.getElementById("cmp-modal").classList.add("open");
}}
function closeCompare() {{ document.getElementById("cmp-modal").classList.remove("open"); }}

function renderEvents() {{
  document.getElementById("ev-body").innerHTML = BUNDLE.events.map(e =>
    `<tr><td><strong>${{e.date}}</strong></td><td>${{e.type}}</td><td>${{e.title}}</td><td style="color:var(--muted);">${{e.note}}</td></tr>`
  ).join("");
}}

renderMarket();
renderSummary();
renderTabs();
renderCards();
renderEvents();
</script>
</body>
</html>
"""
    index_path = dist_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    return index_path
