---
name: datayes-robo
description: "浏览器自动化操作萝卜投研(r.datayes.com)。使用 browser tool + snapshot 数据清洗。browser tool 失败时立即停止并报告错误。"
metadata:
  {
    "openclaw":
      {
        "emoji": "🥕",
        "requires": { "browser": true },
      },
  }
---

# 萝卜投研 Browser Automation Skill

## 硬性约束

- 浏览器操作只用 `browser` tool，禁止 curl/web_fetch/web_search 等替代
- 允许使用 `shell` 执行 `python3 scripts/clean_snapshot.py` 进行 snapshot 数据清洗
- browser tool 失败 → 立即停止，报告错误和修复建议，结束
- 凭证不得回显到聊天回复中（手机号、密码均不可出现在回复文本里）
- snapshot 的 ref 是一次性的，每次 snapshot 后只能用当次返回的 ref，绝不复用旧 ref

## 凭证解析

```
1. shell: echo "$DATAYES_PHONE" / echo "$DATAYES_PASSWORD"
2. 两个都非空 → 用于登录（不要在回复中提及具体值）
3. 任一为空 → 提示用户在聊天中提供
```

## 核心流程（严格按顺序）

### Step 1: 启动浏览器

```
browser(action="start", profile="openclaw")
```

### Step 2: 登录状态检查（每次任务必须执行，不可跳过）

```
browser(action="navigate", targetUrl="https://r.datayes.com", profile="openclaw")
browser(action="act", request={ kind: "wait", loadState: "domcontentloaded" })
browser(action="act", request={ kind: "wait", timeMs: 3000 })
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
```

**snapshot 返回截断后的页面内容（可直接分析）+ 完整文件路径**，立即用清洗脚本处理（参见下方 "Snapshot 数据清洗" 章节）。

判断标准（基于清洗后的 `summary.json` 中 `login_status` 字段）：
- `logged_in` → 已登录，跳到 Step 4
- `not_logged_in` → 未登录，执行 Step 3
- `unknown` → 看 snapshot 内容判断

**登录状态判断的核心逻辑：**
- 如果首页能正常浏览（有导航栏：首页/研报/资讯/数据，有搜索框，有资讯列表或研报列表）→ 已登录
- 如果页面显示登录表单（tab "密码登录"、textbox "手机号码/邮箱/账号"、button "登 录"）→ 未登录
- 简单来说：能看到完整页面内容 = 已登录，看到登录表单 = 未登录

### Step 3: 登录（仅未登录时执行）

```
browser(action="navigate", targetUrl="https://r.datayes.com/auth/login", profile="openclaw")
browser(action="act", request={ kind: "wait", loadState: "domcontentloaded" })
browser(action="act", request={ kind: "wait", timeMs: 2000 })
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
# 找到"密码登录"tab → click
# 找到手机号输入框 → type PHONE
# 找到密码输入框 → type PASSWORD
# 找到登录按钮 → click
browser(action="act", request={ kind: "wait", loadState: "domcontentloaded" })
browser(action="act", request={ kind: "wait", timeMs: 3000 })
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
# 确认页面跳转到首页且能看到导航栏+资讯列表 → 登录成功
# 仍然停留在登录表单 → 登录失败
# 出现验证码 → 截图告知用户手动处理
```

### Step 4: 执行查询任务

首页资讯列表已在清洗后的 `summary.json` 中获取，直接使用。
需要操作时，从 `elements.json` 中查找目标元素的 `ref`。

#### 查询个股信息（重要）

当用户要求查询某只股票的信息时，**必须使用个股详情页**，不要使用搜索页：

