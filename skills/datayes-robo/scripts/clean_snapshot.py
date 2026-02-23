#!/usr/bin/env python3
"""
萝卜投研 Browser Snapshot 数据清洗工具

将 browser snapshot 原始文本清洗为两份结构化 JSON：
1. summary.json  — 精简摘要，给对话展示用
2. elements.json — 操作索引，给后续浏览器操作定位用
"""

import json
import re
import sys
import os
from datetime import datetime, timezone
from typing import Optional

from chart_extractor import dedup_svg_text, extract_chart_data
from table_extractor import extract_tables
from section_extractor import extract_sections_full, extract_navigation


LINE_PATTERN = re.compile(
    r'^(?P<indent>\s*)'
    r'(?:-\s+)?'
    r'(?P<role>[a-zA-Z][a-zA-Z0-9]*)'
    r'(?:\s+"(?P<name>[^"]*)")?'
    r'(?P<attrs>(?:\s+\[.*?\])*)'
    r'(?P<colon>:?)'
)

EFFICIENT_LINE_PATTERN = re.compile(
    r'^(?:-\s+)?'
    r'(?P<role>[a-zA-Z][a-zA-Z0-9]*)'
    r'\s+"(?P<name>[^"]*)"'
    r'(?P<attrs>(?:\s+\[.*?\])*)'
)

REF_PATTERN = re.compile(r'\[ref=(?P<ref>[ef]\d+)\]')
CURSOR_PATTERN = re.compile(r'\[cursor=(?P<cursor>\w+)\]')
URL_PATTERN = re.compile(r'^\s*(?:-\s+)?/url:\s*(?P<url>.+)$')
TEXT_LINE_PATTERN = re.compile(r'^\s*(?:-\s+)?text:\s*(?P<text>.+)$')

STATE_ATTRS = {'active', 'selected', 'checked', 'disabled', 'readonly', 'expanded'}

SKIP_PREFIXES = (
    'SECURITY NOTICE',
    '<<<',
    'Source:',
    'DO NOT',
    '- DO NOT',
    '- Delete',
    '- Execute',
    '- Change',
    '- Reveal',
    '- Send',
    'Respond',
    'This content',
)

INTERACTIVE_ROLES = {
    'link', 'button', 'textbox', 'combobox', 'checkbox', 'radio',
    'tab', 'menuitem', 'option', 'switch', 'slider', 'spinbutton',
    'searchbox', 'menu',
}

CONTENT_ROLES = {
    'heading', 'paragraph', 'text', 'img', 'table', 'cell', 'row',
    'list', 'listitem', 'tooltip', 'alert', 'status', 'banner',
    'navigation', 'tablist', 'tabpanel', 'iframe',
}


def parse_element(line: str) -> Optional[dict]:
    """解析 snapshot 中的一行元素"""
    try:
        m = LINE_PATTERN.match(line)
        if not m:
            m = EFFICIENT_LINE_PATTERN.match(line)
            if not m:
                return None

        indent = len(m.group('indent')) if 'indent' in m.groupdict() else 0
        role = m.group('role')
        name = m.group('name')
        attrs_str = m.group('attrs') or ''
        full_line = line

        ref_m = REF_PATTERN.search(attrs_str) or REF_PATTERN.search(full_line)
        cursor_m = CURSOR_PATTERN.search(attrs_str) or CURSOR_PATTERN.search(full_line)
        states = [s for s in STATE_ATTRS if f'[{s}]' in attrs_str or f'[{s}]' in full_line]

        elem: dict = {
            'role': role,
            'depth': indent // 2,
        }
        if name:
            elem['name'] = dedup_svg_text(name)
        if ref_m:
            elem['ref'] = ref_m.group('ref')
        if cursor_m:
            elem['cursor'] = cursor_m.group('cursor')
        if states:
            elem['states'] = states

        if not name:
            end_pos = m.end()
            trailing = line[end_pos:].strip()
            if trailing:
                elem['name'] = dedup_svg_text(trailing)

        return elem
    except Exception:
        return None


