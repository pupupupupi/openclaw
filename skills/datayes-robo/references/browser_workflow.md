# Browser Tool 操作工作流参考

## 核心原则

所有浏览器操作遵循 **observe → act → verify** 三步循环。

## 完整登录工作流示例

```
# 0. 解析凭证（环境变量优先）
# shell: echo "$DATAYES_PHONE"    → 如果非空则为 PHONE
# shell: echo "$DATAYES_PASSWORD" → 如果非空则为 PASSWORD
# 如果任一为空 → 在聊天中向用户询问

# 1. 确保浏览器已启动
browser(action="status", profile="openclaw")
# 如果 running=false:
browser(action="start", profile="openclaw")

# 2. 导航到登录页
browser(action="navigate", targetUrl="https://robo.datayes.com/login", profile="openclaw")

# 3. 等待页面完全加载
browser(action="act", profile="openclaw", request={kind: "wait", loadState: "networkidle"})

# 4. 截图确认当前页面状态
browser(action="screenshot", profile="openclaw")

# 5. 获取 AI 快照定位表单元素
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
# → 从返回结果中找到：
#   - 登录方式切换 tab（如"密码登录"）
#   - 手机号输入框 ref
#   - 密码输入框 ref
#   - 登录按钮 ref

# 6. 如需切换到密码登录模式
browser(action="act", profile="openclaw", request={kind: "click", ref: "<tab_ref>"})

# 7. 输入手机号（PHONE 来自环境变量或用户输入）
browser(action="act", profile="openclaw", request={kind: "type", ref: "<phone_ref>", text: PHONE})

# 8. 输入密码（PASSWORD 来自环境变量或用户输入）
browser(action="act", profile="openclaw", request={kind: "type", ref: "<password_ref>", text: PASSWORD})

# 9. 点击登录
browser(action="act", profile="openclaw", request={kind: "click", ref: "<login_btn_ref>"})

# 10. 等待跳转
browser(action="act", profile="openclaw", request={kind: "wait", loadState: "networkidle", timeoutMs: 15000})

# 11. 验证登录结果
browser(action="screenshot", profile="openclaw")
```

## 数据提取工作流

```
# 1. 导航到目标页面
browser(action="navigate", targetUrl="https://robo.datayes.com/v2/stock/600519", profile="openclaw")

# 2. 等待数据渲染
browser(action="act", profile="openclaw", request={kind: "wait", loadState: "networkidle"})

# 3. 获取快照提取数据
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
# → 从 snapshot 文本中解析出股票数据

# 4. 如需查看更多 tab（如"财务"）
browser(action="act", profile="openclaw", request={kind: "click", ref: "<财务tab_ref>"})
browser(action="act", profile="openclaw", request={kind: "wait", loadState: "networkidle"})
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
```

## act request kind 速查

| kind | 用途 | 必需参数 |
|------|------|----------|
| `click` | 点击元素 | `ref` |
| `type` | 输入文本 | `ref`, `text` |
| `press` | 按键 | `key`（如 `Enter`, `Tab`） |
| `hover` | 悬停 | `ref` |
| `scrollIntoView` | 滚动到可见 | `ref` |
| `select` | 下拉选择 | `ref`, `values` |
| `fill` | 批量填表 | `fields` |
| `wait` | 等待条件 | `text`/`loadState`/`timeMs` 等 |
| `evaluate` | 执行 JS | `fn` |
| `close` | 关闭标签页 | — |

## snapshot 参数选择

| 场景 | 推荐参数 |
|------|----------|
| 常规页面分析 | `snapshotFormat="ai"` |
| 大页面/性能优先 | `snapshotFormat="ai", mode="efficient"` |
| 需要精确 ref | `snapshotFormat="ai", refs="aria"` |
| 仅看可交互元素 | `snapshotFormat="ai", interactive=true` |
| 带标注截图 | `snapshotFormat="ai", labels=true` |
| 指定区域 | `snapshotFormat="ai", selector="<CSS选择器>"` |

## targetId 保持

snapshot 返回的 `targetId` 标识当前标签页。后续 act 操作应传入同一个 `targetId` 以确保操作在同一标签页上执行：

```
# snapshot 返回 targetId: "ABC123"
browser(action="act", profile="openclaw", request={kind: "click", ref: "e5", targetId: "ABC123"})
```
