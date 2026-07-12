#!/usr/bin/env python3
import subprocess
import sys
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re
import configparser
import threading
from croniter import croniter

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
# 日志系统
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
EnableTCPFallback = config.get("GENERAL", "EnableTCPFallback", fallback="True") == "True"

# Cron
CronExpr = None
if config.has_section("CRON"):
    CronExpr = config.get("CRON", "Timing", fallback=None)

print("\n=== NetPulse 配置加载成功 ===")
print(f"PingCount      = {PingCount}")
print(f"TcpingCount    = {TcpingCount}")
print(f"DefaultTCPPort = {DefaultTCPPort}")
print(f"Threads        = {Threads}")
print(f"InputFile      = {InputFile}")
if CronExpr:
    print(f"Cron           = {CronExpr}")
print("=============================\n")

log(f"配置: Ping={PingCount} TCP={TcpingCount} Threads={Threads}")
if CronExpr:
    log(f"Cron 表达式: {CronExpr}")

# ==================================================
# 出口 IP 显示
# ==================================================
def show_myip_info():
    try:
        proc = subprocess.run(
            ["curl", "myip.ipip.net"],
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
            log(f"出口 IP: {info}")
    except Exception as e:
        log(f"获取出口 IP 失败: {e}")

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

log(f"选择模式: {mode}")

# ==================================================
# 读取目标
# ==================================================
targets = []
cli_warnings = []

with open(os.path.join(BASE_DIR, InputFile), "r", encoding="utf-8") as f:
    for raw in f:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        host = None
        port = None

        if ("[" in line) != ("]" in line):
            cli_warnings.append(f"  \"{line}\" → IPv6 括号不匹配")
        host_only = line.split()[0]
        if host_only.count(":") >= 2 and not host_only.startswith("["):
            cli_warnings.append(f"  \"{line}\" → IPv6 必须加 []，请改用 [{host_only}]")

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

log(f"加载目标数量: {len(targets)}")

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
# ICMP
# ==================================================
def run_ping(host):
    try:
        cmd = ["ping", "-n", str(PingCount), host]
        out = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, timeout=PingCount * 3
        ).decode("gbk", errors="ignore")

        loss_match = re.search(r"\((\d+)%\s*(?:丢失|loss)\)", out, re.IGNORECASE)
        avg_match = re.search(r"(?:平均|Average)\s*=\s*(\d+)ms", out, re.IGNORECASE)

        loss = f"{loss_match.group(1)}%" if loss_match else "100%"
        avg = avg_match.group(1) if avg_match else "Timeout"

        return avg, loss

    except Exception as e:
        log(f"PING 异常 {host}: {e}")
        return "Timeout", "100%"

# ==================================================
# DNS 解析
# ==================================================
def resolve_host(host):
    """解析域名 → 返回首要 IP（实际被 ping/tcping 使用的那个）"""
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
    exe = os.path.join(BASE_DIR, "tcping.exe")
    if not os.path.exists(exe):
        return "Timeout", "100%"

    cmd = [exe, "-n", str(TcpingCount), host, str(port)]

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

        for line in out.splitlines():
            if "time=" in line.lower():
                try:
                    ms = float(
                        line.lower().split("time=")[1].replace("ms", "").strip()
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
def _is_all_lost(loss_str):
    try:
        return float(loss_str.replace("%", "")) >= 100.0
    except (ValueError, AttributeError):
        return loss_str == "100%"


def worker(idx, host, port):
    if mode == "1":
        resolved = resolve_host(host)
        ip_part = f",{resolved}" if resolved else ""
        avg, loss = run_ping(host)
        result = f"{host},ICMP,{avg},{loss}{ip_part}"
    elif mode == "2":
        resolved = resolve_host(host)
        ip_part = f",{resolved}" if resolved else ""
        p = port if port else DefaultTCPPort
        avg, loss = run_tcping(host, p)
        result = f"{host},TCP:{p},{avg},{loss}{ip_part}"
    else:
        # mode 3: 混合模式
        if port:
            resolved = resolve_host(host)
            ip_part = f",{resolved}" if resolved else ""
            avg, loss = run_tcping(host, port)
            result = f"{host},TCP:{port},{avg},{loss}{ip_part}"
        else:
            resolved = resolve_host(host)
            ip_part = f",{resolved}" if resolved else ""

            # 第一步: ICMP
            avg, loss = run_ping(host)
            if avg != "Timeout" and not _is_all_lost(loss):
                result = f"{host},ICMP,{avg},{loss}{ip_part}"
                return idx, result

            # 开关关闭则直接返回 ICMP 结果
            if not EnableTCPFallback:
                result = f"{host},ICMP,{avg},{loss}{ip_part}"
                return idx, result

            # 第二步: TCP 80
            avg80, loss80 = run_tcping(host, 80)
            if avg80 != "Timeout" and not _is_all_lost(loss80):
                result = f"{host},TCP:80,{avg80},{loss80}{ip_part}"
                return idx, result

            # 第三步: TCP 443
            avg443, loss443 = run_tcping(host, 443)
            if avg443 != "Timeout" and not _is_all_lost(loss443):
                result = f"{host},TCP:443,{avg443},{loss443}{ip_part}"
                return idx, result

            # 全部失败
            result = f"{host},ALL_FAIL,Timeout,100%{ip_part}"
            return idx, result

    return idx, result

# ==================================================
# 单次执行
# ==================================================
def run_once():

    print("\n===== NetPulse 执行开始 =====\n")
    print("💡 实时结果为完成顺序，非目标列表顺序；保存文件按列表顺序排列\n")
    log("执行开始")

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
    log(f"输出文件: {outfile}")

# ==================================================
# 调度逻辑
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
            log(f"下一次执行: {next_run}")

            if wait > 0:
                time.sleep(wait)

            run_once()

    except KeyboardInterrupt:
        print("\nCron 已停止")
        log("Cron 停止")

# ==================================================
# 退出等待（exe）
# ==================================================
def wait_before_exit():
    if getattr(sys, "frozen", False):
        input("\n按回车退出...")

wait_before_exit()