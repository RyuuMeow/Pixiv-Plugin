# Pixiv Plugin

這是一個為 [CLI-Downloader](https://github.com/RyuuMeow/CLI-Downloader) 提供 Pixiv 下載支援的插件。

## 支援的 URL 格式

本插件支援以下格式的 Pixiv 網址：

* **單篇作品 (Artwork)**：下載指定的單篇作品（支援單圖、多圖頁面以及動圖 Ugoira）。
  * `https://www.pixiv.net/artworks/<artwork_id>`
* **作者作品列表 (User Illustrations / Manga)**：取得指定作者的所有插畫或漫畫作品（支援分頁）。
  * `https://www.pixiv.net/users/<user_id>`
  * `https://www.pixiv.net/users/<user_id>/illustrations`
  * `https://www.pixiv.net/users/<user_id>/manga`

## 模板變數 (Template Variables)

在設定下載路徑、資料夾或檔名模板時，您可以使用以下可用的 Metadata 變數：

* `{artwork_id}`: 作品 ID
* `{title}`: 作品標題
* `{author_name}`: 作者名稱 (User Name)
* `{author_id}`: 作者 ID (User ID)
* `{create_date}`: 作品建立日期
* `{artwork_type}`: 作品類型代碼（例如 0、1、2 分別代表不同類型如插畫、動圖等）
* `{tags}`: 該作品的標籤列表
* `{gallery_id}`: 作品圖庫 ID（等同於作品 ID）

**預設資料夾模板**：`{author_name}/{artwork_id}-{title}`

*(註：多頁作品的單張圖片檔名會自動加上 `_p0`, `_p1` 等後綴；動圖 Ugoira 會被打包為 `_ugoira.zip`。)*

## 插件設定 (Settings)

您可以在 CLI-Downloader 的設定中針對本插件進行以下自定義設定：

* `language`：向 Pixiv 請求資料時使用的語言。可選值為 `en` (預設), `ja`, `zh`。
* `http.user_agent`：發送 HTTP 請求時使用的 User-Agent (預設為 `Mozilla/5.0 CLI-Downloader/0.1`)。
* `http.timeout_seconds`：請求的超時時間，單位為秒 (預設為 `30.0`，範圍 1.0 ~ 120.0)。

## 帳號認證與限制級內容 (Secrets)

若要下載 R-18、限制級或需要登入才能查看的作品，請在互動式設定頁
開啟 `Plugins / Pixiv / Auth / Session` 並按下 `Login`。CLI-Downloader
會開啟隔離的瀏覽器登入視窗，在取得 Pixiv 工作階段後自動保存並關閉。

舊版 `plugins.pixiv.phpsessid` 值仍可作相容 fallback，但不再顯示於設定頁。
