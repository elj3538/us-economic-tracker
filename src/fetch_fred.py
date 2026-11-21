"""FRED 公開CSV（APIキー不要）および stooq から米国経済指標・マーケットデータを取得するモジュール。"""

from __future__ import annotations

import io
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None
import requests as std_requests

logger = logging.getLogger(__name__)

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
}


def _http_get(url: str, timeout: int = 20):
    if cffi_requests is not None:
        return cffi_requests.get(url, impersonate="chrome", timeout=timeout)
    return std_requests.get(url, headers=HEADERS, timeout=timeout)


def fetch_fred_series(series_id: str, cache_dir: Path | None = None, use_cache: bool = True) -> list[tuple[str, float]]:
    """FRED公開CSVから (date_str, float_val) の時系列リストを取得する。"""
    cache_file = cache_dir / f"fred_{series_id}.json" if cache_dir else None
    if use_cache and cache_file and cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600.0
        if age_hours <= 16.0:
            try:
                return [tuple(x) for x in json.loads(cache_file.read_text(encoding="utf-8"))]
            except Exception:
                pass

    url = FRED_CSV_URL.format(series_id=series_id)
    for attempt in range(3):
        try:
            resp = _http_get(url, timeout=20)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text))
            if df.shape[1] < 2:
                return []
            date_col, val_col = df.columns[0], df.columns[1]
            pts: list[tuple[str, float]] = []
            for d_raw, v_raw in zip(df[date_col], df[val_col]):
                if pd.isna(v_raw) or str(v_raw).strip() in ("", "."):
                    continue
                try:
                    pts.append((str(d_raw)[:10], float(v_raw)))
                except (TypeError, ValueError):
                    continue
            if cache_file and pts:
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                cache_file.write_text(json.dumps(pts), encoding="utf-8")
            return pts
        except Exception as exc:
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            logger.warning("FRED [%s] 取得失敗: %s", series_id, exc)
            return []
    return []


def transform_series(pts: list[tuple[str, float]], mode: str) -> list[dict[str, Any]]:
    """FRED生時系列を指標定義の変換モード（raw / yoy_m / yoy_q / mom_m / diff_m）へ変換する。"""
    if not pts:
        return []
    out: list[dict[str, Any]] = []
    n = len(pts)
    if mode == "raw":
        for d, v in pts:
            out.append({"date": d, "value": round(v, 4)})
    elif mode == "yoy_m":
        for i in range(12, n):
            prev = pts[i - 12][1]
            if prev != 0:
                out.append({"date": pts[i][0], "value": round((pts[i][1] / prev - 1.0) * 100.0, 3)})
    elif mode == "yoy_q":
        for i in range(4, n):
            prev = pts[i - 4][1]
            if prev != 0:
                out.append({"date": pts[i][0], "value": round((pts[i][1] / prev - 1.0) * 100.0, 3)})
    elif mode == "mom_m":
        for i in range(1, n):
            prev = pts[i - 1][1]
            if prev != 0:
                out.append({"date": pts[i][0], "value": round((pts[i][1] / prev - 1.0) * 100.0, 3)})
    elif mode == "diff_m":
        for i in range(1, n):
            out.append({"date": pts[i][0], "value": round(pts[i][1] - pts[i - 1][1], 3)})
    else:
        for d, v in pts:
            out.append({"date": d, "value": round(v, 4)})
    return out


def fetch_jgb10y_series(cache_dir: Path | None = None, use_cache: bool = True) -> list[tuple[str, float]]:
    """日本10年国債利回りの日次推移を stooq から取得（失敗時はFRED月次 IRLTLT01JPM156N にフォールバック）。"""
    try:
        resp = _http_get("https://stooq.com/q/d/l/?s=10yjp.b&i=d", timeout=15)
        if resp.status_code == 200 and "Date,Open" in resp.text:
            df = pd.read_csv(io.StringIO(resp.text))
            pts: list[tuple[str, float]] = []
            for d_raw, v_raw in zip(df["Date"], df["Close"]):
                if pd.isna(v_raw):
                    continue
                pts.append((str(d_raw)[:10], float(v_raw)))
            if pts:
                return pts[-260:]
    except Exception:
        pass
    return fetch_fred_series("IRLTLT01JPM156N", cache_dir=cache_dir, use_cache=use_cache)


