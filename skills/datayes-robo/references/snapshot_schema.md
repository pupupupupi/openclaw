# Snapshot 数据清洗 Schema

## 概述

`scripts/clean_snapshot.py` 将 browser snapshot 原始文本清洗为两份 JSON：

- `summary.json` — 精简摘要，给对话展示（通常 2-5K 字符）
- `elements.json` — 操作索引，给浏览器操作定位

## summary.json 结构

```json
{
  "page_url": "https://r.datayes.com",
  "page_type": "home | stock_detail | login | search | report_list | news_feed | data | fund | unknown",
  "login_status": "logged_in | not_logged_in | unknown",
  "truncated": false,
  "navigation": ["首页", "自选", "研报", "资讯", "数据", "股票", "基金", "组合", "更多"],
  "search": {
    "ai_search_ref": "e9",
    "input_ref": "e65",
    "placeholder": "亿联网络"
  },
  "hot_keywords": ["国九条", "中国中免", "黄金"],
  "features": ["指标库", "个股分析", "行业分析"],
  "news": [
    {
      "title": "春节要闻：最热出行；外盘大涨...",
      "url": "/details/robo-news/1475458982826004480"
    }
  ],
  "reports": [
    {
      "title": "比亚迪（002594）：2026年1月销量点评...",
      "url": "/details/report/8395161"
    }
  ],
  "sections": [
    {
      "name": "营业收入",
      "items": [
        {"text": "11574.39亿元", "role": "generic", "ref": "e340"},
        {"text": "-8.20%", "role": "generic", "ref": "e341"}
      ],
      "states": ["selected"]
    }
  ],
  "stock_code": "601390",
  "stock_info": {
    "stock_name_code": "中国中铁601390.SH",
    "price": "5.50",
    "change_pct": "-2.31%"
  },
  "key_data": {
    "最新": "5.50",
    "涨幅": "-2.31%",
    "今开": "5.56",
    "最高": "5.58",
    "最低": "5.48",
    "总值": "1357.74亿",
    "换手": "1.31%",
    "主力净流入": "-2.75亿"
  },
  "menu_structure": [
    {
      "group": "实时行情",
      "items": [
        {"text": "实时行情", "ref": "e117"}
      ]
    }
  ],
  "tables": [
    {
      "title": "主营构成：",
      "headers": ["主营业务", "主营收入(万元)", "收入比例", "主营成本(万元)", "成本占比"],
      "rows": [
        ["资产管理", "270,258.24", "47.76%", "284,784.62", "55.84%"],
        ["经纪业务", "203,150.25", "35.90%", "156,782.82", "30.74%"]
      ]
    }
  ]
}
```

### page_type 判断逻辑

| 类型 | URL 特征 |
|------|----------|
| `home` | `r.datayes.com` 根路径 |
| `stock_detail` | `/stock/{code}` |
| `login` | `/auth/login` |
| `search` | `/search` |
| `report_list` | `/fastreport` |
| `news_feed` | `/intelligent_feed` |
| `data` | `/data/` |
| `fund` | `/mof/` |
| `unknown` | 其他 |

### login_status 判断逻辑

| 状态 | 判断依据 |
|------|----------|
| `logged_in` | 有 img "avatar"，或有用户菜单项（修改密码/个人中心），或能正常浏览完整页面（有导航栏+业务内容） |
| `not_logged_in` | 有 tab "密码登录" / button "登 录"（登录页面） |
| `unknown` | 以上条件均不满足 |

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `page_url` | string | 当前页面 URL |
| `page_type` | string | 页面类型 |
| `login_status` | string | 登录状态判断 |
| `truncated` | bool | snapshot 是否被截断 |
| `navigation` | string[] | 顶部导航栏项目（仅 `<navigation>` 标签内的子元素） |
| `search` | object? | 搜索框信息 |
| `features` | string[]? | 功能入口 |
| `hot_keywords` | string[] | 搜索热词（最多15个） |
| `news` | object[]? | 资讯列表（最多30条） |
| `reports` | object[]? | 研报列表（最多30条） |
| `sections` | object[]? | 页面分区（最多20个，每分区最多15项） |
| `stock_code` | string? | 股票代码（仅 stock_detail 页） |
| `stock_info` | object? | 股票行情摘要（仅 stock_detail 页） |
| `key_data` | object? | 关键行情数据标签-值配对 dict（仅 stock_detail 页） |
| `chart_data` | object[]? | 图表结构化数据，年份-数值配对（仅 stock_detail 页，含营收/净利润/毛利率等） |
| `tables` | object[]? | 表格结构化数据，含表头和行数据（仅 stock_detail 页，含主营构成/股东/董事会等） |
| `menu_structure` | object[]? | 左侧菜单结构（仅 stock_detail 页） |

### key_data 结构（仅个股页）

标签-值配对的 dict，从页面行情区域提取已知标签（最新/均价/涨跌/今开/涨幅/最高/总手/最低/金额/量比/涨停/跌停/换手/净资产/总股本/总值/流通股/流值/委比/委差/主力流入/主力流出/主力净流入等）：

