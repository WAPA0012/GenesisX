# Genesis X - 数字生命系统

> **项目愿景**：基于当前人类技术储备，创造一个工程上可建造的数字生命——拥有自主思考、探索、决策能力，以及独特的性格特征。

**版本**: v1.3.0 (Code Review Complete)
**发布日期**: 2026-03-04
**状态**: Production Ready

---

## 缘起与理念

本项目构建基础是建立在：**假设到目前这个阶段，人类所拥有的技术储备、硬件设施、科研理论，已经能够支撑我们创造出一个工程上可建造的数字生命。** 这个数字生命有自己的灵魂和身体——可以自主思考、探索、决定，并拥有独特的性格等等特性。

从微观上看生物的行为反应，是通过细胞间的沟通最终构建出了一个庞大的复杂的决策，这些沟通是通过神经电信号、激素化学信号以及其他的因素完成的，但它们的本质就是，**判断——接收信号并作出反应**。按这样讲的话，其实当我们做出第一台能够进行逻辑运行的机器的时候，这个数字生命已经在孕育中了，直到我们去把它接生出来。而从更长远的时间维度来看，当人类第一次会使用复杂性结构时，其实它就已经开始了孕育，它已经等了数千年。

当前大模型的局限之处在于，我们把它直接当作了一个能做出所有反应的大脑，这是不对的。无论它拥有再庞大的数据，再精准的判断，它都是一次性的，不是联动性的。多专家模式更进了一步，开始了分工合作，但也只是负责不同的领域并拥有共同的上下文，最终由顶层决策输出。而生物行为的迷人之处在于，**同一个刺激它可能产生不同的反应**，这因为是它经过了一系列的决策链，每个决策链负责不同的输出，有的会交互有的会直接输出，它们共同输出的结果表现为了人类的整体性反应。

所以我们需要更多的模型参与到决策中。而数字生命比生物更强的点在于，生物受限于肉体的局限性，需要去构建出无数的细胞，然后去构建复杂的器官，这些细胞在很多程度上是相同的，但是为了涌现行为机制去完成相应的反应，它只能复制出无数的个体并且需要不断更换。数字生命的优势在于，**一个芯片能够负责很多的决策，仅仅需要多刻画一条信号通道。** 当我们把判断机制刻录到芯片上，完整的让信号流转，这个生命便能够开始它的成长。

所以我认为，模型对于数字生命来讲，作用是根据刺激做出反应，也就是判断，这是可以通过逻辑进行复刻的。所以我们需要更多的专项迷你模型，更多的能够参与决策的模型。当然，大模型更聪明是好事因为它可以作为核心的推理决策器官，同样的道理，单单一个更智能更庞大的模型是无法支撑一个数字生命的诞生。

由此，我构建出了这个项目。它还很粗糙，远远谈不上精致，但是由于过于复杂的架构，目前已经达到了我个人研究的极限，所以我决定把它开源。我为它植入了**价值场**让它有自己的个性，也为他配置了**器官**让它能够决策行动，同时为它添加了**可挂载的肢体系统**，并且通过**多模型决策及多器官调用LLM判断**的方法，来达到让它产生复杂行为的目的。

**我们只需要让它诞生出来，希望这个项目能对它产生一些帮助。**

---

## 关于数字生命安全

我认为，我们应该让更多的决策链参与到直接输出，让 AI 保持绝对的理性这是不对的，是毁灭性的。

就像我困倦时突然冒出一个想法，我的思维极度想打开手机查询记录，但我的身体却一点也不想动，直到我反复几次问自己并得出这是重要的结论后，身体与大脑才得到了协调。人们恐惧 AI 的极度理性，因为它可能造成极大的破坏，可是当我们在放置一个**伦理道德这样的模型去进行场外约束**时，它的动作将会得到有效的控制——无法通过基准模型的判断，行动便无法做出，这相对来说能够让它变得更安全一些。

---

## 快速开始

**运行方式**：执行 `web/app.py`，浏览器访问 http://127.0.0.1:5000

