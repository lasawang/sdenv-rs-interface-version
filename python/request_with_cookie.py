# -*- coding: utf-8 -*-
"""
先调用 sdenv 生成 cookie，再携带 cookie 发起 HTTP 请求。

用法:
    python python/request_with_cookie.py https://target-site.com/page
    python python/request_with_cookie.py https://target-site.com/page --request-url https://target-site.com/api
    python python/request_with_cookie.py https://target-site.com/page -X POST --json '{"a":1}'
"""

import argparse
import json
import sys

from sdenv_client import SdenvClient, DEFAULT_USER_AGENT


def parse_headers(header_list):
    headers = {}
    for raw in header_list or []:
        if ':' not in raw:
            raise ValueError(f'Header 格式错误: {raw}，应为 Key:Value')
        key, value = raw.split(':', 1)
        headers[key.strip()] = value.strip()
    return headers


def build_parser():
    parser = argparse.ArgumentParser(description='使用 sdenv 生成 cookie 并发起请求')
    parser.add_argument('cookie_url', help='用于生成 cookie 的 URL')
    parser.add_argument('--request-url', help='实际请求 URL，默认自动推断')
    parser.add_argument('--host', default='localhost', help='sdenv API 主机，默认 localhost')
    parser.add_argument('--port', type=int, default=3000, help='sdenv API 端口，默认 3000')
    parser.add_argument('-X', '--method', default='GET', help='HTTP 方法，默认 GET')
    parser.add_argument('-H', '--header', action='append', help='请求头，支持多次传入，格式 Key:Value')
    parser.add_argument('--data', help='请求体字符串')
    parser.add_argument('--json', dest='json_text', help='JSON 请求体字符串')
    parser.add_argument('--timeout', type=int, default=30000, help='超时毫秒，默认 30000')
    parser.add_argument('--proxy', help='代理地址，例如 http://127.0.0.1:7890')
    parser.add_argument('--user-agent', default=DEFAULT_USER_AGENT, help='请求和 navigator 使用的 UA')
    parser.add_argument('--verify', action='store_true', help='生成 cookie 时启用二次验证请求')
    parser.add_argument('--show-body', action='store_true', help='输出响应 body 预览')
    parser.add_argument('--body-limit', type=int, default=600, help='body 预览长度，默认 600')
    return parser


def main():
    args = build_parser().parse_args()
    client = SdenvClient(host=args.host, port=args.port)

    health = client.health()
    print(json.dumps({'stage': 'health', 'result': health}, ensure_ascii=False))
    if health.get('status') != 'ok':
        return 2

    try:
        headers = parse_headers(args.header)
    except ValueError as e:
        print(json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False))
        return 1

    json_data = None
    if args.json_text:
        try:
            json_data = json.loads(args.json_text)
        except json.JSONDecodeError as e:
            print(json.dumps({'success': False, 'error': f'JSON 解析失败: {e}'}, ensure_ascii=False))
            return 1

    result = client.request_with_cookie(
        args.cookie_url,
        request_url=args.request_url,
        method=args.method,
        headers=headers,
        data=args.data,
        json_data=json_data,
        user_agent=args.user_agent,
        proxy=args.proxy,
        timeout=args.timeout,
        verify=args.verify,
    )

    summary = {
        'success': result.get('success'),
        'stage': result.get('stage'),
        'target_url': result.get('target_url'),
        'status_code': result.get('status_code'),
        'cookieLength': len(result.get('cookies', '')),
        'error': result.get('error'),
    }
    print(json.dumps({'stage': 'request_with_cookie', 'result': summary}, ensure_ascii=False))

    if args.show_body:
        body = result.get('body')
        if isinstance(body, str):
            print(body[:args.body_limit])
        else:
            print(body)

    return 0 if result.get('success') else 1


if __name__ == '__main__':
    sys.exit(main())
