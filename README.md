# 米国経済指標トラッカー（`us-economic-tracker`）

FRED（セントルイス連銀）の公開CSVエンドポイント（**APIキー不要**）から米国主要38指標・主要マーケット6項目を自動取得し、景気後退警戒シグナル・zスコア急変アラート・2指標比較チャート・FOMCスケジュールを備えた静的ダッシュボードを生成します。

## 実行方法
```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py --workers 6
```