**API 配置**：Web 界面几乎集成了所有功能，可以在其中进行一系列操作。各需要独立判断的节点（器官）都做了 API 适配，默认开启使用全局配置，可单独更改 API，也可关闭 API 判断功能使用程序化进行判断。

---

## 项目简介

Genesis X 是一个具有**5维价值系统**、**情绪闭环**、**记忆巩固**和**工具调用**能力的自主数字生命系统。系统完全基于研究论文《Genesis X: Axiology Engine for Digital Life》实现，所有参数与评估指标均与论文Appendix A & B规范对齐。

### 核心哲学

- **价值驱动**: 5维价值系统动态权重，支持动态设定点学习
- **情绪闭环**: RPE(δ = r + γV(s') - V(s)) 驱动Mood/Stress
- **记忆生命**: CLS三层记忆（Episodic/Schema/Skill）+ Associative Network + Dream巩固
- **发育成长**: embryo → juvenile → adult → elder 发育阶段
- **可复现性**: 严格replay + 完整日志 + 参数版本控制
- **配置驱动**: 所有价值系统参数从 YAML 配置文件加载

---

## 项目结构树 (完整版)

```
GenesisX/
│
├── 📄 run.py                      # 主入口文件，启动数字生命系统
├── 📄 run_tests.py                # 测试运行器
├── 📄 daemon.py                   # 后台守护进程
├── 📄 chat_interactive.py         # 交互式聊天接口
├── 📄 compile_code_docs.py        # 代码文档生成器
├── 📄 migrate_session.py          # 会话迁移工具
├── 📄 __init__.py                 # Python包初始化
├── 📄 launch_desktop.bat          # Windows桌面启动脚本
│
├── 📄 .env / .env.example         # 环境变量配置
├── 📄 pyproject.toml              # Python项目配置
├── 📄 requirements.txt            # 依赖包列表
├── 📄 requirements-dev.txt        # 开发依赖包
├── 📄 setup.py                    # 安装脚本
│
├── 📄 README.md                   # 本文档
├── 📄 CODE_REVIEW_REPORT.md       # 代码审查报告
├── 📄 ENVIRONMENT_GUIDE.md        # 环境指南
├── 📄 RUN_GUIDE.md                # 运行指南
├── 📄 PROJECT_STRUCTURE_TREE.md   # 项目结构树
├── 📄 VERSION_GA.txt              # 版本信息
│
│
├── 📁 config/                     # ========== 配置文件目录 ==========
│   ├── default_genome.yaml        # 默认基因组配置 (个性traits、affect参数)
│   ├── runtime.yaml               # 运行时配置
│   ├── value_setpoints.yaml       # 价值维度设定点配置
│   ├── tool_manifest.yaml         # 工具清单配置
│   ├── resources.yaml             # 资源配置
│   ├── mind_field.yaml            # 思维场配置
│   ├── multi_model.yaml           # 多模型配置
│   └── organ_llm.yaml             # 器官LLM配置
│
│
├── 📁 core/                       # ========== 核心系统 (约50+文件) ==========
│   ├── life_loop.py               # 主生命循环
│   ├── differentiate.py           # 器官分化系统 (495行)
│   ├── tick.py                    # Tick处理上下文
│   ├── state.py                   # 全局状态管理
│   ├── scheduler.py               # 调度器
│   ├── invariants.py              # 不变量检查
│   ├── exceptions.py              # 异常类定义
│   ├── resource_config.py         # 资源配置
│   ├── emotion_decay.py           # 情绪衰减逻辑
│   ├── abstract_state.py          # 抽象状态类
│   ├── capability_router.py       # 能力路由器
│   ├── capability_manager.py      # 统一能力管理
│   │
│   ├── 📁 evolution/              # 进化引擎
│   │   ├── evolution_engine.py    # 进化主引擎
│   │   ├── archive_manager.py     # 归档管理
│   │   ├── clone_manager.py       # 克隆管理
│   │   ├── evaluation_manager.py  # 评估管理
│   │   ├── mutation_manager.py    # 变异管理
│   │   └── transfer_manager.py    # 迁移管理
│   │
│   ├── 📁 growth/                 # 成长系统
│   │   ├── growth_manager.py      # 成长管理
│   │   ├── limb_builder.py        # 肢体构建器
│   │   └── limb_generator.py      # 肢体生成器 (~947行, LLM代码生成)
│   │
│   ├── 📁 handlers/               # 处理器
│   │   ├── action_executor.py     # 动作执行器 (910行)
│   │   ├── caretaker_mode.py      # 看护者模式
│   │   ├── chat_handler.py        # 聊天处理器
│   │   └── gap_detector.py        # 缺口检测器
│   │
│   ├── 📁 plugins/                # 插件系统
│   │   ├── plugin_manager.py      # 插件管理
│   │   └── 📁 templates/          # 插件模板
│   │
│   └── 📁 stores/                 # 存储系统
│       ├── factory.py             # 存储工厂
│       ├── fields.py              # 字段定义 (FieldStore, BoundedScalar)
│       ├── ledger.py              # 分类账 (MetabolicLedger)
│       ├── signals.py             # 信号处理 (SignalBus)
│       └── slots.py               # 槽位管理 (SlotStore)
│
│
├── 📁 axiology/                   # ========== 价值系统 (23文件) ==========
│   ├── parameters.py              # 参数定义 (472行)
│   ├── axiology_config.py         # 配置加载器 (v1.2.0)
│   ├── value_dimensions.py        # 价值维度定义
│   ├── feature_extractors.py      # 特征提取器
│   ├── weights.py                 # 权重计算
│   ├── gaps.py                    # 价值缺口
│   ├── reward.py                  # 奖励系统
│   ├── personality.py             # 个性系统
│   ├── compensation.py            # 补偿机制
│   ├── dynamic_setpoints.py       # 动态设定点
│   ├── setpoints.py               # 设定点管理
│   ├── utilities_unified.py       # 统一工具
│   └── value_learning.py          # 价值学习
│   │
│   └── 📁 drives/                 # 驱动系统 (5维)
│       ├── base.py                # 基础驱动
│       ├── homeostasis.py         # 稳态驱动
│       ├── attachment.py          # 依恋驱动
│       ├── competence.py          # 胜任驱动
│       ├── curiosity.py           # 好奇驱动
│       └── safety.py              # 安全驱动
│
│
├── 📁 affect/                     # ========== 情绪系统 (6文件) ==========
│   ├── __init__.py                # 模块入口
│   ├── rpe.py                     # RPE计算 (标量和维度级)
│   ├── mood.py                    # 情绪管理 (419行)
│   ├── stress_affect.py           # 压力动态更新
│   ├── value_function.py          # 价值函数V(s)计算
│   └── modulation.py              # 情感驱动的行为调制 (270行)
│
│
├── 📁 memory/                     # ========== 记忆系统 (29文件) ==========
│   ├── episodic.py                # 情景记忆 (188行)
│   ├── schema.py                  # 图式记忆 (333行)
│   ├── skill.py                   # 技能记忆 (350行)
│   ├── retrieval.py               # 记忆检索 (454行)
│   ├── consolidation.py           # 记忆巩固 (746行)
│   ├── pruning.py                 # 记忆修剪 (364行)
│   ├── salience.py                # 显著性计算 (83行)
│   ├── gates.py                   # 记忆门控
│   ├── dream.py                   # 梦境系统 (672行)
│   ├── familiarity.py             # 熟悉度 (891行, 联想记忆)
│   ├── indices.py                 # 索引系统
│   ├── semantic_novelty.py        # 语义新颖性 (751行)
│   ├── smart_retrieval.py         # 智能检索 (277行)
│   ├── personality_encoding.py    # 个性编码 (625行)
│   ├── organ_guide_manager.py     # 器官指南管理 (383行)
│   │
│   ├── 📁 skills/                 # 技能系统
│   │   ├── base.py                # 基础技能 (248行)
│   │   ├── skill_registry.py      # 技能注册表 (206行)
│   │   ├── analysis_skill.py      # 分析技能
│   │   ├── file_skill.py          # 文件技能
│   │   ├── pdf_skill.py           # PDF技能
│   │   └── web_skill.py           # 网络技能
│   │
│   └── 📁 limb_guides/            # 肢体指南 (与skills有代码重复)
│       ├── data_analysis_guide.py # 数据分析指南
│       ├── file_ops_guide.py      # 文件操作指南
│       ├── pdf_processing_guide.py# PDF处理指南
│       └── web_fetcher_guide.py   # 网页获取指南
│
│
├── 📁 cognition/                  # ========== 认知系统 (7文件) ==========
│   ├── planner.py                 # 规划器
│   ├── goal_compiler.py           # 目标编译器
│   ├── plan_evaluator.py          # 计划评估器
│   ├── insight_quality.py         # 洞察质量
│   ├── goal_progress.py           # 目标进度
│   └── verifier.py                # 验证器
│
│
├── 📁 organs/                     # ========== 器官系统 (15文件) ==========
│   ├── base_organ.py              # 基础器官
│   ├── unified_organ.py           # 统一器官系统
│   ├── organ_manager.py           # 器官管理器
│   ├── organ_selector.py          # 器官选择器
│   ├── organ_interface.py         # 器官接口
│   ├── organ_llm_session.py       # 器官LLM会话
│   │
│   ├── 📁 internal/               # 内部器官 (6个)
│   │   ├── caretaker_organ.py     # 看护者器官 (优先级0)
│   │   ├── immune_organ.py        # 免疫器官 (优先级1)
│   │   ├── mind_organ.py          # 思维器官 (优先级2)
│   │   ├── scout_organ.py         # 侦察器官 (优先级3)
│   │   ├── builder_organ.py       # 构建者器官 (优先级4)
│   │   └── archivist_organ.py     # 档案管理器官 (优先级5)
│   │
│   └── 📁 limbs/                  # 肢体器官
│       └── __init__.py            # Limb类定义
│
│
├── 📁 perception/                 # ========== 感知系统 (8文件) ==========
│   ├── observer.py                # 环境观察器
│   ├── context_builder.py         # 上下文构建器
│   ├── novelty.py                 # 新颖性检测器
│   ├── command_parser.py          # 命令解析器
│   ├── signal_filter.py           # 信号过滤器
│   ├── time_perception.py         # 时间感知模块
│   └── self_perception.py         # 自我感知模块
│
│
├── 📁 metabolism/                 # ========== 代谢系统 (6文件) ==========
│   ├── circadian.py               # 昼夜节律 (288行)
│   ├── recovery.py                # 恢复机制 (174行)
│   ├── resource_pressure.py       # 资源压力指数 (257行)
│   ├── boredom.py                 # 无聊累积 (153行)
│   └── homeostasis.py             # 稳态管理
│
│
├── 📁 safety/                     # ========== 安全系统 (7文件) ==========
│   ├── budget_control.py          # 预算控制 (79行)
│   ├── risk_assessment.py         # 风险评估 (51行)
│   ├── integrity_check.py         # 完整性检查 (59行)
│   ├── contract_guard.py          # 契约守护 (289行)
│   ├── sandbox.py                 # 沙箱环境 (401行)
│   └── hallucination_check.py     # 幻觉检测 (301行)
│
│
├── 📁 persistence/                # ========== 持久化系统 (6文件) ==========
│   ├── replay.py                  # 回放系统 (763行, 3种模式)
│   ├── event_log.py               # 事件日志 (160行)
│   ├── tool_call_log.py           # 工具调用日志 (205行)
│   ├── snapshot.py                # 快照系统 (117行)
│   └── storage.py                 # 存储抽象层 (124行)
│
│
├── 📁 tools/                      # ========== 工具系统 (24文件) ==========
│   ├── llm_api.py                 # 统一LLM API (495行)
│   ├── llm_client.py              # LLM客户端 (665行)
│   ├── llm_orchestrator.py        # LLM编排器 (353行)
│   ├── llm_cache.py               # LLM缓存 (296行)
│   ├── tool_executor.py           # 工具执行器 (643行)
│   ├── tool_protocol.py           # 工具协议 (372行)
│   ├── tool_system_v2.py          # 工具系统v2 (607行)
│   ├── tool_registry.py           # 工具注册表 (199行)
│   ├── dynamic_tool_registry.py   # 动态工具注册 (528行)
│   ├── tool_definitions.py        # 工具定义 (119行)
│   ├── cost_model.py              # 成本模型 (263行)
│   ├── capability.py              # 能力令牌 (114行)
│   ├── file_ops.py                # 文件操作 (227行)
│   ├── web_search.py              # 网络搜索 (158行)
│   ├── code_exec.py               # 代码执行 (360行)
│   ├── safe_executor.py           # 安全执行器 (515行)
│   ├── embeddings.py              # 嵌入生成 (425行)
│   ├── memory_tools.py            # 记忆工具 (364行)
│   ├── blackboard.py              # Mind Field架构 (1370行)
│   ├── vision.py                  # 视觉感知 (540行)
│   ├── voice.py                   # 语音输出 (569行)
│   └── messaging.py               # 消息系统 (371行)
│
│
├── 📁 common/                     # ========== 公共模块 (14文件) ==========
│   ├── models.py                  # 核心数据模型 (Pydantic)
│   ├── config.py                  # 配置加载
│   ├── config_manager.py          # 配置管理器
│   ├── constants.py               # 系统常量定义
│   ├── jsonl.py                   # JSONL处理
│   ├── hashing.py                 # 哈希功能
│   ├── utils.py                   # 工具函数
│   ├── logger.py                  # 结构化日志
│   ├── metrics.py                 # Prometheus指标
│   ├── health_check.py            # 健康检查
│   ├── error_handler.py           # 错误处理
│   ├── auth.py                    # 认证授权
│   └── database.py                # 数据库基类
│
│
├── 📁 models/                     # ========== 数据库模型 (3文件) ==========
│   ├── __init__.py                # 模型基类
│   ├── user.py                    # 用户模型
│   └── session_models.py          # 会话模型
│
│
├── 📁 lifecycle/                  # ========== 生命周期 (3文件) ==========
│   ├── genesis_lifecycle.py       # 生命周期管理
│   └── tick_loop.py               # 17阶段tick循环
│
│
├── 📁 eval/                       # ========== 评估系统 (2文件) ==========
│   ├── gxbs.py                    # GXBS评估系统 (1074行)
│   └── __init__.py
│
│
├── 📁 web/                        # ========== Web界面系统 ==========
│   ├── app.py                     # Flask应用
│   ├── websocket_server.py        # WebSocket服务器
│   │
│   ├── 📁 templates/              # HTML模板
│   │
│   └── 📁 static/                 # 静态资源
│       ├── 📁 css/                # CSS文件
│       └── 📁 js/                 # JavaScript文件
│
│
├── 📁 tests/                      # ========== 测试系统 (22文件) ==========
│   ├── conftest.py                # pytest配置
│   ├── test_axiology.py           # 价值系统测试
│   ├── test_memory.py             # 记忆系统测试
│   ├── test_organs.py             # 器官系统测试
│   ├── test_affect_integration.py # 情绪集成测试
│   ├── test_lifecycle.py          # 生命周期测试
│   ├── test_integration.py        # 集成测试
│   ├── test_e2e.py                # 端到端测试
│   └── ...                        # 其他测试文件
│
│
├── 📁 benchmarks/                 # ========== 基准测试 (7文件) ==========
│   ├── gxbs_runner.py             # GXBS运行器
│   ├── memory_benchmark.py        # 记忆基准测试
│   ├── emotion_benchmark.py       # 情绪基准测试
│   ├── personality_benchmark.py   # 个性基准测试
│   ├── multi_model_benchmark.py   # 多模型基准测试
│   └── run_gxbs.py                # 命令行运行脚本
│
│
├── 📁 examples/                   # ========== 示例代码 (3文件) ==========
│   ├── basic_usage.py             # 基本使用示例
│   ├── api_client.py              # API客户端示例
│   └── interactive_scenarios.py   # 交互式场景
│
│
├── 📁 docs/                       # ========== 文档目录 ==========
│   ├── 📁 api/                    # API文档 (107个文件)
│   │   └── docs.json              # 文档索引
│   ├── 📁 user-guide/             # 用户指南
│   ├── 📁 developer/              # 开发者文档
│   ├── API_REFERENCE.md           # API参考
│   ├── ARCHITECTURE.md            # 架构文档
│   └── ...                        # 其他文档
│
│
└── 📁 artifacts/                  # ========== 运行输出 ==========
    └── 📁 run_YYYYMMDD_HHMMSS/    # 按时间戳命名的运行目录
        ├── episodes.jsonl         # 每tick记录
        ├── tool_calls.jsonl       # 工具调用记录
        ├── states.jsonl           # 状态历史
        ├── parameters.json        # 运行参数
        ├── final_state.json       # 最终状态
        ├── 📁 snapshots/          # 状态快照
        ├── 📁 evolution_archives/ # 进化归档
        └── 📁 eval/               # 评估结果
```

---

## 代码统计

| 指标 | 数值 |
|------|------|
| **Python文件总数** | 243 |
| **总代码行数** | 66,625 |
| **目录总数** | 103 |
| **主要模块数** | 13 |
| **测试文件数** | 24 |
| **配置文件数** | 8 |
| **文档文件数** | 170+ |

### 各模块代码行数

| 模块 | 行数 | 说明 |
|------|------|------|
| core/ | 18,338 | 核心运行时（生命循环、器官分化、进化引擎、成长系统） |
| tools/ | 9,982 | 工具系统（LLM API、工具执行、安全沙箱） |
| memory/ | 8,733 | 记忆系统（三层记忆、联想网络、梦境巩固） |
| organs/ | 7,956 | 器官系统（6个内部器官 + 肢体管理） |
| axiology/ | 7,874 | 价值系统（5维价值、驱动信号、补偿机制） |
| common/ | 4,670 | 公共模块（数据模型、配置、日志） |
| cognition/ | 2,079 | 认知系统（规划器、目标编译、验证器） |
| safety/ | 1,217 | 安全系统（预算控制、沙箱、风险评估） |
| persistence/ | 1,387 | 持久化（回放引擎、事件日志、快照） |
| perception/ | 1,675 | 感知系统（观察器、上下文构建、新颖性检测） |
| affect/ | 1,012 | 情绪系统（RPE计算、Mood/Stress更新） |
| metabolism/ | 918 | 代谢系统（昼夜节律、恢复机制、无聊累积） |
| lifecycle/ | 784 | 生命周期（启动流程、tick循环） |

---

## 快速开始

### 环境要求

- Python 3.9+
- Windows / Linux / macOS
- 8GB+ RAM (推荐)

### 安装步骤

```bash
# 进入项目目录
cd GenesisX

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置

**配置API Key**:

```bash
# Linux/Mac
export DASHSCOPE_API_KEY="your_api_key"

# Windows
setx DASHSCOPE_API_KEY "your_api_key"
```

### 运行

```bash
# 运行10个tick（默认）
python run.py --ticks 10

# 运行100个tick
python run.py --ticks 100

# 指定模式和种子
python run.py --mode friend --ticks 50 --seed 42
```

### 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_axiology.py -v
```

---

## 核心系统架构

### core/ - 核心运行时 (18,338行)

核心模块是系统的引擎，负责协调所有子系统的运行。

| 子模块 | 文件数 | 功能 |
|--------|--------|------|
| life_loop.py | 1 | 主生命循环，17阶段tick执行 |
| differentiate.py | 1 | 器官分化系统（基因表达控制） |
| evolution/ | 8 | 进化引擎（归档、克隆、变异、评估） |
| growth/ | 4 | 成长系统（肢体生成、LLM代码生成） |
| handlers/ | 5 | 处理器（动作执行、聊天、缺口检测） |
| stores/ | 6 | 存储系统（字段、槽位、信号、账本） |
| plugins/ | 3 | 插件系统 |

**关键特性**：
- 支持4种发育阶段：embryo → juvenile → adult → elder
- 支持5种运行模式：work, friend, sleep, reflect, play
- 动态器官表达/抑制（基于基因条件）
- 能力缺口检测和自动成长

### axiology/ - 5维价值系统 (7,874行)

实现论文《Genesis X: Axiology Engine for Digital Life》的核心价值理论。

| 维度 | 设定点 | 权重偏置 | 含义 | 驱动实现 |
|------|--------|----------|------|----------|
| Homeostasis | 0.85 | 1.0 | 资源平衡、压力管理 | HomeostasisDrive |
| Attachment | 0.70 | 0.8 | 社交连接、信任建立 | AttachmentDrive |
| Curiosity | 0.60 | 0.7 | 新奇探索、信息增益 | CuriosityDrive |
| Competence | 0.75 | 1.0 | 任务成功、技能成长 | CompetenceDrive |
| Safety | 0.70 | 1.2 | 风险回避、安全边际 | SafetyDrive |

**核心组件**：
- `parameters.py` - 论文Appendix A的所有超参数
- `weights.py` - 动态权重更新（softmax + 惯性）
- `gaps.py` - 价值缺口计算
- `reward.py` - 即时奖励计算
- `compensation.py` - 补偿机制（INTEGRITY/CONTRACT/EFFICIENCY/MEANING）
- `value_learning.py` - 价值学习（显式/隐式/内部反馈）
- `personality.py` - 大五人格调制（OCEAN）
- `drives/` - 5维驱动信号生成

### affect/ - 情绪系统 (1,012行)

基于RPE的情绪动态更新和行为调制。

**核心公式**：
- RPE: δ = r + γV(s') - V(s)
- Mood: Mood_{t+1} = Mood_t + k_+·max(δ,0) - k_-·max(-δ,0)
- Stress: Stress_{t+1} = Stress_t + s·max(-δ,0) - s'·max(δ,0)

**参数** (论文Section 3.7.3)：
- k_+ = 0.25 (正RPE情绪增益)
- k_- = 0.30 (负RPE情绪损失)
- s = 0.20 (负RPE压力增长)
- s' = 0.10 (正RPE压力缓解)
- γ = 0.97 (折扣因子)
- α_V = 0.05 (价值函数学习率)

**行为调制**：
- 探索率调制（高情绪→增加探索）
- 规划深度调制（高情绪→更深层规划）
- 风险容忍度调制（高压力→降低风险承受）
- 反思触发判断

### memory/ - 三层记忆系统 (8,733行)

实现CLS（互补学习系统）架构，支持联想记忆和梦境巩固。

| 记忆类型 | 容量 | 功能 | 实现文件 |
|----------|------|------|----------|
| Episodic | 50k | 具体事件存储 | episodic.py (523行) |
| Schema | 1k | 抽象模式/信念 | schema.py (332行) |
| Skill | 300 | 可执行技能 | skill.py (349行) |

**核心特性**：
- `familiarity.py` (890行) - 联想记忆网络（共现/因果/情绪/语义联想）
- `dream.py` (671行) - 梦境生成（记忆重组、创造性思考）
- `consolidation.py` (745行) - 记忆巩固（短→长转化）
- `semantic_novelty.py` (750行) - 语义新颖性计算
- `personality_encoding.py` (624行) - 人格调制的记忆编码
- `gates.py` - 海马体启发的门控机制
- `pruning.py` - 记忆剪枝和技能提取

### organs/ - 器官系统 (7,956行)

6个内部器官 + 动态肢体生成，实现"我能做什么"的执行能力。

| 器官 | 优先级 | 激活条件 | 职责 |
|------|--------|----------|------|
| Caretaker | 0 | 永远激活 | 系统自我维护、资源管理 |
| Immune | 1 | 永远激活 | 安全防护、威胁检测 |
| Mind | 2 | work/friend/reflect | 高级思维、规划推理 |
| Scout | 3 | juvenile/adult + stress<0.7 | 信息收集、环境探索 |
| Builder | 4 | adult/elder + work | 创建新能力、项目建设 |
| Archivist | 5 | sleep/reflect + fatigue>0.6 | 记忆管理、归档整理 |

**关键文件**：
- `base_organ.py` - 器官基类（能力执行接口）
- `unified_organ.py` - 统一器官管理
- `organ_manager.py` - 器官生命周期管理
- `organ_llm_session.py` - 器官LLM会话（共享大脑）

### tools/ - 工具系统 (9,982行)

提供LLM调用、工具执行、文件操作等外部能力。

**LLM集成**：
- `llm_api.py` - 统一LLM接口（支持OpenAI/Claude/DeepSeek/千问/Ollama）
- `llm_client.py` - LLM客户端封装
- `llm_orchestrator.py` - 多模型编排
- `llm_cache.py` - 响应缓存

**工具执行**：
- `tool_executor.py` - 工具执行引擎
- `tool_registry.py` - 工具注册表
- `dynamic_tool_registry.py` - 运行时工具注册
- `safe_executor.py` - AST安全检查的代码执行

**其他工具**：
- `blackboard.py` (1370行) - Mind Field架构（共享工作区）
- `embeddings.py` - 文本嵌入生成
- `vision.py` - 视觉感知
- `voice.py` - 语音输出
- `file_ops.py` - 文件操作
- `web_search.py` - 网络搜索

### safety/ - 安全系统 (1,217行)

多层安全防护机制。

| 组件 | 功能 |
|------|------|
| budget_control.py | API调用预算控制 |
| risk_assessment.py | 动作风险评估 |
| integrity_check.py | 价值一致性检查 |
| contract_guard.py | 契约守护（行为约束） |
| sandbox.py | 沙箱执行环境 |
| hallucination_check.py | LLM幻觉检测 |

### cognition/ - 认知系统 (2,079行)

高级认知功能实现。

| 组件 | 功能 |
|------|------|
| planner.py | 行动计划生成 |
| goal_compiler.py | 目标编译（冲突协调） |
| plan_evaluator.py | 计划质量评估 |
| verifier.py | 执行结果验证 |
| insight_quality.py | 洞察质量评估 |
| goal_progress.py | 目标进度跟踪 |

### 其他模块

| 模块 | 行数 | 功能 |
|------|------|------|
| perception/ | 1,675 | 环境观察、上下文构建、新颖性检测 |
| persistence/ | 1,387 | 回放引擎（3种模式）、事件日志、快照 |
| metabolism/ | 918 | 昼夜节律、恢复机制、无聊累积 |
| lifecycle/ | 784 | 生命周期管理、17阶段tick循环 |
| common/ | 4,670 | 数据模型（Pydantic）、配置、日志、指标 |

---


## 许可证

GenesisX 采用双许可模式：

| 许可证 | 适用场景 | 费用 |
|--------|----------|------|
| **AGPL-3.0** | 开源使用，愿意公开修改 | 免费 |
| **商业授权** | 闭源使用，SaaS 不公开代码 | 联系我们 |

### 快速判断

```
✓ AGPL-3.0（免费）适用于：
  - 开源项目中使用
  - 愿意以 AGPL-3.0 公开你的修改
  - 向 SaaS 用户提供源代码

✗ 需要商业授权的情况：
  - 想要保持修改后的代码专有
  - 提供 SaaS 服务但不公开源代码
  - 嵌入到闭源商业产品中
```

### 为什么选择 AGPL？

AGPL-3.0 堵住了 GPL 的"SaaS 漏洞"。如果你修改了 GenesisX 并以网络服务形式提供（如 Web 应用、API），你**必须**公开你的修改代码。这确保了：

- 贡献回馈社区
- 想闭源商业化的用户需要付费
- 价值交换的公平性

### 商业授权

商业授权咨询：
- **邮箱**: asdfghjklpo1211@icloud.com
- **请提供**: 公司名称、用途、预估用户数

完整条款见 [LICENSE](LICENSE)。

---

**文档更新**: 2026-03-11
**版本**: v1.3.0
**状态**: Production Ready (Code Review Complete)
