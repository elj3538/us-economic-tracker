"""米国経済指標38項目およびFOMCイベントのマスター定義。"""

from __future__ import annotations

from typing import Any

CATEGORY_ORDER: list[str] = ["景気", "物価", "雇用・所得", "対外", "金利", "為替・市場"]

CATEGORY_GUIDES: dict[str, str] = {
    "景気": "GDP・消費・生産・住宅・地域連銀景況など、米国実体経済の勢いを測る指標群。",
    "物価": "CPI・コアPCE・PPI・期待インフレ率など、FRBの金融政策を左右するインフレ指標群。",
    "雇用・所得": "失業率・サーム・ルール・雇用者数・賃金など、景気後退の判断軸となる労働市場指標群。",
    "対外": "経常収支・貿易収支など、米国の対外バランスを示す指標群。",
    "金利": "FF金利・10年債利回り・長短金利差・信用スプレッドなど、金融環境と市場ストレスを測る指標群。",
    "為替・市場": "ドル指数・S&P500・VIX・WTI原油など、リスク選好とマーケット動向を映す指標群。",
}

# transform: "raw" | "yoy_m" (12ヶ月前年比%) | "yoy_q" (4四半期前年比%) | "mom_m" (前月比%) | "diff_m" (前月差)
INDICATORS_DEF: list[dict[str, Any]] = [
    # --- 景気 (12) ---
    {
        "id": "gdp_growth_us", "fred_id": "A191RL1Q225SBEA", "transform": "raw",
        "category": "景気", "name": "実質GDP成長率（前期比年率）", "shortName": "実質GDP",
        "unit": "%", "digits": 1, "frequency": "quarterly", "betterWhen": "up", "importance": 3,
        "ref_line": 2.0, "description": "米国経済全体の成長ペース（物価変動を除いた前期比年率）。2%前後が潜在成長率の目安。",
    },
    {
        "id": "consumer_sentiment_us", "fred_id": "UMCSENT", "transform": "raw",
        "category": "景気", "name": "ミシガン大学消費者信頼感指数", "shortName": "消費者信頼感",
        "unit": "", "digits": 1, "frequency": "monthly", "betterWhen": "up", "importance": 2,
        "ref_line": 80.0, "description": "家計の景況感・購買意欲を測る先行指標。米国GDPの約7割を占める個人消費の先行目安。",
    },
    {
        "id": "industrial_production_us", "fred_id": "INDPRO", "transform": "raw",
        "category": "景気", "name": "鉱工業生産指数", "shortName": "鉱工業生産",
        "unit": "", "digits": 1, "frequency": "monthly", "betterWhen": "up", "importance": 2,
        "ref_line": 100.0, "description": "製造業・鉱業・公益事業の生産量を示す一致指標（2017年=100）。",
    },
    {
        "id": "durable_goods_orders_us", "fred_id": "DGORDER", "transform": "raw",
        "category": "景気", "name": "耐久財受注", "shortName": "耐久財受注",
        "unit": "百万ドル", "digits": 0, "frequency": "monthly", "betterWhen": "up", "importance": 2,
        "ref_line": None, "description": "企業の設備投資意欲を先行して映す製造業の新規受注額。",
    },
    {
        "id": "retail_sales_us", "fred_id": "RSAFS", "transform": "mom_m",
        "category": "景気", "name": "小売売上高（前月比）", "shortName": "小売売上高",
        "unit": "%", "digits": 2, "frequency": "monthly", "betterWhen": "up", "importance": 3,
        "ref_line": 0.0, "description": "個人消費の勢いを直接示す月次指標。プラス圏維持が景気拡大の柱。",
    },
    {
        "id": "building_permits_us", "fred_id": "PERMIT", "transform": "raw",
        "category": "景気", "name": "住宅着工許可件数（年率）", "shortName": "建築許可件数",
        "unit": "千戸", "digits": 0, "frequency": "monthly", "betterWhen": "up", "importance": 2,
        "ref_line": 1400.0, "description": "住宅市場の代表的な先行指標（LEI構成要素）。金利変動に敏感に反応する。",
    },
    {
        "id": "philly_fed_us", "fred_id": "GACDFSA066MSFRBPHI", "transform": "raw",
        "category": "景気", "name": "フィラデルフィア連銀製造業景況指数", "shortName": "フィラデルフィア連銀景況",
        "unit": "", "digits": 1, "frequency": "monthly", "betterWhen": "up", "importance": 2,
        "ref_line": 0.0, "description": "0を上回れば景気拡大、下回れば縮小を示す速報性の高い製造業DI。",
    },
    {
        "id": "real_pce_mom_us", "fred_id": "PCEC96", "transform": "mom_m",
        "category": "景気", "name": "実質個人消費支出（前月比）", "shortName": "実質個人消費",
        "unit": "%", "digits": 2, "frequency": "monthly", "betterWhen": "up", "importance": 3,
        "ref_line": 0.0, "description": "インフレ調整後の家計消費の伸び。GDP個人消費に直結する重要指標。",
    },
    {
        "id": "empire_state_us", "fred_id": "GACDISA066MSFRBNY", "transform": "raw",
        "category": "景気", "name": "NY連銀製造業景況指数（エンパイア）", "shortName": "NY連銀景況",
        "unit": "", "digits": 1, "frequency": "monthly", "betterWhen": "up", "importance": 1,
        "ref_line": 0.0, "description": "毎月最も早く公表される地域連銀の製造業景況DI。0が拡大・縮小の分岐点。",
    },
    {
        "id": "capacity_utilization_us", "fred_id": "TCU", "transform": "raw",
        "category": "景気", "name": "設備稼働率", "shortName": "設備稼働率",
        "unit": "%", "digits": 1, "frequency": "monthly", "betterWhen": "neutral", "importance": 1,
        "ref_line": 78.0, "description": "生産設備の稼働度合い。80%超は景気過熱・インフレ圧力、75%割れは景気減速の目安。",
    },
    {
        "id": "case_shiller_20_yoy_us", "fred_id": "SPCS20RNSA", "transform": "yoy_m",
        "category": "景気", "name": "ケースシラー20都市住宅価格（前年比）", "shortName": "ケースシラー住宅価格",
        "unit": "%", "digits": 1, "frequency": "monthly", "betterWhen": "neutral", "importance": 2,
        "ref_line": 3.0, "description": "米国主要20都市圏の住宅価格前年比。資産効果と住居費インフレの先行指標。",
    },
    {
        "id": "new_home_sales_us", "fred_id": "HSN1F", "transform": "raw",
        "category": "景気", "name": "新築住宅販売件数（年率）", "shortName": "新築住宅販売",
        "unit": "千戸", "digits": 0, "frequency": "monthly", "betterWhen": "up", "importance": 2,
        "ref_line": 650.0, "description": "契約ベースで集計されるため、住宅市場の転換点をいち早く映す指標。",
    },
    # --- 物価 (5) ---
    {
        "id": "cpi_yoy_us", "fred_id": "CPIAUCSL", "transform": "yoy_m",
        "category": "物価", "name": "消費者物価指数 CPI（前年比）", "shortName": "CPI",
        "unit": "%", "digits": 2, "frequency": "monthly", "betterWhen": "neutral", "importance": 3,
        "ref_line": 2.0, "description": "総合インフレ率。FRBの目標2%との乖離が金利・株価を大きく動かす。",
    },
    {
        "id": "core_cpi_yoy_us", "fred_id": "CPILFENS", "transform": "yoy_m",
        "category": "物価", "name": "コアCPI（食品・エネルギー除く・前年比）", "shortName": "コアCPI",
        "unit": "%", "digits": 2, "frequency": "monthly", "betterWhen": "neutral", "importance": 3,
        "ref_line": 2.0, "description": "変動の大きい食品・エネルギーを除いた基調インフレ率。",
    },
    {
        "id": "core_pce_yoy_us", "fred_id": "PCEPILFE", "transform": "yoy_m",
        "category": "物価", "name": "コアPCEデフレーター（前年比）", "shortName": "コアPCE",
        "unit": "%", "digits": 2, "frequency": "monthly", "betterWhen": "neutral", "importance": 3,
        "ref_line": 2.0, "description": "FRBが金融政策判断で最も重視するインフレ指標。目標水準は2.0%。",
    },
    {
        "id": "ppi_core_yoy_us", "fred_id": "PPIFES", "transform": "yoy_m",
        "category": "物価", "name": "生産者物価指数 コアPPI（前年比）", "shortName": "コアPPI",
        "unit": "%", "digits": 2, "frequency": "monthly", "betterWhen": "down", "importance": 2,
        "ref_line": 2.0, "description": "企業間の取引価格。CPIやPCEへの波及を占う物価の先行指標。",
    },
    {
        "id": "breakeven_inflation_us", "fred_id": "T10YIE", "transform": "raw",
        "category": "物価", "name": "10年期待インフレ率（BEI）", "shortName": "期待インフレ率(10年)",
        "unit": "%", "digits": 2, "frequency": "daily", "betterWhen": "neutral", "importance": 2,
        "ref_line": 2.0, "description": "国債市場が織り込む今後10年の平均インフレ率。2.0〜2.5%の安定が理想。",
    },
    # --- 雇用・所得 (9) ---
    {
        "id": "unemployment_rate_us", "fred_id": "UNRATE", "transform": "raw",
        "category": "雇用・所得", "name": "失業率", "shortName": "失業率",
        "unit": "%", "digits": 1, "frequency": "monthly", "betterWhen": "down", "importance": 3,
        "ref_line": 4.5, "description": "労働市場の健全性を表す最重要指標。急上昇は景気後退の強力なシグナル。",
    },
    {
        "id": "sahm_rule_us", "fred_id": "SAHMREALTIME", "transform": "raw",
        "category": "雇用・所得", "name": "サーム・ルール景気後退指標", "shortName": "サーム・ルール",
        "unit": "%", "digits": 2, "frequency": "monthly", "betterWhen": "down", "importance": 3,
        "ref_line": 0.5, "description": "失業率の3か月平均が過去1年最低から0.50%以上上昇すると景気後退入りを示唆。",
    },
    {
        "id": "nonfarm_payrolls_us", "fred_id": "PAYEMS", "transform": "diff_m",
        "category": "雇用・所得", "name": "非農業部門雇用者数（前月差）", "shortName": "非農業部門雇用者数",
        "unit": "千人", "digits": 0, "frequency": "monthly", "betterWhen": "up", "importance": 3,
        "ref_line": 100.0, "description": "毎月第1金曜発表の米国最重要指標。+10〜20万人程度が安定した雇用拡大の目安。",
    },
    {
        "id": "jobless_claims_us", "fred_id": "ICSA", "transform": "raw",
        "category": "雇用・所得", "name": "新規失業保険申請件数（週次）", "shortName": "新規失業保険申請",
        "unit": "件", "digits": 0, "frequency": "weekly", "betterWhen": "down", "importance": 3,
        "ref_line": 250000.0, "description": "毎週公表される速報性の高い雇用先行指標。25万〜30万件超への急増に警戒。",
    },
    {
        "id": "job_openings_us", "fred_id": "JTSJOL", "transform": "raw",
        "category": "雇用・所得", "name": "JOLTS求人件数", "shortName": "JOLTS求人件数",
        "unit": "千件", "digits": 0, "frequency": "monthly", "betterWhen": "up", "importance": 2,
        "ref_line": 7000.0, "description": "企業の労働需要を示すFRB注目の指標。急減は雇用市場の冷え込みを示唆。",
    },
    {
        "id": "avg_hourly_earnings_yoy_us", "fred_id": "CES0500000003", "transform": "yoy_m",
        "category": "雇用・所得", "name": "平均時給（前年比）", "shortName": "平均時給",
        "unit": "%", "digits": 2, "frequency": "monthly", "betterWhen": "neutral", "importance": 2,
        "ref_line": 3.5, "description": "賃金インフレの指標。3〜3.5%程度がインフレ目標2%と整合的なレンジ。",
    },
    {
        "id": "real_earnings_yoy_us", "fred_id": "LES1252881600Q", "transform": "yoy_q",
        "category": "雇用・所得", "name": "実質週給（前年比）", "shortName": "実質週給",
        "unit": "%", "digits": 2, "frequency": "quarterly", "betterWhen": "up", "importance": 1,
        "ref_line": 0.0, "description": "インフレ調整後の実質賃金の伸び。プラス圏なら家計の購買力が拡大。",
    },
    {
        "id": "personal_income_mom_us", "fred_id": "PI", "transform": "mom_m",
        "category": "雇用・所得", "name": "個人所得（前月比）", "shortName": "個人所得",
        "unit": "%", "digits": 2, "frequency": "monthly", "betterWhen": "up", "importance": 2,
        "ref_line": 0.0, "description": "家計の収入の伸び。個人消費（PCE）の原資となる。",
    },
    {
        "id": "adp_employment_us", "fred_id": "ADPMNUSNERSA", "transform": "diff_m",
        "category": "雇用・所得", "name": "ADP民間雇用者数（前月差）", "shortName": "ADP雇用者数",
        "unit": "千人", "digits": 0, "frequency": "monthly", "betterWhen": "up", "importance": 2,
        "ref_line": 100.0, "description": "米雇用統計の前哨戦として注目される民間部門の雇用増減。",
    },
    # --- 対外 (2) ---
    {
        "id": "current_account_us", "fred_id": "IEABC", "transform": "raw",
        "category": "対外", "name": "経常収支", "shortName": "経常収支",
        "unit": "百万ドル", "digits": 0, "frequency": "quarterly", "betterWhen": "up", "importance": 1,
        "ref_line": 0.0, "description": "貿易・サービス・所得収支の合計。長期的なドル需給の背景。",
    },
    {
        "id": "trade_balance_us", "fred_id": "BOPGSTB", "transform": "raw",
        "category": "対外", "name": "貿易収支（財・サービス）", "shortName": "貿易収支",
        "unit": "百万ドル", "digits": 0, "frequency": "monthly", "betterWhen": "up", "importance": 1,
        "ref_line": 0.0, "description": "輸出入の差額。GDPの純輸出項目に影響する。",
    },
    # --- 金利 (6) ---
    {
        "id": "fed_funds_rate_us", "fred_id": "FEDFUNDS", "transform": "raw",
        "category": "金利", "name": "FF金利（実効政策金利）", "shortName": "FF金利",
        "unit": "%", "digits": 2, "frequency": "monthly", "betterWhen": "neutral", "importance": 3,
        "ref_line": 3.0, "description": "FRBの金融政策の中心。利上げ局面は引き締め、利下げ局面は緩和を示す。",
    },
    {
        "id": "treasury_10y_us", "fred_id": "DGS10", "transform": "raw",
        "category": "金利", "name": "米国10年国債利回り", "shortName": "米10年金利",
        "unit": "%", "digits": 2, "frequency": "daily", "betterWhen": "neutral", "importance": 3,
        "ref_line": 4.0, "description": "世界の長期金利の基準。株式バリュエーション（特にグロース株）に直結。",
    },
    {
        "id": "yield_curve_spread_us", "fred_id": "T10Y2Y", "transform": "raw",
        "category": "金利", "name": "長短金利差（10年−2年）", "shortName": "長短金利差",
        "unit": "%", "digits": 2, "frequency": "daily", "betterWhen": "up", "importance": 3,
        "ref_line": 0.0, "description": "0%割れ（逆イールド）は歴史的に景気後退の先行警告。解消（スティープ化）時も要注意。",
    },
    {
        "id": "credit_spread_us", "fred_id": "BAA10Y", "transform": "raw",
        "category": "金利", "name": "信用スプレッド（Baa社債−10年債）", "shortName": "信用スプレッド",
        "unit": "%", "digits": 2, "frequency": "daily", "betterWhen": "down", "importance": 3,
        "ref_line": 2.5, "description": "企業の信用リスクプレミアム。急拡大（+0.5%以上の急騰や3%超）は金融ストレス警報。",
    },
    {
        "id": "mortgage_rate_us", "fred_id": "MORTGAGE30US", "transform": "raw",
        "category": "金利", "name": "30年固定住宅ローン金利", "shortName": "住宅ローン金利",
        "unit": "%", "digits": 2, "frequency": "weekly", "betterWhen": "neutral", "importance": 2,
        "ref_line": 6.0, "description": "米国家計の住宅購入余力に直結する金利。低下は住宅市場回復の追い風。",
    },
    {
        "id": "fed_balance_sheet_us", "fred_id": "WALCL", "transform": "raw",
        "category": "金利", "name": "FRB総資産（バランスシート）", "shortName": "FRB総資産",
        "unit": "百万ドル", "digits": 0, "frequency": "weekly", "betterWhen": "neutral", "importance": 2,
        "ref_line": None, "description": "量的緩和（QE）・量的引き締め（QT）による市場流動性の指標。",
    },
    # --- 為替・市場 (4) ---
    {
        "id": "sp500_us", "fred_id": "SP500", "transform": "raw",
        "category": "為替・市場", "name": "S&P 500 株価指数", "shortName": "S&P500",
        "unit": "", "digits": 1, "frequency": "daily", "betterWhen": "up", "importance": 3,
        "ref_line": None, "description": "米国大型株500社で構成される代表的な株価指数。",
    },
    {
        "id": "vix_us", "fred_id": "VIXCLS", "transform": "raw",
        "category": "為替・市場", "name": "VIX指数（恐怖指数）", "shortName": "VIX",
        "unit": "", "digits": 2, "frequency": "daily", "betterWhen": "down", "importance": 3,
        "ref_line": 20.0, "description": "S&P500オプションの予想変動率。20以下は平穏、30超はパニック警戒水準。",
    },
    {
        "id": "dollar_index_us", "fred_id": "DTWEXBGS", "transform": "raw",
        "category": "為替・市場", "name": "米ドル指数（広義貿易加重）", "shortName": "ドル指数",
        "unit": "", "digits": 1, "frequency": "daily", "betterWhen": "neutral", "importance": 2,
        "ref_line": 120.0, "description": "主要貿易相手国通貨に対するドルの総合的な強さ。",
    },
    {
        "id": "wti_oil_us", "fred_id": "DCOILWTICO", "transform": "raw",
        "category": "為替・市場", "name": "WTI原油価格", "shortName": "WTI原油",
        "unit": "ドル", "digits": 2, "frequency": "daily", "betterWhen": "neutral", "importance": 2,
        "ref_line": 75.0, "description": "エネルギー価格の国際指標。急騰はインフレ再燃要因、急落は景気減速懸念。",
    },
]

