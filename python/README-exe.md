# sdenv GUI 可执行文件说明

本目录提供 GUI 启动器，用于本地一键启动 `server/index.js` 服务，方便 Python / API 调用。

## 文件

- `python/sdenv_service_gui.py`：GUI 启动器源码
- `python/build_service_gui_exe.bat`：Windows 打包脚本
- `python/build_service_gui_macos.sh`：macOS Apple Silicon 打包脚本

## 前置条件

1. 已安装 Node.js，且 `node` 在 PATH 中可用
2. 已安装项目依赖（至少包含 `node_modules`）
3. 打包时已安装 PyInstaller：

```bash
pip install pyinstaller
```

## Windows 打包

在项目根目录执行：

```bat
python\build_service_gui_exe.bat
```

输出：

- `dist/sdenv-service-gui.exe`

## macOS M 系列（Apple Silicon）打包

在 macOS arm64 机器执行：

```bash
cd python
chmod +x build_service_gui_macos.sh
./build_service_gui_macos.sh
```

输出：

- `dist/sdenv-service-gui-macos-arm64`

## 使用

1. 运行可执行文件
2. 默认 `host=127.0.0.1`，`port=3900`
3. 启动成功后可通过 Python 客户端调用

Python 示例：

```python
from sdenv_client import SdenvClient

client = SdenvClient(host='127.0.0.1', port=3900)
print(client.health())
print(client.crack_url('https://www.hfbank.com.cn/'))
```

## 注意

- GUI 启动器不内置 Node 运行时，需本机已有 Node.js。
- 可执行文件依赖当前项目目录结构（`server/`、`node_modules/` 等）。
- 仓库支持通过 `.github/workflows/release-binaries.yml` 自动构建并上传 Windows/macOS 二进制到 Release。
