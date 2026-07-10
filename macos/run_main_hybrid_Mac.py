#!/usr/bin/env python3
import subprocess
import sys
import os
import socket
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

# 混合模式下 ICMP 不通时自动回退 TCP 80 / 443（True=启用, False=关闭）
EnableTCPFallback = True

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
cli_warnings = []
with open(InputFile, "r", encoding="utf-8") as f:
    for raw in f:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if ("[" in line) != ("]" in line):
            cli_warnings.append(f"  \"{line}\" → IPv6 括号不匹配")
        host_only = line.split()[0]
        if host_only.count(":") >= 2 and not host_only.startswith("["):
            cli_warnings.append(f"  \"{line}\" → IPv6 必须加 []，请改用 [{host_only}]")

        host = None
        port = None
        parts = line.split()
        if len(parts) == 2 and parts[1].isdigit():
            host, port = parts[0], int(parts[1])
            if host.startswith("[") and host.endswith("]"):
                host = host[1:-1]
        elif line.startswith("[") and "]" in line:
            end = line.find("]")
            host = line[1:end]
            if len(line) > end + 1 and line[end + 1] == ":":
                p = line[end + 2:]
                if p.isdigit():
                    port = int(p)
        elif line.count(":") == 1:
            h, p = line.rsplit(":", 1)
            if p.isdigit():
                host, port = h, int(p)
            else:
                host = line
        else:
            host = line

        host = sanitize_host(host)
        targets.append((host, port))

if cli_warnings:
    print("\n⚠️  以下条目存在格式问题:")
    for w in cli_warnings:
        print(f"  {w}")
    print("\n正确的 IPv6 格式: [IPv6] (无端口) 或 [IPv6]:端口 (带端口)")
    ans = input("\n是否忽略并继续？(y/N): ").strip().lower()
    if ans != "y":
        print("已取消")
        sys.exit(0)

# ==================================================
# URL 清理
# ==================================================
def sanitize_host(host):
    """清理 URL 前缀和尾部路径，只保留纯净域名/IP"""
    if not host:
        return host
    import re as _re
    host = _re.sub(r'^https?://', '', host, flags=_re.IGNORECASE)
    host = host.split('/')[0]
    host = host.split('#')[0]
    host = host.split('?')[0]
    host = host.rstrip(':')
    return host

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
# DNS 解析
# ==================================================
def resolve_host(host):
    """解析域名 → 返回首要 IP（实际被 ping/tcping 使用的那个）"""
    # 尝试解析为 IPv4 或 IPv6（已是纯 IP）
    try:
        socket.inet_pton(socket.AF_INET, host)
        return ""
    except (socket.error, AttributeError):
        pass
    try:
        socket.inet_pton(socket.AF_INET6, host)
        return ""
    except (socket.error, AttributeError):
        pass
    # 域名解析
    try:
        info = socket.getaddrinfo(host, None)
        ips = sorted(set(item[4][0] for item in info))
        if not ips:
            return ""
        primary = ips[0]
        extra = f" +{len(ips) - 1}" if len(ips) > 1 else ""
        return primary + extra
    except socket.error:
        return ""

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
        # ICMP 模式：解析 DNS 并显示 IP
        resolved = resolve_host(host)
        ip_part = f",{resolved}" if resolved else ""
        avg, loss, stddev = run_ping(host)
        return idx, f"{host},ICMP,{avg},{loss},{stddev}{ip_part}"

    if mode == "2":
        # TCP 模式：解析 DNS 并显示 IP
        resolved = resolve_host(host)
        ip_part = f",{resolved}" if resolved else ""
        p = port if port else DefaultTCPPort
        avg, loss = run_tcping(host, p)
        return idx, f"{host},TCP:{p},{avg},{loss}{ip_part}"

    # mode == "3" 混合模式
    if port:
        # 有指定端口：直接 TCP
        resolved = resolve_host(host)
        ip_part = f",{resolved}" if resolved else ""
        avg, loss = run_tcping(host, port)
        return idx, f"{host},TCP:{port},{avg},{loss}{ip_part}"
    else:
        # 无端口：DNS 解析 + 级联回退 ICMP → TCP:80 → TCP:443
        resolved = resolve_host(host)
        ip_part = f",{resolved}" if resolved else ""

        # 第一步: ICMP ping
        avg, loss, stddev = run_ping(host)
        if avg != "Timeout" and loss != "100%":
            return idx, f"{host},ICMP,{avg},{loss},{stddev}{ip_part}"

        # 开关关闭则直接返回 ICMP 结果
        if not EnableTCPFallback:
            return idx, f"{host},ICMP,{avg},{loss},{stddev}{ip_part}"

        # 第二步: TCP 80
        avg80, loss80 = run_tcping(host, 80)
        if avg80 != "Timeout" and loss80 != "100%":
            return idx, f"{host},TCP:80,{avg80},{loss80}{ip_part}"

        # 第三步: TCP 443
        avg443, loss443 = run_tcping(host, 443)
        if avg443 != "Timeout" and loss443 != "100%":
            return idx, f"{host},TCP:443,{avg443},{loss443}{ip_part}"

        # 全部失败: 判定不通
        return idx, f"{host},ALL_FAIL,Timeout,100%{ip_part}"

# ==================================================
# 单次执行
# ==================================================
def run_once():
    print("\n===== NetPulse 执行开始 =====\n")
    print("💡 实时结果为完成顺序，非目标列表顺序；保存文件按列表顺序排列\n")
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
