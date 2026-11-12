"""在当前受限沙箱环境里安装 Python 依赖的辅助脚本。

Windows 上 Python 的 os.mkdir(path, mode) 在 mode 为 0o700 这类「仅属主」权限时
会写入一条受限的安全描述符，沙箱进程随后无法在该目录里创建文件（pip 用到的
tempfile.mkdtemp 正是 0o700），于是报 `Permission denied`。这里把目录创建统一
改为默认权限，再转交 pip 执行。

用法：
    python scripts/pip_install.py install -r backend/requirements.txt --target backend/.deps
（参数原样传给 pip install）
"""

from __future__ import annotations

import os
import runpy
import sys
import tempfile

_real_mkdir = os.mkdir
_real_mkdtemp = tempfile.mkdtemp


def _mkdir(path, mode=0o777, *args, **kwargs):
    return _real_mkdir(path, 0o777, *args, **kwargs)


def _mkdtemp(suffix=None, prefix=None, dir=None):
    if prefix is None:
        prefix = tempfile.gettempprefix()
    if suffix is None:
        suffix = ""
    if dir is None:
        dir = tempfile.gettempdir()
    names = tempfile._get_candidate_names()
    for _ in range(tempfile.TMP_MAX):
        path = os.path.join(dir, prefix + next(names) + suffix)
        try:
            _real_mkdir(path, 0o777)
        except FileExistsError:
            continue
        return path
    raise FileExistsError("No usable temporary directory name found")


os.mkdir = _mkdir
tempfile.mkdtemp = _mkdtemp

# 去掉代理设置，避免本地代理未启动时 pip 直接失败
for key in list(os.environ):
    if "proxy" in key.lower():
        os.environ.pop(key, None)

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] != "install":
        args = ["install", *args]
    sys.argv = ["pip", *args]
    runpy.run_module("pip", run_name="__main__")
