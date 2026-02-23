---
name: datayes-robo
description: "浏览器自动化操作萝卜投研(r.datayes.com)。只能用 browser tool，禁止降级。browser tool 失败时立即停止并报告错误。"
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

- 只用 `browser` tool，禁止 Python/curl/web_fetch/web_search 等任何替代
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
browser(action="snapshot", snapshotFormat="ai", mode="efficient", profile="openclaw")
```

判断标准：
- 页面有用户头像/昵称 → 已登录，跳到 Step 4
- 页面有"登录 | 注册"文字 → 未登录，执行 Step 3

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
browser(action="snapshot", snapshotFormat="ai", mode="efficient", profile="openclaw")
# 确认"登录 | 注册"消失 → 登录成功
# 出现验证码 → 截图告知用户手动处理
```

### Step 4: 执行查询任务

首页资讯列表已在 Step 2 的 snapshot 中获取，直接使用。

查看详情页时，必须用 click 点击链接，不要用 navigate 跳 URL（SPA 路由问题）：
```
# 从当次 snapshot 找到目标文章的 link ref
browser(action="act", request={ kind: "click", ref: "<当次snapshot的ref>" })
browser(action="act", request={ kind: "wait", loadState: "domcontentloaded" })
browser(action="act", request={ kind: "wait", timeMs: 3000 })
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
```

个股页可以用 navigate（非 SPA 内部路由）：
```
browser(action="navigate", targetUrl="https://r.datayes.com/v2/stock/{code}", profile="openclaw")
browser(action="act", request={ kind: "wait", loadState: "domcontentloaded" })
browser(action="act", request={ kind: "wait", timeMs: 3000 })
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
```

## snapshot 截断处理

当 snapshot 被 `...(truncated)...` 截断时：
1. 先用 `mode="efficient"` 重试
2. 仍不够 → 用 `scrollIntoView` 滚动到目标区域后再 snapshot
3. 或用 `selector` 缩小范围获取特定区域内容

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
| 个股 | `https://r.datayes.com/v2/stock/{code}` |
| 研报 | `https://r.datayes.com/v2/selection` |
| 宏观 | `https://r.datayes.com/v2/macro` |
| 行业 | `https://r.datayes.com/v2/industry` |

股票代码格式：纯数字，不带交易所前缀（如 `600519`、`300750`）。