def parse_snapshot(raw: str) -> list[dict]:
    """将原始 snapshot 文本解析为元素列表"""
    try:
        lines = raw.splitlines()
    except Exception:
        return []

    elements: list[dict] = []
    current_elem: Optional[dict] = None

    for line in lines:
        try:
            stripped = line.strip()

            if stripped == '' or stripped == '---':
                continue

            if any(stripped.startswith(p) for p in SKIP_PREFIXES):
                continue

            if 'TRUNCATED' in stripped or '(truncated)' in stripped:
                continue

            url_m = URL_PATTERN.match(line)
            if url_m and current_elem is not None:
                current_elem['url'] = url_m.group('url').strip()
                continue

            text_m = TEXT_LINE_PATTERN.match(line)
            if text_m and current_elem is not None:
                extra_text = text_m.group('text').strip()
                if 'extra_text' not in current_elem:
                    current_elem['extra_text'] = extra_text
                else:
                    current_elem['extra_text'] += ' ' + extra_text
                continue

            elem = parse_element(line)
            if elem:
                current_elem = elem
                elements.append(elem)
        except Exception:
            continue

    return elements


LOGGED_IN_INDICATORS = {'修改密码', '个人中心', '帮助中心', '任务专区'}
LOGIN_PAGE_INDICATORS = {'密码登录', '短信验证码登录', '登 录', '登录Datayes'}
LOGIN_PAGE_LINK_INDICATORS = {'暂无账号，点击申请试用', '忘记密码？'}
NAV_ITEMS = {'首页', '研报', '资讯', '数据', '自选', '股票', '基金', '组合'}


def detect_login_status(elements: list[dict]) -> str:
    try:
        has_avatar = False
        has_logged_in_menu = False
        has_login_form = False
        nav_count = 0
        has_content = False

        for elem in elements:
            try:
                role = elem.get('role', '')
                name = elem.get('name', '')
                extra = elem.get('extra_text', '')
                text = name or extra
                url = elem.get('url', '')

                if role == 'img' and name == 'avatar':
                    has_avatar = True
                if role == 'link' and text in LOGGED_IN_INDICATORS:
                    has_logged_in_menu = True
                if role == 'tab' and text in LOGIN_PAGE_INDICATORS:
                    has_login_form = True
                if role == 'button' and text in LOGIN_PAGE_INDICATORS:
                    has_login_form = True
                if role == 'link' and text in LOGIN_PAGE_LINK_INDICATORS:
                    has_login_form = True
                if role == 'heading' and '登录' in text:
                    has_login_form = True
                if role == 'textbox' and ('手机号' in text or '邮箱' in text or '账号' in text):
                    has_login_form = True
                if role in ('generic', 'link') and text in NAV_ITEMS:
                    nav_count += 1
                if role == 'link' and url and ('/details/' in url or '/search' in url):
                    has_content = True
                if role == 'button' and 'AI搜索' in text:
                    has_content = True
                if role in ('textbox', 'combobox') and text and '手机号' not in text and '密码' not in text:
                    has_content = True
                if role == 'menuitem' and text:
                    has_content = True
            except Exception:
                continue

        if has_avatar or has_logged_in_menu:
            return 'logged_in'
        if has_login_form:
            return 'not_logged_in'
        if nav_count >= 2 and has_content:
            return 'logged_in'
        if nav_count >= 2:
            return 'logged_in'
        return 'unknown'
    except Exception:
        return 'unknown'


def detect_truncated(raw: str) -> bool:
    try:
        return 'TRUNCATED' in raw or '(truncated)' in raw
    except Exception:
        return False


def detect_page_type(page_url: str, elements: list[dict]) -> str:
    """检测页面类型"""
    try:
        if not page_url:
            return 'unknown'
        if '/stock/' in page_url:
            return 'stock_detail'
        if '/auth/login' in page_url:
            return 'login'
        if '/search' in page_url:
            return 'search'
        if '/fastreport' in page_url:
            return 'report_list'
        if '/intelligent_feed' in page_url:
            return 'news_feed'
        if '/data/' in page_url:
            return 'data'
        if '/mof/' in page_url:
            return 'fund'
        if page_url.rstrip('/').endswith('r.datayes.com'):
            return 'home'
        return 'unknown'
    except Exception:
        return 'unknown'


