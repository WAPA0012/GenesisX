# GenesisX 项目结构树完整文档

**版本**: v1.3.0
**生成日期**: 2026-03-04
**项目描述**: 一个具有5维价值系统、情绪闭环、记忆巩固和自主能力的数字生命系统

---

## 项目统计

| 指标 | 数值 |
|------|------|
| Python 文件总数 | 243 |
| 目录总数 | 103 |
| 代码总行数 | 66,625 |
| 核心模块数 | 13 |
| 测试文件数 | 24 |
| 配置文件 | 8 |
| 文档文件 | 170+ |

### 各模块代码行数统计

| 模块 | 行数 | 主要功能 |
|------|------|----------|
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

## 目录树概览

```
GenesisX/
├── 📄 根目录文件 (15个)
├── 📁 affect/              # 情绪系统 (6个文件)
├── 📁 artifacts/           # 运行产出目录 (运行时数据)
├── 📁 axiology/            # 价值系统 (17个文件)
│   ├── 📁 drives/          # 驱动子系统 (6个文件)
│   └── 📁 examples/        # 价值系统示例 (2个文件)
├── 📁 benchmarks/          # 基准测试 (7个文件)
├── 📁 cognition/           # 认知系统 (7个文件)
├── 📁 common/              # 公共模块 (15个文件)
├── 📁 config/              # 配置文件 (9个文件)
├── 📁 core/                # 核心运行时 (32个文件)
│   ├── 📁 evolution/       # 进化子系统 (8个文件)
│   ├── 📁 growth/          # 成长子系统 (4个文件)
│   ├── 📁 handlers/        # 事件处理器 (5个文件)
│   ├── 📁 plugins/         # 插件系统 (3个文件)
│   └── 📁 stores/          # 存储后端 (6个文件)
├── 📁 docs/                # 文档目录 (80+个文件)
│   ├── 📁 api/             # API文档 (140+个文件)
│   ├── 📁 developer/       # 开发者文档
│   └── 📁 user-guide/      # 用户指南
├── 📁 eval/                # 评估系统 (2个文件)
├── 📁 examples/            # 示例代码 (3个文件)
├── 📁 lifecycle/           # 生命周期 (3个文件)
├── 📁 logs/                # 日志文件 (4个文件)
├── 📁 memory/              # 记忆系统 (24个文件)
│   ├── 📁 limb_guides/     # 肢体指南 (5个文件 + data/)
│   └── 📁 skills/          # 技能记忆 (7个文件)
├── 📁 metabolism/          # 代谢系统 (5个文件)
├── 📁 models/              # 数据模型 (3个文件)
├── 📁 organs/              # 器官系统 (13个文件)
│   ├── 📁 internal/        # 内部器官 (7个文件)
│   └── 📁 limbs/           # 肢体器官
├── 📁 perception/          # 感知系统 (8个文件)
├── 📁 persistence/         # 持久化 (6个文件)
├── 📁 safety/              # 安全系统 (7个文件)
├── 📁 tests/               # 测试套件 (24个文件)
├── 📁 tools/               # 工具系统 (25个文件)
├── 📁 web/                 # Web界面 (20+个文件)
│   ├── 📁 artifacts/       # Web运行产出
│   ├── 📁 logs/            # Web日志
│   ├── 📁 static/          # 静态资源 (CSS/JS)
│   └── 📁 templates/       # HTML模板 (9个文件)
├── 📁 __pycache__/         # Python缓存
└── 📁 .pytest_cache/       # Pytest缓存
```

---

## 1. 根目录文件 (Root Files)

| 文件名 | 功能描述 |
|--------|----------|
| [.env](.env) | **环境变量配置** - API密钥等敏感信息（不提交到git） |
| [.env.example](.env.example) | **环境变量模板** - 环境变量配置示例 |
| [.gitignore](.gitignore) | **Git忽略配置** - 指定不提交的文件 |
| [__init__.py](__init__.py) | **包初始化** - Python包初始化文件 |
| [chat_interactive.py](chat_interactive.py) | **交互式聊天** - 与数字生命进行对话交互的入口脚本 |
| [chat_test.txt](chat_test.txt) | **聊天测试数据** - 测试用的聊天内容 |
| [compile_code_docs.py](compile_code_docs.py) | **文档生成器** - 编译生成代码文档 |
| [daemon.py](daemon.py) | **守护进程** - 后台运行模式入口 |
| [launch_desktop.bat](launch_desktop.bat) | **桌面启动脚本** - Windows快速启动批处理 |
| [migrate_session.py](migrate_session.py) | **会话迁移工具** - 迁移旧版本会话数据 |
| [pyproject.toml](pyproject.toml) | **项目配置** - 现代Python项目配置（PEP 517/518） |
| [README.md](README.md) | **项目说明** - 项目介绍、安装、使用指南 |
| [requirements.txt](requirements.txt) | **生产依赖** - 运行时必需的Python包列表 |
| [requirements-dev.txt](requirements-dev.txt) | **开发依赖** - 开发和测试所需的额外包 |
| [run.py](run.py) | **主入口文件** - 启动GenesisX数字生命的主程序入口 |
| [run_tests.py](run_tests.py) | **测试运行器** - 执行测试套件 |
| [setup.py](setup.py) | **安装脚本** - 传统Python包安装配置 |
| [test_tools.py](test_tools.py) | **工具测试** - 工具系统测试脚本 |
| [ENVIRONMENT_GUIDE.md](ENVIRONMENT_GUIDE.md) | **环境配置指南** - 详细的环境配置说明 |
| [RUN_GUIDE.md](RUN_GUIDE.md) | **运行指南** - 系统运行说明文档 |
| [PROJECT_STRUCTURE_TREE.md](PROJECT_STRUCTURE_TREE.md) | **项目结构树** - 本文件 |

---

## 2. affect/ - 情绪系统模块

