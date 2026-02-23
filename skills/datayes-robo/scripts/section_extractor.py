#!/usr/bin/env python3
"""
萝卜投研 页面分区提取模块

从 browser snapshot 解析后的元素列表中提取页面分区结构，
过滤图表数据点和表格内元素以避免冗余。
"""

import re
from typing import Optional


UNICODE_ICON_PATTERN = re.compile(r'^[\ue000-\uf8ff]+$')
SKIP_CONTENT_PATTERNS = {'数据来源：Datayes!', '数据来源：Datayes'}


def _is_chart_data_point(text: str) -> bool:
    """判断文本是否为图表数据点（纯数字/百分比/坐标轴刻度）"""
    cleaned: str = text.strip().strip('"')
    if not cleaned:
        return False
    if re.match(r'^-?\d+(\.\d+)?$', cleaned):
        return True
    if re.match(r'^-?\d+(\.\d+)?%$', cleaned):
        return True
    if re.match(r'^-?\d+(\.\d+)?[亿万]$', cleaned):
        return True
    return False


def _is_decorative_text(text: str) -> bool:
    """判断文本是否为装饰性内容（unicode 图标、数据来源声明等）"""
    cleaned: str = text.strip()
    if UNICODE_ICON_PATTERN.match(cleaned):
        return True
    if cleaned in SKIP_CONTENT_PATTERNS:
        return True
    return False


def _build_table_scope(elements: list[dict]) -> set[int]:
    """返回所有属于 table 子树的元素索引集合"""
    scope: set[int] = set()
    table_depth: int = -1
    for i, elem in enumerate(elements):
        if elem.get('role') == 'table':
            table_depth = elem.get('depth', 0)
            scope.add(i)
            continue
        if table_depth >= 0:
            if elem.get('depth', 0) > table_depth:
                scope.add(i)
            else:
                table_depth = -1
    return scope


def extract_sections_full(elements: list[dict]) -> list[dict]:
    """提取页面分区（heading/tab 为分区起点，每个分区最多 15 个有效 item）。
    过滤图表数据点和表格内元素，避免与 chart_data/tables 字段冗余。
    """
    SKIP_TEXTS = {'', 'icon', 'caret-right', 'caret-down', 'caret-up', 'search', 'Hot', 'logo'}
    SKIP_ROLES = {'columnheader', 'cell', 'row', 'rowgroup', 'table', 'img'}
    MAX_ITEMS_PER_SECTION = 15
    sections: list[dict] = []
    table_indices: set[int] = _build_table_scope(elements)

    try:
        current_section: Optional[dict] = None

        for idx, elem in enumerate(elements):
            try:
                role = elem.get('role', '')
                name = elem.get('name', '') or elem.get('extra_text', '')

                if role == 'heading' and name:
                    current_section = {'name': name, 'items': []}
                    sections.append(current_section)
                    continue

                if role == 'tab' and name:
                    current_section = {'name': name, 'items': []}
                    if elem.get('states'):
                        current_section['states'] = elem['states']
                    sections.append(current_section)
                    continue

                if current_section is None:
                    continue
                if not name or name.strip('"') in SKIP_TEXTS:
                    continue
                if len(current_section['items']) >= MAX_ITEMS_PER_SECTION:
                    continue
                if role in SKIP_ROLES:
                    continue
                if idx in table_indices:
                    continue
                if _is_chart_data_point(name):
                    continue
                if _is_decorative_text(name):
                    continue

                item: dict = {'text': name, 'role': role}
                if elem.get('url'):
                    item['url'] = elem['url']
                if elem.get('ref'):
                    item['ref'] = elem['ref']
                if elem.get('states'):
                    item['states'] = elem['states']
                current_section['items'].append(item)
            except Exception:
                continue
    except Exception:
        pass
    return [s for s in sections if s.get('items')]



def extract_navigation(elements: list[dict]) -> list[str]:
    """提取导航栏项目（仅 <navigation> 标签的直接子元素）"""
    nav_items: list[str] = []
    try:
        in_nav = False
        nav_depth = -1
        for elem in elements:
            try:
                if elem.get('role') == 'navigation':
                    in_nav = True
                    nav_depth = elem.get('depth', 0)
                    continue
                if in_nav:
                    if elem.get('depth', 0) <= nav_depth:
                        in_nav = False
                        continue
                    if elem.get('role') in ('link', 'generic', 'listitem') and elem.get('name'):
                        nav_items.append(elem['name'])
            except Exception:
                continue
        if not nav_items:
            for elem in elements[:20]:
                try:
                    if elem.get('role') == 'link' and elem.get('name') in ('首页', '研报', '资讯', '数据'):
                        nav_items.append(elem['name'])
                except Exception:
                    continue
    except Exception:
        pass
    return nav_items
