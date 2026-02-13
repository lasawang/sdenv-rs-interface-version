# -*- coding: utf-8 -*-
"""
sdenv Windows 图形启动器。

功能:
1. 图形界面启动/停止 Node 服务 (server/index.js)
2. 显示服务日志与健康状态
3. 提供可直接复制的 Python 调用示例

说明:
- 默认端口 3900，避免与本机其它 3000 端口服务冲突。
- 需要系统可用 node 命令，并且当前工程目录完整（含 node_modules）。
"""

import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext

try:
    import urllib.request
except Exception:  # pragma: no cover - 兼容极端环境
    urllib = None


APP_TITLE = 'sdenv Service Launcher'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = '3900'
DEFAULT_HEALTH_TIMEOUT_SEC = 15
AUTO_START_ON_OPEN = True
ANSI_ESCAPE_RE = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')


def project_root() -> Path:
    """
    获取项目根目录。
    开发时: python/sdenv_service_gui.py -> 上两级目录
    打包后: 若 exe 所在目录包含 server/index.js，则直接使用 exe 所在目录
    """
    exe_dir = Path(sys.executable).resolve().parent
    if getattr(sys, 'frozen', False):
        candidates = [
            exe_dir,
            exe_dir.parent,
            Path.cwd(),
            Path.cwd().parent,
        ]
        for candidate in candidates:
            if (candidate / 'server' / 'index.js').exists():
                return candidate
        return exe_dir
    return Path(__file__).resolve().parent.parent