# FOMC会合・FRBイベント予定（2026〜2027年）
FOMC_EVENTS: list[dict[str, str]] = [
    {"date": "2026-01-28", "title": "FOMC 政策金利発表", "type": "FOMC", "note": "声明発表・パウエル議長会見"},
    {"date": "2026-03-18", "title": "FOMC 政策金利発表（SEP・ドットチャート）", "type": "FOMC", "note": "経済見通し・金利予測公表"},
    {"date": "2026-04-29", "title": "FOMC 政策金利発表", "type": "FOMC", "note": "声明発表・議長会見"},
    {"date": "2026-06-17", "title": "FOMC 政策金利発表（SEP・ドットチャート）", "type": "FOMC", "note": "経済見通し・金利予測公表"},
    {"date": "2026-07-29", "title": "FOMC 政策金利発表", "type": "FOMC", "note": "声明発表・議長会見"},
    {"date": "2026-08-21", "title": "ジャクソンホール経済シンポジウム", "type": "FRB", "note": "カンザスシティ連銀主催・議長講演"},
    {"date": "2026-09-16", "title": "FOMC 政策金利発表（SEP・ドットチャート）", "type": "FOMC", "note": "経済見通し・金利予測公表"},
    {"date": "2026-10-28", "title": "FOMC 政策金利発表", "type": "FOMC", "note": "声明発表・議長会見"},
    {"date": "2026-12-09", "title": "FOMC 政策金利発表（SEP・ドットチャート）", "type": "FOMC", "note": "年内最終会合・経済見通し公表"},
    {"date": "2027-01-27", "title": "FOMC 政策金利発表", "type": "FOMC", "note": "2027年初回会合"},
    {"date": "2027-03-17", "title": "FOMC 政策金利発表（SEP・ドットチャート）", "type": "FOMC", "note": "経済見通し・金利予測公表"},
    {"date": "2027-04-28", "title": "FOMC 政策金利発表", "type": "FOMC", "note": "声明発表・議長会見"},
    {"date": "2027-06-16", "title": "FOMC 政策金利発表（SEP・ドットチャート）", "type": "FOMC", "note": "経済見通し・金利予測公表"},
]
