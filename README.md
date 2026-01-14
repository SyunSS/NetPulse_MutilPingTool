# 📡 NetPulse

**NetPulse** 是一个跨平台的网络连通性与延迟测试工具，  
支持 **ICMP Ping** 与 **TCP Ping（tcping）**，  
适合用于 **网络质量检测 / 游戏服务器连通性测试 / 故障排查**。

- ✅ Windows：提供 **已编译 EXE**，双击即可使用  
- ✅ macOS：提供 **纯 Python 脚本**，灵活可控  
- ✅ 支持多线程、混合模式、端口自动识别  
- ✅ 结果自动保存为文件  

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
8.8.8.8:53
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

---

## 🧑‍💻 作者信息

- **项目名称**：NetPulse  
- **开发者**：SyunSS  

---

## 📜 License

本项目为个人工具，供学习与交流使用。
