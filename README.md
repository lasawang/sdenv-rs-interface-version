# sdenv的瑞数逆向的接口版本

` sdenv的瑞数逆向的接口版本 ` 是在上游 `sdenv` 基础上做的接口化二次开发版本，目标是提供更直接的 API 调用、Python 客户端能力，以及可执行 GUI 启动器。

## 上游来源声明

- 上游项目：`https://github.com/pysunday/sdenv`
- 当前仓库：`https://github.com/lasawang/sdenv-rs-interface-version`
- 本项目保留上游许可证与来源说明，详细见 `NOTICE.md` 与 `LICENSE`

## 主要能力

- `remote`：远程拉取目标页面并计算瑞数 Cookie
- `local`：传入 HTML/JS/TS 在本地模拟环境中执行
- `execute`：在模拟浏览器环境中执行自定义 JS
- Python SDK：支持 GET/POST、短效 Cookie 缓存复用、失效自动刷新重试
- 资源加速模式：`resource_mode='fast'`，减少非必要资源加载

## 快速开始

### 1. 环境要求

- Node.js `>= 20.19.5`
- Python `>= 3.10`（建议 3.11）
- 已安装项目依赖：`npm i`

### 2. 启动服务

```bash
node server/index.js
```

默认接口：

- `GET /api/health`
- `POST /api/crack`

### 3. Python 调用示例

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

## GUI 可执行文件（Release）

Release 页面：

- `https://github.com/lasawang/sdenv-rs-interface-version/releases`

当前已发布：

- 标签：`v1.1.4-interface`
- Windows EXE：`https://github.com/lasawang/sdenv-rs-interface-version/releases/download/v1.1.4-interface/sdenv-service-gui.exe`
- macOS M 系列：`https://github.com/lasawang/sdenv-rs-interface-version/releases/download/v1.1.4-interface/sdenv-service-gui-macos-arm64`

## 自动构建 Release 资产（Windows + macOS M 系列）

仓库内置工作流：`.github/workflows/release-binaries.yml`

- 触发方式 1：推送标签（如 `v1.1.4-interface`）
- 触发方式 2：GitHub Actions 手动执行 `Release GUI Binaries`
- 产物：
  - `dist/sdenv-service-gui.exe`
  - `dist/sdenv-service-gui-macos-arm64`

## 支持 macOS M 系列可执行文件

本项目已提供 Apple Silicon（arm64）打包脚本，可在 M 系列 Mac 本机生成可执行文件：

```bash
cd python
chmod +x build_service_gui_macos.sh
./build_service_gui_macos.sh
```

输出文件：

- `dist/sdenv-service-gui-macos-arm64`

说明：

- macOS 可执行文件需在 macOS（建议 M 系列机器）本机打包，不建议在 Windows 交叉打包。
- GUI 启动器依赖当前项目目录中的 `server/` 与 `node_modules/`。

## Windows 打包

```bat
python\build_service_gui_exe.bat
```

输出文件：

- `dist/sdenv-service-gui.exe`

## 重要提示

- 本项目仅用于合法授权范围内的安全研究与接口测试。
- 请遵守目标系统的服务条款与当地法律法规。
- 任何未授权使用行为与本项目维护者无关。
