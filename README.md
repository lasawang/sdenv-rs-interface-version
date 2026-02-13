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
from sdenv_client import SdenvClient

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
