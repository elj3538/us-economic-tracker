"""米国経済指標38項目のトレンド・zスコア・景気後退/回復コンボシグナルを分析するモジュール。"""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any


def _lookback_steps(freq: str) -> int:
    if freq == "daily":
        return 63  # 約3か月（営業日）
    if freq == "weekly":
        return 13
    if freq == "quarterly":
        return 1
    return 3  # monthly: 3か月


def analyze_indicators(indicators: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """各指標に統計・トレンド判定・zスコアを付与し、全体 econSummary を算出する。"""
    improving: list[dict[str, Any]] = []
    worsening: list[dict[str, Any]] = []
    neutral: list[dict[str, Any]] = []
    z_alerts: list[dict[str, Any]] = []
    turning_signals: list[dict[str, Any]] = []

    by_id: dict[str, dict[str, Any]] = {}

    for ind in indicators:
        pts = ind.get("points", [])
        if len(pts) < 2:
            ind["stats"] = {"latest": None, "prev": None, "date": None, "diff": None, "diff_3m": None, "zscore": None, "trend": "neutral", "trend_label": "横ばい"}
            by_id[ind["id"]] = ind
            continue

        latest = pts[-1]["value"]
        latest_date = pts[-1]["date"]
        prev = pts[-2]["value"]
        diff = round(latest - prev, 3)

        lb = _lookback_steps(ind["frequency"])
        val_3m = pts[-1 - lb]["value"] if len(pts) > lb else pts[0]["value"]
        diff_3m = round(latest - val_3m, 3)

        # 直近5年（最大60点/日次は252*3）でのzスコア
        win = pts[-756:] if ind["frequency"] == "daily" else (pts[-260:] if ind["frequency"] == "weekly" else pts[-60:])
        vals = [p["value"] for p in win]
        mu = mean(vals)
        sd = pstdev(vals) if len(vals) >= 3 else 0.0
        zscore = round((latest - mu) / sd, 2) if sd > 1e-6 else 0.0

        # 3か月変化が標準偏差の0.25倍以上動いていればトレンドあり
        bw = ind.get("betterWhen", "neutral")
        threshold = sd * 0.20 if sd > 1e-6 else 0.0
        if bw == "neutral" or abs(diff_3m) <= threshold:
            trend = "neutral"
            trend_label = "横ばい"
        elif (bw == "up" and diff_3m > 0) or (bw == "down" and diff_3m < 0):
            trend = "improving"
            trend_label = "改善"
        else:
            trend = "worsening"
            trend_label = "悪化"

        # トレンド転換検知（直近1期の変化方向が過去3か月トレンドと反転）
        turned = False
        if len(pts) > lb + 1 and abs(diff) > sd * 0.15 and abs(diff_3m) > sd * 0.2:
            if (diff > 0 and diff_3m < 0) or (diff < 0 and diff_3m > 0):
                turned = True

        ind["stats"] = {
            "latest": latest,
            "prev": prev,
            "date": latest_date,
            "diff": diff,
            "diff_3m": diff_3m,
            "mean_5y": round(mu, 3),
            "zscore": zscore,
            "trend": trend,
            "trend_label": trend_label,
            "turned": turned,
        }
        by_id[ind["id"]] = ind

        summary_row = {
            "id": ind["id"],
            "shortName": ind["shortName"],
            "category": ind["category"],
            "latest": latest,
            "unit": ind["unit"],
            "diff_3m": diff_3m,
            "zscore": zscore,
            "trend_label": trend_label,
        }
        if trend == "improving":
            improving.append(summary_row)
        elif trend == "worsening":
            worsening.append(summary_row)
        else:
            neutral.append(summary_row)

        if abs(zscore) >= 1.5:
            z_alerts.append(summary_row)
        if turned:
            turning_signals.append(summary_row)

    # 景気後退警戒シグナル（サーム・ルール、長短金利差、信用スプレッド3か月変化、失業率）
    recession_checks: list[dict[str, Any]] = []
    sahm = by_id.get("sahm_rule_us", {}).get("stats", {})
    yc = by_id.get("yield_curve_spread_us", {}).get("stats", {})
    cs = by_id.get("credit_spread_us", {}).get("stats", {})
    claims = by_id.get("jobless_claims_us", {}).get("stats", {})
    permits = by_id.get("building_permits_us", {}).get("stats", {})
    vix = by_id.get("vix_us", {}).get("stats", {})

    if sahm.get("latest") is not None:
        hit = sahm["latest"] >= 0.50
        recession_checks.append({"name": "サーム・ルール (≥0.50%)", "value": f"{sahm['latest']:.2f}%", "alert": hit})
    if yc.get("latest") is not None:
        hit = yc["latest"] < 0.0
        recession_checks.append({"name": "長短金利差 10Y-2Y (<0%)", "value": f"{yc['latest']:+.2f}%", "alert": hit})
    if cs.get("diff_3m") is not None:
        hit = cs["diff_3m"] >= 0.50 or (cs.get("latest") or 0) >= 3.0
        recession_checks.append({"name": "信用スプレッド 3M変化 (≥+0.50% / 3%超)", "value": f"{cs.get('latest',0):.2f}% (3M {cs['diff_3m']:+.2f}%)", "alert": hit})
    if claims.get("latest") is not None:
        hit = claims["latest"] >= 270000
        recession_checks.append({"name": "新規失業保険申請 (≥27万件)", "value": f"{int(claims['latest']):,}件", "alert": hit})
    if vix.get("latest") is not None:
        hit = vix["latest"] >= 25.0
        recession_checks.append({"name": "VIX指数 (≥25)", "value": f"{vix['latest']:.1f}", "alert": hit})

    alert_cnt = sum(1 for c in recession_checks if c["alert"])
    if alert_cnt >= 3:
        regime = "景気後退警戒（高）"
        regime_level = "bad"
    elif alert_cnt >= 1:
        regime = "一部警戒シグナル点灯"
        regime_level = "warn"
    else:
        regime = "景気拡大・安定基調"
        regime_level = "good"

    # 景気回復・追い風チェック
    recovery_checks: list[dict[str, Any]] = []
    if permits.get("diff_3m") is not None:
        recovery_checks.append({"name": "建築許可件数 3M改善", "ok": permits["diff_3m"] > 0, "value": f"{permits['diff_3m']:+.0f}千戸"})
    if cs.get("diff_3m") is not None:
        recovery_checks.append({"name": "信用スプレッド 3M縮小", "ok": cs["diff_3m"] < 0, "value": f"{cs['diff_3m']:+.2f}%"})
    cpi = by_id.get("cpi_yoy_us", {}).get("stats", {})
    if cpi.get("latest") is not None:
        recovery_checks.append({"name": "CPI 3%未満で落ち着き", "ok": cpi["latest"] < 3.0, "value": f"{cpi['latest']:.2f}%"})

    z_alerts.sort(key=lambda x: abs(x["zscore"]), reverse=True)

    econ_summary = {
        "regime": regime,
        "regime_level": regime_level,
        "alert_count": alert_cnt,
        "counts": {
            "total": len(indicators),
            "improving": len(improving),
            "worsening": len(worsening),
            "neutral": len(neutral),
        },
        "improving": improving[:8],
        "worsening": worsening[:8],
        "z_alerts": z_alerts[:8],
        "turning_signals": turning_signals[:8],
        "recession_checks": recession_checks,
        "recovery_checks": recovery_checks,
    }
    return indicators, econ_summary
