#!/usr/bin/env python3
"""
萝卜投研 SVG 图表数据提取模块

从 browser snapshot 解析后的元素列表中识别图表区域，
提取年份-数值配对的结构化数据，并处理 SVG 渲染导致的重复值。
"""

import re
from typing import Optional

YEAR_PATTERN = re.compile(r'^"?(\d{4})"?$')
QUARTER_PATTERN = re.compile(r'^"?(\d{4}Q\d(?:-Q\d)?)"?$')

AXIS_TICK_PATTERN = re.compile(r'^"?-?\d+(\.\d+)?[亿万%]?"?$')

CHART_TITLE_KEYWORDS = [
    '营业收入', '净利润', '扣非净利润', '毛利率', '收入结构',
    'ROE', 'ROA', '资产负债率', '现金流', '股息率',
    'PE', 'PB', 'EPS', '市盈率', '市净率',
]


def dedup_svg_text(text: str) -> str:
    """去除 SVG 图表渲染产生的重复文本（如 '183.31183.31' → '183.31'）"""
    if not text or len(text) < 6:
        return text
    cleaned: str = text.strip().strip('"')
    if not cleaned or len(cleaned) < 6:
        return text
    length: int = len(cleaned)
    if length % 2 != 0:
        return text
    half: int = length // 2
    if half < 3:
        return text
    if cleaned[:half] == cleaned[half:]:
        return cleaned[:half]
    return text


def _is_year_label(text: str) -> bool:
    """判断文本是否为年份标签（如 '2017'、'2025Q1-Q3'）"""
    cleaned: str = text.strip().strip('"')
    if YEAR_PATTERN.match(cleaned):
        return True
    if QUARTER_PATTERN.match(cleaned):
        return True
    if re.match(r'^\d{4}Q\d-Q\d$', cleaned):
        return True
    return False


def _is_axis_tick(text: str) -> bool:
    """判断文本是否为坐标轴刻度（如 '0亿'、'100亿'、'-40%'）"""
    cleaned: str = text.strip().strip('"')
    if re.match(r'^-?\d+[亿万]$', cleaned):
        return True
    return False


def _is_axis_pct_tick(text: str) -> bool:
    """判断文本是否为百分比坐标轴刻度（如 '-40%'、'0%'、'200%'）"""
    cleaned: str = text.strip().strip('"')
    if re.match(r'^-?\d+%$', cleaned) and float(cleaned.rstrip('%')) % 10 == 0:
        return True
    return False


def _is_data_value(text: str) -> bool:
    """判断文本是否为数据值（数字、百分比、带负号的数字）"""
    cleaned: str = dedup_svg_text(text).strip().strip('"')
    if not cleaned:
        return False
    if re.match(r'^-?\d+(\.\d+)?%?$', cleaned):
        return True
    return False


def _find_chart_title(elements: list[dict], img_index: int) -> str:
    """向前搜索图表标题（在 img 元素之前的 generic/heading 中查找）"""
    for i in range(img_index - 1, max(img_index - 30, -1), -1):
        elem: dict = elements[i]
        name: str = elem.get('name', '') or elem.get('extra_text', '')
        if not name:
            continue
        for keyword in CHART_TITLE_KEYWORDS:
            if keyword in name:
                return name
    return ''


def _find_chart_summary(elements: list[dict], img_index: int) -> str:
    """向后搜索图表摘要文本（在 img 元素之后的 generic 中查找）"""
    for i in range(img_index + 1, min(img_index + 50, len(elements))):
        elem: dict = elements[i]
        if elem.get('role') == 'img':
            break
        name: str = elem.get('name', '') or elem.get('extra_text', '')
        if not name or len(name) < 10:
            continue
        if '的' in name and ('亿' in name or '%' in name):
            return name
    return ''


