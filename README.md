# sdenv的瑞数逆向接口版本

本项目是基于上游 `sdenv` 的接口化二次开发版本，提供：

- Node HTTP API（`/api/health`、`/api/crack`）
- Python SDK（`python/sdenv_client.py`）
- npm CLI（`sdenv-rs`）
- Windows/macOS GUI 启动器（Release 产物）

## 上游来源声明

- 上游项目：`https://github.com/pysunday/sdenv`
- 当前仓库：`https://github.com/lasawang/sdenv-rs-interface-version`
- 本项目保留上游许可证与来源说明，详见 `NOTICE.md`、`LICENSE`

## 快速开始

### 1. EXE 无脑使用（推荐）

只想直接用，不想配 Node / C++ 编译环境，按这个流程即可：

1. 到 Release 下载并启动：
- `sdenv-service-gui.exe`（Windows）
- `sdenv-service-gui-macos-arm64.dmg`（macOS Apple Silicon）

2. 默认监听端口 `3900`（可在 GUI 中改端口）

3. 健康检查：

```bash
curl http://127.0.0.1:3900/api/health
```

4. Python 直接请求（`requests`）：

```python
import requests

BASE = "http://127.0.0.1:3900"
health = requests.get(f"{BASE}/api/health", timeout=5).json()
print("health:", health)
```

Release 页面：

- `https://github.com/lasawang/sdenv-rs-interface-version/releases`

### 2. 源码部署环境要求

- Node.js `>= 20.19.5`
- Python `>= 3.10`
- 首次安装依赖时需要本机 C/C++ 编译环境（`node-gyp/canvas`）

### 3. 源码部署

```bash
npm i
```

Windows：

```bat
set SDENV_PORT=3901&& node server/index.js
```

macOS/Linux：

```bash
export SDENV_PORT=3901
node server/index.js
```

健康检查：

```bash
curl http://127.0.0.1:3901/api/health
```

### 4. EXE 部署

从 Release 下载并启动：

- `sdenv-service-gui.exe`（Windows）
- `sdenv-service-gui-macos-arm64.dmg`（macOS Apple Silicon）

Release 页面：

- `https://github.com/lasawang/sdenv-rs-interface-version/releases`

## 接口说明

### GET `/api/health`

返回服务状态与版本。

### POST `/api/crack`

支持 3 种模式：

- `remote`：服务端直接请求目标 URL 生成 Cookie
- `local`：传入 HTML/JS（可带 `ts`）本地执行
- `execute`：在模拟环境执行自定义 JS

`remote` 示例：

```bash
curl -X POST http://127.0.0.1:3901/api/crack ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"remote\",\"url\":\"https://www.suyinwealth.com/lccs\",\"resourceMode\":\"fast\",\"timeout\":45000,\"verify\":true}"
```

常用参数：

- `mode`、`url`
- `resourceMode`: `fast` / `full`
- `timeout`
- `verify`
- `userAgent`、`proxy`（可选）

关键返回：

- `success`
- `isRS`
- `cookies`
- `event`

## Python 使用

### 1. 使用 SDK（推荐）

SDK 文件在仓库内：`python/sdenv_client.py`（不是独立 PyPI 包）。

推荐导入：

```python
from python.sdenv_client import SdenvClient
```

兼容导入（仓库根目录 shim）：

```python
from sdenv_client import SdenvClient
```

示例：

```python
from python.sdenv_client import SdenvClient

client = SdenvClient(host='127.0.0.1', port=3901)
print(client.health())

resp = client.request_with_cookie(
    cookie_url='https://www.suyinwealth.com',
    request_url='https://www.suyinwealth.com/lccs/loadProductNew?page=2&rows=&prd_type=&status=0&client_groups=&interest_way=&min_money=&max_money=&prd_limit=&fund_risk=',
    method='GET',
    resource_mode='fast',
    use_cookie_cache=True,
    cookie_cache_ttl=20000,
    retry_on_cookie_expired=True,
    timeout=45000,
)
print(resp.get('success'), resp.get('status_code'), resp.get('cookie_source'))
```

#### GET 用例（获取网页/接口）

```python
from python.sdenv_client import SdenvClient

client = SdenvClient(host='127.0.0.1', port=3901)
resp = client.request_with_cookie(
    cookie_url='https://www.suyinwealth.com',
    request_url='https://www.suyinwealth.com/lccs/loadProductNew?page=2&rows=&prd_type=&status=0&client_groups=&interest_way=&min_money=&max_money=&prd_limit=&fund_risk=',
    method='GET',
    resource_mode='fast',
    use_cookie_cache=True,
    cookie_cache_ttl=20000,
    retry_on_cookie_expired=True,
    timeout=45000,
    verify=False,
)
print(resp.get('success'), resp.get('status_code'), resp.get('cookie_source'))
```

