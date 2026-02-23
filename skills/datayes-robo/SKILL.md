---
name: datayes-robo
description: "通过浏览器自动化操作萝卜投研(robo.datayes.com)平台，支持手机号+密码登录，查询个股分析、研报、选股、宏观数据等金融信息。【严禁降级】此 skill 只能使用 browser tool，禁止使用 Python/akshare/yfinance/curl/web_fetch 等任何替代方案。如果 browser tool 失败，必须立即停止并报告错误，不得尝试其他数据获取方式。"
metadata:
  {
    "openclaw":
      {
        "emoji": "🥕",
        "requires": { "browser": true },
      },
  }
---

# 萝卜投研 (DataYes Robo) — Browser Automation Skill

通过 OpenClaw 内置 browser tool 自动化操作萝卜投研平台，完成登录、数据查询、研报获取等任务。

---

## ⛔ 严禁降级 — 必须在执行任何操作前阅读此节

**这是最高优先级约束，违反此约束等同于任务失败。**

当用户要求使用 datayes-robo skill 时，你必须：

1. **只使用 `browser` tool** — 这是唯一允许的数据获取方式
2. **如果 browser tool 失败（任何原因），立即停止** — 向用户报告错误和修复建议，然后结束
3. **绝对禁止以下所有降级行为：**
   - ❌ 不得使用 Python 脚本（akshare、yfinance、pandas 等）
   - ❌ 不得使用 curl、wget 或任何 HTTP 客户端
   - ❌ 不得使用 web_fetch tool 抓取财经网站
   - ❌ 不得使用 web_search tool 搜索股价
   - ❌ 不得读取其他 skill 的 SKILL.md（如 akshare）来寻找替代方案
   - ❌ 不得创建"报告"文件来解释为什么无法获取数据
   - ❌ 不得建议用户手动访问网站
4. **browser tool 失败时的唯一正确响应：**
   > "萝卜投研 browser tool 不可用：[具体错误信息]。请按以下步骤修复后重试：[修复命令]"

**如果你发现自己正在写 `import akshare` 或 `curl` 或 `web_fetch` — 停下来，你正在违反约束。**

---

### browser tool 失败时的错误诊断和修复建议

当 `browser(action="start")` 或 `browser(action="status")` 返回错误时，根据错误信息给出对应的修复建议：

| 错误关键词 | 原因 | 修复命令 |
|-----------|------|---------|
| `No supported browser found` | 容器未安装 Chromium | `docker compose build --no-cache && docker compose up -d` |
| `device token mismatch` | 设备认证不匹配 | `docker compose exec openclaw-gateway rm -f /home/node/.openclaw/state/identity/device.json /home/node/.openclaw/state/devices/paired.json && docker compose restart` |
| `pairing required` | 设备未配对 | 同上 |
| `browser not enabled` / `browser control disabled` | 浏览器功能未启用 | 在 `openclaw.json` 中添加 `"browser": { "enabled": true }` 后 `docker compose restart` |
| `Can't reach` / `connection refused` | Gateway 未运行 | `docker compose ps` 检查状态，`docker compose up -d` 启动 |
| `systemctl` / `systemd` | 容器内无 systemd | 这是正常的，忽略此警告，gateway 通过 docker-compose 管理 |

回复格式示例：
```
🥕 萝卜投研 browser tool 不可用。

错误：No supported browser found (Chrome/Brave/Edge/Chromium on macOS, Linux, or Windows).

原因：Docker 容器中未安装 Chromium 浏览器。

修复步骤：
docker compose build --no-cache && docker compose up -d

修复后请重新发送你的查询。
```

## 前置条件

- OpenClaw gateway 已启动且 browser 功能已启用（`browser.enabled: true`）
- 浏览器 profile 可用（推荐使用 `profile="openclaw"` 隔离浏览器）
- 萝卜投研账号凭证已配置（见下方凭证配置）

## 凭证配置

