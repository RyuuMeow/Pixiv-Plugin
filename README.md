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

## 免責聲明（Disclaimer）

**本插件僅供學術研究、網路協定與程式設計技術之教學示範用途使用，不得
用於任何商業用途或違反目標網站服務條款、當地法規之行為。**

本插件為 [CLI-Downloader](https://github.com/RyuuMeow/CLI-Downloader) 之社群擴充元件，示範如何解析特定網站之公開
頁面結構與 API 回應，作為網路請求、資料解析與自動化技術之程式設計
參考範例，不具持續性服務屬性。

- **關於目標網站**：本插件僅為技術層面的介接工具，**對目標網站之
  營運主體、內容來源合法性、著作權歸屬、內容分級或其提供服務是否
  符合當地法規，不做任何調查、保證、背書或評論**。使用者應自行判斷
  並確認該網站及其內容來源之合法性，開發者不因插件支援特定網站而
  暗示或保證該網站之正當性。
- **關於付費／限制內容存取**：本插件不含任何繞過付費牆、破解驗證或
  規避存取控制之機制。若使用者選擇存取需登入或付費之內容，前提為
  使用者本身**已具備合法帳號權限**（如已登入、已訂閱、已付費），
  插件僅代為載入使用者**自行於官方網站登入**取得之 Session／Cookie，
  其存取範圍完全對應該帳號原有之權限，插件本身不擴大、不繞過任何
  平台既有的存取限制。
- 透過本插件存取或下載之任何內容，其著作權、授權與合法性歸屬於原
  網站或原著作權人，本插件與其開發者**不擁有、不主張、不轉移**任何
  相關權利，亦不對內容本身之真實性、合法性負責。**嚴禁將下載內容
  用於商業用途、公開散布、二次上傳或大量轉載。**
- 使用者應自行確認其使用行為符合目標網站服務條款（Terms of Service）
  及所在地區之相關法規。因使用本插件所生之任何後果——包括但不限於
  帳號限制／停權、著作權爭議、法律責任或其他任何損失——**概由使用者
  自行承擔**，與插件開發者、貢獻者無關。
- 本插件依現狀（AS IS）提供，不保證其功能正確性、完整性，亦不保證
  於目標網站政策或結構變更後仍可持續運作。

**若您無法確認目標網站之合法性、無法保證您的使用行為符合當地法規與
目標網站服務條款，請勿安裝或使用本插件。使用本插件即代表您已閱讀、
理解並同意上述所有條款。**

