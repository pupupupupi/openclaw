#!/usr/bin/env python3
"""
萝卜投研 表格数据结构化提取模块

从 browser snapshot 解析后的元素列表中识别 table 结构，
提取表头和行数据，返回结构化的表格列表。
"""

import re
from typing import Optional

FINANCE_TABLE_SKIP = re.compile(r'^(关闭行|每股指标|盈利能力|偿债能力|成长能力|营运能力|现金流量)$')
MAX_COLS_FOR_PIVOT = 20


def _get_text(elem: dict) -> str:
    raw: str = (elem.get('name', '') or elem.get('extra_text', '')).strip()
    return raw.strip('"')


def _collect_table_children(
    elements: list[dict], start: int, table_depth: int,
) -> list[dict]:
    result: list[dict] = []
    j: int = start
    total: int = len(elements)
    while j < total:
        child: dict = elements[j]
        if child.get('depth', 0) <= table_depth:
            break
        result.append(child)
        j += 1
    return result


def _parse_table_rows(
    children: list[dict], table_depth: int,
) -> tuple[list[str], list[list[str]]]:
    headers: list[str] = []
    rows: list[list[str]] = []
    current_row: Optional[list[str]] = None
    in_header: bool = False

    for child in children:
        role: str = child.get('role', '')
        text: str = _get_text(child)

        if role == 'rowgroup':
            if not headers:
                in_header = True
            else:
                in_header = False
            continue

        if role == 'row':
            if current_row is not None and current_row:
                if in_header and not headers:
                    headers = current_row
                elif not in_header:
                    rows.append(current_row)
            current_row = []
            continue

        if role == 'columnheader':
            if text:
                headers.append(text)
            continue

        if role == 'cell':
            if current_row is not None:
                current_row.append(text)
            continue

    if current_row is not None and current_row:
        if in_header and not headers:
            headers = current_row
        elif not in_header:
            rows.append(current_row)

    return headers, rows


def _is_finance_indicator_table(headers: list[str]) -> bool:
    period_count: int = sum(
        1 for h in headers
        if re.match(r'^\d{4}(年报|[一二三]季报|半年报)$', h)
    )
    return period_count >= 4


def _pivot_finance_table(
    headers: list[str], rows: list[list[str]],
) -> tuple[list[str], list[list[str]]]:
    col_count: int = len(headers)
    clean_rows: list[list[str]] = []

    for row in rows:
        cells: list[str] = [c for c in row if c]
        if not cells:
            continue

        first: str = cells[0].strip()
        if FINANCE_TABLE_SKIP.match(first):
            continue
        if first.startswith('关闭行'):
            continue

        if len(cells) == 1:
            continue

        label: str = cells[0]
        values: list[str] = cells[1:]

        if len(values) > col_count:
            values = values[:col_count]

        padded: list[str] = values + [''] * (col_count - len(values))
        clean_rows.append([label] + padded)

    pivot_headers: list[str] = ['指标'] + headers
    return pivot_headers, clean_rows


def extract_tables(elements: list[dict]) -> list[dict]:
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
        children: list[dict] = _collect_table_children(elements, i + 1, table_depth)
        headers, rows = _parse_table_rows(children, table_depth)

        if headers or rows:
            if _is_finance_indicator_table(headers):
                headers, rows = _pivot_finance_table(headers, rows)

            if headers or rows:
                tables.append({'title': title, 'headers': headers, 'rows': rows})

        i += 1 + len(children)

    return tables


def _find_table_title(elements: list[dict], table_index: int) -> str:
    for k in range(table_index - 1, max(table_index - 10, -1), -1):
        elem: dict = elements[k]
        role: str = elem.get('role', '')
        text: str = _get_text(elem)
        if not text:
            continue
        if role in ('heading', 'generic') and 2 <= len(text) <= 30:
            if elem.get('role') == 'table':
                break
            return text
    return ''
