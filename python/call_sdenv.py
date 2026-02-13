# -*- coding: utf-8 -*-
"""
可直接调用的 sdenv Python 脚本（支持命令行和 import 调用）。

命令行示例:
    python python/call_sdenv.py http://www.customs.gov.cn/

代码调用示例:
    from call_sdenv import call_sdenv
    result = call_sdenv("http://www.customs.gov.cn/")
"""

import argparse
import json
import sys
from typing import Dict, Optional

from sdenv_client import DEFAULT_USER_AGENT, SdenvClient


def parse_headers(items) -> Dict[str, str]:
    headers = {}
    for item in items or []:
        if ':' not in item:
            raise ValueError(f'Header 格式错误: {item}，应为 Key:Value')
        key, value = item.split(':', 1)
        headers[key.strip()] = value.strip()
    return headers


def call_sdenv(cookie_url: str,
               request_url: Optional[str] = None,
               host: str = '127.0.0.1',
               port: int = 3900,
               method: str = 'GET',
               headers: Optional[Dict[str, str]] = None,
               data=None,
               json_data=None,
               timeout: int = 30000,
               verify: bool = False,
               proxy: Optional[str] = None,
               user_agent: str = DEFAULT_USER_AGENT):
    client = SdenvClient(host=host, port=port)
    health = client.health()
    if health.get('status') != 'ok':
        return {
            'success': False,
            'stage': 'health',
            'error': 'sdenv 服务不可用',
            'health': health,
        }

    result = client.request_with_cookie(
        cookie_url,
        request_url=request_url,
        method=method,
        headers=headers,
        data=data,
        json_data=json_data,
        timeout=timeout,
        verify=verify,
        proxy=proxy,
        user_agent=user_agent,
    )
    result['health'] = health
    return result


def build_parser():
    parser = argparse.ArgumentParser(description='调用 sdenv 生成 cookie 并发起请求')
    parser.add_argument('cookie_url', help='用于生成 cookie 的 URL')
    parser.add_argument('--request-url', help='最终请求 URL，不传则自动推断')
    parser.add_argument('--host', default='127.0.0.1', help='sdenv 服务 host，默认 127.0.0.1')
    parser.add_argument('--port', type=int, default=3900, help='sdenv 服务端口，默认 3900')
    parser.add_argument('-X', '--method', default='GET', help='HTTP 方法，默认 GET')
    parser.add_argument('-H', '--header', action='append', help='请求头，格式 Key:Value，可传多次')
    parser.add_argument('--data', help='请求体文本')
    parser.add_argument('--json', dest='json_text', help='JSON 请求体文本')
    parser.add_argument('--timeout', type=int, default=30000, help='超时毫秒，默认 30000')
    parser.add_argument('--verify', action='store_true', help='生成 cookie 时启用二次验证')
    parser.add_argument('--proxy', help='代理地址，例如 http://127.0.0.1:7890')
    parser.add_argument('--user-agent', default=DEFAULT_USER_AGENT, help='请求 UA')
    parser.add_argument('--show-body', action='store_true', help='输出 body')
    parser.add_argument('--body-limit', type=int, default=800, help='body 输出长度，默认 800')
    return parser


def main():
    args = build_parser().parse_args()

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

    result = call_sdenv(
        cookie_url=args.cookie_url,
        request_url=args.request_url,
        host=args.host,
        port=args.port,
        method=args.method,
        headers=headers,
        data=args.data,
        json_data=json_data,
        timeout=args.timeout,
        verify=args.verify,
        proxy=args.proxy,
        user_agent=args.user_agent,
    )

    summary = {
        'success': result.get('success'),
        'stage': result.get('stage'),
        'status_code': result.get('status_code'),
        'target_url': result.get('target_url'),
        'cookieLength': len(result.get('cookies', '')),
        'error': result.get('error'),
        'health': result.get('health'),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.show_body:
        body = result.get('body')
        if isinstance(body, str):
            print(body[:args.body_limit])
        else:
            print(body)

    return 0 if result.get('success') else 1


if __name__ == '__main__':
    sys.exit(main())