1. 先获取股票代码：如果不知道代码，使用 `akshare` skill 的 `ak.stock_info_a_code_name()` 查询股票名称对应的代码
2. 直接导航到个股详情页：
```
browser(action="navigate", targetUrl="https://r.datayes.com/stock/{code}", profile="openclaw")
browser(action="act", request={ kind: "wait", loadState: "domcontentloaded" })
browser(action="act", request={ kind: "wait", timeMs: 5000 })
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
```
3. 个股页结构：左侧是导航菜单（实时行情/公司信息/财务数据等），右侧是数据内容区
4. 如果 snapshot 只拿到了左侧菜单没有右侧数据，点击具体子模块后再 snapshot：
```
# 点击"关键数据概览"等子模块链接
browser(action="act", request={ kind: "click", ref: "<子模块link的ref>" })
browser(action="act", request={ kind: "wait", timeMs: 5000 })
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
```

#### 查询基金信息（重要）

基金详情页 URL 格式为 `https://r.datayes.com/mof/app/fund/detail/{fundId}`，其中 `fundId`（如 `MUTUAL-10011892`）需要通过 API 查询获得，不能直接用基金代码拼 URL。

**Step 1: 通过 Python 脚本查询基金 ID**

必须先登录（Step 2/3 完成后），然后用脚本查询（脚本会自动从浏览器获取 cookie 调用 API）：

```
shell: python3 skills/datayes-robo/scripts/fund_search.py 006282
```

返回示例：
```json
{
  "success": true,
  "funds": [
    { "symbol": "006282", "name": "摩根欧洲动力策略股票(QDII)-A", "id": "MUTUAL-10011892",
      "detail_url": "https://r.datayes.com/mof/app/fund/detail/MUTUAL-10011892" }
  ]
}
```

也支持基金名称模糊搜索：
```
shell: python3 skills/datayes-robo/scripts/fund_search.py "摩根欧洲"
```

**Step 2: 导航到基金详情页**

从返回的 `detail_url` 或 `id` 拼接 URL：

```
browser(action="navigate", targetUrl="https://r.datayes.com/mof/app/fund/detail/MUTUAL-10011892", profile="openclaw")
browser(action="act", request={ kind: "wait", loadState: "domcontentloaded" })
browser(action="act", request={ kind: "wait", timeMs: 5000 })
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
```

**注意事项：**
- 脚本需要浏览器已登录（从浏览器 cookie 获取认证信息）
- 返回的 `funds` 数组可能有多个结果（名称模糊匹配时），优先用代码精确匹配的那个
- 禁止在首页搜索框中输入基金代码/名称进行搜索（效率低、容易超时）
- 禁止用浏览器 evaluate 调用 API（跨域 cookie 不携带，会返回 403）

**备选方案（脚本失败时）：** 导航到基金筛选页搜索：
```
browser(action="navigate", targetUrl="https://r.datayes.com/mof/app/fund/product/filter/public?keyword=006282", profile="openclaw")
```

#### 搜索功能（仅用于关键词搜索，不用于查股票/基金详情）

搜索页 `/search?query=` 是搜索引擎，返回资讯/研报/公告等混合结果，**不适合查询个股详细信息**。
仅在以下场景使用搜索：
- 搜索某个关键词相关的资讯/研报（如"新能源"、"AI"）
- 不确定具体内容在哪个页面时

```
browser(action="navigate", targetUrl="https://r.datayes.com/search?query=关键词", profile="openclaw")
```

#### 查看详情页

查看详情页时，必须用 click 点击链接，不要用 navigate 跳 URL（SPA 路由问题）：
```
# 从 elements.json 的 links 中找到目标文章的 ref
browser(action="act", request={ kind: "click", ref: "<elements.json中的ref>" })
browser(action="act", request={ kind: "wait", loadState: "domcontentloaded" })
browser(action="act", request={ kind: "wait", timeMs: 3000 })
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
# → 对新 snapshot 再次执行数据清洗
```

个股页可以用 navigate（非 SPA 内部路由），等待时间需要更长（图表数据加载慢）：
```
browser(action="navigate", targetUrl="https://r.datayes.com/stock/{code}", profile="openclaw")
browser(action="act", request={ kind: "wait", loadState: "domcontentloaded" })
browser(action="act", request={ kind: "wait", timeMs: 5000 })
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
```

