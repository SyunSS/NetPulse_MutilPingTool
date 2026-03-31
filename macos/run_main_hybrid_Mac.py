#!/usr/bin/env python3
import subprocess
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re
import shutil
import time
from croniter import croniter

# ==================================================
# 路径 + 输入文件名
# ==================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

file_name = input("请输入目标文件名（默认 iplist.txt）：").strip()
if not file_name:
    file_name = "iplist.txt"

InputFile = os.path.join(BASE_DIR, file_name)

# ==================================================
# Banner
# ==================================================
def show_banner():
    os.system("clear")
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
"""
    print(banner)

show_banner()

# ==================================================
# 配置区
# ==================================================
PingCount = 4
TcpingCount = 4
DefaultTCPPort = 443
Threads = 5

# Cron 配置（可选）
# 格式: 分 时 日 月 周
# 示例: 每隔 5 分钟执行一次: */5 * * * *
# 示例: 每天凌晨 2 点执行: 0 2 * * *
# 如果留空（CronExpr = ""）或删掉此行，则只运行一次
# Cron 配置
CronExpr = ""

# ==================================================
# 打印配置信息
# ==================================================
print("\n=== NetPulse 配置加载成功 ===")
print(f"PingCount      = {PingCount}")
print(f"TcpingCount    = {TcpingCount}")
print(f"DefaultTCPPort = {DefaultTCPPort}")
print(f"Threads        = {Threads}")
print(f"InputFile      = {InputFile}")
if CronExpr:
    print(f"Cron           = {CronExpr}")
print("=============================\n")

# ==================================================
# 检查文件
# ==================================================
if not os.path.exists(InputFile):
    print(f"❌ 找不到 iplist.txt: {InputFile}")
    sys.exit(1)

# ==================================================
# 出口 IP 显示
# ==================================================
def show_myip_info():
    try:
        proc = subprocess.run(
            ["curl", "-s", "myip.ipip.net"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        info = proc.stdout.strip()
        if info:
            print("🌐 当前出口 IP 信息：")
            print(info + "\n")
    except Exception:
        pass

show_myip_info()

# ==================================================
# 模式选择
# ==================================================
print("[1] ICMP（普通 ping）")
print("[2] TCP（tcping）")
print("[3] 混合模式")
mode = input("请选择测试模式：").strip()
if mode not in {"1", "2", "3"}:
    print("无效选择")
    sys.exit(1)

# ==================================================
# 读取目标
# ==================================================
targets = []
with open(InputFile, "r", encoding="utf-8") as f:
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
# ICMP（增加 stddev）
# ==================================================
def run_ping(host):
    try:
        cmd = ["ping", "-c", str(PingCount), host]
        out = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, timeout=PingCount*3
        ).decode(errors="ignore")

        loss_match = re.search(r"(\d+\.?\d*)% packet loss", out)
        loss = f"{loss_match.group(1)}%" if loss_match else "100%"

        # ⭐ 同时解析 min/avg/max/stddev（兼容 mac / Linux）
        stat_match = re.search(
            r"= ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+)",
            out
        )

        if stat_match:
            avg = stat_match.group(2)
            stddev = stat_match.group(4)
        else:
            avg = "Timeout"
            stddev = "N/A"

        return avg, loss, stddev

    except Exception:
        return "Timeout", "100%", "N/A"

# ==================================================
# TCPing
# ==================================================
def run_tcping(host, port):
    exe = "tcping"
    if not shutil.which(exe):
        return "Timeout", "100%"
    try:
        out = subprocess.check_output(
            [exe, host, str(port)],
            stderr=subprocess.STDOUT,
            timeout=TcpingCount*3
        ).decode(errors="ignore")

        stat_match = re.search(
            r"(\d+)\s+probes sent\.\s+(\d+)\s+successful,\s+(\d+)\s+failed\.",
            out, re.IGNORECASE | re.DOTALL
        )
        if not stat_match:
            return "Timeout", "100%"

        probes = int(stat_match.group(1))
        success = int(stat_match.group(2))
        failed = int(stat_match.group(3))

        if probes == 0 or success == 0:
            return "Timeout", "100%"

        avg_match = re.search(r"Average\s*=\s*([\d\.]+)ms", out)
        avg = avg_match.group(1) if avg_match else "Timeout"

        loss = round((failed / probes) * 100, 1)
        return avg, f"{loss}%"

    except Exception:
        return "Timeout", "100%"

# ==================================================
# Worker
# ==================================================
def worker(idx, host, port):
    if mode == "1":
        avg, loss, stddev = run_ping(host)
        return idx, f"{host},ICMP,{avg},{loss},{stddev}"

    if mode == "2":
        p = port if port else DefaultTCPPort
        avg, loss = run_tcping(host, p)
        return idx, f"{host},TCP:{p},{avg},{loss}"

    if port:
        avg, loss = run_tcping(host, port)
        return idx, f"{host},TCP:{port},{avg},{loss}"
    else:
        avg, loss, stddev = run_ping(host)
        return idx, f"{host},ICMP,{avg},{loss},{stddev}"

# ==================================================
# 单次执行
# ==================================================
def run_once():
    print("\n===== NetPulse 执行开始 =====\n")
    results = [None] * len(targets)

    with ThreadPoolExecutor(max_workers=Threads) as pool:
        futures = [pool.submit(worker, i, h, p) for i, (h, p) in enumerate(targets)]
        for f in as_completed(futures):
            idx, line = f.result()
            results[idx] = line
            print(line)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outfile = os.path.join(BASE_DIR, f"result_{ts}.txt")

    with open(outfile, "w", encoding="utf-8") as f:
        f.write("\n".join(results))

    print(f"\n✅ 完成 → {outfile}")

# ==================================================
# Cron
# ==================================================
if not CronExpr:
    run_once()
else:
    cron = croniter(CronExpr, datetime.now())
    print("\n进入 Cron 循环模式 (Ctrl+C 退出)\n")
    try:
        while True:
            next_run = cron.get_next(datetime)
            wait = (next_run - datetime.now()).total_seconds()
            print(f"下一次执行时间 → {next_run}")
            if wait > 0:
                time.sleep(wait)
            run_once()
    except KeyboardInterrupt:
        print("\nCron 已停止")
