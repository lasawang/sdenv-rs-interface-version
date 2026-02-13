# -*- coding: utf-8 -*-
"""
Python SDK for sdenv service.
"""

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/131.0.0.0 Safari/537.36'
)
DEFAULT_COOKIE_CACHE_TTL = 15000  # milliseconds
DEFAULT_COOKIE_REFRESH_STATUS_CODES = (401, 403, 412, 419)


class SdenvClient:
    """sdenv Python client"""

    def __init__(self, host='localhost', port=3000, *,
                 cookie_cache_ttl=DEFAULT_COOKIE_CACHE_TTL,
                 cookie_cache_max_entries=256):
        self.base_url = f'http://{host}:{port}'
        self.cookie_cache_ttl = max(int(cookie_cache_ttl), 0)
        self.cookie_cache_max_entries = max(int(cookie_cache_max_entries), 1)
        self._cookie_cache = {}

    def _request(self, endpoint, data, extra_timeout=10):
        url = f'{self.base_url}{endpoint}'
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=payload,
            headers={'Content-Type': 'application/json; charset=utf-8'},
            method='POST',
        )
        api_timeout = data.get('timeout', 30000) / 1000 + extra_timeout
        try:
            with urllib.request.urlopen(req, timeout=api_timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode('utf-8')
            try:
                return json.loads(body)
            except Exception:
                return {'success': False, 'error': body, 'status_code': exc.code}
        except urllib.error.URLError as exc:
            return {'success': False, 'error': str(exc.reason)}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}

    def health(self):
        """Service health check"""
        url = f'{self.base_url}/api/health'
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as exc:
            return {'status': 'error', 'error': str(exc)}

    @staticmethod
    def _safe_json_dumps(value):
        try:
            return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        except Exception:
            return repr(value)

    def _build_cookie_cache_key(self, cookie_url, *, user_agent=None, proxy=None,
                                dom_config=None, bom_config=None, navigator_config=None,
                                resource_mode=None, window_proxy_config=None):
        parsed = urllib.parse.urlsplit(cookie_url or '')
        origin = f'{parsed.scheme.lower()}://{parsed.netloc.lower()}'
        raw_key = '|'.join([
            origin,
            user_agent or '',
            proxy or '',
            resource_mode or 'full',
            self._safe_json_dumps(dom_config or {}),
            self._safe_json_dumps(bom_config or {}),
            self._safe_json_dumps(navigator_config or {}),
            self._safe_json_dumps(window_proxy_config or {}),
        ])
        digest = hashlib.sha1(raw_key.encode('utf-8')).hexdigest()
        return f'{origin}|{digest}'

    def _evict_cookie_cache(self):
        if not self._cookie_cache:
            return

        now = time.time()
        expired_keys = []
        for key, entry in self._cookie_cache.items():
            expires_at = float(entry.get('expires_at') or 0)
            if expires_at and expires_at <= now:
                expired_keys.append(key)
        for key in expired_keys:
            self._cookie_cache.pop(key, None)

        overflow = len(self._cookie_cache) - self.cookie_cache_max_entries
        if overflow <= 0:
            return

        keys_by_oldest_use = sorted(
            self._cookie_cache.keys(),
            key=lambda it: float(self._cookie_cache[it].get('last_used_at') or 0),
        )
        for key in keys_by_oldest_use[:overflow]:
            self._cookie_cache.pop(key, None)

    def _get_cached_cookie_entry(self, cache_key):
        self._evict_cookie_cache()
        entry = self._cookie_cache.get(cache_key)
        if not entry:
            return None
        entry['last_used_at'] = time.time()
        return entry

    def _set_cached_cookie_entry(self, cache_key, *, cookies, target_url, event, ttl_ms):
        now = time.time()
        ttl_seconds = max(float(ttl_ms), 0) / 1000
        self._cookie_cache[cache_key] = {
            'cookies': cookies,
            'target_url': target_url,
            'event': event if isinstance(event, dict) else {},
            'created_at': now,
            'last_used_at': now,
            'expires_at': now + ttl_seconds,
        }
        self._evict_cookie_cache()

    def clear_cookie_cache(self, cookie_url=None):
        """Clear all cached cookies or only entries for one site origin."""
        if not cookie_url:
            self._cookie_cache.clear()
            return

        parsed = urllib.parse.urlsplit(cookie_url)
        origin_prefix = f'{parsed.scheme.lower()}://{parsed.netloc.lower()}|'
        keys = [key for key in self._cookie_cache.keys() if key.startswith(origin_prefix)]
        for key in keys:
            self._cookie_cache.pop(key, None)

    def get_cookie_cache_stats(self):
        """Return current in-memory cookie cache metrics."""
        self._evict_cookie_cache()
        return {
            'count': len(self._cookie_cache),
            'max_entries': self.cookie_cache_max_entries,
            'default_ttl_ms': self.cookie_cache_ttl,
        }

    def crack_url(self, url, *,
                  dom_config=None, bom_config=None, navigator_config=None,
                  user_agent=None, proxy=None, timeout=30000, verify=True,
                  resource_mode=None,
                  window_proxy_config=None):
        """Remote mode: request URL and crack RS cookie."""
        data = {
            'mode': 'remote',
            'url': url,
            'timeout': timeout,
            'verify': verify,
        }
        if dom_config:
            data['domConfig'] = dom_config
        if bom_config:
            data['bomConfig'] = bom_config
        if navigator_config:
            data['navigatorConfig'] = navigator_config
        if user_agent:
            data['userAgent'] = user_agent
        if proxy:
            data['proxy'] = proxy
        if resource_mode:
            data['resourceMode'] = resource_mode
        if window_proxy_config:
            data['windowProxyConfig'] = window_proxy_config
        return self._request('/api/crack', data)

    def crack_local(self, url, html, js, *,
                    ts=None, dom_config=None, bom_config=None,
                    navigator_config=None, timeout=30000,
                    window_proxy_config=None):
        """Local mode: crack with provided HTML/JS/ts."""
        data = {
            'mode': 'local',
            'url': url,
            'html': html,
            'js': js,
            'timeout': timeout,
        }
        if ts is not None:
            data['ts'] = ts
        if dom_config:
            data['domConfig'] = dom_config
        if bom_config:
            data['bomConfig'] = bom_config
        if navigator_config:
            data['navigatorConfig'] = navigator_config
        if window_proxy_config:
            data['windowProxyConfig'] = window_proxy_config
        return self._request('/api/crack', data)

    def execute_js(self, js_code, *,
                   url=None, html=None,
                   dom_config=None, bom_config=None,
                   navigator_config=None, timeout=30000,
                   wait_event=None, window_proxy_config=None):
        """Execute custom JS in simulated browser context."""
        data = {
            'mode': 'execute',
            'jsCode': js_code,
            'timeout': timeout,
        }
        if url:
            data['url'] = url
        if html:
            data['html'] = html
        if dom_config:
            data['domConfig'] = dom_config
        if bom_config:
            data['bomConfig'] = bom_config
        if navigator_config:
            data['navigatorConfig'] = navigator_config
        if wait_event:
            data['waitEvent'] = wait_event
        if window_proxy_config:
            data['windowProxyConfig'] = window_proxy_config
        return self._request('/api/crack', data)

    def _send_request_with_cookie(self, *, target_url, method, headers, cookies, user_agent,
                                  data, json_data, proxy, timeout, decode, crack_result):
        request_headers = {}
        if isinstance(headers, dict):
            request_headers.update({str(k): str(v) for k, v in headers.items()})
        request_headers.setdefault('Cookie', cookies)
        request_headers.setdefault('User-Agent', user_agent)
        request_headers.setdefault('Accept', '*/*')

        request_body = None
        if json_data is not None:
            request_body = json.dumps(json_data, ensure_ascii=False).encode('utf-8')
            request_headers.setdefault('Content-Type', 'application/json; charset=utf-8')
        elif data is not None:
            if isinstance(data, bytes):
                request_body = data
            elif isinstance(data, bytearray):
                request_body = bytes(data)
            elif isinstance(data, str):
                request_body = data.encode('utf-8')
            elif isinstance(data, dict):
                request_body = urllib.parse.urlencode(data).encode('utf-8')
                request_headers.setdefault('Content-Type', 'application/x-www-form-urlencoded; charset=utf-8')
            else:
                return {
                    'success': False,
                    'stage': 'request',
                    'error': f'unsupported data type: {type(data)}',
                    'crack_result': crack_result,
                }

        opener = urllib.request.build_opener()
        if proxy:
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({'http': proxy, 'https': proxy})
            )

        req = urllib.request.Request(
            target_url,
            data=request_body,
            headers=request_headers,
            method=method.upper(),
        )

        req_timeout = timeout / 1000 + 10
        try:
            with opener.open(req, timeout=req_timeout) as resp:
                raw_body = resp.read()
                body_text = raw_body.decode(decode, errors='replace')
                resp_headers = dict(resp.headers.items())
                content_type = resp.headers.get('content-type', '')
                json_body = None
                if 'application/json' in content_type.lower():
                    try:
                        json_body = json.loads(body_text)
                    except Exception:
                        json_body = None
                return {
                    'success': True,
                    'cookies': cookies,
                    'target_url': target_url,
                    'status_code': resp.status,
                    'headers': resp_headers,
                    'body': body_text,
                    'json': json_body,
                    'crack_result': crack_result,
                }
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode(decode, errors='replace')
            return {
                'success': False,
                'stage': 'request',
                'error': str(exc),
                'status_code': exc.code,
                'headers': dict(exc.headers.items()) if exc.headers else {},
                'body': error_body,
                'cookies': cookies,
                'target_url': target_url,
                'crack_result': crack_result,
            }
        except urllib.error.URLError as exc:
            return {
                'success': False,
                'stage': 'request',
                'error': str(exc.reason),
                'cookies': cookies,
                'target_url': target_url,
                'crack_result': crack_result,
            }
        except Exception as exc:
            return {
                'success': False,
                'stage': 'request',
                'error': str(exc),
                'cookies': cookies,
                'target_url': target_url,
                'crack_result': crack_result,
            }

    def _crack_cookie_bundle(self, cookie_url, request_url, *, ua, proxy, timeout, verify,
                             dom_config, bom_config, navigator_config,
                             resource_mode, window_proxy_config):
        crack_result = self.crack_url(
            cookie_url,
            dom_config=dom_config,
            bom_config=bom_config,
            navigator_config=navigator_config,
            user_agent=ua,
            proxy=proxy,
            timeout=timeout,
            verify=verify,
            resource_mode=resource_mode,
            window_proxy_config=window_proxy_config,
        )

        if not crack_result.get('success'):
            return {
                'success': False,
                'stage': 'crack',
                'error': crack_result.get('error') or 'failed to generate cookie',
                'crack_result': crack_result,
            }

        cookies = crack_result.get('cookies', '')
        if not cookies:
            return {
                'success': False,
                'stage': 'crack',
                'error': 'cookie is empty',
                'crack_result': crack_result,
            }

        event = crack_result.get('event') if isinstance(crack_result.get('event'), dict) else {}
        target_url = request_url or event.get('url') or cookie_url
        return {
            'success': True,
            'cookies': cookies,
            'event': event,
            'target_url': target_url,
            'crack_result': crack_result,
        }

    def request_with_cookie(self, cookie_url, request_url=None, *,
                            method='GET', headers=None, data=None, json_data=None,
                            dom_config=None, bom_config=None, navigator_config=None,
                            user_agent=None, proxy=None, timeout=30000, verify=False,
                            resource_mode=None,
                            use_cookie_cache=True, cookie_cache_ttl=None,
                            force_refresh_cookie=False,
                            retry_on_cookie_expired=True,
                            refresh_status_codes=None,
                            window_proxy_config=None, decode='utf-8'):
        """
        Generate cookie first, then send an HTTP request with that cookie.
        Built-in cache is origin-scoped to support multiple RS sites.
        """
        if data is not None and json_data is not None:
            return {
                'success': False,
                'stage': 'request',
                'error': 'data and json_data cannot be used together',
            }

        refresh_codes = DEFAULT_COOKIE_REFRESH_STATUS_CODES
        if refresh_status_codes is not None:
            refresh_codes = tuple(int(it) for it in refresh_status_codes)

        ua = user_agent or DEFAULT_USER_AGENT
        effective_cache_ttl = self.cookie_cache_ttl if cookie_cache_ttl is None else max(int(cookie_cache_ttl), 0)
        cache_enabled = bool(use_cookie_cache) and effective_cache_ttl > 0

        cache_key = self._build_cookie_cache_key(
            cookie_url,
            user_agent=ua,
            proxy=proxy,
            dom_config=dom_config,
            bom_config=bom_config,
            navigator_config=navigator_config,
            resource_mode=resource_mode,
            window_proxy_config=window_proxy_config,
        )

        crack_result = None
        cookies = ''
        target_url = request_url or cookie_url
        cookie_source = 'fresh'

        if cache_enabled and not force_refresh_cookie:
            cache_entry = self._get_cached_cookie_entry(cache_key)
            if cache_entry:
                cookies = cache_entry.get('cookies', '')
                event = cache_entry.get('event') if isinstance(cache_entry.get('event'), dict) else {}
                target_url = request_url or cache_entry.get('target_url') or event.get('url') or cookie_url
                cookie_source = 'cache'

        if not cookies:
            fresh_bundle = self._crack_cookie_bundle(
                cookie_url,
                request_url,
                ua=ua,
                proxy=proxy,
                timeout=timeout,
                verify=verify,
                dom_config=dom_config,
                bom_config=bom_config,
                navigator_config=navigator_config,
                resource_mode=resource_mode,
                window_proxy_config=window_proxy_config,
            )
            if not fresh_bundle.get('success'):
                return fresh_bundle

            crack_result = fresh_bundle.get('crack_result')
            cookies = fresh_bundle.get('cookies')
            target_url = fresh_bundle.get('target_url')
            cookie_source = 'fresh'

            if cache_enabled:
                self._set_cached_cookie_entry(
                    cache_key,
                    cookies=cookies,
                    target_url=target_url,
                    event=fresh_bundle.get('event'),
                    ttl_ms=effective_cache_ttl,
                )

        first_response = self._send_request_with_cookie(
            target_url=target_url,
            method=method,
            headers=headers,
            cookies=cookies,
            user_agent=ua,
            data=data,
            json_data=json_data,
            proxy=proxy,
            timeout=timeout,
            decode=decode,
            crack_result=crack_result,
        )
        first_response['cookie_source'] = cookie_source
        first_response['cache_key'] = cache_key
        first_response['retried_with_fresh_cookie'] = False

        if first_response.get('success'):
            return first_response

        status_code = first_response.get('status_code')
        should_retry = (
            retry_on_cookie_expired and
            cookie_source == 'cache' and
            isinstance(status_code, int) and
            status_code in refresh_codes
        )
        if not should_retry:
            return first_response

        self._cookie_cache.pop(cache_key, None)
        fresh_bundle = self._crack_cookie_bundle(
            cookie_url,
            request_url,
            ua=ua,
            proxy=proxy,
            timeout=timeout,
            verify=verify,
            dom_config=dom_config,
            bom_config=bom_config,
            navigator_config=navigator_config,
            resource_mode=resource_mode,
            window_proxy_config=window_proxy_config,
        )
        if not fresh_bundle.get('success'):
            first_response['refresh_error'] = fresh_bundle.get('error')
            first_response['crack_result'] = fresh_bundle.get('crack_result')
            return first_response

        fresh_cookies = fresh_bundle.get('cookies')
        refreshed_target_url = fresh_bundle.get('target_url')
        crack_result = fresh_bundle.get('crack_result')

        if cache_enabled:
            self._set_cached_cookie_entry(
                cache_key,
                cookies=fresh_cookies,
                target_url=refreshed_target_url,
                event=fresh_bundle.get('event'),
                ttl_ms=effective_cache_ttl,
            )

        retry_response = self._send_request_with_cookie(
            target_url=refreshed_target_url,
            method=method,
            headers=headers,
            cookies=fresh_cookies,
            user_agent=ua,
            data=data,
            json_data=json_data,
            proxy=proxy,
            timeout=timeout,
            decode=decode,
            crack_result=crack_result,
        )
        retry_response['cookie_source'] = 'fresh'
        retry_response['cache_key'] = cache_key
        retry_response['retried_with_fresh_cookie'] = True
        retry_response['first_response'] = {
            'success': first_response.get('success'),
            'status_code': first_response.get('status_code'),
            'error': first_response.get('error'),
        }
        return retry_response


