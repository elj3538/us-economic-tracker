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


def _parse_wareki_date(s: str) -> str | None:
    """財務省CSVの和暦日付（例: R8.11.19, H31.4.26）を YYYY-MM-DD に変換する。"""
    s = s.strip()
    if not s or "." not in s:
        return None
    era = s[0].upper()
    parts = s[1:].split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    base = {"R": 2018, "H": 1988, "S": 1925}.get(era)
    if base is None:
        return None
    return f"{base + y:04d}-{m:02d}-{d:02d}"


def fetch_jgb10y_series(cache_dir: Path | None = None, use_cache: bool = True) -> list[tuple[str, float]]:
    """日本10年国債利回りの日次推移を財務省公式CSV（jgbcm.csv）から取得する。"""
    pts: list[tuple[str, float]] = []
    for url in (
        "https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv",
        "https://www.mof.go.jp/jgbs/reference/interest_rate/jgbcm.csv",
    ):
        try:
            resp = _http_get(url, timeout=15)
            if resp.status_code != 200:
                continue
            text = resp.content.decode("cp932", errors="ignore")
            by_date: dict[str, float] = {}
            for line in text.splitlines():
                cols = [c.strip() for c in line.split(",")]
                if len(cols) <= 10:
                    continue
                dt = _parse_wareki_date(cols[0])
                if not dt or cols[10] in ("", "-"):
                    continue
                try:
                    by_date[dt] = float(cols[10])
                except ValueError:
                    continue
            if by_date:
                pts = [(d, by_date[d]) for d in sorted(by_date.keys())[-90:]]
                if url.endswith("jgbcm.csv") or len(pts) >= 5:
                    # 当月CSVも最新補完するため、allが取れたらそのまま最新日を確認して返す
                    if url.endswith("jgbcm_all.csv"):
                        # 当月最新(jgbcm.csv)もマージ
                        try:
                            r2 = _http_get("https://www.mof.go.jp/jgbs/reference/interest_rate/jgbcm.csv", timeout=10)
                            if r2.status_code == 200:
                                for ln in r2.content.decode("cp932", errors="ignore").splitlines():
                                    cs = [c.strip() for c in ln.split(",")]
                                    if len(cs) > 10:
                                        d2 = _parse_wareki_date(cs[0])
                                        if d2 and cs[10] not in ("", "-"):
                                            try:
                                                by_date[d2] = float(cs[10])
                                            except ValueError:
                                                pass
                                pts = [(d, by_date[d]) for d in sorted(by_date.keys())[-90:]]
                        except Exception:
                            pass
                    return pts
        except Exception:
            continue
    return fetch_fred_series("IRLTLT01JPM156N", cache_dir=cache_dir, use_cache=use_cache)


def _fetch_yf_series(symbol: str) -> list[tuple[str, float]]:
    """yfinanceから直近3か月分の日次終値 (date, close) を取得する。"""
    try:
        import yfinance as yf
        hist = yf.Ticker(symbol).history(period="4mo", interval="1d")
        if hist is None or hist.empty or "Close" not in hist.columns:
            return []
        close = hist["Close"].dropna()
        return [(idx.strftime("%Y-%m-%d"), float(v)) for idx, v in close.items()]
    except Exception:
        return []


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
    """主要マーケット6カード（ドル円・米10年・日本10年・WTI・S&P500・日経平均）を最新日次データで取得する。"""
    specs = [
        {"id": "usdjpy", "label": "ドル円", "unit": "円", "digits": 2, "yf": "JPY=X", "fred_id": "DEXJPUS", "source": "Yahoo Finance (日次)"},
        {"id": "us10y", "label": "米10年国債利回り", "unit": "%", "digits": 2, "yf": "^TNX", "fred_id": "DGS10", "source": "Yahoo Finance / 米財務省"},
        {"id": "jgb10y", "label": "日本10年国債利回り", "unit": "%", "digits": 2, "yf": None, "fred_id": "_JGB10Y_", "source": "財務省（日次国債金利）"},
        {"id": "wti", "label": "WTI原油", "unit": "ドル", "digits": 2, "yf": "CL=F", "fred_id": "DCOILWTICO", "source": "Yahoo Finance (先物日次)"},
        {"id": "sp500", "label": "S&P 500", "unit": "", "digits": 1, "yf": "^GSPC", "fred_id": "SP500", "source": "Yahoo Finance (日次)"},
        {"id": "nikkei225", "label": "日経平均株価", "unit": "円", "digits": 0, "yf": "^N225", "fred_id": "NIKKEI225", "source": "Yahoo Finance / FRED"},
    ]
    cards: list[dict[str, Any]] = []
    for sp in specs:
        if sp["fred_id"] == "_JGB10Y_":
            pts = fetch_jgb10y_series(cache_dir=cache_dir, use_cache=use_cache)
        else:
            yf_pts = _fetch_yf_series(sp["yf"]) if sp.get("yf") else []
            fr_pts = fetch_fred_series(sp["fred_id"], cache_dir=cache_dir, use_cache=use_cache)
            # 日付が新しいソースを自動採用
            if yf_pts and (not fr_pts or yf_pts[-1][0] >= fr_pts[-1][0]):
                pts = yf_pts
            else:
                pts = fr_pts
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
