#!/usr/bin/env python3
import subprocess
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re
import configparser

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


# ===== 程序入口 =====
if __name__ == "__main__":
    show_banner()
	
# ==================================================
# 关键：统一工作目录（兼容 PyInstaller exe）
# ==================================================
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

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

print("=== NetPulse 配置加载成功 ===")
print(f"PingCount      = {PingCount}")
print(f"TcpingCount    = {TcpingCount}")
print(f"DefaultTCPPort = {DefaultTCPPort}")
print(f"Threads        = {Threads}")
print(f"InputFile      = {InputFile}")
print("=============================\n")

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

# ==================================================
# ICMP
# ==================================================
def run_ping(host):
    try:
        cmd = ["ping", "-n", str(PingCount), host]
        out = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, timeout=PingCount * 3
        ).decode("gbk", errors="ignore")

        loss_match = re.search(r"\((\d+)%\s*丢失\)", out)
        if not loss_match:
            return "Timeout", "100%"

        loss = f"{loss_match.group(1)}%"

        avg_match = re.search(r"平均\s*=\s*(\d+)ms", out)
        avg = avg_match.group(1) if avg_match else "Timeout"

        return avg, loss

    except Exception:
        return "Timeout", "100%"

# ==================================================
# TCPing
# ==================================================
def run_tcping(host, port):
    exe = os.path.join(BASE_DIR, "tcping.exe")
    if not os.path.exists(exe):
        return "Timeout", "100%"

    times = []
    success = 0

    try:
        out = subprocess.check_output(
            [exe, "-n", str(TcpingCount), host, str(port)],
            stderr=subprocess.STDOUT,
            timeout=TcpingCount * 3
        ).decode(errors="ignore")

        for line in out.splitlines():
            if "time=" in line.lower():
                try:
                    ms = float(line.lower().split("time=")[1].replace("ms", ""))
                    times.append(ms)
                    success += 1
                except:
                    pass
    except Exception:
        pass

    if success == 0:
        return "Timeout", "100%"

    avg = int(sum(times) / len(times))
    loss = round((1 - success / TcpingCount) * 100, 1)
    return avg, f"{loss}%"

# ==================================================
# Worker
# ==================================================
def worker(idx, host, port):
    if mode == "1":
        avg, loss = run_ping(host)
        return idx, f"{host},ICMP,{avg},{loss}"

    if mode == "2":
        p = port if port else DefaultTCPPort
        avg, loss = run_tcping(host, p)
        return idx, f"{host},TCP:{p},{avg},{loss}"

    if port:
        avg, loss = run_tcping(host, port)
        return idx, f"{host},TCP:{port},{avg},{loss}"
    else:
        avg, loss = run_ping(host)
        return idx, f"{host},ICMP,{avg},{loss}"

# ==================================================
# 并发执行
# ==================================================
results = [None] * len(targets)

with ThreadPoolExecutor(max_workers=Threads) as pool:
    futures = [pool.submit(worker, i, h, p) for i, (h, p) in enumerate(targets)]
    for f in as_completed(futures):
        idx, line = f.result()
        results[idx] = line
        print(line)

# ==================================================
# 写结果
# ==================================================
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
outfile = os.path.join(BASE_DIR, f"result_{ts}.txt")

with open(outfile, "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print(f"\n✅ 测试完成，结果已保存到：{outfile}")

def wait_before_exit():
    if getattr(sys, "frozen", False):
        input("\n按回车键退出...")

wait_before_exit()