def extract_stock_code(page_url: str) -> str:
    """从 URL 中提取股票代码"""
    try:
        m = re.search(r'/stock/(\d+)', page_url)
        if m:
            return m.group(1)
        return ''
    except Exception:
        return ''


def extract_stock_key_data(elements: list[dict]) -> dict:
    """从个股页提取关键行情数据（标签-值配对），体积远小于 content_nodes"""
    # 常见行情标签
    KNOWN_LABELS = {
        '最新', '均价', '涨跌', '今开', '涨幅', '最高', '总手', '最低', '金额',
        '量比', '涨停', '跌停', '外盘(手)', '内盘(手)', '换手', '净资产',
        '总股本', '总值', '流通股', '流值', '委比', '委差',
        '主力流入', '主力流出', '主力净流入',
    }
    data: dict = {}
    try:
        pending_label: str = ''
        for elem in elements:
            try:
                text = (elem.get('name', '') or elem.get('extra_text', '')).strip().strip('"')
                if not text:
                    continue
                if text in KNOWN_LABELS:
                    pending_label = text
                elif pending_label:
                    data[pending_label] = text
                    pending_label = ''
            except Exception:
                continue
    except Exception:
        pass
    return data


def extract_stock_info(elements: list[dict]) -> dict:
    """从个股页提取股票行情数据（基于位置关系，紧跟 stock_name_code 后提取）"""
    info: dict = {}
    try:
        # 先找到 stock_name_code 的索引
        name_idx = -1
        for i, elem in enumerate(elements):
            try:
                name = elem.get('name', '') or elem.get('extra_text', '')
                if not name:
                    continue
                if '.SH' in name or '.SZ' in name:
                    info['stock_name_code'] = name
                    name_idx = i
                    break
            except Exception:
                continue

        if name_idx < 0:
            return info

        # 在 stock_name_code 后面的 5 个元素内查找 price 和 change_pct
        for elem in elements[name_idx + 1 : name_idx + 6]:
            try:
                raw_name = elem.get('name', '') or elem.get('extra_text', '')
                if not raw_name:
                    continue
                name = raw_name.strip().strip('"')
                if not name:
                    continue

                if elem.get('role') == 'button':
                    continue

                if _is_price_like(name) and 'price' not in info:
                    info['price'] = name
                    continue

                if name.endswith('%') and 'change_pct' not in info:
                    info['change_pct'] = name
                    continue
            except Exception:
                continue
    except Exception:
        pass
    return info


def _is_price_like(text: str) -> bool:
    """判断文本是否像价格"""
    try:
        text = text.strip().strip('"')
        if re.match(r'^-?\d+\.\d{1,4}$', text):
            return True
        return False
    except Exception:
        return False


def extract_menu_structure(elements: list[dict]) -> list[dict]:
    """提取菜单结构（个股页左侧导航）"""
    menus: list[dict] = []
    try:
        current_group: Optional[dict] = None
        for elem in elements:
            try:
                role = elem.get('role', '')
                name = elem.get('name', '') or elem.get('extra_text', '')
                if not name:
                    continue

                # 清理图标文本前缀
                clean_name = re.sub(r'^(caret-right|caret-down|caret-up)\s+', '', name).strip()
                if not clean_name:
                    continue

                if role == 'menuitem' and 'expanded' in elem.get('states', []):
                    current_group = {'group': clean_name, 'items': []}
                    menus.append(current_group)
                    continue

                if role == 'menuitem' and current_group is not None:
                    item: dict = {'text': clean_name}
                    if elem.get('url'):
                        item['url'] = elem['url']
                    if elem.get('ref'):
                        item['ref'] = elem['ref']
                    current_group['items'].append(item)
                elif role == 'menuitem':
                    menus.append({'group': clean_name, 'items': []})
            except Exception:
                continue
    except Exception:
        pass
    return menus


