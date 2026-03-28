#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetPulse GUI - Windows Edition
Author: Based on SyunSS/NetPulse_MutilPingTool
GUI Edition: v2 (Cron Wizard + Multi-Theme)

依赖安装：
    pip install customtkinter croniter
"""

import subprocess
import sys
import os
import time
import re
import configparser
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# 用于强制终止子进程
_active_processes = set()
_process_lock = threading.Lock()

THEMES = {
    "暗夜极客": {
        "mode": "dark",
        "bg_dark":       "#0d1117",
        "bg_card":       "#161b22",
        "bg_input":      "#21262d",
        "border":        "#30363d",
        "accent":        "#2d9bf0",
        "accent_hover":  "#58b4f8",
        "success":       "#3fb950",
        "warning":       "#d29922",
        "danger":        "#f85149",
        "text_primary":  "#e6edf3",
        "text_secondary":"#8b949e",
        "ping_ok":       "#3fb950",
        "ping_slow":     "#d29922",
        "ping_fail":     "#f85149",
        "ping_icmp":     "#2d9bf0",
        "ping_tcp":      "#a371f7",
    },
    "深海蓝": {
        "mode": "dark",
        "bg_dark":       "#050d1a",
        "bg_card":       "#0a1628",
        "bg_input":      "#0f2040",
        "border":        "#1a3a60",
        "accent":        "#00b4d8",
        "accent_hover":  "#48cae4",
        "success":       "#06d6a0",
        "warning":       "#ffd166",
        "danger":        "#ef476f",
        "text_primary":  "#caf0f8",
        "text_secondary":"#5e9fc0",
        "ping_ok":       "#06d6a0",
        "ping_slow":     "#ffd166",
        "ping_fail":     "#ef476f",
        "ping_icmp":     "#00b4d8",
        "ping_tcp":      "#c77dff",
    },
    "赛博紫": {
        "mode": "dark",
        "bg_dark":       "#0c001a",
        "bg_card":       "#160030",
        "bg_input":      "#200045",
        "border":        "#3d006b",
        "accent":        "#bf5af2",
        "accent_hover":  "#d07ef7",
        "success":       "#30e3ca",
        "warning":       "#f9c74f",
        "danger":        "#f94144",
        "text_primary":  "#f0e0ff",
        "text_secondary":"#9966cc",
        "ping_ok":       "#30e3ca",
        "ping_slow":     "#f9c74f",
        "ping_fail":     "#f94144",
        "ping_icmp":     "#bf5af2",
        "ping_tcp":      "#f72585",
    },
    "抹茶绿": {
        "mode": "dark",
        "bg_dark":       "#050f08",
        "bg_card":       "#0b1e10",
        "bg_input":      "#122b18",
        "border":        "#1f4a29",
        "accent":        "#52b788",
        "accent_hover":  "#74c69d",
        "success":       "#95d5b2",
        "warning":       "#e9c46a",
        "danger":        "#e76f51",
        "text_primary":  "#d8f3dc",
        "text_secondary":"#74a57f",
        "ping_ok":       "#95d5b2",
        "ping_slow":     "#e9c46a",
        "ping_fail":     "#e76f51",
        "ping_icmp":     "#52b788",
        "ping_tcp":      "#b7e4c7",
    },
    "浅色简约": {
        "mode": "light",
        "bg_dark":       "#f0f2f5",
        "bg_card":       "#ffffff",
        "bg_input":      "#f6f8fa",
        "border":        "#d0d7de",
        "accent":        "#0969da",
        "accent_hover":  "#218bff",
        "success":       "#1a7f37",
        "warning":       "#9a6700",
        "danger":        "#d1242f",
        "text_primary":  "#1f2328",
        "text_secondary":"#636c76",
        "ping_ok":       "#1a7f37",
        "ping_slow":     "#9a6700",
        "ping_fail":     "#d1242f",
        "ping_icmp":     "#0969da",
        "ping_tcp":      "#8250df",
    },
}

CURRENT_THEME = "暗夜极客"

def C(key):
    """全局取当前主题色"""
    return THEMES[CURRENT_THEME][key]


# ============================================================
# 核心逻辑（纯函数，无 UI 依赖）
# ============================================================

def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()


def load_config(base_dir=None):
    d = base_dir or BASE_DIR
    cfg = configparser.ConfigParser()
    cfg_path = os.path.join(d, "config.ini")
    if os.path.exists(cfg_path):
        cfg.read(cfg_path, encoding="utf-8")
    defaults = {
        "PingCount": "4", "TcpingCount": "4",
        "DefaultTCPPort": "443", "Threads": "5", "InputFile": "iplist.txt",
    }
    if not cfg.has_section("GENERAL"):
        cfg.add_section("GENERAL")
    for k, v in defaults.items():
        if not cfg.has_option("GENERAL", k):
            cfg.set("GENERAL", k, v)
    if not cfg.has_section("CRON"):
        cfg.add_section("CRON")
    if not cfg.has_option("CRON", "Timing"):
        cfg.set("CRON", "Timing", "")
    return cfg


def save_config(cfg, base_dir=None):
    d = base_dir or BASE_DIR
    with open(os.path.join(d, "config.ini"), "w", encoding="utf-8") as f:
        cfg.write(f)


def load_targets(filepath):
    targets = []
    if not os.path.exists(filepath):
        return targets
    with open(filepath, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            host, port = None, None
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                host, port = parts[0], int(parts[1])
            elif ":" in line and not line.startswith("["):
                h, p = line.rsplit(":", 1)
                if p.isdigit():
                    host, port = h, int(p)
                else:
                    host = line
            else:
                host = line
            targets.append((host, port))
    return targets


def run_ping(host, count, timeout_mult=3):
    try:
        cmd = ["ping", "-n", str(count), host]
        # Windows: 隐藏命令行窗口
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        out = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, timeout=count * timeout_mult,
            startupinfo=startupinfo
        ).decode("gbk", errors="ignore")
        loss_match = re.search(r"\((\d+)%\s*丢失\)", out)
        avg_match  = re.search(r"平均\s*=\s*(\d+)ms", out)
        loss = f"{loss_match.group(1)}%" if loss_match else "100%"
        avg  = avg_match.group(1) if avg_match else "Timeout"
        return avg, loss
    except Exception:
        return "Timeout", "100%"


def run_ping_with_progress(host, count, progress_callback=None, timeout_mult=3, stop_event=None):
    """带进度回调的 ping 函数"""
    proc = None
    try:
        cmd = ["ping", "-n", str(count), host]
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        # 使用 Popen 实时获取输出
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            startupinfo=startupinfo
        )
        
        # 注册到全局进程集合
        with _process_lock:
            _active_processes.add(proc)
        
        out_lines = []
        reply_count = 0
        
        for line in iter(proc.stdout.readline, b''):
            # 检查是否需要停止
            if stop_event and stop_event.is_set():
                proc.terminate()
                break
            
            line_str = line.decode("gbk", errors="ignore")
            out_lines.append(line_str)
            
            # 检测回复包
            if "来自" in line_str or "Reply from" in line_str:
                reply_count += 1
                if progress_callback:
                    progress_callback(reply_count, count)
        
        proc.wait(timeout=count * timeout_mult)
        out = "".join(out_lines)
        
        loss_match = re.search(r"\((\d+)%\s*丢失\)", out)
        avg_match  = re.search(r"平均\s*=\s*(\d+)ms", out)
        loss = f"{loss_match.group(1)}%" if loss_match else "100%"
        avg  = avg_match.group(1) if avg_match else "Timeout"
        return avg, loss
    except Exception:
        return "Timeout", "100%"
    finally:
        if proc:
            with _process_lock:
                _active_processes.discard(proc)
            try:
                if proc.poll() is None:
                    proc.terminate()
            except:
                pass


def run_tcping(host, port, count, base_dir, timeout_mult=3):
    exe = os.path.join(base_dir, "tcping.exe")
    if not os.path.exists(exe):
        return "N/A(no tcping.exe)", "N/A"
    cmd = [exe, "-n", str(count), host, str(port)]
    times, loss = [], "100%"
    try:
        # Windows: 隐藏命令行窗口
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=count * timeout_mult, text=True, encoding="utf-8", errors="ignore",
            startupinfo=startupinfo
        )
        out = proc.stdout
        for line in out.splitlines():
            if "time=" in line.lower():
                try:
                    ms = float(
                        line.lower().split("time=")[1]
                        .replace("ms", "").strip().split()[0]
                    )
                    times.append(ms)
                except Exception:
                    pass
        fail_m = re.search(r"\(([\d\.]+)%\s*fail\)", out, re.IGNORECASE)
        if fail_m:
            loss = f"{fail_m.group(1)}%"
    except Exception:
        return "Timeout", "100%"
    if not times:
        return "Timeout", loss
    return str(int(sum(times) / len(times))), loss


def run_tcping_with_progress(host, port, count, base_dir, progress_callback=None, timeout_mult=3, stop_event=None):
    """带进度回调的 tcping 函数"""
    exe = os.path.join(base_dir, "tcping.exe")
    if not os.path.exists(exe):
        return "N/A(no tcping.exe)", "N/A"
    cmd = [exe, "-n", str(count), host, str(port)]
    times, loss = [], "100%"
    proc = None
    try:
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        
        # 使用 Popen 实时获取输出
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            startupinfo=startupinfo, text=True, encoding="utf-8", errors="ignore"
        )
        
        # 注册到全局进程集合
        with _process_lock:
            _active_processes.add(proc)
        
        out_lines = []
        reply_count = 0
        
        for line in iter(proc.stdout.readline, ''):
            # 检查是否需要停止
            if stop_event and stop_event.is_set():
                proc.terminate()
                break
            
            out_lines.append(line)
            
            # 检测回复包
            if "time=" in line.lower():
                reply_count += 1
                if progress_callback:
                    progress_callback(reply_count, count)
                try:
                    ms = float(
                        line.lower().split("time=")[1]
                        .replace("ms", "").strip().split()[0]
                    )
                    times.append(ms)
                except Exception:
                    pass
        
        proc.wait(timeout=count * timeout_mult)
        out = "".join(out_lines)
        
        fail_m = re.search(r"\(([\d\.]+)%\s*fail\)", out, re.IGNORECASE)
        if fail_m:
            loss = f"{fail_m.group(1)}%"
    except Exception:
        return "Timeout", "100%"
    finally:
        if proc:
            with _process_lock:
                _active_processes.discard(proc)
            try:
                if proc.poll() is None:
                    proc.terminate()
            except:
                pass
    if not times:
        return "Timeout", loss
    return str(int(sum(times) / len(times))), loss


def worker_func(idx, host, port, mode, cfg, base_dir):
    ping_count   = cfg.getint("GENERAL", "PingCount",      fallback=4)
    tcp_count    = cfg.getint("GENERAL", "TcpingCount",    fallback=4)
    default_port = cfg.getint("GENERAL", "DefaultTCPPort", fallback=443)
    if mode == "1":
        avg, loss = run_ping(host, ping_count)
        proto = "ICMP"
    elif mode == "2":
        p = port if port else default_port
        avg, loss = run_tcping(host, p, tcp_count, base_dir)
        proto = f"TCP:{p}"
    else:
        if port:
            avg, loss = run_tcping(host, port, tcp_count, base_dir)
            proto = f"TCP:{port}"
        else:
            avg, loss = run_ping(host, ping_count)
            proto = "ICMP"
    return idx, host, proto, avg, loss


def worker_func_with_progress(idx, host, port, mode, cfg, base_dir, result_q, ping_count, tcp_count, stop_event):
    """带进度回调的 worker 函数"""
    default_port = cfg.getint("GENERAL", "DefaultTCPPort", fallback=443)
    
    def progress_callback(current, total):
        result_q.put(("update_active", host, current, total))
    
    if mode == "1":
        avg, loss = run_ping_with_progress(host, ping_count, progress_callback, stop_event=stop_event)
        proto = "ICMP"
    elif mode == "2":
        p = port if port else default_port
        avg, loss = run_tcping_with_progress(host, p, tcp_count, base_dir, progress_callback, stop_event=stop_event)
        proto = f"TCP:{p}"
    else:
        if port:
            avg, loss = run_tcping_with_progress(host, port, tcp_count, base_dir, progress_callback, stop_event=stop_event)
            proto = f"TCP:{port}"
        else:
            avg, loss = run_ping_with_progress(host, ping_count, progress_callback, stop_event=stop_event)
            proto = "ICMP"
    return idx, host, proto, avg, loss


# ============================================================
# Cron 自然语言解析
# ============================================================

def cron_to_human(expr: str) -> str:
    """把 cron 表达式翻译成中文自然语言描述"""
    expr = expr.strip()
    if not expr:
        return "单次运行（不重复）"
    parts = expr.split()
    if len(parts) != 5:
        return f"自定义表达式：{expr}"

    minute, hour, dom, month, dow = parts

    # 常用快速匹配
    patterns = [
        # 每 N 分钟
        (r"^\*/(\d+)$", None, None, None, None,
         lambda m: f"每隔 {m.group(1)} 分钟执行一次"),
        # 每小时整点
        ("0", "*", "*", "*", "*",
         lambda: "每小时整点执行一次"),
        # 每天某时整点
        (r"^0$", r"^(\d+)$", "*", "*", "*",
         lambda hm: f"每天 {hm.group(1)}:00 执行一次"),
        # 每天某时某分
        (r"^(\d+)$", r"^(\d+)$", "*", "*", "*",
         lambda mm, hm: f"每天 {hm.group(1)}:{int(mm.group(1)):02d} 执行一次"),
        # 每 N 小时
        ("0", r"^\*/(\d+)$", "*", "*", "*",
         lambda hm: f"每隔 {hm.group(1)} 小时执行一次"),
    ]

    DOW_CN = {"0":"周日","1":"周一","2":"周二","3":"周三",
              "4":"周四","5":"周五","6":"周六","7":"周日"}

    # 逐一手动判断常见模式
    # 每 N 分钟
    m = re.match(r"^\*/(\d+)$", minute)
    if m and hour == "*" and dom == "*" and month == "*" and dow == "*":
        n = int(m.group(1))
        return f"每隔 {n} 分钟执行一次"

    # 每小时 N 分
    m = re.match(r"^(\d+)$", minute)
    if m and hour == "*" and dom == "*" and month == "*" and dow == "*":
        return f"每小时第 {m.group(1)} 分钟执行一次"

    # 每天 H:M
    mm = re.match(r"^(\d+)$", minute)
    hm = re.match(r"^(\d+)$", hour)
    if mm and hm and dom == "*" and month == "*" and dow == "*":
        return f"每天 {hm.group(1)}:{int(mm.group(1)):02d} 执行一次"

    # 每隔 N 小时（分钟=0）
    if minute == "0":
        hm2 = re.match(r"^\*/(\d+)$", hour)
        if hm2 and dom == "*" and month == "*" and dow == "*":
            return f"每隔 {hm2.group(1)} 小时执行一次"

    # 每周几 H:M
    mm = re.match(r"^(\d+)$", minute)
    hm = re.match(r"^(\d+)$", hour)
    dm = re.match(r"^(\d)$", dow)
    if mm and hm and dom == "*" and month == "*" and dm:
        day_cn = DOW_CN.get(dm.group(1), f"周{dm.group(1)}")
        return f"每{day_cn} {hm.group(1)}:{int(mm.group(1)):02d} 执行一次"

    # 每月某天 H:M
    mm = re.match(r"^(\d+)$", minute)
    hm = re.match(r"^(\d+)$", hour)
    dm = re.match(r"^(\d+)$", dom)
    if mm and hm and dm and month == "*" and dow == "*":
        return f"每月 {dm.group(1)} 日 {hm.group(1)}:{int(mm.group(1)):02d} 执行一次"

    return f"自定义计划：{expr}"


# ============================================================
# Cron 可视化编辑弹窗
# ============================================================

class CronWizard(ctk.CTkToplevel):
    """
    点击「设置」按钮弹出的 Cron 向导窗口。
    包含：快速预设 + 5 个字段分别下拉选择 + 实时自然语言预览。
    """
    PRESETS = [
        ("每 1 分钟",     "*/1 * * * *"),
        ("每 5 分钟",     "*/5 * * * *"),
        ("每 10 分钟",    "*/10 * * * *"),
        ("每 15 分钟",    "*/15 * * * *"),
        ("每 30 分钟",    "*/30 * * * *"),
        ("每 1 小时",     "0 */1 * * *"),
        ("每 2 小时",     "0 */2 * * *"),
        ("每 6 小时",     "0 */6 * * *"),
        ("每天 0 点",     "0 0 * * *"),
        ("每天 6 点",     "0 6 * * *"),
        ("每天 12 点",    "0 12 * * *"),
        ("每天 18 点",    "0 18 * * *"),
        ("每天 22 点",    "0 22 * * *"),
        ("每周一 9 点",   "0 9 * * 1"),
        ("每月 1 日 0 点","0 0 1 * *"),
    ]

    # 字段候选值
    MINUTE_OPTS = ["*"] + [f"*/{n}" for n in [1,2,5,10,15,20,30]] + [str(i) for i in range(0, 60)]
    HOUR_OPTS   = ["*"] + [f"*/{n}" for n in [1,2,3,4,6,8,12]] + [str(i) for i in range(0, 24)]
    DOM_OPTS    = ["*"] + [str(i) for i in range(1, 32)]
    MONTH_OPTS  = ["*"] + [str(i) for i in range(1, 13)]
    DOW_OPTS    = ["*", "0 (周日)", "1 (周一)", "2 (周二)", "3 (周三)",
                   "4 (周四)", "5 (周五)", "6 (周六)"]

    def __init__(self, parent, current_expr: str, callback):
        super().__init__(parent)
        self.callback = callback
        self.title("⏰ Cron 定时设置")
        self.geometry("520x560")
        self.resizable(False, False)
        self.configure(fg_color=C("bg_dark"))
        self.attributes("-topmost", True)
        self.grab_set()

        self._expr_var = tk.StringVar(value=current_expr or "*/5 * * * *")
        self._build()
        self._parse_expr_to_fields(self._expr_var.get())
        self._update_preview()

    def _build(self):
        pad = {"padx": 16, "pady": 6}

        # 标题
        ctk.CTkLabel(
            self, text="⏰  定时任务设置",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=C("accent")
        ).pack(pady=(16, 4))
        ctk.CTkLabel(
            self, text="设置完成后点击「确定」应用",
            font=ctk.CTkFont(size=11), text_color=C("text_secondary")
        ).pack()

        sep = ctk.CTkFrame(self, fg_color=C("border"), height=1)
        sep.pack(fill="x", padx=16, pady=10)

        # ── 快速预设 ──────────────────────────────
        ctk.CTkLabel(self, text="快速预设", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C("text_secondary")).pack(anchor="w", padx=16)

        preset_frame = ctk.CTkFrame(self, fg_color=C("bg_card"), corner_radius=8)
        preset_frame.pack(fill="x", padx=16, pady=(4, 10))

        # 分两列显示预设按钮
        preset_frame.columnconfigure((0, 1, 2, 3), weight=1)
        for i, (label, expr) in enumerate(self.PRESETS):
            row, col = divmod(i, 4)
            btn = ctk.CTkButton(
                preset_frame, text=label, height=26,
                font=ctk.CTkFont(size=11),
                fg_color=C("bg_input"), hover_color=C("border"),
                border_width=1, border_color=C("border"),
                text_color=C("text_primary"),
                command=lambda e=expr: self._apply_preset(e)
            )
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="ew")

        sep2 = ctk.CTkFrame(self, fg_color=C("border"), height=1)
        sep2.pack(fill="x", padx=16, pady=4)

        # ── 精细调整（5 个字段）──────────────────
        ctk.CTkLabel(self, text="精细调整", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C("text_secondary")).pack(anchor="w", padx=16)

        fields_frame = ctk.CTkFrame(self, fg_color=C("bg_card"), corner_radius=8)
        fields_frame.pack(fill="x", padx=16, pady=(4, 8))
        fields_frame.columnconfigure((0,1,2,3,4), weight=1)

        field_defs = [
            ("分钟", self.MINUTE_OPTS),
            ("小时", self.HOUR_OPTS),
            ("日",   self.DOM_OPTS),
            ("月",   self.MONTH_OPTS),
            ("周",   self.DOW_OPTS),
        ]
        self._field_vars = []
        for col, (label, opts) in enumerate(field_defs):
            ctk.CTkLabel(
                fields_frame, text=label,
                font=ctk.CTkFont(size=11), text_color=C("text_secondary")
            ).grid(row=0, column=col, padx=4, pady=(8,2))
            var = tk.StringVar(value="*")
            self._field_vars.append(var)
            cb = ctk.CTkComboBox(
                fields_frame, values=opts, variable=var,
                width=88, height=30,
                fg_color=C("bg_input"), border_color=C("border"),
                button_color=C("border"), button_hover_color=C("accent"),
                dropdown_fg_color=C("bg_card"),
                dropdown_text_color=C("text_primary"),
                text_color=C("text_primary"),
                font=ctk.CTkFont(family="Consolas", size=12),
                command=lambda val, v=var: self._on_field_change()
            )
            cb.grid(row=1, column=col, padx=4, pady=(0,8))
            var.trace_add("write", lambda *a: self._on_field_change())

        # ── 表达式预览 ──────────────────────────
        expr_frame = ctk.CTkFrame(self, fg_color=C("bg_card"), corner_radius=8)
        expr_frame.pack(fill="x", padx=16, pady=4)
        expr_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            expr_frame, text="表达式：",
            font=ctk.CTkFont(size=12), text_color=C("text_secondary")
        ).grid(row=0, column=0, padx=(12, 4), pady=10)

        self._expr_entry = ctk.CTkEntry(
            expr_frame, textvariable=self._expr_var,
            height=30, fg_color=C("bg_input"), border_color=C("border"),
            font=ctk.CTkFont(family="Consolas", size=13),
            text_color=C("accent")
        )
        self._expr_entry.grid(row=0, column=1, padx=(0,12), pady=10, sticky="ew")
        self._expr_var.trace_add("write", lambda *a: self._on_expr_typed())

        # ── 自然语言预览 ─────────────────────────
        self._preview_lbl = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=C("success"),
            wraplength=460
        )
        self._preview_lbl.pack(pady=6)

        # ── 底部按钮 ──────────────────────────────
        sep3 = ctk.CTkFrame(self, fg_color=C("border"), height=1)
        sep3.pack(fill="x", padx=16, pady=(4,0))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=10)
        btn_row.columnconfigure((0,1,2), weight=1)

        ctk.CTkButton(
            btn_row, text="清空（单次运行）", height=34,
            fg_color=C("bg_input"), hover_color=C("border"),
            border_width=1, border_color=C("border"),
            font=ctk.CTkFont(size=12), text_color=C("text_primary"),
            command=self._clear
        ).grid(row=0, column=0, padx=(0,6), sticky="ew")

        ctk.CTkButton(
            btn_row, text="取消", height=34,
            fg_color=C("bg_input"), hover_color=C("border"),
            border_width=1, border_color=C("border"),
            font=ctk.CTkFont(size=12), text_color=C("text_primary"),
            command=self.destroy
        ).grid(row=0, column=1, padx=6, sticky="ew")

        ctk.CTkButton(
            btn_row, text="✔ 确定", height=34,
            fg_color=C("accent"), hover_color=C("accent_hover"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._confirm
        ).grid(row=0, column=2, padx=(6,0), sticky="ew")

    # ── 内部逻辑 ───────────────────────────────────
    def _apply_preset(self, expr):
        self._expr_var.set(expr)
        self._parse_expr_to_fields(expr)
        self._update_preview()

    def _parse_expr_to_fields(self, expr):
        """把表达式拆回 5 个字段"""
        parts = expr.strip().split()
        if len(parts) != 5:
            return
        for i, part in enumerate(parts):
            raw = part
            # dow 字段：把数字映射到带中文的选项
            if i == 4:
                dow_map = {
                    "0": "0 (周日)", "1": "1 (周一)", "2": "2 (周二)",
                    "3": "3 (周三)", "4": "4 (周四)", "5": "5 (周五)",
                    "6": "6 (周六)", "7": "7 (周日)",
                }
                raw = dow_map.get(part, part)
            self._field_vars[i].set(raw)

    def _fields_to_expr(self):
        """把 5 个字段合并成表达式"""
        parts = []
        for i, var in enumerate(self._field_vars):
            val = var.get().split()[0]  # 去掉中文注释部分 "0 (周日)" → "0"
            parts.append(val)
        return " ".join(parts)

    def _on_field_change(self):
        expr = self._fields_to_expr()
        self._expr_var.set(expr)
        self._update_preview()

    def _on_expr_typed(self):
        """用户手动修改表达式框时，同步字段并更新预览"""
        self._parse_expr_to_fields(self._expr_var.get())
        self._update_preview()

    def _update_preview(self):
        expr = self._expr_var.get().strip()
        human = cron_to_human(expr)
        self._preview_lbl.configure(text=f"📌 {human}")

    def _clear(self):
        self._expr_var.set("")
        self._preview_lbl.configure(text="📌 单次运行（不重复）")

    def _confirm(self):
        self.callback(self._expr_var.get().strip())
        self.destroy()


# ============================================================
# 主应用
# ============================================================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        global CURRENT_THEME

        self.title("NetPulse  ·  Multi-Ping Tool")
        self.geometry("1120x760")
        self.minsize(900, 600)

        self.cfg        = load_config()
        self.base_dir   = tk.StringVar(value=BASE_DIR)
        self.mode_var   = tk.StringVar(value="3")
        self.running    = False
        self.stop_flag  = threading.Event()
        self.result_q   = queue.Queue()
        self.targets    = []
        self._theme_name = CURRENT_THEME
        self._myip_info = None  # 保存获取到的 IP 信息

        self._apply_ctk_theme()
        self._build_ui()
        self._reload_all()
        self.after(100, self._poll_queue)
        self._fetch_myip()  # 启动时获取出口 IP

    # ── 获取出口 IP ─────────────────────────────────────────
    def _fetch_myip(self):
        """异步获取出口 IP 信息"""
        # 确保 _ip_lbl 已创建
        if not hasattr(self, "_ip_lbl") or self._ip_lbl is None:
            return
        
        # 重置为获取中状态
        self._ip_lbl.configure(text="🌐 获取中...")
        
        def fetch():
            try:
                # Windows: 隐藏命令行窗口
                startupinfo = None
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = subprocess.SW_HIDE
                
                proc = subprocess.run(
                    ["curl", "myip.ipip.net"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    startupinfo=startupinfo
                )
                info = proc.stdout.strip()
                if info:
                    # 简化显示，只取 IP 和地理位置
                    parts = info.split()
                    if len(parts) >= 2:
                        ip = parts[0]
                        location = " ".join(parts[1:]) if len(parts) > 1 else ""
                        return f"🌐 {ip} {location[:30]}"
                    return f"🌐 {info[:50]}"
            except Exception as e:
                print(f"[NetPulse] 获取 IP 失败: {e}")
                return None
        
        def update():
            result = fetch()
            # 使用 after 确保在主线程更新 UI
            self.after(0, lambda: self._update_ip_label(result))
        
        threading.Thread(target=update, daemon=True).start()
    
    def _update_ip_label(self, result):
        """在主线程更新 IP 标签"""
        if hasattr(self, "_ip_lbl") and self._ip_lbl is not None:
            if result:
                self._myip_info = result
                self._ip_lbl.configure(text=result)
            else:
                self._ip_lbl.configure(text="")

    # ── 主题 ────────────────────────────────────────────────
    def _apply_ctk_theme(self):
        mode = THEMES[self._theme_name]["mode"]
        ctk.set_appearance_mode(mode)
        self.configure(fg_color=C("bg_dark"))

    def _switch_theme(self, name):
        global CURRENT_THEME
        CURRENT_THEME = name
        self._theme_name = name
        # 销毁重建整个 UI 是最稳妥的做法
        for widget in self.winfo_children():
            widget.destroy()
        ctk.set_appearance_mode(THEMES[name]["mode"])
        self.configure(fg_color=C("bg_dark"))
        self._build_ui()
        self._reload_all()
        self._fetch_myip()  # 换主题后重新获取 IP

    # ── UI 总入口 ────────────────────────────────────────────
    def _build_ui(self):
        self._build_topbar()
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        main.columnconfigure(0, weight=0, minsize=316)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # 左侧改为可滚动容器，内容超出高度时自动出滚动条
        left = ctk.CTkScrollableFrame(
            main,
            fg_color="transparent",
            scrollbar_button_color=C("border"),
            scrollbar_button_hover_color=C("accent"),
            width=310,
        )
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self._build_left(left)

        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        self._build_right(right)

    # ── 顶栏 ────────────────────────────────────────────────
    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color=C("bg_card"), corner_radius=0, height=58)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar, text="⚡ NetPulse",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=C("accent")
        ).pack(side="left", padx=20)

        ctk.CTkLabel(
            bar, text="Multi-Ping Tool  ·  GUI Edition",
            font=ctk.CTkFont(size=12), text_color=C("text_secondary")
        ).pack(side="left", padx=4)

        # ── 出口 IP 显示（中间）──────────────────
        self._ip_lbl = ctk.CTkLabel(
            bar, text="🌐 获取中...",
            font=ctk.CTkFont(size=11),
            text_color=C("text_secondary")
        )
        self._ip_lbl.pack(side="left", padx=(20, 0))

        # ── 皮肤选择（右侧）──────────────────────
        right_bar = ctk.CTkFrame(bar, fg_color="transparent")
        right_bar.pack(side="right", padx=14)

        ctk.CTkLabel(right_bar, text="🎨 皮肤:",
                     font=ctk.CTkFont(size=12),
                     text_color=C("text_secondary")).pack(side="left", padx=(0,6))

        theme_names = list(THEMES.keys())
        self._theme_cb = ctk.CTkComboBox(
            right_bar,
            values=theme_names,
            width=120, height=30,
            fg_color=C("bg_input"), border_color=C("border"),
            button_color=C("border"), button_hover_color=C("accent"),
            dropdown_fg_color=C("bg_card"),
            dropdown_text_color=C("text_primary"),
            text_color=C("text_primary"),
            font=ctk.CTkFont(size=12),
            command=self._switch_theme
        )
        self._theme_cb.set(self._theme_name)
        self._theme_cb.pack(side="left", padx=(0, 14))

        # ── 工作目录 ──────────────────────────────
        ctk.CTkLabel(right_bar, text="工作目录:",
                     font=ctk.CTkFont(size=12),
                     text_color=C("text_secondary")).pack(side="left")

        self._dir_entry = ctk.CTkEntry(
            right_bar, textvariable=self.base_dir,
            width=220, height=30,
            fg_color=C("bg_input"), border_color=C("border"),
            font=ctk.CTkFont(size=11)
        )
        self._dir_entry.pack(side="left", padx=6)

        ctk.CTkButton(
            right_bar, text="浏览", width=52, height=30,
            command=self._browse_dir,
            fg_color=C("bg_input"), hover_color=C("border"),
            border_width=1, border_color=C("border"),
            font=ctk.CTkFont(size=11)
        ).pack(side="left")

    # ── 左侧面板 ─────────────────────────────────────────────
    def _build_left(self, parent):
        parent.columnconfigure(0, weight=1)

        # 模式选择
        self._card(parent, "🔀 测试模式", row=0)
        mode_f = ctk.CTkFrame(parent, fg_color=C("bg_card"), corner_radius=10)
        mode_f.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        for val, label, color in [
            ("1", "ICMP Ping",      C("ping_icmp")),
            ("2", "TCP Ping",       C("ping_tcp")),
            ("3", "混合模式 (推荐)", C("success")),
        ]:
            ctk.CTkRadioButton(
                mode_f, text=label, variable=self.mode_var, value=val,
                font=ctk.CTkFont(size=13),
                fg_color=color, hover_color=color,
                text_color=C("text_primary")
            ).pack(anchor="w", padx=14, pady=3)

        # 参数配置
        self._card(parent, "⚙️ 参数配置", row=2)
        cfg_f = ctk.CTkFrame(parent, fg_color=C("bg_card"), corner_radius=10)
        cfg_f.grid(row=3, column=0, sticky="ew", pady=(0, 5))
        cfg_f.columnconfigure(1, weight=1)

        fields = [
            ("Ping 次数",    "PingCount",       "4"),
            ("TCPing 次数",  "TcpingCount",      "4"),
            ("默认 TCP 端口","DefaultTCPPort",   "443"),
            ("线程数",       "Threads",          "5"),
        ]
        self._cfg_vars = {}
        for r, (label, key, default) in enumerate(fields):
            ctk.CTkLabel(cfg_f, text=label, font=ctk.CTkFont(size=12),
                         text_color=C("text_secondary")
                         ).grid(row=r, column=0, padx=(12,6), pady=3, sticky="w")
            var = tk.StringVar(value=self.cfg.get("GENERAL", key, fallback=default))
            self._cfg_vars[key] = var
            ctk.CTkEntry(
                cfg_f, textvariable=var, width=90, height=26,
                fg_color=C("bg_input"), border_color=C("border"),
                font=ctk.CTkFont(size=12)
            ).grid(row=r, column=1, padx=(0,12), pady=3, sticky="e")

        ctk.CTkButton(
            cfg_f, text="💾 保存配置", height=30,
            command=self._save_cfg,
            fg_color=C("accent"), hover_color=C("accent_hover"),
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=len(fields), column=0, columnspan=2,
               padx=12, pady=(4, 8), sticky="ew")

        # 目标列表
        self._card(parent, "📋 目标列表", row=4)
        tgt_f = ctk.CTkFrame(parent, fg_color=C("bg_card"), corner_radius=10)
        tgt_f.grid(row=5, column=0, sticky="ew", pady=(0, 5))
        tgt_f.columnconfigure(0, weight=1)

        path_f = ctk.CTkFrame(tgt_f, fg_color="transparent")
        path_f.grid(row=0, column=0, sticky="ew", padx=10, pady=(8,4))
        path_f.columnconfigure(0, weight=1)
        self._iplist_var = tk.StringVar(
            value=self.cfg.get("GENERAL", "InputFile", fallback="iplist.txt")
        )
        ctk.CTkEntry(
            path_f, textvariable=self._iplist_var, height=26,
            fg_color=C("bg_input"), border_color=C("border"),
            font=ctk.CTkFont(size=11)
        ).grid(row=0, column=0, sticky="ew", padx=(0,6))
        ctk.CTkButton(
            path_f, text="📂", width=32, height=26,
            command=self._browse_iplist,
            fg_color=C("bg_input"), hover_color=C("border"),
            border_width=1, border_color=C("border"),
            font=ctk.CTkFont(size=13)
        ).grid(row=0, column=1)

        # 目标列表文本框：固定高度 160，在可滚动容器内不需要随窗口伸缩
        self._iplist_text = ctk.CTkTextbox(
            tgt_f, height=160,
            fg_color=C("bg_input"), border_color=C("border"),
            border_width=1, font=ctk.CTkFont(family="Consolas", size=12),
            text_color=C("text_primary")
        )
        self._iplist_text.grid(row=1, column=0, sticky="ew", padx=10, pady=(0,3))

        ctk.CTkLabel(
            tgt_f, text="每行一个：IP / 域名 / IP 端口 / 域名:端口",
            font=ctk.CTkFont(size=10), text_color=C("text_secondary")
        ).grid(row=2, column=0, padx=10, sticky="w")

        btn_row = ctk.CTkFrame(tgt_f, fg_color="transparent")
        btn_row.grid(row=3, column=0, padx=10, pady=(3,8), sticky="ew")
        btn_row.columnconfigure((0,1), weight=1)

        for col, (text, cmd) in enumerate([
            ("📥 加载文件", self._load_iplist),
            ("💾 保存文件", self._save_iplist),
        ]):
            ctk.CTkButton(
                btn_row, text=text, height=28,
                command=cmd,
                fg_color=C("bg_input"), hover_color=C("border"),
                border_width=1, border_color=C("border"),
                font=ctk.CTkFont(size=12)
            ).grid(row=0, column=col, padx=(0,3) if col==0 else (3,0), sticky="ew")

        # Cron
        self._card(parent, "⏰ 定时任务", row=6)
        cron_f = ctk.CTkFrame(parent, fg_color=C("bg_card"), corner_radius=10)
        cron_f.grid(row=7, column=0, sticky="ew", pady=(0, 8))
        cron_f.columnconfigure(0, weight=1)

        cron_inner = ctk.CTkFrame(cron_f, fg_color="transparent")
        cron_inner.grid(row=0, column=0, sticky="ew", padx=10, pady=(8,4))
        cron_inner.columnconfigure(1, weight=1)

        ctk.CTkLabel(cron_inner, text="表达式:",
                     font=ctk.CTkFont(size=12),
                     text_color=C("text_secondary")
                     ).grid(row=0, column=0, padx=(0,8))

        self._cron_var = tk.StringVar(
            value=self.cfg.get("CRON", "Timing", fallback="")
        )
        self._cron_entry = ctk.CTkEntry(
            cron_inner, textvariable=self._cron_var,
            height=26, placeholder_text="留空=单次运行",
            fg_color=C("bg_input"), border_color=C("border"),
            font=ctk.CTkFont(family="Consolas", size=12)
        )
        self._cron_entry.grid(row=0, column=1, sticky="ew")

        ctk.CTkButton(
            cron_inner, text="🔧 设置", width=58, height=26,
            command=self._open_cron_wizard,
            fg_color=C("accent"), hover_color=C("accent_hover"),
            font=ctk.CTkFont(size=11, weight="bold")
        ).grid(row=0, column=2, padx=(8, 0))

        # 自然语言预览
        self._cron_human_lbl = ctk.CTkLabel(
            cron_f, text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=C("success"), wraplength=280
        )
        self._cron_human_lbl.grid(row=1, column=0, padx=12, pady=(2, 2), sticky="w")

        self._cron_status = ctk.CTkLabel(
            cron_f, text="● 未运行",
            font=ctk.CTkFont(size=11), text_color=C("text_secondary")
        )
        self._cron_status.grid(row=2, column=0, padx=12, pady=(0, 6), sticky="w")

        # 监听 cron_var 变化，实时更新自然语言
        self._cron_var.trace_add("write", lambda *a: self._refresh_cron_human())
        self._refresh_cron_human()

    # ── 右侧面板 ─────────────────────────────────────────────
    def _build_right(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(2, weight=1)

        # 控制按钮行
        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ctrl.columnconfigure(2, weight=1)

        self._run_btn = ctk.CTkButton(
            ctrl, text="▶  开始测试", width=140, height=38,
            command=self._start_test,
            fg_color=C("success"), hover_color=C("ping_ok"),
            font=ctk.CTkFont(size=14, weight="bold"), corner_radius=8
        )
        self._run_btn.grid(row=0, column=0, padx=(0,8))

        self._stop_btn = ctk.CTkButton(
            ctrl, text="⏹  停止", width=100, height=38,
            command=self._stop_test,
            fg_color=C("danger"), hover_color=C("ping_fail"),
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8, state="disabled"
        )
        self._stop_btn.grid(row=0, column=1, padx=(0,8))

        ctk.CTkButton(
            ctrl, text="🗑 清空", width=80, height=38,
            command=self._clear_output,
            fg_color=C("bg_card"), hover_color=C("border"),
            border_width=1, border_color=C("border"),
            font=ctk.CTkFont(size=13), corner_radius=8
        ).grid(row=0, column=2, sticky="w")

        ctk.CTkButton(
            ctrl, text="📤 导出结果", width=110, height=38,
            command=self._export_result,
            fg_color=C("bg_card"), hover_color=C("border"),
            border_width=1, border_color=C("border"),
            font=ctk.CTkFont(size=13), corner_radius=8
        ).grid(row=0, column=3, padx=(8,0))

        # 正在测试列表（实时进度）- 使用可滚动容器
        self._active_frame = ctk.CTkFrame(
            parent, fg_color=C("bg_card"),
            corner_radius=10, border_width=1, border_color=C("border")
        )
        self._active_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self._active_frame.grid_remove()  # 默认隐藏
        self._active_frame.columnconfigure(0, weight=1)
        
        active_hdr = ctk.CTkFrame(self._active_frame, fg_color=C("bg_input"),
                                  corner_radius=0, height=32)
        active_hdr.grid(row=0, column=0, sticky="ew")
        active_hdr.grid_propagate(False)
        ctk.CTkLabel(active_hdr, text="🔄 正在测试",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=C("accent")
                     ).pack(side="left", padx=12)
        
        # 使用可滚动框架，最大高度限制
        self._active_scroll = ctk.CTkScrollableFrame(
            self._active_frame,
            fg_color="transparent",
            scrollbar_button_color=C("border"),
            scrollbar_button_hover_color=C("accent"),
            height=120,  # 最大显示高度
        )
        self._active_scroll.grid(row=1, column=0, sticky="ew", padx=8, pady=8)
        
        # 使用网格布局支持多列
        self._active_container = ctk.CTkFrame(
            self._active_scroll, fg_color="transparent"
        )
        self._active_container.pack(fill="both", expand=True)
        
        self._active_widgets = {}  # host -> (frame, label, progress)
        self._active_cols = 2  # 默认列数
        
        # 绑定窗口大小变化事件，动态调整列数
        self.bind("<Configure>", self._on_window_resize)

        # 输出区域
        out_frame = ctk.CTkFrame(
            parent, fg_color=C("bg_card"),
            corner_radius=10, border_width=1, border_color=C("border")
        )
        out_frame.grid(row=2, column=0, sticky="nsew")
        out_frame.columnconfigure(0, weight=1)
        out_frame.rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(out_frame, fg_color=C("bg_input"),
                           corner_radius=0, height=34)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="📡 实时输出",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=C("text_secondary")
                     ).pack(side="left", padx=14)
        self._status_lbl = ctk.CTkLabel(
            hdr, text="待机",
            font=ctk.CTkFont(size=11), text_color=C("text_secondary")
        )
        self._status_lbl.pack(side="right", padx=14)

        self._output = ctk.CTkTextbox(
            out_frame,
            fg_color=C("bg_dark"),
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=C("text_primary"),
            wrap="none", border_width=0, corner_radius=0
        )
        self._output.grid(row=1, column=0, sticky="nsew", padx=1, pady=(0,1))
        self._output.configure(state="disabled")

        # 进度条
        self._progress = ctk.CTkProgressBar(
            parent, height=6, corner_radius=3,
            fg_color=C("bg_card"), progress_color=C("accent")
        )
        self._progress.grid(row=3, column=0, sticky="ew", pady=(6,0))
        self._progress.set(0)

        # 统计栏
        stats_f = ctk.CTkFrame(parent, fg_color=C("bg_card"),
                                corner_radius=10, height=56)
        stats_f.grid(row=3, column=0, sticky="ew", pady=(8,0))
        stats_f.pack_propagate(False)
        stats_f.columnconfigure((0,1,2,3), weight=1)
        self._stat_total = self._stat_box(stats_f, "总计",   "0", 0)
        self._stat_ok    = self._stat_box(stats_f, "成功",   "0", 1, C("success"))
        self._stat_slow  = self._stat_box(stats_f, "延迟高", "0", 2, C("warning"))
        self._stat_fail  = self._stat_box(stats_f, "超时",   "0", 3, C("danger"))

    def _stat_box(self, parent, label, val, col, color=None):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.grid(row=0, column=col, sticky="nsew", padx=4, pady=6)
        v_lbl = ctk.CTkLabel(
            f, text=val,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=color or C("text_primary")
        )
        v_lbl.pack()
        ctk.CTkLabel(f, text=label,
                     font=ctk.CTkFont(size=10),
                     text_color=C("text_secondary")).pack()
        return v_lbl

    def _card(self, parent, title, row):
        ctk.CTkLabel(
            parent, text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=C("text_secondary")
        ).grid(row=row, column=0, sticky="w", padx=4, pady=(6, 2))

    # ── Cron 向导 ────────────────────────────────────────────
    def _open_cron_wizard(self):
        CronWizard(self, self._cron_var.get(), self._on_cron_confirmed)

    def _on_cron_confirmed(self, expr):
        self._cron_var.set(expr)
        self._refresh_cron_human()

    def _refresh_cron_human(self):
        expr = self._cron_var.get().strip()
        human = cron_to_human(expr)
        self._cron_human_lbl.configure(text=f"📌 {human}")

    # ── 加载 / 保存 ──────────────────────────────────────────
    def _reload_all(self):
        bd = self.base_dir.get()
        self.cfg = load_config(bd)
        for key, var in self._cfg_vars.items():
            var.set(self.cfg.get("GENERAL", key, fallback=var.get()))
        self._cron_var.set(self.cfg.get("CRON", "Timing", fallback=""))
        self._iplist_var.set(self.cfg.get("GENERAL", "InputFile", fallback="iplist.txt"))
        self._load_iplist()
        self._refresh_cron_human()

    def _browse_dir(self):
        d = filedialog.askdirectory(title="选择工作目录",
                                    initialdir=self.base_dir.get())
        if d:
            self.base_dir.set(d)
            self._reload_all()

    def _browse_iplist(self):
        path = filedialog.askopenfilename(
            title="选择目标列表文件",
            initialdir=self.base_dir.get(),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            self._iplist_var.set(os.path.basename(path))
            self._load_iplist_from(path)

    def _iplist_path(self):
        val = self._iplist_var.get()
        if os.path.isabs(val):
            return val
        return os.path.join(self.base_dir.get(), val)

    def _load_iplist(self):
        self._load_iplist_from(self._iplist_path())

    def _load_iplist_from(self, path):
        self._iplist_text.configure(state="normal")
        self._iplist_text.delete("1.0", "end")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self._iplist_text.insert("1.0", f.read())

    def _save_iplist(self):
        path = self._iplist_path()
        content = self._iplist_text.get("1.0", "end-1c")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self._toast("目标列表已保存 ✓")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{e}")

    def _save_cfg(self):
        for key, var in self._cfg_vars.items():
            self.cfg.set("GENERAL", key, var.get())
        self.cfg.set("CRON", "Timing", self._cron_var.get().strip())
        self.cfg.set("GENERAL", "InputFile", self._iplist_var.get())
        try:
            save_config(self.cfg, self.base_dir.get())
            self._toast("配置已保存 ✓")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{e}")

    # ── 测试执行 ──────────────────────────────────────────────
    def _start_test(self):
        if self.running:
            return
        self._save_iplist()
        self._save_cfg()
        self.targets = load_targets(self._iplist_path())
        if not self.targets:
            messagebox.showwarning("提示", "目标列表为空，请先添加测试目标！")
            return
        self.running = True
        self.stop_flag.clear()
        self._run_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._progress.set(0)
        self._reset_stats()

        cron_expr = self._cron_var.get().strip()
        if cron_expr:
            self._cron_status.configure(
                text=f"● Cron 运行中: {cron_expr}", text_color=C("success")
            )
            threading.Thread(target=self._cron_loop,
                             args=(cron_expr,), daemon=True).start()
        else:
            threading.Thread(target=self._run_once_thread, daemon=True).start()

    def _stop_test(self):
        self.stop_flag.set()
        self._kill_all_processes()  # 强制终止所有子进程
        self.running = False
        self._run_btn.configure(state="normal")
        self._stop_btn.configure(state="disabled")
        self._cron_status.configure(text="● 已停止", text_color=C("danger"))
        self._set_status("已停止")
        self._clear_active_targets()  # 清空正在测试列表
    
    def _kill_all_processes(self):
        """强制终止所有活动的子进程"""
        with _process_lock:
            procs = list(_active_processes)
        for proc in procs:
            try:
                if proc.poll() is None:  # 进程还在运行
                    proc.terminate()  # 先尝试正常终止
                    # 等待一小会儿，如果还没终止就强制 kill
                    try:
                        proc.wait(timeout=0.5)
                    except subprocess.TimeoutExpired:
                        if sys.platform == "win32":
                            # Windows 强制终止
                            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], 
                                         capture_output=True)
                        else:
                            proc.kill()
            except Exception:
                pass
        with _process_lock:
            _active_processes.clear()

    def _cron_loop(self, expr):
        try:
            from croniter import croniter
        except ImportError:
            self.result_q.put(("log",
                "⚠️  需要安装 croniter: pip install croniter\n", "warning"))
            self._stop_test()
            return
        cron = croniter(expr, datetime.now())
        while not self.stop_flag.is_set():
            next_run = cron.get_next(datetime)
            wait = (next_run - datetime.now()).total_seconds()
            self.result_q.put(("log",
                f"\n⏰ 下次执行 → {next_run.strftime('%Y-%m-%d %H:%M:%S')}\n",
                "accent"))
            while wait > 0 and not self.stop_flag.is_set():
                time.sleep(min(1, wait))
                wait = (next_run - datetime.now()).total_seconds()
            if not self.stop_flag.is_set():
                self._run_once_inner()
        self.result_q.put(("done",))

    def _run_once_thread(self):
        self._run_once_inner()
        self.result_q.put(("done",))

    def _run_once_inner(self):
        targets = self.targets
        mode    = self.mode_var.get()
        cfg     = self.cfg
        bd      = self.base_dir.get()
        threads = cfg.getint("GENERAL", "Threads", fallback=5)
        ping_count = cfg.getint("GENERAL", "PingCount", fallback=4)
        tcp_count = cfg.getint("GENERAL", "TcpingCount", fallback=4)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.result_q.put(("log",
            f"\n{'='*50}\n⚡ NetPulse 执行开始  [{ts}]\n{'='*50}\n", "accent"))
        self.result_q.put(("set_status", f"测试中... 共 {len(targets)} 个目标"))
        self.result_q.put(("reset_stats",))
        self.result_q.put(("clear_active",))

        results = [None] * len(targets)
        completed = 0
        stat = {"ok": 0, "slow": 0, "fail": 0}
        
        # 添加所有目标到正在测试列表
        for h, p in targets:
            self.result_q.put(("add_active", h, p, mode))

        with ThreadPoolExecutor(max_workers=threads) as pool:
            futures = {
                pool.submit(worker_func_with_progress, i, h, p, mode, cfg, bd, 
                           self.result_q, ping_count, tcp_count, self.stop_flag): i
                for i, (h, p) in enumerate(targets)
            }
            for f in as_completed(futures):
                if self.stop_flag.is_set():
                    # 强制终止所有子进程
                    self._kill_all_processes()
                    # 取消剩余任务
                    for future in futures:
                        future.cancel()
                    break
                try:
                    idx, host, proto, avg, loss = f.result()
                    results[idx] = (host, proto, avg, loss)
                    color = "normal"
                    if avg in ("Timeout",) or avg.startswith("N/A"):
                        color = "fail"; stat["fail"] += 1
                    else:
                        try:
                            ms = int(avg)
                            if ms > 200:
                                color = "slow"; stat["slow"] += 1
                            else:
                                color = "ok"; stat["ok"] += 1
                        except ValueError:
                            color = "fail"; stat["fail"] += 1
                    completed += 1
                    line = f"  {host:<35} {proto:<12} {avg+'ms':<12} 丢包:{loss}"
                    self.result_q.put(("result_line", line, color))
                    self.result_q.put(("progress", completed / len(targets)))
                    self.result_q.put(("stats", completed,
                                       stat["ok"], stat["slow"], stat["fail"]))
                    self.result_q.put(("remove_active", host))
                except Exception as e:
                    self.result_q.put(("log", f"  ⚠️  任务异常: {e}\n", "warning"))

        out_ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(bd, f"result_{out_ts}.txt")
        lines = [f"{h},{pr},{a},{l}" for r in results
                 if r for h, pr, a, l in [r]]
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.result_q.put(("log",
                f"\n✅ 完成！结果已保存 → {out_path}\n", "ok"))
        except Exception as e:
            self.result_q.put(("log", f"\n⚠️  保存结果失败: {e}\n", "warning"))

    # ── 队列轮询 ──────────────────────────────────────────────
    def _poll_queue(self):
        try:
            while True:
                item = self.result_q.get_nowait()
                cmd = item[0]
                if cmd == "log":
                    self._append_output(item[1], item[2])
                elif cmd == "result_line":
                    self._append_output(item[1] + "\n", item[2])
                elif cmd == "progress":
                    self._progress.set(item[1])
                elif cmd == "stats":
                    _, total, ok, slow, fail = item
                    self._stat_total.configure(text=str(total))
                    self._stat_ok.configure(text=str(ok))
                    self._stat_slow.configure(text=str(slow))
                    self._stat_fail.configure(text=str(fail))
                elif cmd == "set_status":
                    self._set_status(item[1])
                elif cmd == "reset_stats":
                    self._reset_stats()
                elif cmd == "clear_active":
                    self._clear_active_targets()
                elif cmd == "add_active":
                    _, host, port, mode = item
                    self._add_active_target(host, port, mode)
                elif cmd == "update_active":
                    _, host, current, total = item
                    self._update_active_progress(host, current, total)
                elif cmd == "remove_active":
                    _, host = item
                    self._remove_active_target(host)
                elif cmd == "done":
                    self.running = False
                    self._run_btn.configure(state="normal")
                    self._stop_btn.configure(state="disabled")
                    self._set_status("测试完成")
                    self._progress.set(1)
                    self._clear_active_targets()
                    if not self._cron_var.get().strip():
                        self._cron_status.configure(
                            text="● 单次完成", text_color=C("success"))
        except queue.Empty:
            pass
        self.after(80, self._poll_queue)

    def _append_output(self, text, color="normal"):
        color_map = {
            "normal":  C("text_primary"),
            "ok":      C("ping_ok"),
            "slow":    C("ping_slow"),
            "fail":    C("ping_fail"),
            "accent":  C("accent"),
            "warning": C("warning"),
        }
        fg = color_map.get(color, C("text_primary"))
        self._output.configure(state="normal")
        inner: tk.Text = self._output._textbox
        tag = f"color_{color}"
        inner.tag_configure(tag, foreground=fg)
        inner.insert("end", text, tag)
        inner.see("end")
        self._output.configure(state="disabled")

    # ── 窗口大小变化处理 ─────────────────────────────────────
    def _on_window_resize(self, event=None):
        """根据窗口宽度动态调整列数"""
        if not hasattr(self, '_active_container'):
            return
        
        width = self.winfo_width()
        # 根据窗口宽度决定列数
        if width < 1000:
            new_cols = 1
        elif width < 1400:
            new_cols = 2
        else:
            new_cols = 3
        
        if new_cols != self._active_cols:
            self._active_cols = new_cols
            self._relayout_active_targets()
    
    def _relayout_active_targets(self):
        """重新布局所有正在测试的目标"""
        # 清除现有布局
        for widget in self._active_container.winfo_children():
            widget.grid_forget()
        
        # 重新布局
        for idx, (host, (frame, lbl, progress_lbl)) in enumerate(self._active_widgets.items()):
            row = idx // self._active_cols
            col = idx % self._active_cols
            frame.grid(row=row, column=col, sticky="ew", padx=4, pady=2)
        
        # 配置列权重
        for c in range(self._active_cols):
            self._active_container.columnconfigure(c, weight=1)

    # ── 正在测试列表管理 ─────────────────────────────────────
    def _add_active_target(self, host, port, mode):
        """添加一个正在测试的目标到列表"""
        if host in self._active_widgets:
            return
        
        # 显示容器
        self._active_frame.grid()
        
        # 创建进度项
        frame = ctk.CTkFrame(self._active_container, fg_color=C("bg_input"), corner_radius=6)
        
        # 目标信息
        proto = "ICMP" if mode == "1" else (f"TCP:{port}" if port else "TCP")
        info_text = f"{host} ({proto})"
        lbl = ctk.CTkLabel(
            frame, text=info_text,
            font=ctk.CTkFont(size=11),
            text_color=C("text_primary")
        )
        lbl.pack(side="left", padx=(10, 5))
        
        # 进度标签
        progress_lbl = ctk.CTkLabel(
            frame, text="准备中...",
            font=ctk.CTkFont(size=10),
            text_color=C("accent")
        )
        progress_lbl.pack(side="right", padx=10)
        
        self._active_widgets[host] = (frame, lbl, progress_lbl)
        
        # 布局
        idx = len(self._active_widgets) - 1
        row = idx // self._active_cols
        col = idx % self._active_cols
        frame.grid(row=row, column=col, sticky="ew", padx=4, pady=2)
        self._active_container.columnconfigure(col, weight=1)
    
    def _update_active_progress(self, host, current, total):
        """更新指定目标的进度"""
        if host not in self._active_widgets:
            return
        frame, lbl, progress_lbl = self._active_widgets[host]
        progress_lbl.configure(text=f"{current}/{total}")
    
    def _remove_active_target(self, host):
        """从正在测试列表中移除目标"""
        if host not in self._active_widgets:
            return
        frame, lbl, progress_lbl = self._active_widgets[host]
        frame.destroy()
        del self._active_widgets[host]
        
        # 重新布局剩余项目
        self._relayout_active_targets()
        
        # 如果没有正在测试的目标，隐藏容器
        if not self._active_widgets:
            self._active_frame.grid_remove()
    
    def _clear_active_targets(self):
        """清空所有正在测试的目标"""
        for frame, lbl, progress_lbl in self._active_widgets.values():
            frame.destroy()
        self._active_widgets.clear()
        self._active_frame.grid_remove()

    def _set_status(self, msg):
        self._status_lbl.configure(text=msg)

    def _reset_stats(self):
        for lbl in (self._stat_total, self._stat_ok,
                    self._stat_slow, self._stat_fail):
            lbl.configure(text="0")

    def _clear_output(self):
        self._output.configure(state="normal")
        self._output.delete("1.0", "end")
        self._output.configure(state="disabled")
        self._progress.set(0)
        self._reset_stats()
        self._set_status("待机")

    def _export_result(self):
        content = self._output._textbox.get("1.0", "end-1c")
        if not content.strip():
            messagebox.showinfo("提示", "输出区域为空，无内容可导出。")
            return
        path = filedialog.asksaveasfilename(
            title="导出结果",
            defaultextension=".txt",
            initialfile=f"netpulse_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self._toast(f"已导出 → {os.path.basename(path)}")

    def _toast(self, msg, duration=2500):
        toast = ctk.CTkToplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(fg_color=C("bg_card"))
        ctk.CTkLabel(
            toast, text=f"  {msg}  ",
            font=ctk.CTkFont(size=12),
            text_color=C("success"),
            fg_color=C("bg_card"), corner_radius=6
        ).pack(padx=2, pady=6)
        self.update_idletasks()
        x = self.winfo_x() + self.winfo_width()  - 340
        y = self.winfo_y() + self.winfo_height() - 70
        toast.geometry(f"+{x}+{y}")
        toast.after(duration, toast.destroy)


# ============================================================
# 入口
# ============================================================
def main():
    try:
        import customtkinter  # noqa
    except ImportError:
        print("[NetPulse GUI] 缺少依赖，请运行：pip install customtkinter croniter")
        sys.exit(1)
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()