def _extract_child_groups(elements: list[dict], parent_index: int) -> list[list[dict]]:
    """提取 img 元素下的直接子 generic 分组"""
    parent_depth: int = elements[parent_index].get('depth', 0)
    child_depth: int = parent_depth + 1
    groups: list[list[dict]] = []
    current_group: Optional[list[dict]] = None

    for i in range(parent_index + 1, len(elements)):
        elem: dict = elements[i]
        depth: int = elem.get('depth', 0)
        if depth <= parent_depth:
            break
        if depth == child_depth and elem.get('role') == 'generic':
            current_group = []
            groups.append(current_group)
            continue
        if current_group is not None and depth > child_depth:
            current_group.append(elem)

    return groups


def _classify_group(items: list[dict]) -> str:
    """分类一个子分组的类型：years / values / axis_ticks / unknown"""
    if not items:
        return 'unknown'
    texts: list[str] = []
    for item in items:
        name: str = (item.get('name', '') or item.get('extra_text', '')).strip()
        if name:
            texts.append(name)
    if not texts:
        return 'unknown'
    year_count: int = sum(1 for t in texts if _is_year_label(t))
    if year_count >= len(texts) * 0.7:
        return 'years'
    axis_count: int = sum(1 for t in texts if _is_axis_tick(t))
    if axis_count >= len(texts) * 0.7:
        return 'axis_ticks'
    pct_axis_count: int = sum(1 for t in texts if _is_axis_pct_tick(t))
    if pct_axis_count >= len(texts) * 0.7:
        return 'axis_ticks'
    if len(texts) <= 6 and pct_axis_count == len(texts):
        return 'axis_ticks'
    value_count: int = sum(1 for t in texts if _is_data_value(t))
    if value_count >= len(texts) * 0.7:
        return 'values'
    return 'unknown'


def _extract_texts(items: list[dict]) -> list[str]:
    """从元素列表中提取文本，对数据值做去重"""
    result: list[str] = []
    for item in items:
        raw: str = (item.get('name', '') or item.get('extra_text', '')).strip()
        if raw:
            result.append(dedup_svg_text(raw).strip('"'))
    return result


def _parse_single_chart(
    elements: list[dict],
    img_index: int,
) -> Optional[dict]:
    """解析单个图表（一个 img 元素及其子元素）"""
    groups: list[list[dict]] = _extract_child_groups(elements, img_index)
    if len(groups) < 2:
        return None

    classified: list[tuple[str, list[str]]] = []
    for group in groups:
        group_type: str = _classify_group(group)
        texts: list[str] = _extract_texts(group)
        classified.append((group_type, texts))

    year_groups: list[list[str]] = [t for typ, t in classified if typ == 'years']
    value_groups: list[list[str]] = [t for typ, t in classified if typ == 'values']

    if not year_groups or not value_groups:
        return None

    years: list[str] = year_groups[0]
    title: str = _find_chart_title(elements, img_index)
    summary_text: str = _find_chart_summary(elements, img_index)

    chart: dict = {
        'title': title,
        'years': years,
        'series': [],
    }

    for values in value_groups:
        if len(values) == len(years):
            paired: dict = {}
            for j in range(len(years)):
                paired[years[j]] = values[j]
            chart['series'].append(paired)

    if summary_text:
        chart['summary'] = summary_text

    if not chart['series']:
        return None

    return chart


def extract_chart_data(elements: list[dict]) -> list[dict]:
    """从元素列表中提取所有图表的结构化数据"""
    charts: list[dict] = []
    seen_keys: set = set()

    for i, elem in enumerate(elements):
        if elem.get('role') != 'img':
            continue
        chart: Optional[dict] = _parse_single_chart(elements, i)
        if chart is None:
            continue
        years_key: str = ','.join(chart.get('years', []))
        first_series_key: str = ''
        if chart.get('series'):
            first_vals: list[str] = list(chart['series'][0].values())
            first_series_key = ','.join(first_vals[:3])
        dedup_key: str = years_key + '|' + first_series_key
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)
        charts.append(chart)

    return charts
