# 📡 NetPulse

**NetPulse** 是一个跨平台的网络连通性与延迟测试工具，支持 **ICMP Ping** 与 **TCP Ping（tcping）**，适合用于 **网络质量检测 / 游戏服务器连通性测试 / 故障排查**。

- ✅ Windows：提供 **GUI 图形界面** + **命令行版本**，双击即用
- ✅ macOS：提供 **纯 Python 脚本**，灵活可控
- ✅ 支持多线程、混合模式、端口自动识别
- ✅ 结果自动保存为文件
- ✅ 支持 Cron 定时功能

---

## ✨ 功能特性

- **三种测试模式**
    1. ICMP Ping（普通 ping）
    2. TCP Ping（tcping）
    3. 混合模式（无端口 → ping，有端口 → tcping）

- **自动识别输入**
    - `8.8.8.8`
    - `8.8.8.8 53`
    - `example.com`
    - `example.com 4433`

- **输出结果**
    - 平均延迟（ms）
    - 丢包率（%）
    - 自动生成时间戳结果文件

- **定时任务（Cron）**
    - 支持标准 Cron 表达式
    - GUI 版提供可视化向导，一键选择常用定时模式

---

## 📁 项目目录结构

```text
NetPulse/
├─ macos/
│   ├─ iplist.txt
│   ├─ run_main_hybrid_Mac.py
│   └─ tcping
│   
├─ windows/
│   ├─ config.ini
│   ├─ iplist.txt
│   ├─ NetPulse.exe          # 命令行版本（保留）
│   ├─ NetPulseGUI.exe       # GUI 图形界面版本（推荐）
│   ├─ netpulse_gui.py       # GUI 源码
│   ├─ run_main_hybrid.py    # 命令行源码
│   └─ tcping.exe
│   
└─ README.md
```

---

## 🪟 Windows 使用说明

### 🎨 方式一：GUI 图形界面（推荐）

进入 `windows` 目录，双击运行：

```text
NetPulseGUI.exe
```

或从源码运行：

```bash
cd windows
pip install customtkinter croniter
python netpulse_gui.py
```

#### GUI 功能概览

```
┌─────────────────────────────────────────────────────────┐
│  ⚡ NetPulse  ·  Multi-Ping Tool  GUI Edition  [工作目录▼] │
├──────────────┬──────────────────────────────────────────┤
│ 🔀 测试模式   │  ▶ 开始测试  ⏹ 停止  🗑 清空  📤 导出     │
│   ● ICMP     │ ┌──────────────────────────────────────┐ │
│   ○ TCP      │ │  📡 实时输出                   待机   │ │
│   ● 混合(推荐)│ │                                      │ │
│ ⚙️ 参数配置   │ │  8.8.8.8    ICMP   12ms   丢包:0%    │ │
│  Ping次数: 4 │ │  1.1.1.1:53 TCP:53 8ms    丢包:0%    │ │
│  线程数:   5 │ │  dead.host  ICMP   Timeout 丢包:100% │ │
│  [💾保存配置] │ └──────────────────────────────────────┘ │
│ 📋 目标列表   │  ████████████░░░░  进度条                 │
│ [iplist.txt] │ ┌──────┬──────┬────────┬──────┐         │
│ 8.8.8.8      │ │  3   │  2   │   0    │  1   │         │
│ 1.1.1.1 53   │ │ 总计  │ 成功  │ 延迟高 │ 超时  │         │
│ baidu.com    │ └──────┴──────┴────────┴──────┘         │
│ [加载] [保存] │                                          │
│ ⏰ Cron       │                                          │
│ 每隔 5 分钟执行 │                                          │
└──────────────┴──────────────────────────────────────────┘
```

| 功能 | 说明 |
|------|------|
| **测试模式** | ICMP / TCP / 混合模式一键切换 |
| **参数配置** | Ping 次数、TCP 端口、线程数可视化编辑，自动保存到 config.ini |
| **目标列表** | 内置编辑器，支持加载/保存 iplist.txt，实时编辑目标地址 |
| **实时输出** | 彩色结果（绿=正常 / 黄=延迟高 / 红=超时），进度条 + 统计面板 |
| **定时任务** | 可视化 Cron 向导，15+ 快速预设，自然语言预览（如"每隔 5 分钟执行一次"）|
| **主题切换** | 5 套皮肤：暗夜极客 / 深海蓝 / 赛博紫 / 抹茶绿 / 浅色简约 |
| **工作目录** | 支持切换不同目录，自动加载对应配置 |
| **结果导出** | 一键导出测试结果为 .txt 文件 |

#### GUI 打包为 EXE

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name NetPulseGUI --version-file=version.txt netpulse_gui.py
```

---

### ⌨️ 方式二：命令行版本

进入 `windows` 目录，双击运行：

```text
NetPulse.exe
```

或从源码运行：

```bash
cd windows
python run_main_hybrid.py
```

#### 编辑测试目标

修改 `windows/iplist.txt`：

```text
8.8.8.8
8.8.8.8 53
223.5.5.5 53
baidu.com
```

#### 修改测试参数

编辑 `windows/config.ini`：

```ini
[GENERAL]
PingCount = 4
TcpingCount = 4
DefaultTCPPort = 443
Threads = 5
InputFile = iplist.txt

[CRON]
Timing = */10 * * * *  ; 每 10 分钟执行一次
```

> ⚠️ 留空或删除 Timing 则只运行一次

---

### 📋 Windows 日志说明

Windows 版本**额外启用了日志功能**，用于应对以下情况：

- PowerShell / CMD 窗口被意外关闭
- 编码、路径、权限等 Windows 特有问题

程序运行时会**同时生成两类文件**：

```text
result_YYYYMMDD_HHMMSS.txt   # 整理后的最终测试结果
log_YYYYMMDD_HHMMSS.txt      # 完整运行日志（含调试信息）
```

---

## 🍎 macOS 使用说明

### 1️⃣ 环境要求

- macOS
- Python 3.x
- tcping 可执行文件（已放在同目录）

赋予 tcping 执行权限：

```bash
chmod +x macos/tcping
```

### 2️⃣ 运行程序

```bash
cd macos
python3 run_main_hybrid_Mac.py
```

### 3️⃣ 配置定时任务

编辑脚本顶部的 `CronExpr` 变量：

```python
CronExpr = "*/10 * * * *"  # 每 10 分钟执行一次
```

---

## 📄 输出结果说明

程序运行过程中会实时输出结果，并自动生成文件：

```text
result_YYYYMMDD_HHMMSS.txt
```

示例：

```text
8.8.8.8,ICMP,24,0%
8.8.8.8,TCP:53,31,0%
baidu.com,TCP:443,82,0%
```

> ℹ️ macOS 默认只生成 result 文件  
> Windows 会同时生成 result + log

---

## 🧑‍💻 作者信息

- **项目名称**：NetPulse
- **开发者**：SyunSS

---

## 📜 License

本项目为个人工具，供学习与交流使用。

---

### 💬 开发者碎碎念

> 同一份逻辑代码：  
> **macOS：写完就能跑**  
> **Windows：要考虑控制台、编码、exe、权限、窗口关闭、日志兜底……**  
> 日志功能的存在，本质上是 **"被 Windows 复杂度逼出来的"** 😅  
>  
> 于是后来干脆写了个 GUI，让 Windows 用户也能优雅地使用 🎨

---