## Snapshot 数据清洗（每次 snapshot 后必须执行）

snapshot tool 返回截断后的页面内容和完整文件路径。截断内容可直接在对话中分析，完整内容保存在文件中供清洗脚本使用。

**snapshot 返回内容包含两部分：**
1. 截断后的页面内容（accessibility tree），可直接在对话中分析
2. 完整 snapshot 文件路径，用于 `clean_snapshot.py` 深度清洗

```
SECURITY NOTICE: ...
<<<EXTERNAL_UNTRUSTED_CONTENT ...>>>
Source: Browser
---
generic [active] [ref=e1]:
  ...（截断后的页面内容）...
<<<END_EXTERNAL_UNTRUSTED_CONTENT ...>>>
Full snapshot saved to: /tmp/snapshot_<uuid>/snapshot_raw.txt (15234 chars)
Note: content above is truncated to 30000 chars. Read the file for full content.
```

### 清洗流程

snapshot 返回的内容已包含截断后的页面文本（可直接分析），同时完整内容保存在文件中。
对于需要深度清洗的场景（提取结构化数据），使用文件路径调用清洗脚本：

```
# 1. 从 snapshot 返回中提取文件路径（Full snapshot saved to: /tmp/snapshot_xxx/snapshot_raw.txt）
# 2. 用 --summary-only 直接输出摘要到 stdout（推荐，避免 cat 大文件）
shell: python3 skills/datayes-robo/scripts/clean_snapshot.py /tmp/snapshot_<uuid>/snapshot_raw.txt --summary-only --page-url "<当前页面URL>"

# 3. 需要操作定位时（点击链接/按钮），额外获取 elements
shell: python3 skills/datayes-robo/scripts/clean_snapshot.py /tmp/snapshot_<uuid>/snapshot_raw.txt --elements-only --page-url "<当前页面URL>"
```

重要：
- 优先用 `--summary-only`，不要写文件再 cat（减少对话上下文占用）
- 只在需要点击操作时才用 `--elements-only` 获取 ref
- 不需要手动生成 uuid，snapshot tool 已自动处理

### 写文件模式（可选，需要反复查阅时使用）

```
# 不指定 -o 时自动生成唯一输出目录
shell: python3 skills/datayes-robo/scripts/clean_snapshot.py /tmp/snapshot_<uuid>/snapshot_raw.txt --page-url "<当前页面URL>"
# 输出: /tmp/datayes_cleaned_<uuid>/summary.json + elements.json
```

### 清洗输出说明

**summary.json**（给对话展示）：
- `page_url` — 当前页面 URL
- `page_type` — 页面类型（`home`/`stock_detail`/`login`/`search`/`report_list`/`news_feed`/`data`/`fund`/`unknown`）
- `login_status` — 登录状态判断
- `truncated` — snapshot 是否被截断
- `navigation` — 导航栏项目（仅顶部导航栏，通常 ~9 项）
- `hot_keywords` — 搜索热词
- `news` — 资讯列表（标题 + URL，最多30条）
- `reports` — 研报列表（标题 + URL，最多30条）
- `sections` — 页面分区（heading/tab 为分区起点，每分区最多15项）
- `stock_code` — 股票代码（仅个股页）
- `stock_info` — 股票行情摘要（仅个股页，含 stock_name_code/price/change_pct）
- `key_data` — 关键行情数据标签-值配对（仅个股页，如 `{"最新": "5.50", "涨幅": "-2.31%", "总值": "1357.74亿"}`）
- `menu_structure` — 左侧菜单结构（仅个股页）

**elements.json**（给操作定位）：
- `links` — 所有链接（ref + text + url）
- `buttons` — 所有按钮（ref + text）
- `inputs` — 所有输入框（ref + text + input_type）
- `tabs` — 所有标签页（ref + text + states）
- `images` — 所有图片（ref + text）
- `checkboxes` — 所有复选框（ref + text + states）

