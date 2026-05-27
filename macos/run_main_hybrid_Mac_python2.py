#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import sys
import os
import threading
from datetime import datetime
import re
import shutil
import time

try:
    from croniter import croniter
except:
    croniter = None

# ==================================================
# 路径修复（关键）
# ==================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
InputFile = os.path.join(BASE_DIR, "iplist.txt")

# ==================================================
# Banner
# ==================================================
def show_banner():
    os.system("clear")
    print("""
========================================
        NetPulse - Python2 Enhanced
        ICMP + TCP + Jitter
========================================
""")

show_banner()

# ==================================================
# 配置
# ==================================================
PingCount = 4
TcpingCount = 4
DefaultTCPPort = 443
Threads = 5
CronExpr = ""

print("\n=== 配置加载 ===")
print("PingCount =", PingCount)
print("TcpingCount =", TcpingCount)
print("Threads =", Threads)
print("InputFile =", InputFile)
print("================\n")

# ==================================================
# 检查文件
# ==================================================
if not os.path.exists(InputFile):
    print("❌ 找不到 iplist.txt:", InputFile)
    sys.exit(1)

# ==================================================
# 出口IP
# ==================================================
def show_myip_info():
    try:
        proc = subprocess.Popen(
            ["curl", "-s", "myip.ipip.net"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, _ = proc.communicate()
        print("🌐 当前出口IP：")
        print(out.strip() + "\n")
    except:
        pass

show_myip_info()

# ==================================================
# 模式选择
# ==================================================
print("[1] ICMP")
print("[2] TCP")
print("[3] 混合")
mode = raw_input("选择模式: ").strip()

if mode not in ["1", "2", "3"]:
    print("无效选择")
    sys.exit(1)

# ==================================================
# 读取目标
# ==================================================
targets = []

with open(InputFile, "r") as f:
    for raw in f:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        host = None
        port = None

        if line.startswith("[") and "]" in line:
            end = line.find("]")
            host = line[1:end]
            if len(line) > end + 1 and line[end + 1] == ":":
                p = line[end + 2:]
                if p.isdigit():
                    port = int(p)
        elif line.count(":") >= 2:
            host = line
        elif ":" in line:
            parts = line.split(":")
            if parts[-1].isdigit():
                host = ":".join(parts[:-1])
                port = int(parts[-1])
            else:
                host = line
        else:
            host = line

        targets.append((host, port))

# ==================================================
# ICMP（带 stddev）
# ==================================================
def run_ping(host):
    try:
        cmd = ["ping", "-c", str(PingCount), host]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        start = time.time()
        timeout = PingCount * 3 + 2
        while proc.poll() is None:
            if time.time() - start > timeout:
                proc.kill()
                proc.wait()
                return "Timeout", "100%", "N/A"
            time.sleep(0.1)
        out = proc.stdout.read()

        # 丢包
        loss_match = re.search(r"(\d+\.?\d*)% packet loss", out)
        loss = loss_match.group(1) + "%" if loss_match else "100%"

        # mac: stddev / linux: mdev
        stat_match = re.search(
            r"= ([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+)",
            out
        )

        if stat_match:
            min_v = stat_match.group(1)
            avg = stat_match.group(2)
            max_v = stat_match.group(3)
            stddev = stat_match.group(4)
        else:
            avg = "Timeout"
            stddev = "N/A"

        return avg, loss, stddev

    except:
        return "Timeout", "100%", "N/A"

# ==================================================
# TCP
# ==================================================
def run_tcping(host, port):
    if not os.system("which tcping > /dev/null 2>&1") == 0:
        return "Timeout", "100%"

    try:
        out = subprocess.check_output(["tcping", host, str(port)])

        stat_match = re.search(
            r"(\d+)\s+probes.*?(\d+)\s+successful.*?(\d+)\s+failed",
            out, re.S
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

        loss = str(round((failed * 100.0 / probes), 1)) + "%"

        return avg, loss

    except:
        return "Timeout", "100%"

# ==================================================
# Worker
# ==================================================
results = []
lock = threading.Lock()

def worker(idx, host, port):
    global results

    if mode == "1":
        avg, loss, stddev = run_ping(host)
        line = "%s,ICMP,%s,%s,%s" % (host, avg, loss, stddev)

    elif mode == "2":
        p = port if port else DefaultTCPPort
        avg, loss = run_tcping(host, p)
        line = "%s,TCP:%s,%s,%s" % (host, p, avg, loss)

    else:
        if port:
            avg, loss = run_tcping(host, port)
            line = "%s,TCP:%s,%s,%s" % (host, port, avg, loss)
        else:
            avg, loss, stddev = run_ping(host)
            line = "%s,ICMP,%s,%s,%s" % (host, avg, loss, stddev)

    lock.acquire()
    results[idx] = line
    print(line)
    lock.release()

# ==================================================
# 执行
# ==================================================
def run_once():
    print("\n===== 开始 =====\n")

    global results
    results = [None] * len(targets)

    threads = []

    for i, (h, p) in enumerate(targets):
        t = threading.Thread(target=worker, args=(i, h, p))
        t.start()
        threads.append(t)

        if len(threads) >= Threads:
            for t in threads:
                t.join()
            threads = []

    for t in threads:
        t.join()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outfile = os.path.join(BASE_DIR, "result_%s.txt" % ts)

    with open(outfile, "w") as f:
        f.write("\n".join(results))

    print("\n完成 →", outfile)

# ==================================================
# Cron
# ==================================================
if not CronExpr or not croniter:
    run_once()
else:
    cron = croniter(CronExpr, datetime.now())
    print("进入循环")

    try:
        while True:
            next_run = cron.get_next(datetime)
            wait = (next_run - datetime.now()).total_seconds()

            print("下次执行:", next_run)

            if wait > 0:
                time.sleep(wait)

            run_once()

    except KeyboardInterrupt:
        print("已停止")