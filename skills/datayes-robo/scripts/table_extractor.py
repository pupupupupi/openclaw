#!/usr/bin/env python3
"""
萝卜投研 表格数据结构化提取模块

从 browser snapshot 解析后的元素列表中识别 table 结构，
提取表头和行数据，返回结构化的表格列表。
"""

from typing import Optional


def _get_text(elem: dict) -> str:
    raw: str = (elem.get('name', '') or elem.get('extra_text', '')).strip()
    return raw.strip('"')


def extract_tables(elements: list[dict]) -> list[dict]:
    """从元素列表中提取所有表格的结构化数据。

    返回格式:
    [
        {
            "title": "主营构成",
            "headers": ["主营业务", "主营收入(万元)", "收入比例", ...],
            "rows": [
                ["资产管理", "270,258.24", "47.76%", ...],
                ...
            ]
        }
    ]
    """
    tables: list[dict] = []
    i: int = 0
    total: int = len(elements)

    while i < total:
        elem: dict = elements[i]
        if elem.get('role') != 'table':
            i += 1
            continue

        table_depth: int = elem.get('depth', 0)
        title: str = _find_table_title(elements, i)
        headers: list[str] = []
        rows: list[list[str]] = []
        current_row: Optional[list[str]] = None
        in_header: bool = False

        j: int = i + 1
        while j < total:
            child: dict = elements[j]
            child_depth: int = child.get('depth', 0)
            if child_depth <= table_depth:
                break
            role: str = child.get('role', '')
            text: str = _get_text(child)

            if role == 'rowgroup':
                if not headers:
                    in_header = True
                else:
                    in_header = False
                j += 1
                continue

            if role == 'row':
                current_row = []
                if in_header and not headers:
                    pass
                j += 1
                continue

            if role == 'columnheader' and text:
                headers.append(text)
                j += 1
                continue

            if role == 'cell' and text and current_row is not None:
                current_row.append(text)
                next_is_cell: bool = (
                    j + 1 < total
                    and elements[j + 1].get('role') == 'cell'
                    and elements[j + 1].get('depth', 0) > table_depth
                )
                next_is_row: bool = (
                    j + 1 < total
                    and elements[j + 1].get('role') == 'row'
                )
                next_is_out: bool = (
                    j + 1 >= total
                    or elements[j + 1].get('depth', 0) <= table_depth
                )
                if not next_is_cell:
                    if current_row:
                        if not in_header:
                            rows.append(current_row)
                        elif not headers:
                            headers = current_row
                    current_row = []
                j += 1
                continue

            j += 1

        if headers or rows:
            table_data: dict = {'title': title, 'headers': headers, 'rows': rows}
            tables.append(table_data)

        i = j

    return tables


def _find_table_title(elements: list[dict], table_index: int) -> str:
    """向前搜索表格标题"""
    for k in range(table_index - 1, max(table_index - 10, -1), -1):
        elem: dict = elements[k]
        role: str = elem.get('role', '')
        text: str = _get_text(elem)
        if not text:
            continue
        if role in ('heading', 'generic') and len(text) >= 2 and len(text) <= 30:
            if elem.get('role') == 'table':
                break
            return text
    return ''