# ===== convenience wrappers =====

_default_client = None


def get_client(host='localhost', port=3000):
    """Get or create a shared client instance."""
    global _default_client
    if _default_client is None or _default_client.base_url != f'http://{host}:{port}':
        _default_client = SdenvClient(host, port)
    return _default_client


def crack_url(url, **kwargs):
    """Convenience wrapper for remote crack."""
    host = kwargs.pop('host', 'localhost')
    port = kwargs.pop('port', 3000)
    return get_client(host, port).crack_url(url, **kwargs)


def crack_local(url, html, js, **kwargs):
    """Convenience wrapper for local crack."""
    host = kwargs.pop('host', 'localhost')
    port = kwargs.pop('port', 3000)
    return get_client(host, port).crack_local(url, html, js, **kwargs)


def execute_js(js_code, **kwargs):
    """Convenience wrapper for execute_js."""
    host = kwargs.pop('host', 'localhost')
    port = kwargs.pop('port', 3000)
    return get_client(host, port).execute_js(js_code, **kwargs)


def request_with_cookie(cookie_url, **kwargs):
    """Convenience wrapper for cookie + request flow."""
    host = kwargs.pop('host', 'localhost')
    port = kwargs.pop('port', 3000)
    return get_client(host, port).request_with_cookie(cookie_url, **kwargs)


if __name__ == '__main__':
    import sys

    client = SdenvClient()
    health = client.health()
    print(f'service health: {health}')

    if len(sys.argv) > 1:
        target_url = sys.argv[1]
        print(f'cracking: {target_url}')
        result = client.crack_url(target_url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