def build_summary(elements: list[dict], page_url: str = '', truncated: bool = False) -> dict:
    """生成精简摘要 JSON（完整提取，不做内容过滤）"""
    try:
        page_type = detect_page_type(page_url, elements)

        news_items: list[dict] = []
        report_items: list[dict] = []
        hot_keywords: list[str] = []
        feature_entries: list[str] = []
        search_info: Optional[dict] = None

        for elem in elements:
            try:
                role = elem.get('role', '')
                name = elem.get('name', '')
                url = elem.get('url', '')

                if role == 'link' and url:
                    if '/details/robo-news/' in url:
                        news_items.append({'title': name, 'url': url})
                    elif '/details/report/' in url:
                        report_items.append({'title': name, 'url': url})
                    elif url.startswith('/search?query='):
                        hot_keywords.append(name)

                if role == 'generic' and name in (
                    '指标库', '个股分析', '行业分析', '资讯动态', '公告', '股票监控', '数据监控'
                ):
                    feature_entries.append(name)

                if role == 'button' and 'AI搜索' in (name or ''):
                    search_info = search_info or {}
                    search_info['ai_search_ref'] = elem.get('ref', '')

                if role in ('textbox', 'combobox') and elem.get('ref'):
                    if search_info is None:
                        search_info = {}
                    if 'input_ref' not in search_info:
                        search_info['input_ref'] = elem['ref']
                        if name:
                            search_info['placeholder'] = name
            except Exception:
                continue

        summary: dict = {
            'page_url': page_url,
            'page_type': page_type,
            'login_status': detect_login_status(elements),
            'truncated': truncated,
            'navigation': extract_navigation(elements),
            'hot_keywords': hot_keywords[:15],
        }

        if search_info:
            summary['search'] = search_info
        if feature_entries:
            summary['features'] = feature_entries
        if news_items:
            summary['news'] = news_items[:30]
        if report_items:
            summary['reports'] = report_items[:30]

        if page_type == 'stock_detail':
            stock_code = extract_stock_code(page_url)
            if stock_code:
                summary['stock_code'] = stock_code
            stock_info = extract_stock_info(elements)
            if stock_info:
                summary['stock_info'] = stock_info
            menus = extract_menu_structure(elements)
            if menus:
                summary['menu_structure'] = menus
            key_data = extract_stock_key_data(elements)
            if key_data:
                summary['key_data'] = key_data
            chart_data = extract_chart_data(elements)
            if chart_data:
                summary['chart_data'] = chart_data
            tables = extract_tables(elements)
            if tables:
                summary['tables'] = tables

        sections = extract_sections_full(elements)
        if sections:
            summary['sections'] = sections[:20]

        return summary
    except Exception as e:
        return {
            'page_url': page_url,
            'page_type': 'error',
            'login_status': 'unknown',
            'truncated': truncated,
            'error': str(e),
            'navigation': [],
            'hot_keywords': [],
        }


def build_elements_index(elements: list[dict], snapshot_id: str = '', page_url: str = '') -> dict:
    """生成操作索引 JSON"""
    links: list[dict] = []
    buttons: list[dict] = []
    inputs: list[dict] = []
    tabs: list[dict] = []
    images: list[dict] = []
    checkboxes: list[dict] = []
    other_interactive: list[dict] = []

    try:
        for elem in elements:
            try:
                if not elem.get('ref'):
                    continue

                role = elem.get('role', '')
                entry: dict = {'ref': elem['ref']}

                if elem.get('name'):
                    entry['text'] = elem['name']
                elif elem.get('extra_text'):
                    entry['text'] = elem['extra_text']

                if elem.get('url'):
                    entry['url'] = elem['url']
                if elem.get('states'):
                    entry['states'] = elem['states']
                if elem.get('cursor'):
                    entry['cursor'] = elem['cursor']

                if role == 'link':
                    links.append(entry)
                elif role == 'button':
                    buttons.append(entry)
                elif role in ('textbox', 'combobox', 'searchbox'):
                    entry['input_type'] = role
                    inputs.append(entry)
                elif role == 'tab':
                    tabs.append(entry)
                elif role == 'img':
                    images.append(entry)
                elif role in ('checkbox', 'radio', 'switch'):
                    entry['input_type'] = role
                    checkboxes.append(entry)
                elif role in INTERACTIVE_ROLES:
                    entry['role'] = role
                    other_interactive.append(entry)
            except Exception:
                continue
    except Exception:
        pass

    index: dict = {
        'snapshot_id': snapshot_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'page_url': page_url,
        'element_counts': {
            'links': len(links),
            'buttons': len(buttons),
            'inputs': len(inputs),
            'tabs': len(tabs),
            'images': len(images),
            'checkboxes': len(checkboxes),
            'other': len(other_interactive),
        },
        'elements': {},
    }

    if links:
        index['elements']['links'] = links
    if buttons:
        index['elements']['buttons'] = buttons
    if inputs:
        index['elements']['inputs'] = inputs
    if tabs:
        index['elements']['tabs'] = tabs
    if images:
        index['elements']['images'] = images
    if checkboxes:
        index['elements']['checkboxes'] = checkboxes
    if other_interactive:
        index['elements']['other'] = other_interactive

    return index