def fetch_all_indicators(
    defs: list[dict[str, Any]],
    cache_dir: Path | None = None,
    use_cache: bool = True,
    workers: int = 6,
) -> tuple[list[dict[str, Any]], list[str]]:
    """全38指標を並列取得・変換して返す。"""
    raw_cache: dict[str, list[tuple[str, float]]] = {}
    unique_ids = sorted({d["fred_id"] for d in defs})

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        fmap = {pool.submit(fetch_fred_series, sid, cache_dir, use_cache): sid for sid in unique_ids}
        for fut in as_completed(fmap):
            sid = fmap[fut]
            raw_cache[sid] = fut.result()

    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for d in defs:
        raw = raw_cache.get(d["fred_id"], [])
        pts = transform_series(raw, d["transform"])
        if not pts:
            failures.append(d["id"])
        # 直近15年分程度を保持（日次は最大2500点、月次・四半期は全期間）
        if d["frequency"] == "daily" and len(pts) > 2500:
            pts = pts[-2500:]
        item = dict(d)
        item["points"] = pts
        item["source_url"] = f"https://fred.stlouisfed.org/series/{d['fred_id']}"
        results.append(item)
    return results, failures


def fetch_market_cards(
    cache_dir: Path | None = None,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """主要マーケット6カード（ドル円・米10年・日本10年・WTI・S&P500・日経平均）を取得する。"""
    specs = [
        {"id": "usdjpy", "label": "ドル円", "unit": "円", "digits": 2, "fred_id": "DEXJPUS", "source": "FRED (FRB H.10)"},
        {"id": "us10y", "label": "米10年国債利回り", "unit": "%", "digits": 2, "fred_id": "DGS10", "source": "FRED (米財務省)"},
        {"id": "jgb10y", "label": "日本10年国債利回り", "unit": "%", "digits": 2, "fred_id": "_JGB10Y_", "source": "stooq / FRED"},
        {"id": "wti", "label": "WTI原油", "unit": "ドル", "digits": 2, "fred_id": "DCOILWTICO", "source": "FRED (EIA)"},
        {"id": "sp500", "label": "S&P 500", "unit": "", "digits": 1, "fred_id": "SP500", "source": "FRED (S&P DJI)"},
        {"id": "nikkei225", "label": "日経平均株価", "unit": "円", "digits": 0, "fred_id": "NIKKEI225", "source": "FRED (日経)"},
    ]
    cards: list[dict[str, Any]] = []
    for sp in specs:
        pts = (
            fetch_jgb10y_series(cache_dir=cache_dir, use_cache=use_cache)
            if sp["fred_id"] == "_JGB10Y_"
            else fetch_fred_series(sp["fred_id"], cache_dir=cache_dir, use_cache=use_cache)
        )
        if not pts:
            cards.append({**sp, "latest": None, "prev": None, "change": None, "change_pct": None, "date": None, "spark": []})
            continue
        latest_d, latest_v = pts[-1]
        prev_v = pts[-2][1] if len(pts) >= 2 else latest_v
        chg = round(latest_v - prev_v, 4)
        chg_pct = round((latest_v / prev_v - 1.0) * 100.0, 2) if prev_v != 0 else None
        spark = [round(v, 3) for _, v in pts[-60:]]
        cards.append(
            {
                "id": sp["id"],
                "label": sp["label"],
                "unit": sp["unit"],
                "digits": sp["digits"],
                "source": sp["source"],
                "latest": round(latest_v, sp["digits"] if sp["digits"] > 0 else 1),
                "prev": round(prev_v, sp["digits"] if sp["digits"] > 0 else 1),
                "change": round(chg, 3),
                "change_pct": chg_pct,
                "date": latest_d,
                "spark": spark,
            }
        )
    return cards
