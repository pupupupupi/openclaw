# 萝卜投研页面路由参考

## 核心页面

| 功能 | URL | 说明 |
|------|-----|------|
| 首页 | `https://r.datayes.com` | 市场概览、热门资讯 |
| 登录 | `https://r.datayes.com/auth/login` | 手机号+密码登录 |
| 个股详情 | `https://r.datayes.com/stock/{code}` | 个股全景分析 |
| 基金详情 | `https://r.datayes.com/mof/app/fund/detail/{fundId}` | 基金详情页（fundId 如 `MUTUAL-10011892`，需 API 查询） |
| 研报中心 | `https://r.datayes.com/fastreport` | 券商研报列表 |
| 资讯 | `https://r.datayes.com/intelligent_feed` | 资讯动态 |
| 数据 | `https://r.datayes.com/data/economy_database` | 宏观经济数据库 |
| 基金 | `https://r.datayes.com/mof/app/fund/product/filter/public` | 公募基金筛选 |
| 组合 | `https://r.datayes.com/mof/portfolio/overview` | 投资组合概览 |
| 市场概况 | `https://r.datayes.com/market/quotation` | 大盘走势、板块热度 |
| 搜索 | `https://r.datayes.com/search?query={关键词}` | 站内搜索 |

## 个股详情页子模块

个股页 `https://r.datayes.com/stock/{code}` 通常包含以下 tab/区域（具体以 snapshot 为准）：

- 概览 — 实时行情、核心指标
- 财务 — 三大报表、财务指标趋势
- 估值 — PE/PB/PS 历史分位
- 研报 — 该股相关券商研报
- 资金 — 主力资金、北向资金
- 公告 — 公司公告列表
- 新闻 — 相关新闻资讯

## 常用股票代码示例

| 股票 | 代码 | 市场 |
|------|------|------|
| 贵州茅台 | 600519 | 沪市主板 |
| 平安银行 | 000001 | 深市主板 |
| 宁德时代 | 300750 | 创业板 |
| 中芯国际 | 688981 | 科创板 |
| 比亚迪 | 002594 | 深市主板 |
| 招商银行 | 600036 | 沪市主板 |
| 中国平安 | 601318 | 沪市主板 |
| 腾讯控股 | 00700 | 港股（如支持） |

## 搜索功能

站内搜索有多种方式：

1. 直接 URL 导航（最可靠）：`https://r.datayes.com/search?query=关键词`
2. 点击首页 "AI搜索" 按钮进入搜索模式
3. 在搜索框中输入后按 Enter

搜索支持：
- 股票代码搜索（如 `600519`）
- 股票名称搜索（如 `茅台`）
- 拼音首字母搜索（如 `gzmt`）
- 关键词搜索（如 `新能源`）

搜索后会出现下拉建议列表或搜索结果页，点击即可跳转到对应页面。

注意：首页搜索框可能需要先点击 "AI搜索" 按钮激活，直接在 textbox 中 type 可能超时。
