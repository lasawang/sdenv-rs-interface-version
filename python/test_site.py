import os
import time
from sdenv_client import SdenvClient

SITES = [
    {
        'cookie_url': 'https://www.suyinwealth.com',
        'request_url': 'https://www.suyinwealth.com/lccs/loadProductNew?page=2&rows=&prd_type=&status=0&client_groups=&interest_way=&min_money=&max_money=&prd_limit=&fund_risk=',
    },
    {
        'cookie_url': 'https://www.hfbank.com.cn/',
        'request_url': 'https://www.hfbank.com.cn/',
    },
]


def _pick_client(host='127.0.0.1'):
    env_port = os.getenv('SDENV_PORT')
    candidate_ports = []
    if env_port:
        try:
            candidate_ports.append(int(env_port))
        except ValueError:
            pass
    candidate_ports.extend([3901, 3000])

    seen = set()
    for port in candidate_ports:
        if port in seen:
            continue
        seen.add(port)
        client = SdenvClient(host=host, port=port)
        health = client.health()
        if health.get('status') == 'ok':
            print(f'using service: {host}:{port}')
            print(health)
            return client

    raise RuntimeError(
        f'Cannot connect sdenv service, tried ports: {sorted(seen)}. '
        f'Start server first, e.g. `set SDENV_PORT=3901&& node server/index.js`.'
    )


client = _pick_client()

for site in SITES:
    print('---', site['cookie_url'])
    for idx in range(2):
        t0 = time.perf_counter()
        resp = client.request_with_cookie(
            cookie_url=site['cookie_url'],
            request_url=site['request_url'],
            method='GET',
            verify=False,
            resource_mode='fast',
            use_cookie_cache=True,
            cookie_cache_ttl=20000,  # 20s
            retry_on_cookie_expired=True,
            timeout=45000,
        )
        elapsed = time.perf_counter() - t0
        print({
            'round': idx + 1,
            'success': resp.get('success'),
            'status_code': resp.get('status_code'),
            'cookie_source': resp.get('cookie_source'),
            'retried': resp.get('retried_with_fresh_cookie'),
            'elapsed_s': round(elapsed, 3),
        })

print('cache_stats:', client.get_cookie_cache_stats())
