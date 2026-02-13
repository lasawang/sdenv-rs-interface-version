# sdenv的瑞数逆向的接口版本

`sdenv的瑞数逆向的接口版本` 是基于上游 `sdenv` 的接口化二次开发版本，提供 Node API、Python SDK、GUI 启动器与 npm CLI。

## 上游来源声明

- 上游项目：`https://github.com/pysunday/sdenv`
- 当前仓库：`https://github.com/lasawang/sdenv-rs-interface-version`
- 本项目保留上游许可证与来源说明，详见 `NOTICE.md` 与 `LICENSE`

## 主要能力

- `remote`：远程拉取页面并计算瑞数 Cookie
- `local`：传入 HTML/JS/TS 在本地模拟环境执行
- `execute`：在模拟浏览器环境中执行自定义 JS
- Python SDK：支持 GET/POST、短效 Cookie 缓存复用、失效自动刷新重试
- `resource_mode='fast'`：减少非必要资源加载

## 部署方式（多种）

### 方式 1：源码部署（推荐）

适合你自己维护服务端、二次开发。

1. 准备环境
- Node.js `>= 20.19.5`
- Python `>= 3.10`（建议 3.11）
- 由于 `node-gyp/canvas`，首次安装需要本机 C/C++ 编译环境

2. 安装依赖

```bash
npm i
```

3. 启动服务（示例用 3901 端口）

Windows:

```bat
set SDENV_PORT=3901&& node server/index.js
```

macOS/Linux:

```bash
export SDENV_PORT=3901
node server/index.js
```

默认接口：
- `GET /api/health`
- `POST /api/crack`

### 方式 2：npm 全局安装（CLI）

适合本机直接命令行调用。

```bash
npm i -g sdenv-rs-interface-version
sdenv-rs https://www.example.com
```

说明：首次安装同样可能需要本机编译环境（`node-gyp/canvas`）。

### 方式 3：npm 作为项目依赖

适合集成到你自己的 Node 项目中。

```bash
npm i sdenv-rs-interface-version
```

或直接安装 GitHub 最新源码：

```bash
npm i git+https://github.com/lasawang/sdenv-rs-interface-version.git
```

代码中使用：

```js
const sdenv = require('sdenv-rs-interface-version');
```

### 方式 4：Python SDK 部署调用

适合 Python 服务端/脚本直接调用本项目 API。

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
)
print(resp.get('status_code'), resp.get('cookie_source'))
```

测试脚本：

```bash
python python/test_site.py
```

`test_site.py` 会自动探测端口（`SDENV_PORT` -> `3901` -> `3000`）。

说明：

- `sdenv_client` 不是单独发布到 PyPI 的公网包。
- SDK 源码在 `python/sdenv_client.py`。
- 推荐导入：`from python.sdenv_client import SdenvClient`。
- 为兼容旧写法，仓库根目录也提供了 `sdenv_client.py` 入口，可直接 `from sdenv_client import SdenvClient`。

### 方式 5：使用 Release 可执行文件（免源码启动）

适合不想手动启动 Node 服务的同学。

Release 页面：
- `https://github.com/lasawang/sdenv-rs-interface-version/releases`

当前常用资产：
- Windows：`sdenv-service-gui.exe`
- macOS Apple Silicon：`sdenv-service-gui-macos-arm64.dmg`

### 方式 6：生产常驻（PM2）

适合线上长期运行。

```bash
npm i
npm i -g pm2
pm2 start server/index.js --name sdenv-rs --update-env
pm2 save
```

可配合环境变量（如 `SDENV_PORT`、代理等）做多实例部署。

## 详细使用

### 1. 服务健康检查

服务启动后先确认健康状态：

```bash
curl http://127.0.0.1:3901/api/health
```

预期返回：

```json
{"status":"ok","version":"1.1.5"}
```

### 2. HTTP API 使用（`POST /api/crack`）

#### 2.1 `remote` 模式（最常用）

服务端自动请求目标 URL，计算 Cookie 并返回结果。

```bash
curl -X POST http://127.0.0.1:3901/api/crack ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"remote\",\"url\":\"https://www.suyinwealth.com/lccs\",\"resourceMode\":\"fast\",\"timeout\":45000,\"verify\":true}"
```

常用参数：

- `mode`: `remote`
- `url`: 目标页面
- `resourceMode`: `fast` 或 `full`
- `timeout`: 超时毫秒
- `verify`: 是否二次验证
- `userAgent`、`proxy`: 可选

