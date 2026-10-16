# 電車玩家 SEO／GEO 週報代理

每週一早上 6 點（台灣時間），GitHub Actions 會自動：

1. **Search Console**：拉 52ev.com.tw 最近 28 天和前 28 天的點擊、曝光、排名，找出「排第 8–20 名」和「曝光高但點擊率低」的詞
2. **AI 探針（GEO）**：把 `questions.yml` 裡的客戶問題丟給有上網搜尋能力的 AI，記錄有沒有提到「電車玩家」、有沒有引用官網、引用了哪些競爭網站
3. **分析**：Claude 讀數據＋網站現有頁面（llms.txt、sitemap）＋上週報告，寫週報與 3–5 個下週 SEO 任務（格式與網站 repo 的 `tasks/seo-next.md` 相同）
4. **存檔**：週報寫進 `reports/`，原始數據寫進 `data/`
5. **通知**：Telegram 傳摘要與週報連結

沒設定的金鑰會自動略過那一步，不會整個失敗。

## 設定（一次性）

到這個 repo 的 **Settings → Secrets and variables → Actions**：

| 名稱 | 類型 | 必要 | 怎麼取得 |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Secret | ✅ | console.anthropic.com → API Keys。分析與 Claude 探針都用它 |
| `GSC_SERVICE_ACCOUNT_JSON` | Secret | ✅ | 見下方「Search Console 服務帳戶」 |
| `TELEGRAM_BOT_TOKEN` | Secret | ✅ | Telegram 找 @BotFather → `/newbot`，拿到的 token |
| `TELEGRAM_CHAT_ID` | Secret | ✅ | 先傳任一訊息給你的機器人，再打開 `https://api.telegram.org/bot<token>/getUpdates`，找 `"chat":{"id":...}` 的數字 |
| `PERPLEXITY_API_KEY` | Secret | 選用 | perplexity.ai → API。加了就多一個 AI 引擎 |
| `GSC_SITE` | Variable | 選用 | 預設 `sc-domain:52ev.com.tw`（網域資源）。如果你的 Search Console 是「網址前置字元」資源，改成 `https://52ev.com.tw/` |

### Search Console 服務帳戶

1. 到 console.cloud.google.com 建立（或選一個）專案
2. 「API 和服務 → 程式庫」啟用 **Google Search Console API**
3. 「IAM 與管理 → 服務帳戶」建立服務帳戶 → 進去「金鑰」→ 新增金鑰 → JSON，下載檔案
4. 到 Search Console → 設定 → 使用者和權限 → 新增使用者，貼上服務帳戶的 email（`xxx@xxx.iam.gserviceaccount.com`），權限選「受限」即可
5. 把 JSON 檔整份內容貼進 `GSC_SERVICE_ACCOUNT_JSON`

## 手動執行

GitHub → Actions → 「每週 SEO／GEO 週報」→ Run workflow。勾選「不跑 AI 探針」可以先省錢測試 Search Console 和 Telegram。

## 費用

- GitHub Actions：每週跑一次、幾分鐘，在免費額度內【推論，依帳號方案】
- Claude API：每週 26 題探針（含網路搜尋）＋一份分析報告。實際金額看第一次執行後 console.anthropic.com 的用量為準

## 調整

- 改問題：編輯 `questions.yml`
- 改報告重點：編輯 `agent/analyze.py` 的 `SYSTEM`
- 改時間：編輯 `.github/workflows/weekly.yml` 的 `cron`
