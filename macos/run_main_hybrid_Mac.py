#!/usr/bin/env python3
import subprocess
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re
import shutil

# ======================
# 参数区
# ======================
PingCount = 5
TcpingCount = 5
DefaultTCPPort = 443
Threads = 5
InputFile = "iplist.txt"

print("### NetPulse macOS 版 ICMP / TCPing 测试工具 ###\n")

print("【配置说明】")
print(f"- ICMP Ping 次数 : {PingCount}")
print(f"- TCPing 次数    : {TcpingCount}")
print(f"- 默认 TCP 端口  : {DefaultTCPPort}")
print(f"- 并发线程数    : {Threads}")
print(f"- 输入文件      : {InputFile}\n")

# ======================
# 当前公网 IP（可选信息）
# ======================
try:
    ip_info = subprocess.check_output(
        ["curl", "-s", "myip.ipip.net"],
        timeout=5
    ).decode(errors="ignore").strip()

    if ip_info:
        print(f"🌐 当前公网 IP 信息：{ip_info}\n")
except Exception:
    # 获取失败不影响主流程
    pass

# ======================
# 模式选择
# ======================
print("[1] ICMP（普通 ping）")
print("[2] TCP（tcping）")
print("[3] 混合模式（无端口 ping，有端口 tcping）")

mode = input("请选择测试模式：").strip()
if mode not in {"1", "2", "3"}:
    print("无效选择")
    sys.exit(1)

# ======================
# 读取输入
# ======================
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

# ======================
# ICMP (macOS ping)
# ======================
def run_ping(host):
    try:
        cmd = ["ping", "-c", str(PingCount), host]
        out = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, timeout=PingCount * 3
        ).decode(errors="ignore")

        loss_match = re.search(r"(\d+\.?\d*)% packet loss", out)
        loss = f"{loss_match.group(1)}%" if loss_match else "100%"

        avg_match = re.search(r"round-trip min/avg/max/.* = [\d\.]+/([\d\.]+)/", out)
        avg = avg_match.group(1) if avg_match else "Timeout"

        return avg, loss

    except Exception:
        return "Timeout", "100%"

# ======================
# TCPing (macOS tcping)
# ======================
def run_tcping(host, port):
    exe = "tcping"
    if not shutil.which(exe):
        return "Timeout", "100%"

    try:
        out = subprocess.check_output(
            [exe, host, str(port)],
            stderr=subprocess.STDOUT,
            timeout=TcpingCount * 3
        ).decode(errors="ignore")

        stat_match = re.search(
            r"(\d+)\s+probes sent\.\s+(\d+)\s+successful,\s+(\d+)\s+failed\.",
            out,
            re.IGNORECASE | re.DOTALL
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

# ======================
# Worker
# ======================
def worker(idx, host, port):
    if mode == "1":  # ICMP
        avg, loss = run_ping(host)
        return idx, f"{host},ICMP,{avg},{loss}"

    if mode == "2":  # TCP
        p = port if port else DefaultTCPPort
        avg, loss = run_tcping(host, p)
        return idx, f"{host},TCP:{p},{avg},{loss}"

    # 混合模式
    if port:
        avg, loss = run_tcping(host, port)
        return idx, f"{host},TCP:{port},{avg},{loss}"
    else:
        avg, loss = run_ping(host)
        return idx, f"{host},ICMP,{avg},{loss}"

# ======================
# 并发执行
# ======================
results = [None] * len(targets)

with ThreadPoolExecutor(max_workers=Threads) as pool:
    futures = [
        pool.submit(worker, i, h, p)
        for i, (h, p) in enumerate(targets)
    ]
    for f in as_completed(futures):
        idx, line = f.result()
        results[idx] = line
        print(line)

# ======================
# 写结果
# ======================
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
outfile = f"result_{ts}.txt"

with open(outfile, "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print(f"\n✅ 测试完成，结果已保存到：{outfile}")