返回关键字段：

- `success`: 是否成功
- `isRS`: 是否检测到瑞数
- `cookies`: 生成的 Cookie 字符串
- `event`: 跳转事件信息（可能带 `url`）

#### 2.2 `local` 模式

你自己传 HTML/JS 给服务执行，适合离线调试。

```json
{
  "mode": "local",
  "url": "https://target.example.com/",
  "html": "<html>...</html>",
  "js": "/* rs js code */",
  "ts": {"sign": "xxx"},
  "timeout": 30000
}
```

#### 2.3 `execute` 模式

在模拟浏览器环境中执行自定义 JS。

```json
{
  "mode": "execute",
  "url": "https://target.example.com/",
  "html": "<html><body></body></html>",
  "jsCode": "document.title = 'ok'; document.title;",
  "timeout": 30000
}
```

### 3. Python SDK 详细示例

#### 3.1 基础连通

```python
from python.sdenv_client import SdenvClient

client = SdenvClient(host='127.0.0.1', port=3901)
print(client.health())
```

#### 3.2 直接算 Cookie

```python
resp = client.crack_url(
    "https://www.suyinwealth.com/lccs",
    resource_mode="fast",
    timeout=45000,
    verify=True,
)
print(resp.get("success"), len(resp.get("cookies", "")))
```

#### 3.3 计算 Cookie 并发起目标请求（推荐）

```python
resp = client.request_with_cookie(
    cookie_url="https://www.suyinwealth.com",
    request_url="https://www.suyinwealth.com/lccs/loadProductNew?page=2&rows=&prd_type=&status=0&client_groups=&interest_way=&min_money=&max_money=&prd_limit=&fund_risk=",
    method="GET",
    resource_mode="fast",
    timeout=45000,
    verify=False,
    use_cookie_cache=True,
    cookie_cache_ttl=20000,
    retry_on_cookie_expired=True,
)
print(resp.get("success"), resp.get("status_code"), resp.get("cookie_source"))
```

#### 3.4 POST JSON 示例

```python
resp = client.request_with_cookie(
    cookie_url="https://example.com/",
    request_url="https://example.com/api/demo",
    method="POST",
    json_data={"page": 1, "size": 20},
    headers={"X-Requested-With": "XMLHttpRequest"},
    use_cookie_cache=True,
)
print(resp.get("status_code"))
```

#### 3.5 Cookie 缓存管理

```python
print(client.get_cookie_cache_stats())
client.clear_cookie_cache("https://www.suyinwealth.com")
```

### 4. CLI 使用

#### 4.1 npm 全局命令

```bash
sdenv-rs https://www.suyinwealth.com/lccs
```

#### 4.2 Python 命令行封装

```bash
python python/call_sdenv.py https://www.suyinwealth.com/ --request-url "https://www.suyinwealth.com/lccs/loadProductNew?page=2&rows=&prd_type=&status=0&client_groups=&interest_way=&min_money=&max_money=&prd_limit=&fund_risk=" --host 127.0.0.1 --port 3901 --show-body
```

### 5. 常见问题

#### 5.1 端口不一致导致连接失败

- 服务默认端口是 `3000`。
- 你可以统一使用 `SDENV_PORT=3901` 启动。
- `python/test_site.py` 已支持端口探测顺序：`SDENV_PORT -> 3901 -> 3000`。

#### 5.2 `node-gyp`/C++ 编译失败

当前版本安装仍需要本机编译环境（如 Windows 的 Visual Studio C++ Build Tools）。

#### 5.3 HTTPS/老旧站点握手报错

项目已内置以下兼容设置（服务端启动自动生效）：

- `NODE_TLS_REJECT_UNAUTHORIZED=0`
- `OPENSSL_LEGACY_RENEGOTIATION=1`

## GUI 打包说明

- Windows 打包：`python\build_service_gui_exe.bat`
- macOS M 系列打包：`python/build_service_gui_macos.sh`

详细说明见：`python/README-exe.md`

## 发布到 npm（维护者）

```bash
npm login
npm run pack:check
npm publish --access public
```

若账号开启 2FA：

```bash
npm publish --access public --otp=6位验证码或recovery-code
```

## 重要提示

- 本项目仅用于合法授权范围内的安全研究与接口测试。
- 请遵守目标系统服务条款与当地法律法规。
- 任何未授权使用行为与本项目维护者无关。