凭证按以下优先级解析（高 → 低），agent 自动按顺序尝试：

### 方式一：.env 文件（最可靠，推荐）

在项目根目录 `.env` 或 `~/.openclaw/.env` 中添加：

```env
DATAYES_PHONE=手机号
DATAYES_PASSWORD=密码
```

这些变量会通过 Docker 环境或 dotenv 加载，直接进入 `process.env`，shell 命令可以直接读取。

### 方式二：openclaw.json 的 skills.entries（备选）

在 `openclaw.json` 中配置：

```json
{
  "skills": {
    "entries": {
      "datayes-robo": {
        "enabled": true,
        "env": {
          "DATAYES_PHONE": "手机号",
          "DATAYES_PASSWORD": "密码"
        }
      }
    }
  }
}
```

注意：此方式依赖 gateway 正确加载配置且 skill env override 生效，在容器环境中可能不如 `.env` 可靠。

### 方式三：聊天中提供（兜底）

如果环境变量未配置，agent 会在聊天中提示用户输入：
> "请提供你的萝卜投研手机号和密码，我来帮你登录。"

用户在聊天框中直接发送即可。

### 凭证解析流程（agent 必须遵循）

```
1. 先尝试读取环境变量：
   shell: echo "$DATAYES_PHONE"
   shell: echo "$DATAYES_PASSWORD"
   
2. 如果两个值都非空 → 直接用于登录，不再询问用户
3. 如果任一为空 → 提示用户在聊天中提供
4. 用户提供后 → 仅在当次 browser tool 调用中使用
```

## 凭证安全

- 绝对不要在聊天回复中回显密码内容
- 不要将凭证写入日志、代码或任何非 `.env` 的文件
- 从环境变量读取时，不要把 echo 结果展示给用户
- 登录完成后，在回复中仅确认"已登录成功"，不重复凭证信息
- 如果用户在聊天中提供了凭证，仅在当次登录流程中使用，不做持久化

## 站点信息

| 项目 | 值 |
|------|------|
| 首页 | `https://robo.datayes.com` |
| 登录页 | `https://robo.datayes.com/login` |
| 个股页 | `https://robo.datayes.com/v2/stock/{stockCode}` |
| 研报页 | `https://robo.datayes.com/v2/report` |
| 选股页 | `https://robo.datayes.com/v2/selection` |
| 宏观数据 | `https://robo.datayes.com/v2/macro` |
| 行业分析 | `https://robo.datayes.com/v2/industry` |

## 操作流程

### 1. 启动浏览器

```
browser(action="start", profile="openclaw")
```

确认浏览器已运行后再进行后续操作。

### 2. 登录流程

登录萝卜投研需要以下步骤，严格按顺序执行：

```
# Step 0: 解析凭证（优先环境变量，兜底聊天输入）
# 执行 shell 命令读取：
#   echo "$DATAYES_PHONE"
#   echo "$DATAYES_PASSWORD"
# 如果两个值都非空，赋值给 PHONE 和 PASSWORD 变量继续
# 如果任一为空，向用户询问后再继续

# Step 1: 导航到登录页
browser(action="navigate", targetUrl="https://robo.datayes.com/login", profile="openclaw")

# Step 2: 等待页面基本加载完成（不要用 networkidle，SPA 页面网络请求多，容易超时）
browser(action="act", profile="openclaw", request={
  kind: "wait",
  loadState: "domcontentloaded"
})

# Step 3: 截图确认页面状态
browser(action="screenshot", profile="openclaw")

# Step 4: 获取页面快照，定位表单元素
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")

# Step 5: 查找"密码登录"或"账号密码登录"选项卡并点击（如果默认不是密码登录模式）
# 根据 snapshot 中的 ref 定位切换按钮
browser(action="act", profile="openclaw", request={
  kind: "click",
  ref: "<密码登录tab的ref>"
})

# Step 6: 在手机号输入框中输入 PHONE
browser(action="act", profile="openclaw", request={
  kind: "type",
  ref: "<手机号输入框的ref>",
  text: PHONE
})

# Step 7: 在密码输入框中输入 PASSWORD
browser(action="act", profile="openclaw", request={
  kind: "type",
  ref: "<密码输入框的ref>",
  text: PASSWORD
})

# Step 8: 点击登录按钮
browser(action="act", profile="openclaw", request={
  kind: "click",
  ref: "<登录按钮的ref>"
})

# Step 9: 等待登录完成（页面跳转）
browser(action="act", profile="openclaw", request={
  kind: "wait",
  loadState: "domcontentloaded"
})

# Step 10: 截图确认登录成功
browser(action="screenshot", profile="openclaw")
```