```json
{
  "最新": "5.50",
  "涨幅": "-2.31%",
  "今开": "5.56",
  "总值": "1357.74亿",
  "换手": "1.31%",
  "主力净流入": "-2.75亿"
}
```

### chart_data 结构（仅个股页）

从 SVG 图表中提取的结构化财务数据，年份与数值已正确配对。SVG 渲染产生的重复值（如 `183.31183.31`）已自动去重。每个图表包含 title、years 轴、多条 series（年份→数值 dict）和可选的 summary：

```json
{
  "title": "营业收入",
  "years": ["2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025Q1-Q3"],
  "series": [
    {"2017": "183.31", "2018": "198.28", "2019": "211.78", "2020": "163.49", "2024": "270.90", "2025Q1-Q3": "212.34"},
    {"2017": "6.08%", "2018": "8.16%", "2019": "6.81%", "2020": "-22.80%", "2024": "3.42%", "2025Q1-Q3": "6.01%"}
  ],
  "summary": "2025Q1-Q3的营收为212.34亿，同比增长6.01%"
}
```

### tables 结构（仅个股页）

从页面 table 元素中提取的结构化表格数据，包含表头（columnheader）和行数据（cell）。适用于公司信息页的主营构成、十大股东、董事会等表格：

```json
{
  "title": "主营构成：",
  "headers": ["主营业务", "主营收入(万元)", "收入比例", "主营成本(万元)", "成本占比"],
  "rows": [
    ["资产管理", "270,258.24", "47.76%", "284,784.62", "55.84%"],
    ["经纪业务", "203,150.25", "35.90%", "156,782.82", "30.74%"]
  ]
}
```

### sections 分区结构

以 `heading` 或 `tab` 为分区起点，收集后续有文本的子节点（每分区最多 15 项）。过滤图表数据点（纯数字/百分比/坐标轴刻度）、表格内元素、unicode 图标字符和装饰性文本，避免与 `chart_data`/`tables` 字段冗余：

```json
{
  "name": "营业收入",
  "items": [
    {"text": "11574.39亿元", "role": "generic", "ref": "e340"},
    {"text": "-8.20%", "role": "generic", "ref": "e341"}
  ],
  "states": ["selected"]
}
```

## elements.json 结构

```json
{
  "snapshot_id": "1a2e22ae8ccaae3d",
  "timestamp": "2026-02-23T19:14:00+00:00",
  "page_url": "https://r.datayes.com",
  "element_counts": {
    "links": 57,
    "buttons": 3,
    "inputs": 2,
    "tabs": 0,
    "images": 5,
    "checkboxes": 0,
    "other": 0
  },
  "elements": {
    "links": [
      {"ref": "e147", "text": "头条 春节要闻...", "url": "/details/robo-news/..."}
    ],
    "buttons": [
      {"ref": "e58", "text": "查看更多"}
    ],
    "inputs": [
      {"ref": "e65", "text": "亿联网络", "input_type": "textbox"}
    ],
    "tabs": [
      {"ref": "e50", "text": "密码登录", "states": ["selected"]}
    ],
    "images": [
      {"ref": "e53", "text": "avatar", "cursor": "pointer"}
    ],
    "checkboxes": [
      {"ref": "e87", "text": "自动登录", "input_type": "checkbox", "states": ["checked"]}
    ]
  }
}
```

## 使用方式

### snapshot tool 返回格式

snapshot tool 返回截断后的页面内容（accessibility tree）+ 完整文件路径：

```
SECURITY NOTICE: ...
<<<EXTERNAL_UNTRUSTED_CONTENT ...>>>
Source: Browser
---
generic [active] [ref=e1]:
  ...（截断后的页面内容）...
<<<END_EXTERNAL_UNTRUSTED_CONTENT ...>>>
Full snapshot saved to: /tmp/snapshot_<uuid>/snapshot_raw.txt (15234 chars)
Note: content above is truncated to 12000 chars. Read the file for full content.
```

### 命令行（推荐 --summary-only）

```bash
# 摘要直接输出到 stdout（推荐）
python3 scripts/clean_snapshot.py /tmp/snapshot_<uuid>/snapshot_raw.txt --summary-only --page-url "https://r.datayes.com"

# 操作索引直接输出到 stdout
python3 scripts/clean_snapshot.py /tmp/snapshot_<uuid>/snapshot_raw.txt --elements-only

# 写文件模式（需要反复查阅时）
python3 scripts/clean_snapshot.py /tmp/snapshot_<uuid>/snapshot_raw.txt --page-url "https://r.datayes.com"
```

不指定 `-o` 时自动生成唯一输出目录 `/tmp/datayes_cleaned_<uuid>/`。

### 作为模块导入

```python
from clean_snapshot import clean_snapshot

summary, elements = clean_snapshot(raw_text, page_url="https://r.datayes.com")
```

## 重要提醒

- `ref` 是一次性的，每次 snapshot 后旧 ref 失效
- `elements.json` 仅对应当次 snapshot，不可跨 snapshot 使用
- 个股页的 `stock_info` 提供快速行情摘要，`key_data` 提供完整行情标签-值配对，`menu_structure` 提供左侧导航结构
- summary 体积通常在 2-5K 字符，适合直接进入对话上下文
