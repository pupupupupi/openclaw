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

# 2. 先检查登录状态（导航到首页）
browser(action="navigate", targetUrl="https://r.datayes.com", profile="openclaw")
browser(action="act", profile="openclaw", request={kind: "wait", loadState: "domcontentloaded"})
browser(action="act", profile="openclaw", request={kind: "wait", timeMs: 3000})
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
# → snapshot 返回文件路径（不返回原文），如: /tmp/snapshot_<uuid>/snapshot_raw.txt
# → 用返回的路径执行数据清洗: python3 scripts/clean_snapshot.py <路径> --page-url "..."
# → 检查清洗后 summary.json 的 login_status
# → 如果能看到导航栏+资讯列表等完整内容 → 已登录，跳过登录
# → 如果看到登录表单（tab "密码登录"、button "登 录"）→ 未登录

# 3. 导航到登录页（仅未登录时）
browser(action="navigate", targetUrl="https://r.datayes.com/auth/login", profile="openclaw")

# 4. 等待页面加载（禁止 networkidle，萝卜投研持续有网络请求会超时）
browser(action="act", profile="openclaw", request={kind: "wait", loadState: "domcontentloaded"})
browser(action="act", profile="openclaw", request={kind: "wait", timeMs: 2000})

# 5. 获取 AI 快照定位表单元素
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
# → snapshot 返回文件路径，用清洗脚本处理后从 elements.json 中找到：
#   - tab "密码登录" ref
#   - textbox "手机号码/邮箱/账号" ref
#   - 密码输入框 ref
#   - button "登 录" ref

# 6. 如需切换到密码登录模式
browser(action="act", profile="openclaw", request={kind: "click", ref: "<tab_ref>"})

# 7. 输入手机号（PHONE 来自环境变量或用户输入）
browser(action="act", profile="openclaw", request={kind: "type", ref: "<phone_ref>", text: PHONE})

# 8. 输入密码（PASSWORD 来自环境变量或用户输入）
browser(action="act", profile="openclaw", request={kind: "type", ref: "<password_ref>", text: PASSWORD})

# 9. 点击登录
browser(action="act", profile="openclaw", request={kind: "click", ref: "<login_btn_ref>"})

# 10. 等待跳转
browser(action="act", profile="openclaw", request={kind: "wait", loadState: "domcontentloaded"})
browser(action="act", profile="openclaw", request={kind: "wait", timeMs: 3000})

# 11. 验证登录结果
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
# → 用返回的文件路径执行数据清洗，检查 login_status == "logged_in"
# → 能看到导航栏+资讯列表 → 登录成功
# → 仍有 tab "密码登录" → 登录失败，检查是否有验证码
# → 出现验证码 → 截图告知用户手动处理
```

## 数据提取工作流

```
# 1. 获取股票代码（如不知道，用 akshare skill 查询）
# python3 -c "import akshare as ak; df = ak.stock_info_a_code_name(); print(df[df['name'].str.contains('中国中铁')])"

# 2. 导航到个股详情页
browser(action="navigate", targetUrl="https://r.datayes.com/stock/601390", profile="openclaw")

# 3. 等待数据渲染（个股页图表数据加载较慢，需要更长等待）
browser(action="act", profile="openclaw", request={kind: "wait", loadState: "domcontentloaded"})
browser(action="act", profile="openclaw", request={kind: "wait", timeMs: 5000})

# 4. 获取快照提取数据（使用默认模式，不用 efficient）
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")
# → snapshot 返回文件路径，用清洗脚本处理

# 5. 如果 snapshot 只拿到左侧菜单，点击具体子模块查看数据
browser(action="act", profile="openclaw", request={kind: "click", ref: "<关键数据概览link的ref>"})
browser(action="act", profile="openclaw", request={kind: "wait", timeMs: 5000})
browser(action="snapshot", snapshotFormat="ai", profile="openclaw")

# 6. 如需查看更多 tab（如"财务"）
browser(action="act", profile="openclaw", request={kind: "click", ref: "<财务tab_ref>"})
browser(action="act", profile="openclaw", request={kind: "wait", timeMs: 3000})
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
| 常规页面分析（默认） | `snapshotFormat="ai"` |
| 需要精确 ref | `snapshotFormat="ai", refs="aria"` |
| 仅看可交互元素 | `snapshotFormat="ai", interactive=true` |
| 带标注截图 | `snapshotFormat="ai", labels=true` |
| 指定区域 | `snapshotFormat="ai", selector="<CSS选择器>"` |
| 页面过大被截断时 | `snapshotFormat="ai", mode="efficient"` (限制可通过 `OPENCLAW_SNAPSHOT_EFFICIENT_MAX_CHARS` 配置) |

## targetId 保持

snapshot 返回的 details 中包含 `targetId`，标识当前标签页。后续 act 操作应传入同一个 `targetId` 以确保操作在同一标签页上执行：

```
# snapshot details 中 targetId: "ABC123"
browser(action="act", profile="openclaw", request={kind: "click", ref: "e5", targetId: "ABC123"})
```