### 操作定位示例

```
# 用户说"打开比亚迪的研报"
# 1. 从 elements.json 的 links 中搜索包含"比亚迪"的链接
# 2. 找到: {"ref": "e203", "text": "比亚迪（002594）：...", "url": "/details/report/8395161"}
# 3. 使用该 ref 执行点击
browser(action="act", request={ kind: "click", ref: "e203" })
```

详细 schema 参见 `references/snapshot_schema.md`。

## snapshot 截断处理

snapshot 内容会被截断后返回到对话中（由 `OPENCLAW_SNAPSHOT_MAX_CHARS` 控制，默认 12000 字符），完整内容自动保存到文件。截断不影响清洗脚本，因为清洗脚本读取的是完整文件。

注意：聊天历史有 12K 字符限制（`CHAT_HISTORY_TEXT_MAX_CHARS`），snapshot 原文在后续对话轮次中会被截断。因此每次 snapshot 后必须立即执行数据清洗，用清洗后的精简 summary 做后续对话。

处理策略（当页面内容过大时）：
1. 用 `selector` 缩小范围获取特定区域：
   ```
   browser(action="snapshot", snapshotFormat="ai", selector=".main-content", profile="openclaw")
   ```
2. 用 `scrollIntoView` 滚动到目标区域后再 snapshot（注意：scrollIntoView 不会触发懒加载）
3. 如果页面有"查看更多"按钮，需要先 click 加载更多内容，再 snapshot：
   ```
   browser(action="act", request={ kind: "click", ref: "<查看更多按钮ref>" })
   browser(action="act", request={ kind: "wait", timeMs: 2000 })
   browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
   ```
4. 清洗后的 `summary.json` 中 `truncated: true` 表示原始 snapshot 被截断，可能需要分区获取
5. 备选：使用 `mode="efficient"` 减少输出量（内容更精简但可能丢失重要数据）

## 页面等待规则

- 禁止使用 `loadState: "networkidle"`（萝卜投研持续有网络请求，会超时）
- 统一用 `domcontentloaded` + `timeMs: 3000` 组合
- 数据未加载完 → 再等一次 `timeMs: 3000` 后重新 snapshot

## 错误诊断

| 错误关键词 | 修复命令 |
|-----------|---------|
| `No supported browser found` | `docker compose build --no-cache && docker compose up -d` |
| `device token mismatch` / `pairing required` | `docker compose exec openclaw-gateway rm -f /home/node/.openclaw/state/identity/device.json /home/node/.openclaw/state/devices/paired.json && docker compose restart` |
| `browser not enabled` | openclaw.json 添加 `"browser": { "enabled": true }` 后 restart |
| `Can't reach` / `connection refused` | `docker compose up -d` |
| `Element "xxx" not found` | 重新 snapshot 获取新 ref，用新 ref 操作 |

## 站点 URL

| 页面 | URL |
|------|-----|
| 首页 | `https://r.datayes.com` |
| 登录 | `https://r.datayes.com/auth/login` |
| 搜索 | `https://r.datayes.com/search?query={关键词}` |
| 个股 | `https://r.datayes.com/stock/{code}` |
| 基金详情 | `https://r.datayes.com/mof/app/fund/detail/{fundId}` |
| 研报 | `https://r.datayes.com/fastreport` |
| 资讯 | `https://r.datayes.com/intelligent_feed` |
| 数据 | `https://r.datayes.com/data/economy_database` |
| 基金 | `https://r.datayes.com/mof/app/fund/product/filter/public` |
| 组合 | `https://r.datayes.com/mof/portfolio/overview` |
| 市场概况 | `https://r.datayes.com/market/quotation` |

股票代码格式：纯数字，不带交易所前缀（如 `600519`、`300750`）。