负责数字生命的情绪计算、RPE(奖励预测误差)处理、情绪衰减等。

| 文件 | 功能 |
|------|------|
| [__init__.py](affect/__init__.py) | 模块初始化，导出主要类和函数 |
| [rpe.py](affect/rpe.py) | **RPE计算** - 实现奖励预测误差 δ = r + γV(s') - V(s) |
| [mood.py](affect/mood.py) | **心情系统** - 基于RPE更新心情值，支持多维度情绪 |
| [stress_affect.py](affect/stress_affect.py) | **压力系统** - 基于负RPE累积压力，支持压力缓解 |
| [modulation.py](affect/modulation.py) | **情绪调节** - 情绪对认知和行为的调节作用 |
| [value_function.py](affect/value_function.py) | **价值函数** - 状态价值V(s)的估算与更新 |

---

## 3. axiology/ - 价值系统模块

实现5维价值系统(homeostasis, attachment, curiosity, competence, safety)，包括特征提取、缺口计算、动态权重等。

### 3.1 主模块文件

| 文件 | 功能 |
|------|------|
| [__init__.py](axiology/__init__.py) | 模块初始化，导出所有公共接口和补偿机制 |
| [axiology_config.py](axiology/axiology_config.py) | **配置加载器** - 从YAML加载价值系统参数 |
| [parameters.py](axiology/parameters.py) | **参数定义** - 论文Appendix A的所有超参数 |
| [value_dimensions.py](axiology/value_dimensions.py) | **价值维度** - 定义5个价值维度及其计算方法 |
| [feature_extractors.py](axiology/feature_extractors.py) | **特征提取** - 从状态中提取各价值维度的特征值 |
| [gaps.py](axiology/gaps.py) | **缺口计算** - 计算特征值与设定点之间的差距 |
| [weights.py](axiology/weights.py) | **动态权重** - 基于缺口计算softmax权重分布 |
| [reward.py](axiology/reward.py) | **奖励函数** - 综合各维度计算即时奖励 |
| [setpoints.py](axiology/setpoints.py) | **设定点管理** - 管理各维度的目标值 |
| [dynamic_setpoints.py](axiology/dynamic_setpoints.py) | **动态设定点** - 自动学习最优设定点 |
| [utilities_unified.py](axiology/utilities_unified.py) | **统一效用函数** - 计算各维度的效用值 |
| [value_learning.py](axiology/value_learning.py) | **价值学习** - 从经验中学习价值偏好 |
| [personality.py](axiology/personality.py) | **个性系统** - 定义个体的性格特质和偏好 |
| [compensation.py](axiology/compensation.py) | **补偿机制(方案B)** - INTEGRITY/CONTRACT/EFFICIENCY/MEANING的补偿实现 |

### 3.2 drives/ - 驱动子系统

| 文件 | 功能 |
|------|------|
| [__init__.py](axiology/drives/__init__.py) | 驱动模块初始化 |
| [base.py](axiology/drives/base.py) | **驱动基类** - 所有驱动的抽象基类 |
| [homeostasis.py](axiology/drives/homeostasis.py) | **稳态驱动** - 维持体内平衡(能量、疲劳、压力) |
| [attachment.py](axiology/drives/attachment.py) | **依恋驱动** - 社交连接和关系建立 |
| [curiosity.py](axiology/drives/curiosity.py) | **好奇驱动** - 探索新奇事物的动机 |
| [competence.py](axiology/drives/competence.py) | **胜任驱动** - 掌握技能和完成任务的动力 |
| [safety.py](axiology/drives/safety.py) | **安全驱动** - 规避风险和自我保护 |

### 3.3 examples/ - 示例代码

| 文件 | 功能 |
|------|------|
| [__init__.py](axiology/examples/__init__.py) | 示例模块初始化 |
| [compensation_example.py](axiology/examples/compensation_example.py) | 补偿机制使用示例 |

---

## 4. cognition/ - 认知系统模块

负责高级认知功能：规划、目标编译、验证等。

| 文件 | 功能 |
|------|------|
| [__init__.py](cognition/__init__.py) | 认知模块初始化 |
| [goal_compiler.py](cognition/goal_compiler.py) | **目标编译器** - 将用户目标编译为系统可执行目标 |
| [goal_progress.py](cognition/goal_progress.py) | **目标进度** - 跟踪目标完成进度 |
| [insight_quality.py](cognition/insight_quality.py) | **洞察质量** - 评估洞察的价值和质量 |
| [planner.py](cognition/planner.py) | **计划生成器** - 生成行动计划 |
| [plan_evaluator.py](cognition/plan_evaluator.py) | **计划评估** - 评估计划质量和可行性 |
| [verifier.py](cognition/verifier.py) | **验证器** - 验证计划执行结果 |

---

## 5. common/ - 公共模块

通用工具、配置和基础组件。

| 文件 | 功能 |
|------|------|
| [__init__.py](common/__init__.py) | 公共模块初始化 |
| [auth.py](common/auth.py) | **认证** - 用户认证和授权 |
| [config.py](common/config.py) | **配置** - 配置管理 |
| [config_manager.py](common/config_manager.py) | **配置管理器** - 配置文件加载和管理 |
| [constants.py](common/constants.py) | **常量** - 系统常量定义 |
| [database.py](common/database.py) | **数据库** - 数据库连接管理 |
| [error_handler.py](common/error_handler.py) | **错误处理** - 统一错误处理机制 |
| [hashing.py](common/hashing.py) | **哈希** - 哈希计算工具 |
| [health_check.py](common/health_check.py) | **健康检查** - 系统健康状态检查 |
| [jsonl.py](common/jsonl.py) | **JSONL处理** - JSONL格式读写工具 |
| [logger.py](common/logger.py) | **日志系统** - 统一的日志记录 |
| [metrics.py](common/metrics.py) | **指标收集** - 系统指标收集和上报 |
| [models.py](common/models.py) | **数据模型** - 核心数据模型定义 |
| [utils.py](common/utils.py) | **工具函数** - 通用工具函数集合 |

---

## 6. config/ - 配置文件目录

| 文件 | 功能 |
|------|------|
| [default_genome.yaml](config/default_genome.yaml) | **默认基因组** - 器官基因配置，定义初始人格 |
| [llm_config.env.example](config/llm_config.env.example) | **LLM配置示例** - LLM服务配置模板 |
| [mind_field.yaml](config/mind_field.yaml) | **心智场配置** - 心智场参数设置 |
| [multi_model.yaml](config/multi_model.yaml) | **多模型配置** - 多LLM模型协调配置 |
| [organ_llm.yaml](config/organ_llm.yaml) | **器官LLM配置** - 各器官使用的LLM配置 |
| [resources.yaml](config/resources.yaml) | **资源配置** - 资源限制和配额配置 |
| [runtime.yaml](config/runtime.yaml) | **运行时配置** - Tick配置、预算约束等 |
| [tool_manifest.yaml](config/tool_manifest.yaml) | **工具清单** - 可用工具定义和权限 |
| [value_setpoints.yaml](config/value_setpoints.yaml) | **价值设定点** - 5维价值系统的设定点配置 |

---

## 7. core/ - 核心运行时模块

系统的核心引擎，负责生命循环、器官分化、状态管理、tick调度等。

### 7.1 主模块文件

| 文件 | 功能 |
|------|------|
| [__init__.py](core/__init__.py) | 核心模块初始化 |
| [abstract_state.py](core/abstract_state.py) | **抽象状态** - 状态基类定义 |
| [autonomous_scheduler.py](core/autonomous_scheduler.py) | **自主调度器** - 自主行为的调度管理 |
| [capability_gap_detector.py](core/capability_gap_detector.py) | **能力缺口检测** - 识别系统能力不足 |
| [capability_manager.py](core/capability_manager.py) | **能力管理器** - 系统能力的管理 |
| [capability_router.py](core/capability_router.py) | **能力路由** - 动态能力分发和路由 |
| [differentiate.py](core/differentiate.py) | **器官分化** - 发育阶段和器官表达系统 |
| [emotion_decay.py](core/emotion_decay.py) | **情绪衰减** - 情绪随时间的自然衰减 |
| [exceptions.py](core/exceptions.py) | **异常定义** - 核心异常类 |
| [exploration.py](core/exploration.py) | **探索系统** - 探索行为管理 |
| [invariants.py](core/invariants.py) | **不变量检查** - 维护系统不变式 |
| [life_loop.py](core/life_loop.py) | **生命循环** - 主循环引擎，协调所有系统 |
| [life_loop_backup.py](core/life_loop_backup.py) | **生命循环备份** - 备用版本 |
| [resource_config.py](core/resource_config.py) | **资源配置** - 资源管理配置 |
| [scheduler.py](core/scheduler.py) | **调度器** - 任务和器官的调度管理 |
| [state.py](core/state.py) | **状态管理** - 系统状态的定义和更新 |
| [tick.py](core/tick.py) | **Tick执行** - 单个tick的完整执行流程 |

### 7.2 evolution/ - 进化子系统

| 文件 | 功能 |
|------|------|
| [__init__.py](core/evolution/__init__.py) | 进化模块初始化 |
| [archive_manager.py](core/evolution/archive_manager.py) | **档案管理** - 进化档案的存储和检索 |
| [clone_manager.py](core/evolution/clone_manager.py) | **克隆管理** - 系统克隆和复制 |
| [evaluation_manager.py](core/evolution/evaluation_manager.py) | **评估管理** - 进化适应度评估 |
| [evolution_engine.py](core/evolution/evolution_engine.py) | **进化引擎** - 进化核心算法 |
| [models.py](core/evolution/models.py) | **进化模型** - 进化数据模型定义 |
| [mutation_manager.py](core/evolution/mutation_manager.py) | **变异管理** - 参数变异和优化 |
| [transfer_manager.py](core/evolution/transfer_manager.py) | **迁移管理** - 学习迁移和共享 |

### 7.3 growth/ - 成长子系统

| 文件 | 功能 |
|------|------|
| [__init__.py](core/growth/__init__.py) | 成长模块初始化 |
| [growth_manager.py](core/growth/growth_manager.py) | **成长管理器** - 管理系统成长过程 |
| [limb_builder.py](core/growth/limb_builder.py) | **肢体构建器** - 动态构建新肢体/工具 |
| [limb_generator.py](core/growth/limb_generator.py) | **肢体生成器** - LLM驱动的肢体生成(V32风格) |

### 7.4 handlers/ - 事件处理器

| 文件 | 功能 |
|------|------|
| [__init__.py](core/handlers/__init__.py) | 处理器模块初始化 |
| [action_executor.py](core/handlers/action_executor.py) | **行动执行器** - 执行系统行动 |
| [caretaker_mode.py](core/handlers/caretaker_mode.py) | **看护者模式** - 自我维护模式 |
| [chat_handler.py](core/handlers/chat_handler.py) | **聊天处理器** - 处理聊天交互 |
| [gap_detector.py](core/handlers/gap_detector.py) | **差距检测** - 检测状态差距 |

### 7.5 plugins/ - 插件系统

| 文件 | 功能 |
|------|------|
| [__init__.py](core/plugins/__init__.py) | 插件模块初始化 |
| [plugin_manager.py](core/plugins/plugin_manager.py) | **插件管理器** - 管理系统插件 |
| [templates/__init__.py](core/plugins/templates/__init__.py) | 插件模板 |

### 7.6 stores/ - 存储后端

| 文件 | 功能 |
|------|------|
| [__init__.py](core/stores/__init__.py) | 存储模块初始化 |
| [factory.py](core/stores/factory.py) | **存储工厂** - 创建存储实例 |
| [fields.py](core/stores/fields.py) | **字段存储** - 状态字段的存储和访问 |
| [ledger.py](core/stores/ledger.py) | **账本存储** - 代谢账本，追踪资源消耗 |
| [signals.py](core/stores/signals.py) | **信号存储** - 信号值的存储和更新 |
| [slots.py](core/stores/slots.py) | **槽位存储** - 动态槽位管理 |

---

## 8. docs/ - 文档目录

### 8.1 主文档文件

| 文件 | 功能 |
|------|------|
| [API_REFERENCE.md](docs/API_REFERENCE.md) | **API参考手册** - 完整的API文档 |
| [architecture_clarification.md](docs/architecture_clarification.md) | **架构说明** - 系统架构澄清 |
| [architecture_diagram.md](docs/architecture_diagram.md) | **架构图** - 系统架构可视化 |
| [dependency_analysis.md](docs/dependency_analysis.md) | **依赖分析** - 模块依赖关系分析 |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | **部署指南** - 生产环境部署说明 |
| [evolution_stages.md](docs/evolution_stages.md) | **进化阶段** - 系统进化阶段说明 |
| [LLM_API配置指南.md](docs/LLM_API配置指南.md) | **LLM配置指南** - LLM API配置（中文） |
| [MULTI_MODEL_GUIDE.md](docs/MULTI_MODEL_GUIDE.md) | **多模型指南** - 多LLM模型使用 |
| [project_structure_full.md](docs/project_structure_full.md) | **完整结构** - 完整项目结构说明 |
| [refactoring_complete.md](docs/refactoring_complete.md) | **重构说明** - 重构完成记录 |
| [skills_vs_organs_summary.md](docs/skills_vs_organs_summary.md) | **技能与器官** - 两者对比总结 |
| [tutorials.md](docs/tutorials.md) | **教程** - 使用教程 |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | **用户指南** - 用户使用说明 |
| [VALUE_SYSTEM_CONFIG.md](docs/VALUE_SYSTEM_CONFIG.md) | **价值系统配置** - 价值系统详细配置 |
| [WEB_OPTIMIZATION.md](docs/WEB_OPTIMIZATION.md) | **Web优化** - Web界面优化指南 |

### 8.2 api/ - API文档目录 (140+个文件)

自动生成的API文档，每个模块和子模块都有对应的.md文件：

- `affect*.md` - 情感系统API
- `axiology*.md` - 价值系统API
- `cognition*.md` - 认知系统API
- `common*.md` - 公共组件API
- `core*.md` - 核心系统API
- `memory*.md` - 记忆系统API
- `metabolism*.md` - 代谢系统API
- `organs*.md` - 器官系统API
- `perception*.md` - 感知系统API
- `persistence*.md` - 持久化API
- `safety*.md` - 安全系统API
- `tools*.md` - 工具系统API

| 关键文件 | 功能 |
|---------|------|
| [docs.json](docs/api/docs.json) | API文档JSON索引 |
| [README.md](docs/api/README.md) | API文档索引页面 |

### 8.3 developer/ & user-guide/

| 目录 | 功能 |
|------|------|
| [developer/README.md](docs/developer/README.md) | 开发者文档入口 |
| [user-guide/README.md](docs/user-guide/README.md) | 用户指南入口 |

---

## 9. eval/ - 评估系统

| 文件 | 功能 |
|------|------|
| [__init__.py](eval/__init__.py) | 评估模块初始化 |
| [gxbs.py](eval/gxbs.py) | **GXBS评估** - GenesisX基准评估标准 |

---

## 10. examples/ - 示例代码

| 文件 | 功能 |
|------|------|
| [api_client.py](examples/api_client.py) | **API客户端示例** - 展示如何调用API |
| [basic_usage.py](examples/basic_usage.py) | **基础用法** - 系统基础使用示例 |
| [interactive_scenarios.py](examples/interactive_scenarios.py) | **交互场景** - 交互式使用场景示例 |

---

## 11. lifecycle/ - 生命周期

| 文件 | 功能 |
|------|------|
| [__init__.py](lifecycle/__init__.py) | 生命周期模块初始化 |
| [genesis_lifecycle.py](lifecycle/genesis_lifecycle.py) | **创世纪生命周期** - 系统启动和初始化流程 |
| [tick_loop.py](lifecycle/tick_loop.py) | **滴答循环** - 主运行循环实现 |

---

## 12. logs/ - 日志目录

| 文件 | 功能 |
|------|------|
| [errors.json](logs/errors.json) | **错误日志** - 错误记录JSON格式 |
| [genesis.json](logs/genesis.json) | **主日志** - 系统运行日志 |
| [genesis.json.1](logs/genesis.json.1) | **日志备份** - 轮转备份日志 |
| [server.log](logs/server.log) | **服务器日志** - Web服务器日志 |

---

## 13. memory/ - 记忆系统模块

实现情节记忆、模式记忆、联想记忆、记忆巩固等。

### 13.1 主模块文件

| 文件 | 功能 |
|------|------|
| [__init__.py](memory/__init__.py) | 记忆模块初始化 |
| [consolidation.py](memory/consolidation.py) | **记忆巩固** - 梦-反思-洞察巩固机制 |
| [dream.py](memory/dream.py) | **梦系统** - 睡眠时的记忆处理和整合 |
| [episodic.py](memory/episodic.py) | **情节记忆** - 存储具体事件和经历 |
| [familiarity.py](memory/familiarity.py) | **熟悉度** - 联想记忆的熟悉度计算 |
| [gates.py](memory/gates.py) | **记忆门控** - 控制信息流入记忆 |
| [indices.py](memory/indices.py) | **记忆索引** - 记忆索引系统 |
| [organ_guide_manager.py](memory/organ_guide_manager.py) | **器官指南管理器** - 管理器官使用指南 |
| [personality_encoding.py](memory/personality_encoding.py) | **人格编码** - 人格调制的记忆编码 |
| [pruning.py](memory/pruning.py) | **记忆修剪** - 遗忘曲线和记忆清理 |
| [retrieval.py](memory/retrieval.py) | **记忆检索** - 混合检索系统 |
| [salience.py](memory/salience.py) | **显著性** - 计算记忆的重要性 |
| [schema.py](memory/schema.py) | **模式记忆** - 抽象模式和规律 |
| [semantic_novelty.py](memory/semantic_novelty.py) | **语义新颖性** - 使用嵌入向量评估新颖性 |
| [skill.py](memory/skill.py) | **技能记忆** - 技能的存储和学习 |
| [smart_retrieval.py](memory/smart_retrieval.py) | **智能检索** - 智能记忆检索系统 |
| [utils.py](memory/utils.py) | **记忆工具** - 记忆相关工具函数 |

### 13.2 limb_guides/ - 肢体指南

| 文件 | 功能 |
|------|------|
| [__init__.py](memory/limb_guides/__init__.py) | 肢体指南模块初始化 |
| [data/organ_guides.json](memory/limb_guides/data/organ_guides.json) | **器官指南数据** - JSON格式的指南数据 |
| [data_analysis_guide.py](memory/limb_guides/data_analysis_guide.py) | **数据分析指南** - 数据分析能力指南 |
| [file_ops_guide.py](memory/limb_guides/file_ops_guide.py) | **文件操作指南** - 文件操作能力指南 |
| [pdf_processing_guide.py](memory/limb_guides/pdf_processing_guide.py) | **PDF处理指南** - PDF处理能力指南 |
| [web_fetcher_guide.py](memory/limb_guides/web_fetcher_guide.py) | **网页获取指南** - 网页获取能力指南 |

### 13.3 skills/ - 技能系统

| 文件 | 功能 |
|------|------|
| [__init__.py](memory/skills/__init__.py) | 技能模块初始化 |
| [analysis_skill.py](memory/skills/analysis_skill.py) | **分析技能** - 数据分析技能实现 |
| [base.py](memory/skills/base.py) | **技能基类** - 所有技能的抽象基类 |
| [file_skill.py](memory/skills/file_skill.py) | **文件技能** - 文件操作技能实现 |
| [pdf_skill.py](memory/skills/pdf_skill.py) | **PDF技能** - PDF处理技能实现 |
| [skill_registry.py](memory/skills/skill_registry.py) | **技能注册表** - 技能注册和管理 |
| [web_skill.py](memory/skills/web_skill.py) | **网页技能** - 网页操作技能实现 |

---

## 14. metabolism/ - 代谢系统模块

负责数字生命的能量管理和资源调节。

| 文件 | 功能 |
|------|------|
| [__init__.py](metabolism/__init__.py) | 代谢模块初始化 |
| [boredom.py](metabolism/boredom.py) | **厌倦系统** - 激励探索，避免停滞 |
| [circadian.py](metabolism/circadian.py) | **昼夜节律** - 模拟生物钟 |
| [recovery.py](metabolism/recovery.py) | **恢复系统** - 休息和恢复机制 |
| [resource_pressure.py](metabolism/resource_pressure.py) | **资源压力** - 资源不足时的行为调节 |

---

## 15. models/ - 数据模型

| 文件 | 功能 |
|------|------|
| [__init__.py](models/__init__.py) | 模型模块初始化 |
| [session_models.py](models/session_models.py) | **会话模型** - 会话数据模型定义 |
| [user.py](models/user.py) | **用户模型** - 用户数据模型定义 |

---

## 16. organs/ - 器官系统模块

管理所有内部器官和肢体，提供统一的调用接口。

### 16.1 主模块文件

| 文件 | 功能 |
|------|------|
| [__init__.py](organs/__init__.py) | 器官模块初始化 |
| [base_organ.py](organs/base_organ.py) | **器官基类** - 所有器官的抽象基类 |
| [organ_interface.py](organs/organ_interface.py) | **器官接口** - 器官接口定义 |
| [organ_llm_session.py](organs/organ_llm_session.py) | **器官LLM会话** - 器官的LLM会话管理 |
| [organ_manager.py](organs/organ_manager.py) | **器官管理器** - 管理所有器官和肢体 |
| [organ_selector.py](organs/organ_selector.py) | **器官选择器** - 根据情境选择器官 |
| [unified_organ.py](organs/unified_organ.py) | **统一器官** - 统一器官实现 |

### 16.2 internal/ - 内部器官

| 文件 | 功能 |
|------|------|
| [__init__.py](organs/internal/__init__.py) | 内部器官模块初始化 |
| [archivist_organ.py](organs/internal/archivist_organ.py) | **档案器官** - 记忆管理和归档 |
| [builder_organ.py](organs/internal/builder_organ.py) | **构建器官** - 创建新能力和肢体 |
| [caretaker_organ.py](organs/internal/caretaker_organ.py) | **看护器官** - 系统自我维护 |
| [immune_organ.py](organs/internal/immune_organ.py) | **免疫器官** - 安全防护和威胁检测 |
| [mind_organ.py](organs/internal/mind_organ.py) | **心智器官** - 高级思维和决策 |
| [scout_organ.py](organs/internal/scout_organ.py) | **侦察器官** - 信息收集和探索 |

### 16.3 limbs/ - 肢体器官

| 文件 | 功能 |
|------|------|
| [__init__.py](organs/limbs/__init__.py) | 肢体模块初始化（可动态扩展） |

---

## 17. perception/ - 感知系统模块

负责感知输入和环境理解。

| 文件 | 功能 |
|------|------|
| [__init__.py](perception/__init__.py) | 感知模块初始化 |
| [command_parser.py](perception/command_parser.py) | **命令解析** - 解析用户命令 |
| [context_builder.py](perception/context_builder.py) | **上下文构建** - 构建感知上下文 |
| [novelty.py](perception/novelty.py) | **新颖性检测** - 检测新颖刺激 |
| [observer.py](perception/observer.py) | **观察者** - 监控系统和环境 |
| [self_perception.py](perception/self_perception.py) | **自我感知** - 自我状态监控 |
| [signal_filter.py](perception/signal_filter.py) | **信号过滤** - 过滤感知信号 |
| [time_perception.py](perception/time_perception.py) | **时间感知** - 时间知觉处理 |

---

## 18. persistence/ - 持久化模块

负责状态和数据的持久化存储。

| 文件 | 功能 |
|------|------|
| [__init__.py](persistence/__init__.py) | 持久化模块初始化 |
| [event_log.py](persistence/event_log.py) | **事件日志** - 记录所有事件 |
| [replay.py](persistence/replay.py) | **回放引擎** - 三模式回放(strict/semantic/fork) |
| [snapshot.py](persistence/snapshot.py) | **状态快照** - 系统状态快照 |
| [storage.py](persistence/storage.py) | **存储管理** - 通用存储接口 |
| [tool_call_log.py](persistence/tool_call_log.py) | **工具调用日志** - 专门记录工具调用 |

---

## 19. safety/ - 安全系统模块

负责数字生命的安全防护和风险控制。

| 文件 | 功能 |
|------|------|
| [__init__.py](safety/__init__.py) | 安全模块初始化 |
| [budget_control.py](safety/budget_control.py) | **预算控制** - 资源使用限制 |
| [contract_guard.py](safety/contract_guard.py) | **契约守护** - 行为约束检查 |
| [hallucination_check.py](safety/hallucination_check.py) | **幻觉检测** - LLM输出验证 |
| [integrity_check.py](safety/integrity_check.py) | **完整性检查** - 价值一致性验证 |
| [risk_assessment.py](safety/risk_assessment.py) | **风险评估** - 评估动作的风险等级 |
| [sandbox.py](safety/sandbox.py) | **沙箱** - 安全执行环境 |

---

## 20. tests/ - 测试套件目录

包含24个测试文件，覆盖系统各个模块。

| 文件 | 测试内容 |
|------|----------|
| [__init__.py](tests/__init__.py) | 测试包初始化 |
| [conftest.py](tests/conftest.py) | pytest配置 - 测试夹具和共享设置 |
| [test_affect_integration.py](tests/test_affect_integration.py) | 情绪系统集成测试 |
| [test_associative_memory.py](tests/test_associative_memory.py) | 联想记忆测试 |
| [test_axiology.py](tests/test_axiology.py) | 价值系统测试 |
| [test_chat_interaction.py](tests/test_chat_interaction.py) | 聊天交互测试 |
| [test_dynamic_setpoints.py](tests/test_dynamic_setpoints.py) | 动态设定点测试 |
| [test_e2e.py](tests/test_e2e.py) | 端到端测试 |
| [test_emotion_combinations.py](tests/test_emotion_combinations.py) | 情感组合测试 |
| [test_fixes.py](tests/test_fixes.py) | 修复验证测试 |
| [test_fixes_verification.py](tests/test_fixes_verification.py) | 修复确认测试 |
| [test_goal_compiler.py](tests/test_goal_compiler.py) | 目标编译器测试 |
| [test_insight_quality.py](tests/test_insight_quality.py) | 洞察质量测试 |
| [test_integration.py](tests/test_integration.py) | 集成测试 |
| [test_life_loop_integration.py](tests/test_life_loop_integration.py) | 生命循环集成测试 |
| [test_lifecycle.py](tests/test_lifecycle.py) | 生命周期测试 |
| [test_llm_features.py](tests/test_llm_features.py) | LLM功能测试 |
| [test_memory.py](tests/test_memory.py) | 记忆系统测试 |
| [test_organ_coordination.py](tests/test_organ_coordination.py) | 器官协调测试 |
| [test_organs.py](tests/test_organs.py) | 器官系统测试 |
| [test_p2_9_p1_8.py](tests/test_p2_9_p1_8.py) | 特定功能测试 |
| [test_semantic_novelty.py](tests/test_semantic_novelty.py) | 语义新颖性测试 |
| [test_tool_parser.py](tests/test_tool_parser.py) | 工具解析测试 |
| [test_utility_normalization.py](tests/test_utility_normalization.py) | 效用归一化测试 |
| [test_value_dimensions.py](tests/test_value_dimensions.py) | 价值维度测试 |

---

## 21. tools/ - 工具系统模块

提供各种外部工具和能力接口。

| 文件 | 功能 |
|------|------|
| [__init__.py](tools/__init__.py) | 工具模块初始化 |
| [blackboard.py](tools/blackboard.py) | **黑板系统** - 信息共享和工作区 |
| [capability.py](tools/capability.py) | **能力工具** - 系统能力接口 |
| [code_exec.py](tools/code_exec.py) | **代码执行** - 安全的代码执行环境 |
| [cost_model.py](tools/cost_model.py) | **成本模型** - API调用成本计算 |
| [dynamic_tool_registry.py](tools/dynamic_tool_registry.py) | **动态工具注册** - 运行时工具注册 |
| [embeddings.py](tools/embeddings.py) | **向量嵌入** - 文本嵌入工具 |
| [file_ops.py](tools/file_ops.py) | **文件操作** - 文件读写和管理 |
| [llm_api.py](tools/llm_api.py) | **LLM API** - LLM服务调用接口 |
| [llm_cache.py](tools/llm_cache.py) | **LLM缓存** - LLM响应缓存 |
| [llm_client.py](tools/llm_client.py) | **LLM客户端** - 统一LLM接口 |
| [llm_orchestrator.py](tools/llm_orchestrator.py) | **LLM编排器** - 多模型协调 |
| [memory_tools.py](tools/memory_tools.py) | **记忆工具** - 记忆操作工具 |
| [messaging.py](tools/messaging.py) | **消息系统** - 内部消息传递 |
| [safe_executor.py](tools/safe_executor.py) | **安全执行器** - AST安全检查的执行器 |
| [tool_definitions.py](tools/tool_definitions.py) | **工具定义** - 工具元数据定义 |
| [tool_executor.py](tools/tool_executor.py) | **工具执行器** - 工具执行引擎 |
| [tool_protocol.py](tools/tool_protocol.py) | **工具协议** - 工具调用标准协议 |
| [tool_registry.py](tools/tool_registry.py) | **工具注册表** - 管理所有可用工具 |
| [tool_system_v2.py](tools/tool_system_v2.py) | **工具系统V2** - 统一工具调用接口 |
| [vision.py](tools/vision.py) | **视觉处理** - 图像处理工具 |
| [voice.py](tools/voice.py) | **语音处理** - 语音识别和合成 |
| [web_search.py](tools/web_search.py) | **网页搜索** - 网络搜索集成 |

---

## 22. benchmarks/ - 性能基准测试

| 文件 | 功能 |
|------|------|
| [__init__.py](benchmarks/__init__.py) | 基准测试模块初始化 |
| [emotion_benchmark.py](benchmarks/emotion_benchmark.py) | **情感基准** - 情感系统性能测试 |
| [gxbs_runner.py](benchmarks/gxbs_runner.py) | **GXBS运行器** - GXBS基准运行 |
| [memory_benchmark.py](benchmarks/memory_benchmark.py) | **记忆基准** - 记忆系统性能测试 |
| [multi_model_benchmark.py](benchmarks/multi_model_benchmark.py) | **多模型基准** - 多模型性能比较 |
| [personality_benchmark.py](benchmarks/personality_benchmark.py) | **人格基准** - 人格系统测试 |
| [run_gxbs.py](benchmarks/run_gxbs.py) | **运行GXBS** - GXBS基准启动脚本 |
| [results/](benchmarks/results/) | **结果目录** - 基准测试结果存储 |

---

## 23. web/ - Web界面模块

提供Web界面用于交互。

### 23.1 主文件

| 文件 | 功能 |
|------|------|
| [app.py](web/app.py) | **Flask应用** - Web服务器主程序 |
| [websocket_server.py](web/websocket_server.py) | **WebSocket服务器** - 实时通信 |
| [server.log](web/server.log) | **服务器日志** - Web服务器日志 |
| [mood-website.html](web/mood-website.html) | **情绪展示** - 情绪状态展示页面 |

### 23.2 static/ - 静态资源

#### css/

| 文件 | 功能 |
|------|------|
| [chat-styles.css](web/static/css/chat-styles.css) | **聊天样式** - 聊天界面CSS |
| [genesis-theme.css](web/static/css/genesis-theme.css) | **Genesis主题** - 主题样式 |
| [navigation.css](web/static/css/navigation.css) | **导航样式** - 导航栏CSS |
| [style.css](web/static/css/style.css) | **主样式** - 主样式表 |

#### js/

| 文件 | 功能 |
|------|------|
| [app.js](web/static/js/app.js) | **主应用JS** - 主应用逻辑 |
| [chat-app.js](web/static/js/chat-app.js) | **聊天应用JS** - 聊天功能实现 |
| [navigation.js](web/static/js/navigation.js) | **导航JS** - 导航功能实现 |

### 23.3 templates/ - HTML模板

| 文件 | 功能 |
|------|------|
| [chat.html](web/templates/chat.html) | **聊天页面** - 聊天界面模板 |
| [dashboard.html](web/templates/dashboard.html) | **仪表板** - 系统仪表板 |
| [debug.html](web/templates/debug.html) | **调试页面** - 调试界面 |
| [error.html](web/templates/error.html) | **错误页面** - 错误展示模板 |
| [index.html](web/templates/index.html) | **首页** - 网站首页 |
| [monitor.html](web/templates/monitor.html) | **监控页面** - 系统监控界面 |
| [navigation_test.html](web/templates/navigation_test.html) | **导航测试** - 导航测试页面 |
| [settings.html](web/templates/settings.html) | **设置页面** - 系统设置界面 |

### 23.4 web/artifacts/ & web/logs/

| 目录/文件 | 功能 |
|----------|------|
| [artifacts/web_run/](web/artifacts/web_run/) | Web运行数据存储 |
| [logs/errors.json](web/logs/errors.json) | Web错误日志 |
| [logs/genesis.json](web/logs/genesis.json) | Web运行日志 |

---

## 24. artifacts/ - 运行时数据目录

存储系统运行时产生的各种数据（按时间戳命名）。

### 24.1 聊天会话数据

每个聊天会话目录包含：

| 文件 | 功能 |
|------|------|
| `episodes.jsonl` | **事件记录** - 发生的事件序列 |
| `states.jsonl` | **状态记录** - 系统状态变化序列 |
| `tool_calls.jsonl` | **工具调用** - 工具调用记录 |

聊天会话示例：
- `chat_20260216_142723/`
- `chat_20260216_142739/`
- `chat_20260216_142820/`
- `chat_20260216_143121/`
- `chat_20260216_143156/`
- `chat_20260216_143536/`
- `chat_20260216_144817/`

### 24.2 运行数据

每次完整运行包含：

| 文件/目录 | 功能 |
|----------|------|
| `episodes.jsonl` | **事件记录** |
| `states.jsonl` | **状态序列** |
| `tool_calls.jsonl` | **工具调用记录** |
| `final_state.json` | **最终状态** - 运行结束时的状态 |
| `override_state.json` | **覆盖状态** - 状态覆盖配置 |
| `value_parameters.json` | **价值参数** - 价值系统参数快照 |
| `evolution_archives/` | **进化档案** - 进化历史 |
| `evolution_instances/` | **进化实例** - 进化运行实例 |

运行示例：
- `run_20260223_110305_42/`
- `run_20260223_110330_42/`
- `run_20260223_110503_42/`

### 24.3 测试运行数据

| 目录 | 功能 |
|------|------|
| `test_chat/` | 聊天测试数据 |
| `test_chat_5dim/` | 5维价值测试数据 |
| `test_chat_debug/` | 调试测试数据 |
| `test_chat_debug2/` | 调试测试数据2 |
| `test_chat_final/` | 最终测试数据 |
| `test_chat_fix/` | 修复测试数据 |
| `test_chat_fix2/` | 修复测试数据2 |
| `test_chat_full/` | 完整测试数据 |
| `test_chat_llm/` | LLM测试数据 |
| `test_chat_outcome/` | 结果测试数据 |
| `test_chat_success/` | 成功测试数据 |
| `test_chat_user_msg/` | 用户消息测试数据 |
| `test_context/` | 上下文测试数据 |
| `test_llm_features/` | LLM功能测试数据 |
| `test_run/` ~ `test_run8/` | 运行测试数据1-8 |
| `web_run/` | Web运行数据 |

### 24.4 动态生成的肢体

| 目录 | 功能 |
|------|------|
| `limbs/v32_limb_*/` | **动态肢体** - 运行时生成的肢体模块 |
| `limbs/v32_limb_*/__init__.py` | 肢体模块实现 |

---

## 25. 缓存目录（自动生成）

### __pycache__/

每个Python模块目录下都会有此目录，存储 `.pyc` 编译文件。

### .pytest_cache/

| 文件 | 功能 |
|------|------|
| `.gitignore` | Git忽略配置 |
| `CACHEDIR.TAG` | 缓存目录标记 |
| `README.md` | 缓存说明 |
| `v/cache/lastfailed` | 上次失败的测试 |
| `v/cache/nodeids` | 测试节点ID缓存 |

---

## 附录A: 5维价值系统

### 价值维度定义

| 维度 | 英文 | 设定点 | 权重偏置 | 功能描述 |
|------|------|--------|----------|----------|
| 稳态 | HOMEOSTASIS | 0.70 | 1.0 | 资源平衡、压力管理、系统稳定 |
| 依恋 | ATTACHMENT | 0.70 | 0.8 | 社交连接、信任建立、忽视回避 |
| 好奇 | CURIOSITY | 0.60 | 0.7 | 新奇探索、信息增益、规律发现 |
| 胜任 | COMPETENCE | 0.75 | 1.0 | 任务成功、技能成长、效能感 |
| 安全 | SAFETY | 0.80 | 1.2 | 风险回避、损失预防、安全边际 |

### 补偿机制(方案B)

删除的维度通过补偿机制实现：

| 删除维度 | 补偿方式 | 核心类 |
|---------|---------|--------|
| INTEGRITY | 硬约束检查 | `IntegrityConstraintChecker` |
| CONTRACT | 外部信号提升权重 | `ContractSignalBooster` |
| EFFICIENCY | 并入 HOMEOSTASIS | `EfficiencyMonitor` |
| MEANING | 并入 CURIOSITY | `MeaningTracker` |

---

## 附录B: 自主能力(V32风格)

通过 `core/growth/limb_generator.py` 实现：

| 能力 | 方法 | 与价值系统联动 |
|------|------|---------------|
| 吞噬 | `devour(target_path)` | CURIOSITY 驱动 |
| 生长 | `grow_limb_v32(task, llm_func)` | COMPETENCE 驱动 |
| 挥舞 | `flex_limb_v32(filepath)` | SAFETY 约束 |
| 自主 | `autonomous_action(dopamine, stress, curiosity)` | 条件触发 |

---

## 附录C: 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        GenesisX 数字生命                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐                                ┌─────────────┐│
│  │  perception │ ──→ 输入处理                    │    tools    ││
│  │   感知系统   │                                │   工具系统   ││
│  └──────┬──────┘                                └──────┬──────┘│
│         │                                              │       │
│         ▼                                              ▼       │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐    │
│  │  cognition  │ ←──→ │    core     │ ←──→ │   organs    │    │
│  │   认知系统   │      │   核心系统   │      │   器官系统   │    │
│  └──────┬──────┘      └──────┬──────┘      └──────┬──────┘    │
│         │                    │                    │           │
│         └────────────────────┼────────────────────┘           │
│                              │                                 │
│                              ▼                                 │
│                    ┌─────────────────┐                        │
│                    │     memory      │                        │
│                    │     记忆系统     │                        │
│                    └────────┬────────┘                        │
│                             │                                  │
│         ┌───────────────────┼───────────────────┐             │
│         │                   │                   │             │
│         ▼                   ▼                   ▼             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     │
│  │  axiology   │     │   affect    │     │  metabolism │     │
│  │   价值系统   │     │   情感系统   │     │   代谢系统   │     │
│  └──────┬──────┘     └──────┬──────┘     └──────┬──────┘     │
│         │                   │                   │             │
│         └───────────────────┼───────────────────┘             │
│                             │                                  │
│                             ▼                                  │
│                    ┌─────────────────┐                        │
│                    │     safety      │                        │
│                    │     安全系统     │                        │
│                    └────────┬────────┘                        │
│                             │                                  │
│                             ▼                                  │
│                    ┌─────────────────┐                        │
│                    │  persistence    │                        │
│                    │    持久化系统    │                        │
│                    └─────────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 快速入口

| 功能 | 命令 |
|------|------|
| 运行系统 | `python run.py` |
| 交互聊天 | `python chat_interactive.py` |
| Web界面 | `python web/app.py` |
| 运行测试 | `python run_tests.py` 或 `pytest` |
| 守护进程 | `python daemon.py` |

---

**文档版本**: v1.3.0
**最后更新**: 2026-03-04