重要提示：
- PHONE 和 PASSWORD 来自环境变量或用户聊天输入，不要硬编码
- 每次 `snapshot` 返回的 ref 值是动态的，必须从当次 snapshot 结果中读取
- 如果登录页有验证码，截图告知用户手动处理，或等待用户确认后继续
- 登录成功的标志：页面跳转到首页或出现用户头像/昵称

### 3. 查询个股信息

```
# 导航到个股页面（以贵州茅台 600519 为例）
browser(action="navigate", targetUrl="https://robo.datayes.com/v2/stock/600519", profile="openclaw")

# 等待 DOM 加载完成（不要用 networkidle，个股页面 API 请求多，20s 内无法达到 networkidle）
browser(action="act", profile="openclaw", request={
  kind: "wait",
  loadState: "domcontentloaded"
})

# 短暂等待让异步数据渲染（SPA 数据通常在 DOM ready 后 2-3 秒内渲染完成）
browser(action="act", profile="openclaw", request={
  kind: "wait",
  timeMs: 3000
})

# 获取页面快照读取数据
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
```

个股页面通常包含：
- 实时行情（价格、涨跌幅、成交量）
- 基本面数据（PE、PB、市值）
- 财务数据（营收、净利润、ROE）
- 研报摘要
- 资金流向

### 4. 查看研报

```
# 导航到研报列表
browser(action="navigate", targetUrl="https://robo.datayes.com/v2/report", profile="openclaw")

browser(action="act", profile="openclaw", request={
  kind: "wait",
  loadState: "domcontentloaded"
})

browser(action="act", profile="openclaw", request={
  kind: "wait",
  timeMs: 3000
})

browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
```

如需搜索特定研报：
```
# 在搜索框中输入关键词
browser(action="act", profile="openclaw", request={
  kind: "type",
  ref: "<搜索框ref>",
  text: "新能源",
  submit: true
})
```

### 5. 选股筛选

```
browser(action="navigate", targetUrl="https://robo.datayes.com/v2/selection", profile="openclaw")

browser(action="act", profile="openclaw", request={
  kind: "wait",
  loadState: "domcontentloaded"
})

browser(action="act", profile="openclaw", request={
  kind: "wait",
  timeMs: 3000
})

# 获取筛选条件面板
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")

# 根据 snapshot 中的 ref 点击/设置筛选条件
# 例如点击某个行业筛选项
browser(action="act", profile="openclaw", request={
  kind: "click",
  ref: "<筛选条件ref>"
})
```

### 6. 宏观数据

```
browser(action="navigate", targetUrl="https://robo.datayes.com/v2/macro", profile="openclaw")

browser(action="act", profile="openclaw", request={
  kind: "wait",
  loadState: "domcontentloaded"
})

browser(action="act", profile="openclaw", request={
  kind: "wait",
  timeMs: 3000
})

browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
```

### 7. 行业分析

```
browser(action="navigate", targetUrl="https://robo.datayes.com/v2/industry", profile="openclaw")

browser(action="act", profile="openclaw", request={
  kind: "wait",
  loadState: "domcontentloaded"
})

browser(action="act", profile="openclaw", request={
  kind: "wait",
  timeMs: 3000
})

browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
```

