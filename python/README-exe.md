# sdenv EXE 图形启动器

## 目标
将 `server/index.js` 作为本地服务，通过 Windows 图形界面一键启动，供 Python 代码调用。

## 文件
- `python/sdenv_service_gui.py`：图形启动器源码
- `python/build_service_gui_exe.bat`：一键打包 EXE 脚本

## 前置条件
1. 已安装 Node.js，且 `node` 在 PATH 中可用
2. 已安装项目依赖（含 `node_modules`）
3. 需要打包时，已安装 PyInstaller：`pip install pyinstaller`

## 打包 EXE
在项目根目录执行：

```bat
python\build_service_gui_exe.bat
```

打包后文件：

```text
dist\sdenv-service-gui.exe
```

## 使用
1. 双击 `dist\sdenv-service-gui.exe`
2. 默认 `host=127.0.0.1`，`port=3900`，界面会自动尝试启动服务
3. 如果端口被占用，改端口后点击“启动服务”
4. 状态为运行中后，使用 Python 客户端调用

## Python 调用示例
```python
from sdenv_client import SdenvClient

client = SdenvClient(host='127.0.0.1', port=3900)
print(client.health())
print(client.crack_url('http://www.customs.gov.cn/'))
```

## 注意
- 默认端口使用 `3900`，避免与本机已有 `3000` 服务冲突。
- EXE 仍依赖当前项目目录（至少包含 `server/` 与 `node_modules/`）。