class ServiceManager:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.proc = None
        self.log_queue = queue.Queue()
        self._reader_thread = None

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, host: str, port: str):
        if self.is_running():
            return False, '服务已经在运行。'

        node_bin = shutil.which('node')
        if not node_bin:
            return False, '未找到 node 命令，请先安装 Node.js 并加入 PATH。'

        server_js = self.root_dir / 'server' / 'index.js'
        if not server_js.exists():
            return False, f'未找到服务入口: {server_js}'

        env = os.environ.copy()
        env['SDENV_HOST'] = host.strip() or DEFAULT_HOST
        env['SDENV_PORT'] = str(port).strip() or DEFAULT_PORT

        create_flags = 0
        if os.name == 'nt':
            create_flags = subprocess.CREATE_NO_WINDOW

        try:
            self.proc = subprocess.Popen(
                [node_bin, str(server_js)],
                cwd=str(self.root_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=create_flags,
            )
        except Exception as e:
            self.proc = None
            return False, f'启动失败: {e}'

        self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self._reader_thread.start()
        return True, '服务启动中...'

    def stop(self):
        if not self.is_running():
            return True, '服务未运行。'

        try:
            if os.name == 'nt':
                self.proc.terminate()
            else:
                self.proc.send_signal(signal.SIGTERM)
            self.proc.wait(timeout=8)
            msg = '服务已停止。'
        except Exception:
            try:
                self.proc.kill()
                self.proc.wait(timeout=3)
            except Exception:
                pass
            msg = '服务已强制停止。'
        finally:
            self.proc = None
        return True, msg

    def _read_output(self):
        if not self.proc or not self.proc.stdout:
            return
        for line in self.proc.stdout:
            if line:
                clean = ANSI_ESCAPE_RE.sub('', line.rstrip('\r\n'))
                clean = CONTROL_CHARS_RE.sub('', clean)
                self.log_queue.put(clean)

    @staticmethod
    def health(host: str, port: str, timeout=3):
        if urllib is None:
            return False, 'urllib 模块不可用'
        url = f'http://{host}:{port}/api/health'
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                return resp.status == 200, resp.read().decode('utf-8', errors='replace')
        except Exception as e:
            return False, str(e)


class App:
    def __init__(self, win: tk.Tk):
        self.win = win
        self.win.title(APP_TITLE)
        self.win.geometry('880x620')
        self.win.minsize(840, 560)

        self.root_dir = project_root()
        self.manager = ServiceManager(self.root_dir)

        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        self.port_var = tk.StringVar(value=DEFAULT_PORT)
        self.status_var = tk.StringVar(value='未启动')
        self.health_var = tk.StringVar(value='未检测')

        self._build_ui()
        self._flush_logs_loop()
        self._poll_process_loop()
        self.win.protocol('WM_DELETE_WINDOW', self._on_close)
        if AUTO_START_ON_OPEN:
            self.win.after(200, self.start_service)

    def _build_ui(self):
        top = tk.Frame(self.win)
        top.pack(fill='x', padx=12, pady=10)

        tk.Label(top, text='Host:').grid(row=0, column=0, sticky='w')
        tk.Entry(top, textvariable=self.host_var, width=16).grid(row=0, column=1, sticky='w', padx=(6, 12))

        tk.Label(top, text='Port:').grid(row=0, column=2, sticky='w')
        tk.Entry(top, textvariable=self.port_var, width=10).grid(row=0, column=3, sticky='w', padx=(6, 12))

        tk.Button(top, text='启动服务', width=12, command=self.start_service).grid(row=0, column=4, padx=6)
        tk.Button(top, text='停止服务', width=12, command=self.stop_service).grid(row=0, column=5, padx=6)
        tk.Button(top, text='健康检查', width=12, command=self.check_health).grid(row=0, column=6, padx=6)

        info = tk.Frame(self.win)
        info.pack(fill='x', padx=12)
        tk.Label(info, text=f'项目目录: {self.root_dir}').pack(anchor='w')
        tk.Label(info, textvariable=self.status_var).pack(anchor='w')
        tk.Label(info, textvariable=self.health_var).pack(anchor='w')

        cmd_box = tk.LabelFrame(self.win, text='Python 调用示例')
        cmd_box.pack(fill='x', padx=12, pady=(10, 8))
        self.sample_text = tk.Text(cmd_box, height=5, wrap='none')
        self.sample_text.pack(fill='x', padx=8, pady=8)
        self.sample_text.configure(state='disabled')
        self._refresh_python_sample()

        log_box = tk.LabelFrame(self.win, text='服务日志')
        log_box.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        self.log_text = scrolledtext.ScrolledText(log_box, wrap='word')
        self.log_text.pack(fill='both', expand=True, padx=8, pady=8)
        self.log_text.configure(state='disabled')

    def _refresh_python_sample(self):
        host = self.host_var.get().strip() or DEFAULT_HOST
        port = self.port_var.get().strip() or DEFAULT_PORT
        sample = (
            'from sdenv_client import SdenvClient\n'
            f"client = SdenvClient(host='{host}', port={port})\n"
            "print(client.health())\n"
            "print(client.crack_url('http://www.customs.gov.cn/'))\n"
        )
        self.sample_text.configure(state='normal')
        self.sample_text.delete('1.0', tk.END)
        self.sample_text.insert('1.0', sample)
        self.sample_text.configure(state='disabled')

    def append_log(self, text: str):
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, text + '\n')
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def start_service(self):
        host = self.host_var.get().strip() or DEFAULT_HOST
        port = self.port_var.get().strip() or DEFAULT_PORT
        if not port.isdigit():
            messagebox.showerror('参数错误', '端口必须是数字。')
            return

        ok, msg = self.manager.start(host, port)
        self.status_var.set(f'状态: {msg}')
        self.append_log(msg)
        self._refresh_python_sample()
        if not ok:
            messagebox.showerror('启动失败', msg)
            return
        self._wait_health_ready(host, port)

    def _wait_health_ready(self, host: str, port: str):
        def worker():
            deadline = time.time() + DEFAULT_HEALTH_TIMEOUT_SEC
            while time.time() < deadline and self.manager.is_running():
                ok, payload = self.manager.health(host, port, timeout=2)
                if ok:
                    self.win.after(0, lambda: self.health_var.set(f'健康检查: OK {payload}'))
                    self.win.after(0, lambda: self.status_var.set('状态: 运行中'))
                    return
                time.sleep(0.7)
            self.win.after(0, lambda: self.health_var.set('健康检查: 未就绪，请查看日志'))
        threading.Thread(target=worker, daemon=True).start()

    def stop_service(self):
        ok, msg = self.manager.stop()
        self.status_var.set(f'状态: {msg}')
        self.health_var.set('健康检查: 未检测')
        self.append_log(msg)
        if not ok:
            messagebox.showwarning('停止失败', msg)

    def check_health(self):
        host = self.host_var.get().strip() or DEFAULT_HOST
        port = self.port_var.get().strip() or DEFAULT_PORT
        ok, payload = self.manager.health(host, port)
        if ok:
            self.health_var.set(f'健康检查: OK {payload}')
        else:
            self.health_var.set(f'健康检查: FAIL {payload}')
        self._refresh_python_sample()

    def _flush_logs_loop(self):
        try:
            while True:
                line = self.manager.log_queue.get_nowait()
                self.append_log(line)
        except queue.Empty:
            pass
        self.win.after(120, self._flush_logs_loop)

    def _poll_process_loop(self):
        if self.manager.proc and self.manager.proc.poll() is not None:
            code = self.manager.proc.returncode
            self.manager.proc = None
            self.status_var.set(f'状态: 进程已退出 (code={code})')
            self.append_log(f'服务进程已退出，退出码: {code}')
        self.win.after(500, self._poll_process_loop)

    def _on_close(self):
        if self.manager.is_running():
            if not messagebox.askyesno('退出确认', '服务仍在运行，是否先停止服务再退出？'):
                return
            self.manager.stop()
        self.win.destroy()


def main():
    win = tk.Tk()
    app = App(win)
    app.append_log('sdenv GUI 已启动。')
    app.append_log(f'项目目录: {app.root_dir}')
    win.mainloop()


if __name__ == '__main__':
    main()
