# 📡 NetPulse

**NetPulse** 是一个跨平台的网络连通性与延迟测试工具，  
支持 **ICMP Ping** 与 **TCP Ping（tcping）**，  
适合用于 **网络质量检测 / 游戏服务器连通性测试 / 故障排查**。

- ✅ Windows：提供 **已编译 EXE**，双击即可使用  
- ✅ macOS：提供 **纯 Python 脚本**，灵活可控  
- ✅ 支持多线程、混合模式、端口自动识别  
- ✅ 结果自动保存为文件  
- ✅ 支持Cron定时功能  
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

---

## 📁 项目目录结构

```text
NetPulse/
├─ macos/
│  ├─ iplist.txt
│  ├─ run_main_hybrid_Mac.py
│  └─ tcping
│
├─ windows/
│  ├─ config.ini
│  ├─ iplist.txt
│  ├─ NetPulse.exe
│  ├─ run_main_hybrid.py
│  └─ tcping.exe
│
└─ README.md
```

---

## 🪟 Windows 使用说明（推荐）

### 1️⃣ 运行方式

进入 `windows` 目录，双击运行：

```text
NetPulse.exe
```

无需安装 Python。

---

### 2️⃣ 编辑测试目标

修改：

```text
windows/iplist.txt
```

示例：

```text
8.8.8.8
8.8.8.8 53
223.5.5.5 53
baidu.com
```

---

### 3️⃣ 修改测试参数

编辑：

```text
windows/config.ini
```

示例：

```ini
[general]
ping_count = 100
tcping_count = 100
default_tcp_port = 443
threads = 10
```

> ⚠️ EXE 会优先读取 `config.ini` 中的参数

---

### 4️⃣ Windows 日志（Log）说明 ⭐

Windows 版本**额外启用了日志（log）功能**，用于应对以下情况：

- PowerShell / CMD 窗口被意外关闭  
- EXE 运行过程中无法完整查看输出  
- 编码、路径、权限等 Windows 特有问题  

程序运行时会**同时生成两类文件**：

```text
result_YYYYMMDD_HHMMSS.txt   # 整理后的最终测试结果
log_YYYYMMDD_HHMMSS.txt      # 完整运行日志（含调试信息）
```

- **result 文件**：用于查看最终测试数据  
- **log 文件**：用于问题排查与过程回溯  

即使窗口被关闭，也可以通过 log 文件查看完整执行过程。

---
### 5️⃣ Windows Cron 定时执行（可选）

Windows 版同样支持 Cron 表达式定时执行，配置在 config.ini 的 [CRON] 节：

```ini
[CRON]
Timing = */10 * * * *   ; 每 10 分钟执行一次
```

- 格式：分 时 日 月 周

- 示例：

  - 每隔 5 分钟执行一次: */5 * * * *

  - 每天凌晨 2 点执行: 0 2 * * *

- 如果留空或删掉此行，则只运行一次

- 程序运行时会打印 下一次执行时间

- 示例输出：

  - 进入 Cron 循环模式 (Ctrl+C 退出)
  - 下一次执行时间 → 2026-02-22 02:00:00

> ℹ️ Windows Cron 功能基于程序内置逻辑，无需额外任务计划程序，也可以配合系统计划任务使用。

## 🍎 macOS 使用说明

### 1️⃣ 环境要求

- macOS
- Python 3.x
- tcping 可执行文件（已放在同目录）

赋予 tcping 执行权限：

```bash
chmod +x macos/tcping
```

---

### 2️⃣ 运行程序

```bash
cd macos
python3 run_main_hybrid_Mac.py
```

---

### 3️⃣ macOS tcping 说明

macOS 系统默认不包含 tcping，  
请确保 `tcping` 文件与脚本在同一目录，且可在终端中正常运行。

---

## 📄 输出结果说明

程序运行过程中会实时输出结果，  
并自动生成文件：

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
### 3️⃣ macOS Cron 定时执行（可选）

macOS 版本支持 Cron 表达式定时执行，配置在脚本顶部的 CronExpr 变量：

```Python
# 格式: 分 时 日 月 周
# 示例: 每隔 5 分钟执行一次: */5 * * * *
# 示例: 每天凌晨 2 点执行: 0 2 * * *
# 如果留空或删掉此行，则只运行一次
CronExpr = "*/10 * * * *"  # 每 10 分钟执行一次
```

- 只需要修改 CronExpr 字符串即可启用定时执行

- 留空则只运行一次

- 脚本运行时会打印 下一次执行时间

- 示例输出：

  - 进入 Cron 循环模式 (Ctrl+C 退出)
  - 下一次执行时间 → 2026-02-22 12:10:00

> ℹ️ Cron 功能基于 Python 的 croniter 模块，无需额外系统 cron 配置

## 🧑‍💻 作者信息

- **项目名称**：NetPulse  
- **开发者**：SyunSS  

---

## 📜 License

本项目为个人工具，供学习与交流使用。

---

### 💬 开发者碎碎念（非技术性说明）

> 同一份逻辑代码：  
> **macOS：写完就能跑**  
> **Windows：要考虑控制台、编码、exe、权限、窗口关闭、日志兜底……**

日志功能的存在，本质上是 **“被 Windows 复杂度逼出来的”** 😅
