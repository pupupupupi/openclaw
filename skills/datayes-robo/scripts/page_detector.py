#!/usr/bin/env python3
"""
萝卜投研 页面检测模块

从 browser snapshot 原始文本或解析后的元素列表中
推断页面 URL、检测页面类型、判断登录状态。
"""

import re


LOGGED_IN_INDICATORS = {'修改密码', '个人中心', '帮助中心', '任务专区'}
LOGIN_PAGE_INDICATORS = {'密码登录', '短信验证码登录', '登 录', '登录Datayes'}
LOGIN_PAGE_LINK_INDICATORS = {'暂无账号，点击申请试用', '忘记密码？'}
NAV_ITEMS = {'首页', '研报', '资讯', '数据', '自选', '股票', '基金', '组合'}


def infer_page_url(raw: str) -> str:
    stock_m = re.search(r'/stock/(\d{6})', raw)
    if stock_m:
        return f'https://r.datayes.com/stock/{stock_m.group(1)}'

    if '/auth/login' in raw and ('密码登录' in raw or '登 录' in raw):
        return 'https://r.datayes.com/auth/login'

    if '搜索结果' in raw and '/search?query=' in raw:
        return 'https://r.datayes.com/search'

    return 'https://r.datayes.com'


def detect_page_type(page_url: str, elements: list[dict]) -> str:
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


def extract_stock_code(page_url: str) -> str:
    try:
        m = re.search(r'/stock/(\d+)', page_url)
        if m:
            return m.group(1)
        return ''
    except Exception:
        return ''
