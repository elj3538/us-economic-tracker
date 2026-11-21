"""米国経済指標トラッカー メイン実行スクリプト。"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from src.analyze import analyze_indicators
from src.fetch_fred import fetch_all_indicators, fetch_market_cards
from src.generate_site import generate_site
from src.indicators_def import INDICATORS_DEF

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="米国経済指標トラッカー 静的サイト生成ツール")
    parser.add_argument("--no-cache", action="store_true", help="ローカルキャッシュを無視して再取得")
    parser.add_argument("--workers", type=int, default=6, help="並列取得ワーカー数（デフォルト: 6）")
    args = parser.parse_args()

    t0 = time.time()
    base_dir = Path(__file__).resolve().parent
    cache_dir = base_dir / "cache"
    dist_dir = base_dir / "dist"
    use_cache = not args.no_cache

    logger.info("=== 米国経済指標トラッカー 生成開始（全%d指標） ===", len(INDICATORS_DEF))
    indicators, failures = fetch_all_indicators(
        INDICATORS_DEF, cache_dir=cache_dir, use_cache=use_cache, workers=args.workers
    )
    logger.info("FRED指標取得完了: 成功 %d / 失敗 %d", len(indicators) - len(failures), len(failures))
    if failures:
        logger.warning("取得失敗ID: %s", failures)

    market_cards = fetch_market_cards(cache_dir=cache_dir, use_cache=use_cache)
    logger.info("主要マーケット取得完了: %d 項目", len(market_cards))

    indicators, econ_summary = analyze_indicators(indicators)
    logger.info(
        "景気分析完了: %s（改善 %d / 悪化 %d / 横ばい %d）",
        econ_summary["regime"],
        econ_summary["counts"]["improving"],
        econ_summary["counts"]["worsening"],
        econ_summary["counts"]["neutral"],
    )

    index_path = generate_site(indicators, econ_summary, market_cards, failures, dist_dir=dist_dir)
    elapsed = time.time() - t0
    logger.info("=== 完了（%.1f秒）: %s ===", elapsed, index_path)


if __name__ == "__main__":
    main()
