#!/usr/bin/env python3
import subprocess
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re
import configparser
import threading

# ==================================================
# Banner
# ==================================================
def show_banner():
    os.system("cls" if os.name == "nt" else "clear")
    banner = r"""
========================================
          _   _      _       ____        
         | \ | | ___| |_ __ |  _ \ _   _ 
         |  \| |/ _ \ | '_ \| |_) | | | |
         | |\  |  __/ | |_) |  __/| |_| |
         |_| \_|\___|_| .__/|_|    \__, |
                     |_|          |___/ 
========================================

        NetPulse - Network Latency Analyzer
        ICMP / TCPing Hybrid Test Tool
            Developer: SyunSS
"""
    print(banner)

if __name__ == "__main__":
    show_banner()

# ==================================================
# 工作目录（兼容 exe）
# ==================================================
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

# ==================================================
# 日志系统（只写文件，默认不 print）
# ==================================================
LOG_FILE = os.path.join(
    BASE_DIR,
    f"NetPulse_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)
LOG_LOCK = threading.Lock()

def log(msg, echo=False):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"

    if echo:
        print(line)

    with LOG_LOCK:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")

log("NetPulse 启动")
log(f"BASE_DIR = {BASE_DIR}")

# ==================================================
# 读取 config.ini
# ==================================================
config = configparser.ConfigParser()
config.read(os.path.join(BASE_DIR, "config.ini"), encoding="utf-8")

PingCount = config.getint("GENERAL", "PingCount", fallback=4)
TcpingCount = config.getint("GENERAL", "TcpingCount", fallback=4)
DefaultTCPPort = config.getint("GENERAL", "DefaultTCPPort", fallback=443)
Threads = config.getint("GENERAL", "Threads", fallback=5)
InputFile = config.get("GENERAL", "InputFile", fallback="iplist.txt")

print("\n=== NetPulse 配置加载成功 ===")
print(f"PingCount      = {PingCount}")
print(f"TcpingCount    = {TcpingCount}")
print(f"DefaultTCPPort = {DefaultTCPPort}")
print(f"Threads        = {Threads}")
print(f"InputFile      = {InputFile}")
print("=============================\n")

log(f"PingCount={PingCount}, TcpingCount={TcpingCount}, Threads={Threads}")

# ==================================================
# 模式选择
# ==================================================
print("[1] ICMP（普通 ping）")
print("[2] TCP（tcping）")
print("[3] 混合模式（无端口 ping，有端口 tcping）")

mode = input("请选择测试模式：").strip()
if mode not in {"1", "2", "3"}:
    print("无效选择")
    sys.exit(1)

log(f"选择模式 = {mode}")

# ==================================================
# 读取目标列表
# ==================================================
targets = []

with open(os.path.join(BASE_DIR, InputFile), "r", encoding="utf-8") as f:
    for raw in f:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        host = None
        port = None

        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            host, port = parts[0], int(parts[1])
        elif ":" in line:
            h, p = line.rsplit(":", 1)
            if p.isdigit():
                host, port = h, int(p)
            else:
                host = line
        else:
            host = line

        targets.append((host, port))

log(f"加载目标数量：{len(targets)}")

# ==================================================
# ICMP Ping
# ==================================================
def run_ping(host):
    try:
        cmd = ["ping", "-n", str(PingCount), host]
        out = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, timeout=PingCount * 3
        ).decode("gbk", errors="ignore")

        log(f"PING {host} 原始输出开始")
        for l in out.splitlines():
            log(l)
        log(f"PING {host} 原始输出结束")

        loss_match = re.search(r"\((\d+)%\s*丢失\)", out)
        if not loss_match:
            return "Timeout", "100%"

        loss = f"{loss_match.group(1)}%"

        avg_match = re.search(r"平均\s*=\s*(\d+)ms", out)
        avg = avg_match.group(1) if avg_match else "Timeout"

        return avg, loss

    except Exception as e:
        log(f"PING 异常 {host}: {e}")
        return "Timeout", "100%"

# ==================================================
# TCPing
# ==================================================
def run_tcping(host, port):
    exe = os.path.join(BASE_DIR, "tcping.exe")
    if not os.path.exists(exe):
        log("tcping.exe 未找到")
        return "Timeout", "100%"

    cmd = [exe, "-n", str(TcpingCount), host, str(port)]
    log(f"TCPING 执行：{' '.join(cmd)}")

    times = []
    loss = "100%"

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=TcpingCount * 3,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        out = proc.stdout

        log(f"TCPING {host}:{port} 原始输出开始")
        for line in out.splitlines():
            log(line)
        log(f"TCPING {host}:{port} 原始输出结束")

        for line in out.splitlines():
            if "time=" in line.lower():
                try:
                    ms = float(
                        line.lower()
                        .split("time=")[1]
                        .replace("ms", "")
                        .strip()
                    )
                    times.append(ms)
                except:
                    pass

        fail_match = re.search(r"\(([\d\.]+)%\s*fail\)", out, re.IGNORECASE)
        if fail_match:
            loss = f"{fail_match.group(1)}%"

    except Exception as e:
        log(f"TCPING 异常 {host}:{port}: {e}")
        return "Timeout", "100%"

    if not times:
        return "Timeout", loss

    avg = int(sum(times) / len(times))
    return avg, loss

# ==================================================
# Worker
# ==================================================
def worker(idx, host, port):
    log(f"任务开始 [{idx}] {host} port={port}")

    if mode == "1":
        avg, loss = run_ping(host)
        result = f"{host},ICMP,{avg},{loss}"
    elif mode == "2":
        p = port if port else DefaultTCPPort
        avg, loss = run_tcping(host, p)
        result = f"{host},TCP:{p},{avg},{loss}"
    else:
        if port:
            avg, loss = run_tcping(host, port)
            result = f"{host},TCP:{port},{avg},{loss}"
        else:
            avg, loss = run_ping(host)
            result = f"{host},ICMP,{avg},{loss}"

    log(f"任务完成 [{idx}] {result}")
    return idx, result

# ==================================================
# 并发执行
# ==================================================
results = [None] * len(targets)

with ThreadPoolExecutor(max_workers=Threads) as pool:
    futures = [pool.submit(worker, i, h, p) for i, (h, p) in enumerate(targets)]
    for f in as_completed(futures):
        idx, line = f.result()
        results[idx] = line
        print(line)   # ✅ 只在这里输出 result

# ==================================================
# 写 result 文件（保持你原来的逻辑）
# ==================================================
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
outfile = os.path.join(BASE_DIR, f"result_{ts}.txt")

with open(outfile, "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print(f"\n✅ 测试完成，结果已保存到：{outfile}")
print(f"📄 详细日志：{LOG_FILE}")

def wait_before_exit():
    if getattr(sys, "frozen", False):
        input("\n按回车键退出...")

wait_before_exit()