#### POST 用例（JSON）

```python
from python.sdenv_client import SdenvClient

client = SdenvClient(host='127.0.0.1', port=3901)
resp = client.request_with_cookie(
    cookie_url='https://example.com',
    request_url='https://example.com/api/demo',
    method='POST',
    json_data={'page': 1, 'size': 20},
    headers={'Content-Type': 'application/json; charset=utf-8'},
    resource_mode='fast',
    use_cookie_cache=True,
    cookie_cache_ttl=20000,
    retry_on_cookie_expired=True,
    timeout=45000,
    verify=False,
)
print(resp.get('success'), resp.get('status_code'), resp.get('cookie_source'))
```

#### POST 用例（Form）

```python
from python.sdenv_client import SdenvClient

client = SdenvClient(host='127.0.0.1', port=3901)
resp = client.request_with_cookie(
    cookie_url='https://example.com',
    request_url='https://example.com/api/form',
    method='POST',
    data={'keyword': 'test', 'page': 1},
    headers={'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'},
    resource_mode='fast',
    use_cookie_cache=True,
    cookie_cache_ttl=20000,
    retry_on_cookie_expired=True,
    timeout=45000,
    verify=False,
)
print(resp.get('success'), resp.get('status_code'), resp.get('cookie_source'))
```

测试脚本：

```bash
python python/test_site.py
```

### 2. 仅下载 EXE（不使用 SDK）

`exe` 不能被 Python `import`，应通过 HTTP 调用本地服务：

全流程（GET + POST）：

1. `GET /api/health` 检查服务可用
2. `POST /api/crack` 生成目标站点 Cookie
3. 带 Cookie 发起目标 `GET` 请求
4. 带 Cookie 发起目标 `POST` 请求

```python
import requests

BASE = "http://127.0.0.1:3900"
TARGET_GET = "https://www.suyinwealth.com/lccs/loadProductNew?page=2&rows=&prd_type=&status=0&client_groups=&interest_way=&min_money=&max_money=&prd_limit=&fund_risk="
TARGET_POST = "https://example.com/api/demo"  # 换成你的真实 POST 接口

health = requests.get(f"{BASE}/api/health", timeout=5).json()
print("health:", health)

payload = {
    "mode": "remote",
    "url": "https://www.suyinwealth.com/lccs",
    "resourceMode": "fast",
    "timeout": 45000,
    "verify": True,
}

crack_resp = requests.post(
    f"{BASE}/api/crack",
    json=payload,
    timeout=60,
).json()

cookie = crack_resp.get("cookies", "")
if not cookie:
    raise RuntimeError(f"failed to get cookie: {crack_resp}")

common_headers = {
    "Cookie": cookie,
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}

# GET 用例
get_resp = requests.get(TARGET_GET, headers=common_headers, timeout=60, verify=False)
print("GET:", get_resp.status_code, get_resp.text[:120])

# POST 用例（JSON）
post_resp = requests.post(
    TARGET_POST,
    headers={**common_headers, "Content-Type": "application/json; charset=utf-8"},
    json={"page": 1, "size": 20},
    timeout=60,
    verify=False,
)
print("POST:", post_resp.status_code, post_resp.text[:120])
```

安装 `requests`：

```bash
pip install requests
```

## npm 使用

全局安装 CLI：

```bash
npm i -g sdenv-rs-interface-version
sdenv-rs https://www.suyinwealth.com/lccs
```

作为依赖：

```bash
npm i sdenv-rs-interface-version
```

## 常见问题

### 1. `ModuleNotFoundError: No module named 'sdenv_client'`

- `sdenv_client` 不是独立 pip 包。
- 请用仓库内 SDK：`from python.sdenv_client import SdenvClient`。

### 2. Python 能不能直接导入 EXE？

不能。EXE 用来启动服务，Python 通过 HTTP 接口调用。

### 3. 连接失败（端口问题）

- Node 默认端口：`3000`
- GUI 默认端口：`3900`
- 建议统一设成 `3901`，并在客户端对应修改

### 4. 安装时报 `node-gyp`/C++ 编译错误

请安装系统编译工具链（Windows 建议 Visual Studio C++ Build Tools）。

## GUI 打包

- Windows：`python\build_service_gui_exe.bat`
- macOS M 系列：`python/build_service_gui_macos.sh`

详细见：`python/README-exe.md`

## 合规声明

- 本项目仅用于合法授权范围内的安全研究与接口测试。
- 请遵守目标系统服务条款与当地法律法规。