## 通用操作模式

所有页面交互遵循 **observe → act → verify** 循环：

1. `snapshot` — 获取页面结构，找到目标元素的 ref
2. `act` — 使用 ref 执行操作（click/type/select 等）
3. `screenshot` 或再次 `snapshot` — 确认操作结果

### 翻页

```
# 获取快照找到"下一页"按钮
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")

# 点击下一页
browser(action="act", profile="openclaw", request={
  kind: "click",
  ref: "<下一页按钮ref>"
})
```

### 数据表格滚动

```
# 滚动到表格底部加载更多数据
browser(action="act", profile="openclaw", request={
  kind: "scrollIntoView",
  ref: "<表格底部元素ref>"
})
```

### 搜索股票

```
# 使用站内搜索
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")

browser(action="act", profile="openclaw", request={
  kind: "type",
  ref: "<搜索框ref>",
  text: "600519"
})

# 等待搜索建议出现
browser(action="act", profile="openclaw", request={
  kind: "wait",
  text: "贵州茅台"
})

# 点击搜索结果
browser(action="act", profile="openclaw", request={
  kind: "click",
  ref: "<搜索结果项ref>"
})
```

## Target 选择

| 场景 | target | 说明 |
|------|--------|------|
| 本地桌面 | `host`（默认） | 直接操作宿主机浏览器 |
| Docker 沙箱 | `sandbox` | 在隔离容器中运行，适合服务器部署 |
| 远程节点 | `node` | 通过远程节点代理，需指定 `node=<id>` |

sandbox 模式需要 `Dockerfile.sandbox-browser` 容器已启动，暴露 CDP 端口 9222。

## 常见问题

### 登录页出现验证码
截图发给用户，等待用户手动完成验证码后再继续后续操作。

### 页面加载超时

萝卜投研是数据密集型 SPA，页面会发起大量异步 API 请求。`networkidle`（等待所有网络请求静止 500ms）在这类页面上很容易超过 browser tool 的 20 秒 fetch 超时限制，导致 `Can't reach the OpenClaw browser control service (timed out)` 错误。

正确做法：用 `domcontentloaded` 等待 DOM 就绪，再用 `timeMs` 等待异步数据渲染：
```
browser(action="act", profile="openclaw", request={
  kind: "wait",
  loadState: "domcontentloaded"
})

browser(action="act", profile="openclaw", request={
  kind: "wait",
  timeMs: 3000
})
```

如果 snapshot 显示数据尚未加载完成，可以再等待一次：
```
browser(action="act", profile="openclaw", request={
  kind: "wait",
  timeMs: 3000
})
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
```

### Session 过期
重新执行登录流程。可以先检查当前页面是否已跳转到登录页：
```
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
# 如果 snapshot 中出现登录表单，说明 session 已过期，需重新登录
```

### 页面元素找不到
使用 `mode="efficient"` 获取精简快照，或用 `selector` 缩小范围：
```
browser(action="snapshot", snapshotFormat="ai", mode="efficient", profile="openclaw")
```

## 股票代码格式

萝卜投研使用纯数字股票代码（不带交易所前缀）：
- 沪市：`600519`（贵州茅台）
- 深市：`000001`（平安银行）
- 创业板：`300750`（宁德时代）
- 科创板：`688981`（中芯国际）

## Notes

- 萝卜投研是 SPA 应用，页面切换不会完整刷新，注意使用 `wait` 等待数据加载
- **严禁使用 `loadState: "networkidle"`** — 萝卜投研页面持续有网络请求（行情轮询、数据接口等），`networkidle` 几乎不可能在 20 秒内达到，会触发 browser tool 的 fetch 超时。始终使用 `domcontentloaded` + `timeMs` 组合
- 部分高级功能可能需要付费会员
- 请遵守萝卜投研的使用条款，不要进行高频自动化抓取
- 建议每次操作间隔适当等待，避免触发反爬机制