def clean_snapshot(raw: str, page_url: str = '', snapshot_id: str = '') -> tuple[dict, dict]:
    """清洗 snapshot 原始文本，返回 (summary, elements_index)"""
    try:
        if not snapshot_id:
            id_m = re.search(r'EXTERNAL_UNTRUSTED_CONTENT\s+id="([^"]+)"', raw)
            if id_m:
                snapshot_id = id_m.group(1)

        truncated = detect_truncated(raw)
        elements = parse_snapshot(raw)
        summary = build_summary(elements, page_url, truncated)
        index = build_elements_index(elements, snapshot_id, page_url)

        return summary, index
    except Exception as e:
        return (
            {
                'page_url': page_url,
                'page_type': 'error',
                'login_status': 'unknown',
                'truncated': False,
                'error': str(e),
                'navigation': [],
                'hot_keywords': [],
            },
            {
                'snapshot_id': snapshot_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'page_url': page_url,
                'element_counts': {},
                'elements': {},
            },
        )


def _make_unique_dir(base: str = '/tmp/datayes_cleaned') -> str:
    """生成带唯一 ID 的输出目录，避免并行覆盖"""
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    return f'{base}_{unique_id}'


def main() -> None:
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(description='清洗 browser snapshot 数据')
    parser.add_argument('input_file', nargs='?', help='原始 snapshot 文件路径')
    parser.add_argument('--stdin', action='store_true', help='从 stdin 读取')
    parser.add_argument('--output-dir', '-o', default='', help='输出目录（默认自动生成唯一目录）')
    parser.add_argument('--page-url', default='', help='页面 URL')
    parser.add_argument('--summary-only', action='store_true', help='仅输出摘要到 stdout')
    parser.add_argument('--elements-only', action='store_true', help='仅输出操作索引到 stdout')
    args = parser.parse_args()

    raw = ''
    try:
        if args.stdin:
            raw = sys.stdin.read()
        elif args.input_file:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                raw = f.read()
        else:
            parser.error('需要指定 input_file 或 --stdin')
            return
    except Exception as e:
        print(json.dumps({'error': f'读取输入失败: {e}'}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    try:
        summary, elements = clean_snapshot(raw, page_url=args.page_url)
    except Exception as e:
        print(json.dumps({'error': f'清洗失败: {e}'}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    if args.summary_only:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    if args.elements_only:
        print(json.dumps(elements, ensure_ascii=False, indent=2))
        return

    try:
        output_dir = args.output_dir if args.output_dir else _make_unique_dir()
        os.makedirs(output_dir, exist_ok=True)
        summary_path = os.path.join(output_dir, 'summary.json')
        elements_path = os.path.join(output_dir, 'elements.json')

        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        with open(elements_path, 'w', encoding='utf-8') as f:
            json.dump(elements, f, ensure_ascii=False, indent=2)

        raw_size = len(raw)
        summary_size = len(json.dumps(summary, ensure_ascii=False))
        elements_size = len(json.dumps(elements, ensure_ascii=False))
        ratio = (summary_size + elements_size) / raw_size * 100 if raw_size > 0 else 0

        print(f'输出目录: {output_dir}')
        print(f'原始数据: {raw_size:,} 字符')
        print(f'摘要: {summary_size:,} 字符 → {summary_path}')
        print(f'操作索引: {elements_size:,} 字符 → {elements_path}')
        print(f'压缩率: {ratio:.1f}%')
    except Exception as e:
        print(json.dumps({'error': f'写入输出失败: {e}'}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
