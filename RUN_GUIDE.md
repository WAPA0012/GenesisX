# Genesis X 运行指南

## 运行方式总览

Genesis X 支持多种运行方式，根据你的需求选择：

| 运行方式 | 文件 | 适用场景 | 完整度 |
|---------|------|----------|--------|
| **交互式聊天** | `chat_interactive.py` | 直接对话，测试功能 | ⭐⭐⭐⭐⭐ 推荐 |
| **Web UI** | `web/app_v2.py` | 浏览器界面，实时监控 | ⭐⭐⭐⭐ |
| **守护进程** | `daemon.py` | 长期后台运行 | ⭐⭐⭐⭐ |
| **FastAPI** | `interface/api_server.py` | REST API，集成其他服务 | ⭐⭐⭐ |
| **CLI** | `interface/cli.py` | 命令行控制 | ⭐⭐⭐ |

---

## 方式一：交互式聊天（推荐）

这是最完整、最直接的运行方式，支持完整的工具调用和状态显示。

### 运行步骤

```bash
# 1. 进入项目目录
cd "C:\Users\Administrator.DESKTOP-9I77JH3\Desktop\额\项目开发\2数字生命\0开发\GenesisX"

# 2. 安装依赖（首次运行）
pip install -r requirements.txt

# 3. 配置 API Key（如果需要）
setx DASHSCOPE_API_KEY "your_api_key_here"

# 4. 运行交互式聊天
python chat_interactive.py
```

### 功能特点

- ✅ 完整的工具调用（文件读写、代码执行、网络搜索等）
- ✅ 实时显示价值系统状态（5维权重、情绪、能量等）
- ✅ 显示工具调用过程和结果
- ✅ 支持多模型切换（千问、OpenAI等）
- ✅ 彩色终端输出，状态可视化

### 交互示例

```
════════════════════════════════════════════════════════════════════════
                    Genesis X 交互式聊天界面 v5
════════════════════════════════════════════════════════════════════════
[系统] 初始化完成...
[系统] 使用模型: qwen-plus
[系统] 当前状态: mood=0.0, stress=0.15, energy=0.80

════════════════════════════════════════════════════════════════════════

你: 帮我列出当前目录的文件

Genesis X: 我来帮你列出当前目录的文件。
  → 工具调用: file_list
    参数: {"path": "."}
  ✓ 结果: 找到 16 个文件

你: [继续对话...]
```

---

## 方式二：Web UI 界面

提供浏览器界面，支持实时监控和控制。

### 运行步骤

```bash
# 启动 Web UI
python web/app_v2.py
```

### 访问地址

```
http://localhost:5000
```

### 功能特点

- ✅ 实时状态监控（能量、情绪、价值权重）
- ✅ 聊天界面
- ✅ 器官状态可视化
- ✅ 历史记录查看
- ✅ 设置点调整

---

## 方式三：守护进程模式

适合长期后台运行，支持自动重启和状态持久化。

### 运行步骤

```bash
# 启动守护进程
python daemon.py

# 其他命令
python daemon.py --stop     # 停止
python daemon.py --status   # 查看状态
python daemon.py --restart  # 重启
```

### 功能特点

- ✅ 后台长期运行
- ✅ 自动错误恢复
- ✅ 状态持久化
- ✅ 日志轮换
- ✅ 优雅关机

---

## 方式四：FastAPI REST API

提供 HTTP API，可集成到其他系统。

### 运行步骤

```bash
# 启动 API 服务器
python -m interface.api_server

# 或使用 uvicorn
uvicorn interface.api_server:app --reload --host 0.0.0.0 --port 8000
```

### API 端点

```
POST   /chat              # 发送消息
GET    /state             # 获取状态
GET    /runs              # 列出运行记录
POST   /replay            # 回放运行
GET    /tools             # 列出可用工具
POST   /tools/{id}/execute # 执行工具
WebSocket /ws              # 实时更新
```

---

## 配置说明

### 1. API Key 配置

```bash
# 通义千问（推荐，国内可用）
setx DASHSCOPE_API_KEY "sk-xxxxxxxx"

# 或 OpenAI
setx OPENAI_API_KEY "sk-xxxxxxxx"
```

### 2. 配置文件

主要配置文件位于 `config/` 目录：

```
config/
├── value_setpoints.yaml    # 价值系统参数
├── default_genome.yaml      # 性格基因组
├── tool_manifest.yaml       # 工具清单
└── runtime.yaml             # 运行时配置
```

### 3. 环境变量

```bash
# 模型选择
GENESISX_MODEL=qwen-plus        # 默认模型
GENESISX_API_KEY=sk-xxxxx       # API密钥

# 运行模式
GENESISX_MODE=work              # work/friend/sleep
GENESISX_TICKS=100              # 运行tick数

# 安全设置
GENESISX_SECRET_KEY=xxxxx       # JWT密钥（API模式）
GENESISX_ENABLE_SANDBOX=1       # 代码沙箱
```

---

## 首次运行检查清单

- [ ] Python 3.9+ 已安装
- [ ] 依赖已安装 (`pip install -r requirements.txt`)
- [ ] API Key 已配置
- [ ] 配置文件目录存在 (`config/`)
- [ ] 输出目录可写 (`artifacts/`)

---

## 常见问题

### Q1: 提示找不到模块

```bash
# 确保在项目根目录运行
cd "C:\Users\Administrator.DESKTOP-9I77JH3\Desktop\额\项目开发\2数字生命\0开发\GenesisX"

# 或设置 PYTHONPATH
set PYTHONPATH=%PYTHONPATH%;%CD%
```

### Q2: API 调用失败

检查：
1. API Key 是否正确
2. 网络连接是否正常
3. 模型名称是否正确

### Q3: 中文显示乱码

```bash
# Windows 控制台设置
chcp 65001
```

### Q4: 代码执行报错

确保启用了沙箱模式：
```bash
set GENESISX_ENABLE_SANDBOX=1
```

---

## 推荐运行流程

对于**完整体验**，推荐以下流程：

1. **首次运行** - 使用 `chat_interactive.py` 熟悉系统
2. **调试阶段** - 使用 `web/app_v2.py` 监控状态
3. **生产部署** - 使用 `daemon.py` 后台运行

---

## 快速启动命令

```bash
# 一键启动交互式聊天
python chat_interactive.py

# 一键启动 Web UI
python web/app_v2.py

# 一键启动守护进程
python daemon.py
```
