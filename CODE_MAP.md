# GenesisX 代码地图与技术说明

> **文档目的**：供 AI/开发者在新会话中快速建立对整个项目的精确认知，直接进入优化工作。
> **覆盖范围**：逐模块、逐文件梳理 242 个 Python 文件（约 84k 行），标注设计意图、数据流、模块耦合与潜在问题。
> **生成方式**：通读源码 + 论文对照，标注 `🔍问题` 为值得后续迭代的点。
> **版本基准**：v1.3.0，5 维价值系统（已从早期 9 维精简）。
> **最后更新**：2026-07-06
> **进度**：✅ 第1-2章已完成精读（46文件/14k行） ✅ 第8章 core/ 已完成精读（43文件/18338行） ✅ 第3章 memory/ 已完成精读（29文件/8733行） ✅ 第5章 organs/ 已完成精读（15文件/7956行） ⏳ 第4,6,7,9章待续（61文件/22k行）

---

## 目录

- [0. 项目概览与心智模型](#0-项目概览与心智模型)
- [1. 基础层 `common/` + `models/`](#1-基础层-common--models) ✅
- [2. 核心理论层 `axiology/` + `affect/`](#2-核心理论层-axiology--affect) ✅
- [3. 记忆层 `memory/`](#3-记忆层-memory) ✅
- [4. 认知/感知/代谢 `cognition/` + `perception/` + `metabolism/`](#4-认知感知代谢) ⏳待续
- [5. 器官层 `organs/`](#5-器官层-organs) ✅
- [6. 工具层 `tools/`](#6-工具层-tools) ⏳待续
- [7. 安全 + 持久化 `safety/` + `persistence/`](#7-安全--持久化) ⏳待续
- [8. 核心引擎 `core/`](#8-核心引擎-core-最重要) ✅
- [9. 入口 + Web `lifecycle/` + `web/` + 顶层脚本](#9-入口--web)
- [A. 全局问题清单（按优先级）](#a-全局问题清单)
- [B. 新会话上手指南](#b-新会话上手指南)

---

## 0. 项目概览与心智模型

### 一句话定位
GenesisX 是一个**数字生命系统**：不是套壳 LLM，而是用工程手段复现"生命"的决策机制——价值驱动、情绪闭环、记忆巩固、器官分化、自我进化。LLM 在其中扮演"判断器官"而非"全能大脑"。

### 每个 Tick 发生了什么（17 阶段，论文 Algorithm 1）
```
body_update → observe → compute_middle_vars → compute_effective_states
→ retrieve → axiology → goal_compile → model_config_check
→ plan_propose → plan_evaluate → execute → reward_affect_update
→ memory_write → value_learn → soul_learn → consolidate_trigger → persist
```
**核心循环逻辑**：观察环境 → 检索记忆 → 算价值缺口和权重 → 编译目标 → 规划 → 器官执行 → 算奖励和RPE → 写记忆 → 学习价值/人格 → 巩固 → 持久化。

### 模块依赖层次（下层不依赖上层）
```
Layer 0 (基础):    common/ models/           ← 数据契约、配置、工具
Layer 1 (理论):    axiology/ affect/         ← 价值与情绪（论文核心）
Layer 2 (状态):    metabolism/ perception/   ← 身体状态与环境感知
Layer 3 (记忆):    memory/                   ← 三层记忆+联想+梦境
Layer 4 (认知):    cognition/                ← 规划/目标/验证
Layer 5 (能力):    organs/ tools/            ← 器官(决策)+工具(执行)
Layer 6 (防护):    safety/ persistence/      ← 约束+回放
Layer 7 (引擎):    core/                     ← life_loop 编排一切
Layer 8 (入口):    lifecycle/ web/ run.py    ← 启动与交互
```

### 关键设计决策（理解代码的前提）
1. **5 维价值**：HOMEOSTASIS/ATTACHMENT/CURIOSITY/COMPETENCE/SAFETY。早期版本曾有 9 维（含 INTEGRITY/CONTRACT/EFFICIENCY/MEANING），后三者被重新定位——INTEGRITY 改为硬约束、CONTRACT 改为权重外部输入、EFFICIENCY 并入 HOMEOSTASIS、MEANING 并入 CURIOSITY。**代码里出现这些词时要注意它的当前角色**。
2. **器官 ≠ 工具**：器官是决策主体（ propose_actions），工具是执行手段。6 个内部器官按优先级+激活条件动态分化。
3. **LLM 是器官的"大脑"**：每个器官可挂独立 LLM 会话（independent 模式），或共享一个会话（shared 模式），或不用 LLM 走规则（disabled）。
4. **配置驱动**：几乎所有参数在 `config/*.yaml`，代码常量在 `common/constants.py`（论文对齐）。

---

## 1. 基础层 `common/` + `models/`

> 14 + 3 文件。全系统的数据契约、配置加载、日志、工具函数。**这是理解其他所有模块的前置**。

### 1.1 `common/models.py` (323行) ⭐核心契约
**职责**：定义全系统传递的 Pydantic 数据模型。所有模块间数据流动都用这里的类型。

| 类 | 用途 | 关键字段/方法 |
|---|---|---|
| `ValueDimension(Enum)` | 5 维价值枚举 | HOMEOSTASIS/ATTACHMENT/CURIOSITY/COMPETENCE/SAFETY |
| `PriorityLevel(Enum)` | 6 级目标优先级 | CRITICAL=6 → OPTIONAL=1；`from_source()` 按目标来源映射 |
| `ActionType(Enum)` | 动作类型 | CHAT/USE_TOOL/LEARN_SKILL/SLEEP/REFLECT/EXPLORE/OPTIMIZE/GROW/THINK |
| `Observation` | 环境观察 O_t | type/payload/tick |
| `Action` | 动作 a_t | type/params/risk_level/capability_req/estimated_cost |
| `Goal` | 目标 g | priority_level(6级)/progress/status/compat(兼容性)/source；`get_effective_priority()`/`is_compatible_with()`/`is_expired()`/`update_progress()` |
| `CostVector` | 资源消耗 | cpu_tokens/io_ops/net_bytes/latency_ms/risk_score/money；`total_cost()` 加权汇总 |
| `Outcome` | 动作执行结果 | ok/status/cost_vector/evidence_refs/major_error |
| `EpisodeRecord` ⭐ | 一个 tick 的完整记录 e_t | observation/action/outcome/reward/delta/delta_per_dim/weights/gaps/utilities；**持久化和回放的基本单元** |
| `CapabilityResult` | 器官/肢体能力执行结果 | success/message/data/cost（统一定义，避免重复） |

**🔍问题 P1-1**：`Goal` 同时有 `priority_level`(新,1-6) 和 `priority`(旧,float 0-1)。注释标 `priority` 为 deprecated，但代码里可能仍有调用方。**优化时检查 `priority` 的所有读取点，统一到 `priority_level`。**

**🔍问题 P1-2**：`Goal.is_expired(current_tick)` 参数 `current_tick` 实际未使用（只比较 datetime），签名误导。

### 1.2 `common/constants.py` (395行) ⭐论文参数中心
**职责**：把论文 Appendix A 的所有超参数集中为常量。11 个 dataclass 分组：Memory/ValueSystem/Affect/Metabolism/ToolCost/Learning/Consolidation/Scheduler/SafeMode/Cognition/Tool。

全局单例：`MEMORY`, `VALUE_SYSTEM`, `AFFECT`, `METABOLISM`, `TOOL_COST`, `LEARNING`, `CONSOLIDATION`, `SCHEDULER`, `SAFE_MODE`, `COGNITION`, `TOOL`。

**🔍问题 P1-3（重要）**：**常量与 YAML 配置存在双重来源**。例如 `ValueSystemConstants.WEIGHT_TEMPERATURE=2.0`，但 `value_setpoints.yaml` 里 `tau=4.0`，`axiology/parameters.py` 里 `CoreHyperparameters.tau=4.0`。**三处 τ 值不一致**（2.0 vs 4.0）。实际生效的是哪个取决于各模块读哪个——这是优化时的高危区，需统一。同理 Affect 参数在 constants(0.25/0.30) 和 default_genome.yaml(0.25/0.30) 和 parameters.py 三处。

### 1.3 `common/config.py` (458行) ⭐配置加载主入口
**职责**：`load_config()` 是全系统配置加载的入口，被 run.py/web app.py 调用。

**关键流程**（`load_config()`）：
1. `_load_env_from_project_root()` 向上找 5 层目录的 `.env`（兼容从 web/ 子目录启动）
2. 加载 5 个 YAML：runtime/genome/value_setpoints/tool_manifest/organ_llm
3. 用 Pydantic 模型校验：`RuntimeConfig`/`ValueSetpointsConfig`/`OrganLLMConfig`
4. 从环境变量读 LLM 配置（LLM_API_KEY/BASE/MODEL），兼容旧 DASHSCOPE_API_KEY（带 deprecation 警告）
5. 返回 dict，key: runtime/genome/value_setpoints/tool_manifest/organ_llm/llm/session_id

**关键 Pydantic 配置类**：
- `Config(BaseSettings)`：读 .env 的 LLM 配置
- `RuntimeConfig`：`extra="allow"`（修复 H17，允许 runtime.yaml 额外字段不报错）
- `OrganLLMConfig`：器官 LLM 三模式配置，`get_organ_config(name)`/`get_shared_config()` 返回合并后的配置

**🔍问题 P1-4**：存在**两套配置加载体系**——`config.py:load_config()`(返回 dict) 和 `config_manager.py:ConfigManager`(返回 GenesisXConfig 对象)。两者并行存在，`config_manager` 更完整（含热重载、环境检测、多源合并）但似乎未被主流程采用。**优化时确认哪个是 active 的，废弃另一个。**

### 1.4 `common/config_manager.py` (509行)
**职责**：更完整的配置管理器（环境检测 dev/staging/prod、多源合并 env>yaml>json、热重载、密钥校验、导出）。

`GenesisXConfig` 聚合了 Database/API/LLM/Memory/Axiology/Personality/Affect/Runtime/Security 9 个子配置。`ConfigManager` 单例 via `get_config_manager()`。

**🔍问题 P1-5**：与 `config.py` 功能重叠（见 P1-4）。`load_config()` 这里返回类型与 `config.py` 的同名函数不同，**极易混淆**。

### 1.5 `common/logger.py` (356行)
**职责**：结构化日志，`get_logger(name)` 工厂。全系统统一用 `from common.logger import get_logger`。支持 structlog（若安装）+ 标准 logging 回退。

### 1.6 `common/jsonl.py` (102行)
**职责**：`JSONLWriter` 类，追加写 JSONL 文件。**持久化系统的基石**——episodes/states/tool_calls 都用它写。注意：自定义 datetime/Enum/Pydantic 序列化。

### 1.7 `common/hashing.py` (91行)
**职责**：`hash_content()`/`hash_dict()`/`hash_any()`(SHA256)/`redact_sensitive()`(脱敏)。用于记忆去重、日志脱敏。

### 1.8 `common/utils.py` (289行)
**职责**：通用工具——`safe_execute()`(异常捕获执行)、`ensure_directory_exists()`、`validate_secrets()`、`serialize_labels()`、`retry_on_failure()`、`format_timedelta()`。

### 1.9 `common/error_handler.py` (403行)
**职责**：错误处理基础设施。`CircuitBreaker`(熔断器，防止级联失败)、`RetryPolicy`(指数退避)、`ErrorHandler`(错误分类+回调)。全局 `get_error_handler()` 单例。

**🔍问题 P1-6**：`error_handler` 和 `utils.retry_on_failure` 功能重叠，两处都有重试逻辑。

### 1.10 `common/metrics.py` (501行)
**职责**：Prometheus 指标暴露。Counter/Histogram/Gauge 封装。用于生产监控。

### 1.11 `common/health_check.py` (469行)
**职责**：健康检查系统。`HealthCheckSystem` 单例，注册 liveness/readiness 检查。内置 Database/LLMAPI/DiskSpace/Memory 四类检查。

### 1.12 `common/auth.py` (699行) ⚠️
**职责**：认证授权——`PasswordHasher`(bcrypt)、`JWTManager`(access/refresh token)、`AuthService`(注册/登录/登出/密码重置)、装饰器 `require_auth`/`require_role`。

**🔍问题 P1-7（重要）**：这是**生产级 Web 应用的认证模块**，但 GenesisX 当前是单用户桌面/本地系统。699 行的 auth 代码（含密码重置、角色、token 黑名单）**疑似过度工程或来自模板**。优化迭代时确认是否真的需要，还是可大幅精简。

### 1.13 `common/database.py` (12行)
**职责**：**几乎空文件**，仅声明。SQLAlchemy 在 requirements 但实际未深度使用。

**🔍问题 P1-8**：database.py 形同虚设。若不用关系数据库（项目主要用 JSONL 持久化），考虑移除 SQLAlchemy/alembic/psycopg2 依赖以瘦身。

### 1.14 `models/` (3文件)
- `user.py`(437行)：SQLAlchemy 用户模型（配合 auth.py）。**🔍问题**：与 common/auth.py 同属疑似过度工程的生产 Web 模块。
- `session_models.py`(349行)：会话/对话的数据库模型。
- `__init__.py`(85行)：模型基类。

**🔍问题 P1-9**：整个 `models/` + `auth.py`(~1200行) 是为多用户 Web 服务准备的，但 GenesisX 核心是单实例数字生命。这是**最大的"可精简区"**——若研究方向不涉及多用户，这 1200 行可整体移除。

---

## 2. 核心理论层 `axiology/` + `affect/`

> 论文《Genesis X: Axiology Engine for Digital Life》的核心实现。价值系统驱动一切行为，情绪系统形成闭环反馈。**这是项目的灵魂，也是最容易出 bug 的地方（大量数值计算）。**

### 2.1 价值计算流水线（一个 tick 内的完整数据流）
```
state(能量/压力/bond/novelty/...)
  ↓ feature_extractors.extract_all_features()
features f^(i) (每维一个标量特征)
  ↓ gaps.compute_gaps() : gap = setpoint - feature
gaps d_i (价值缺口)
  ↓ weights.compute_weights() : w = softmax(τ · d̃), d̃ = d · g(θ)
weights w_i (动态权重,和=1)
  ↓ utilities_unified.compute_all_utilities() : u^(i) = f(feature, setpoint)
utilities u^(i) (每维效用,归一化到[-1,1])
  ↓ reward.compute_reward() : r = Σ w_i · u_i
reward r_t (标量奖励)
  ↓ affect: compute_rpe() : δ = r + γV(s') - V(s)
RPE δ_t → 更新 Mood/Stress → 调制下一 tick 行为
```

### 2.2 `axiology/` (23文件) — 5维价值系统

#### `axiology/__init__.py` (399行) ⚠️
**职责**：模块导出口。**但含 210 行的向后兼容 `UtilityCalculator` fallback**（当 `utility.py` 不存在时动态定义）。
**🔍问题 P2-1（重要）**：`__init__.py` 不应包含如此大的兼容类定义。且 fallback 的 `UtilityCalculator.compute_all_utilities()` 调用了 `self.compute_safety`。**优化时确认无外部依赖后删除整个 fallback 块。**

#### `axiology/weights.py` (544行) ⭐权重计算核心
**论文公式实现**：`w_i = softmax(τ · d_i · g_i(θ))`
- `compute_weights(gaps, biases, temperature, idle_bias, idle_epsilon)`：纯函数版，log-sum-exp 数值稳定
- `WeightUpdater` 类：状态化版本，含 5 步流程（偏置→softmax→优先级覆盖→惯性→契约增强）
- `PriorityOverrideConfig`：论文 3.6.4 关键维度覆盖与滞回（homeostasis/safety 缺口超 θ_hi=0.8 时强制最小权重，低于 θ_lo=0.4 释放，含 1 小时超时）
- `_apply_contract_boost()`：CONTRACT 维度补偿（方案B），活跃任务时提升 competence/homeostasis 权重

**🔍问题 P2-2**：`compute_weights()`(纯函数) 和 `WeightUpdater.update_weights()`(类方法) **逻辑重复**。前者是后者的子集。应统一为类方法，纯函数设为 deprecated。

#### `axiology/feature_extractors.py` (473行)
**职责**：从 state 提取每维特征 `f^(i)`。`extract_all_features()` 是入口。
- homeostasis: 能量/压力/疲劳综合
- attachment: bond/trust + `compute_neglect_penalty()`（忽视惩罚，半衰期24h）
- curiosity: novelty（含 `_compute_semantic_novelty()`）
- competence: success_rate/quality/skill_coverage
- safety: `compute_risk_score()`

#### `axiology/utilities_unified.py` (741行) ⭐效用计算核心
**职责**：效用函数"唯一真相源"（注释明确取代了 utility.py/utility_normalized.py/utilities.py）。所有效用归一化到 [-1,1]。
- 5 维核心 + 4 个废弃维度（integrity/contract/meaning/efficiency 保留向后兼容）
- `clip_utility()`/`tanh_normalize()`/`normalize_utility()`

#### `axiology/gaps.py` (116行)
`compute_gaps(state)` = setpoint - feature。`GapCalculator` 从 YAML 读 setpoint。

#### `axiology/reward.py` (95行)
`compute_reward(gaps, weights)` = `Σ w_i · u_i`（**参数名 gaps 误导，实际用 utilities**）。

#### `axiology/axiology_config.py` (281行)
`AxiologyConfig` 单例，从 `value_setpoints.yaml` 加载。`get_axiology_config()` 全局访问。

#### `axiology/parameters.py` (501行)
论文 Appendix A 所有超参数的 dataclass 定义。`get_default_parameters()` 返回聚合体。

#### `axiology/personality.py` (626行)
大五人格(OCEAN) → 中间变量(ET/CT/ES) → 权重偏置 g_i(θ)。`Personality.from_yaml()`。

#### `axiology/value_dimensions.py` (799行) 🔍重复
**🔍问题 P2-3（重要）**：与 `feature_extractors.py` + `utilities_unified.py` **严重功能重叠**——都定义了 `extract_homeostasis_feature`/`compute_homeostasis_utility` 等。life_loop 实际调用的是 feature_extractors + utilities_unified。**优化时废弃 value_dimensions.py。**

#### `axiology/compensation.py` (920行) — 删除维度补偿（方案B）
4 个删除维度以新形式保留：`IntegrityConstraintChecker`(硬约束)/`ContractSignalBooster`(权重提升)/`EfficiencyMonitor`(并入homeostasis)/`MeaningTracker`(并入curiosity)。`CompensationManager` 统一管理。

#### `axiology/setpoints.py` (341行) + `dynamic_setpoints.py` (512行) 🔍重复
setpoint 管理散落 3 处（加 axiology_config.py）。
**🔍问题 P2-4**：需统一 setpoint 管理。

#### `axiology/value_learning.py`
`ValueLearner` 价值学习（显式/隐式/内部反馈）。

#### `axiology/drives/` (6文件) — 5维驱动力 ⚠️禁用
**🔍问题 P2-5**：`life_loop.py` 顶部注释显示这 5 个 Drive **被注释禁用**（"暂时禁用新模块（需要调试）"）。驱动力系统虽实现但未接入主循环。**优化时要么调试启用，要么移除死代码。**

### 2.3 `affect/` (6文件) — 情绪闭环

#### `affect/rpe.py` (179行) ⭐RPE计算（论文 3.7.2）
- `compute_rpe(reward, V, V', γ)`：标量 `δ = r + γV(s') - V(s)`，clip [-2,2]
- `compute_per_dimension_rpe()`：维度级 `δ^(i) = u^(i) + γV^(i)(s') - V^(i)(s)`
- `compute_weighted_rpe()`：全局 `δ = Σ w_i · δ^(i)`
- `RPEComputer`：维护每维 V^(i)（EMA α_V=0.05），TD target 更新

#### `affect/value_function.py` (55行) ⭐标量价值函数
`ValueFunction`：标量 V(s) 的 TD 学习。

#### `affect/mood.py` (419行) ⭐Mood更新
`update_mood(mood, delta, k_plus, k_minus)`：`Mood += k_+·max(δ,0) - k_-·max(-δ,0)`，clip [0,1]。支持维度级系数（`AffectConfig`）。

#### `affect/stress_affect.py`
`update_stress()`：`Stress += s·max(-δ,0) - s'·max(δ,0)`，含失败处理和衰减。

#### `affect/modulation.py` (270行) ⭐行为调制
`AffectModulation`：情绪→行为调制。高 mood 增加探索率、加深规划；高 stress 降低风险容忍。

### 2.x axiology/affect 速查
**调试点优先级**：weights.py(权重不收敛) > rpe.py(RPE爆炸) > utilities_unified.py(效用越界) > modulation.py(行为怪异)
**参数一致性**：τ（2.0/4.0 冲突）、k_+/k_-（三处定义）必须统一，见 P1-3。

---

## 3. 记忆层 `memory/`

> 29 文件/8733 行——项目第三大模块。论文 §3.4（CLS 三层记忆）+ §3.4.3（熟悉度/联想）+ §3.4.4（人格调制编码）+ §3.10.4（梦-反思-洞察巩固）的落地。承担"经验→知识→技能"的压缩与"联想/遗忘/做梦"。
>
> **目录结构**：
> ```
> memory/
> ├── episodic.py        (523)  ⭐ CLS第1层：情节记忆，append-only，JSONL持久化
> ├── schema.py          (332)  ⭐ CLS第2层：图式记忆，信念+证据+置信度
> ├── skill.py           (349)  ⭐ CLS第3层：技能记忆，可执行宏动作
> ├── retrieval.py       (453)  ⭐ 混合检索(语义/关键词/近因/显著性/联想)
> ├── smart_retrieval.py (276)     规则/AI驱动的"要不要检索"决策
> ├── consolidation.py   (745)  ⭐ 梦-反思-洞察巩固(实际接入)
> ├── dream.py           (671)  🔍 DreamDirector(与consolidation重复，孤立)
> ├── familiarity.py     (890)  ⭐ 联想网络(共现/因果/情绪/语义/时间)+普鲁斯特效应
> ├── semantic_novelty.py(750)     嵌入后端(sentence-transformers/API/本地/TF-IDF)
> ├── salience.py        (82)      论文§3.10.4显著性公式
> ├── personality_encoding.py(624) 🔍 论文§3.4.4人格调制编码(孤立)
> ├── organ_guide_manager.py(382)  器官使用指南(JSON存储)
> ├── gates.py           (187)  🔍 海马门控(孤立,仅测试)
> ├── pruning.py         (363)  🔍 容量管理+巩固(孤立,仅测试+archivist)
> ├── indices.py         (274)  🔍 多索引检索(孤立,仅测试+archivist/snapshot)
> ├── utils.py           (62)      get_episode_attr/cosine_similarity
> ├── __init__.py        (186)
> ├── skills/            (7文件)   外部工具技能(文件/网页/PDF/分析)
> └── limb_guides/       (5文件)  🔍 肢体指南(与skills逐字节重复+导入即崩)
> ```
>
> **接入真相**（精读+全项目grep确认）：life_loop 实际只用了 `EpisodicMemory`/`SchemaMemory`/`SkillMemory`/`MemoryRetrieval`/`DreamConsolidator`/`smart_retrieval` 这 6 个。`dream.py`(DreamDirector)、`personality_encoding.py`、`gates.py`、`pruning.py`、`indices.py` **运行时孤立**（仅 tests/test_memory.py 引用）。详见 3.x 速查与 P3-5。

### 3.1 CLS 三层记忆数据流（论文 §3.4）

```
EpisodeRecord(e_t)  ──append──►  EpisodicMemory [N_ep=50000]  episodes.jsonl (持久)
   (life_loop PHASE 12)                                    │
                                                           │ 梦境巩固 (PHASE 15, 周期触发)
                                                           ▼
                          高显著性 episodes  ──压缩──►  SchemaMemory [N_sch=1000]  schemas.jsonl (⚠未持久)
                                                           │      "Goal X 通常产生 ~reward"
                                                           ▼
                          成功动作序列    ──提取──►  SkillMemory  [N_sk=300]   skills.jsonl (⚠未持久)
                                                               "可复用宏动作"
检索方向(PHASE 3):  user_message ──smart_retrieval决策──► retrieve_episodes/schemas/skills ──► 构建context
```

### 3.2 `episodic.py` (523行) ⭐ CLS 第1层 — 情节记忆
**职责**：`EpisodicMemory`——append-only 的情节存储，backed by `episodes.jsonl`。论文 §3.4 的 M_t。

**数据结构**（内存索引三件套）：
- `_cache: deque` —— 有序 episode 序列（按 tick 单调，因为 tick 递增）
- `_by_tick: Dict[int, EpisodeRecord]` —— tick→episode，O(1) 查找
- `_sorted_ticks: List[int]` —— 排序 tick 列表，`bisect` 二分查找做时间范围查询

**写入** `append(episode)`：① 入 deque + 字典 + `bisect.insort` 维持有序 ② 加联想记忆 ③ **立即持久化**（修复 H22，每条 append 都 `open(ab)` 写盘）④ 超 `max_cache_size`(默认50000) 淘汰队首。

**查询**：`query_recent(n)`（逆序取 n）、`query_by_time_range`（二分定位 `[left,right)`）、`query_by_goal`/`query_by_tags`（线性扫描）、`query_high_salience`（按 |delta|）。

**磁盘管理**：`prune_disk_by_salience(threshold, keep_recent_ratio, backup)`（保留高|delta|+最近 N%，备份后重写）、`archive_old_episodes`（旧 tick 归档到独立文件）。两者都会**清空缓存重载**。

**🔍问题 P3-1（重要，性能）— 每 tick 一次文件 `open/append/close`**：`_persist_episode` 每次 append 都 `open(episodes_path,'ab')` 写一行再关。高频写（每 tick 一条 episode）下，文件反复打开关闭，IO 开销显著。对比 `common/jsonl.JSONLWriter` 是流式（open 一次写多次）。episodic 绕过了 life_loop 已有的 JSONLWriter 自己重写了一套持久化（见 P3-2）。优化应复用常驻的 JSONLWriter。
**🔍问题 P3-2（重要，重复实现）— 持久化逻辑绕开 JSONLWriter 重写**：episodic.py、schema.py、skill.py 各自用 `orjson`/`json` 手写 JSONL 读写，而 common/jsonl.py 已有统一 `JSONLWriter`+`read_jsonl`（含自定义 datetime/Enum/Pydantic 序列化）。三套写法并存，序列化行为可能不一致（如 episodic 用 `default=str` 兜底，schema/skill 用 model_dump）。
**🔍问题 P3-3**：`_persist_episode` 用 `print` 调试输出（L118/132/138）而非 logger——每条 episode 都打印，污染日志。
**🔍问题**：`query_by_goal` 用 `ep.current_goal`，但 `query_by_tags` 用 `getattr(ep,'tags',[])`（防御式）——对 EpisodeRecord 是否有 `tags` 字段的不一致假设；缓存淘汰只清 `_cache/_by_tick/_sorted_ticks`，不清联想网络（联想节点引用已淘汰的 tick 会成为悬空引用）。

### 3.3 `schema.py` (332行) ⭐ CLS 第2层 — 图式记忆
**职责**：`SchemaMemory`——压缩知识（信念/规则），带证据与置信度。论文 §3.4 的 K_t。"冲突时降置信度而非删除"。

**`SchemaEntry`**（Pydantic）：`claim`（信念陈述）/`scope`/`confidence∈[0,1]`/`evidence_refs:List[int]`（支持它的 episode tick）/`supporting_count`+`conflicting_count`/`risk_level`/`tags`/`schema_id`（claim+scope 哈希前16位）。

**容量上限** `MAX_CAPACITY=1000`（论文 Appendix A.7 的 N_sch）。超限时 `_evict_lowest_confidence`（线性扫描找最低 confidence 淘汰 + 重建索引）。

**去重/合并**：`add` 先算 schema_id；若已存在则 `_merge_schema`（合并 evidence_refs **截断到50**防无限增长、supporting/conflicting 累加、confidence = supporting/(supporting+conflicting) 重算）。`mark_conflict` 重复同一逻辑。
**🔍问题 P3-4**：schema_id 用 `hash_dict({"claim","scope"})[:16]`——语义相同但文字微差（"Goal A 通常产生0.5奖励" vs "目标A通常产生~0.50奖励"）会产生不同 id，**不被识别为重复**，缓慢撑爆容量。consolidation 生成的 claim 是模板字符串（`f"Goal '{goal}' typically yields reward ~{avg_reward:.2f}"`），avg_reward 微变即产生新 schema。

### 3.4 `skill.py` (349行) ⭐ CLS 第3层 — 技能记忆
**职责**：`SkillMemory`——可执行宏动作（论文 §3.10.3）。`SkillEntry` 含 `action_sequence: List[Action]`/`estimated_cost: CostVector`/`risk_level`/`capabilities`/性能跟踪(`invocation_count`/`success_count`/`average_reward` EMA α=0.2)。

**容量** `MAX_CAPACITY=300`（论文 N_sk）。`_evict_lowest_performing` 淘汰最低 `success_rate()` 的。`record_invocation` 记录每次调用的成功/奖励。`prune_low_performing` 批量清理。

**🔍问题 P3-5（🔴 重要，正确性）— Schema/Skill 永不持久化**：life_loop:190-191 用 `SchemaMemory()`/`SkillMemory()` **无参构造**（未传 persist_path），且 `shutdown()`（core/life_loop.py:1742）**从不调用 `save_to_disk()`**。结果：**巩固产生的 schema/skill 只活在内存，进程结束即全部丢失**。Episodic 有 episodes.jsonl 跨重启累积（session_id=genesisx_persistent），但 CLS 的第 2、3 层记忆**每轮会话从零开始**——直接破坏了论文"经验压缩为长期知识"的核心目标。这是 memory 层最严重的问题。修复：传 persist_path + shutdown 时 save_to_disk + 启动时 load_from_disk（schema/skill 的 load_from_disk/save_to_disk 已实现，只是没被接上）。

### 3.5 `retrieval.py` (453行) ⭐ 混合检索
**职责**：`MemoryRetrieval`——给 PHASE 3 提供 `retrieve_episodes/schemas/skills`。混合打分：`recency + salience + keyword + semantic + associative`。

**`SemanticEmbeddingProvider`**：三后端 `simple`(默认)/`sentence_transformers`/`openai`。**🔍问题 P3-6（重要）— "simple" 后端是 MD5 伪嵌入，毫无语义**：`_simple_embed` 把文本 MD5 后**循环取 16 字节填 384 维**——同一文本恒等向量，相似文本向量无相关性。默认 backend="simple" 时，`semantic_weight` 即使>0 算出的相似度也是噪声。真正的语义检索在 `semantic_novelty.py` 有 sentence-transformers 支持，但 retrieval 走的是这套伪嵌入。两套嵌入实现并存且质量悬殊（见 P3-7）。
**🔍问题 P3-7（重要，重复）— 嵌入实现散落 3 处**：① `retrieval.SemanticEmbeddingProvider._simple_embed`(MD5) ② `familiarity.AssociativeMemory._get_embedding`(默认 md5 seed 的 np.random，或可注入函数) ③ `semantic_novelty.SemanticNoveltyCalculator`(真正的 TF-IDF/sentence-transformers/API)。三处对"嵌入"的实现完全不同，且前两处都是伪嵌入。应统一到 `semantic_novelty` 的 `SemanticNoveltyCalculator`。

**`retrieve_episodes`** 流程：① 候选=`query_by_tags`(limit×2)，无候选回退 `query_recent` ② 联想检索（调 episodic.retrieve_by_association，但 mood/stress 取值代码写死 `current_mood=None`——**🔍问题：FieldStore 导入了但从未读，普鲁斯特效应的情绪门控实际失效**）③ 语义分数（按需）④ 逐条 `_score_episode` 加权归一 ⑤ 排序取 top。
**🔍问题 P3-8**：`retrieve_by_semantic_similarity` 与 `retrieve_episodes(semantic_weight>0)` 功能高度重叠，两个语义检索入口。
**🔍问题**：`recency_score = max(0, 1 - age/1000)`（1000 tick 半衰，魔法数）；权重归一时若全 0 兜底为 1.0（不报错）。

### 3.6 `smart_retrieval.py` (276行) — 检索需求决策
**职责**：`analyze_retrieval_need(message)` 用规则决定检索强度：`NONE`（简单问候，正则匹配）/`BASIC`（短消息/基础关键词）/`SEMANTIC`（回忆/个人信息/复杂问题）。另有 `ai_decide_retrieval`（LLM 决策，异步）。

life_loop PHASE 3 实际调用 `analyze_retrieval_need`（规则版），按 `get_retrieval_config(decision)` 调整检索权重。
**🔍问题 P3-9**：`ai_decide_retrieval` 永不被调用（全项目 grep 仅自身定义）——LLM 决策是死代码，永远走规则。规则关键词表硬编码中文，英文消息基本都落到"默认按词数/问号数"分支。
**🔍问题**：`SEMANTIC_KEYWORDS` 与 `BASIC_KEYWORDS` 有重叠（`'如何'/'什么'` 同时出现在两表），按代码顺序 SEMANTIC 先判，故 BASIC 的这两个词永远不生效。

### 3.7 `consolidation.py` (745行) ⭐ 梦-反思-洞察巩固（实际接入）
**职责**：`DreamConsolidator`——PHASE 15 周期触发（life_loop:1538 当 `episodic.count()>=20` 时）。论文 §3.10.4。流程：
```
should_consolidate(cooldown/attempts/quality降级检查)
 → _sample_episodes(显著性阈值, top20)
 → _extract_schemas(按goal分组, ≥2条且avg_reward>0.3 → 评估Q^insight → 过质量阈值 → P1-8证据验证 → add)
 → _extract_skills(按action_type分组, ≥3条且avg_reward>0.6 → add)
 → _prune_episodes(budget>1000时, 保留最近100+高|delta|)
 → record_success/failure(更新防死循环状态)
```

**`InsightQualityEvaluator`**：论文 Q^insight = `0.4·压缩性 + 0.3·可迁移性 + 0.3·新颖性`。压缩性=`log(n+1)/log(10)`；可迁移性=avg_reward；新颖性=语义嵌入 `1-max cos(emb)`（无 semantic_calculator 时退化为词汇 Jaccard 重叠）。

**`EvidenceConfig`**（论文§3.10.4 强证据）：高影响(safety/attachment 标签 或 Q≥0.8)的洞察需 ≥1 tool_call 或 ≥N 用户确认。`_check_evidence_requirement` 检查 action.type 非 CHAT/SLEEP/REFLECT 算 tool 证据，并探测 `user_confirmed`/`user_rating`/`feedback`/`outcome.ok` 多字段推用户确认。

**防死循环**（论文§3.10.4）：`cooldown_ticks=30`/`max_attempts=3`/连续2次失败降 quality_threshold（最低0.3）。成功重置。

**🔍问题 P3-10（重要，"证据"几乎永远满足）**：默认 `min_tool_calls=1, min_user_confirmations=0`。`_check_evidence_requirement` 的逻辑：当 `min_user_confirmations==0` 时，只要 `tool_call_count>=1` 即 `has_evidence=True`（L401-404）。而 tool 证据的判定极宽（任何非 CHAT/SLEEP/REFLECT 的 action）——USE_TOOL/EXPLORE/LEARN_SKILL 都算。结果：**只要 supporting episodes 里有一条非聊天动作，洞察就通过证据门**。证据验证形同虚设。另外它检查的 `ep.user_confirmed`/`ep.user_rating`/`ep.feedback` 字段在 EpisodeRecord 模型里**不存在**（见 common/models.py），那些分支恒不命中。
**🔍问题 P3-11**：`_extract_skills` 用 `representative_ep.action` 单条作为 `action_sequence`——"宏动作/技能"其实是单动作的快照，没有真正提取"序列"。且 skill 名恒为 `skill_{action_type.lower()}`，同类型反复巩固会因 SkillMemory.add 按 name 去重而**只保留第一条**。
**🔍问题 P3-12**：`_prune_episodes` 调 `prune_disk_by_salience(salience_threshold=0.3)`——但 `_sample_episodes` 已按 salience≥阈值 取样，prune 又用固定 0.3，两处阈值语义不同（一个 Q^insight 门、一个 |delta| 门），易混淆。

### 3.8 `dream.py` (671行) 🔍 孤立 — 与 consolidation 重复
**职责**：`DreamEngine`+`DreamDirector`——梦-反思-洞察的**另一套实现**。`DreamDirector.start_dream_cycle` 同样做 抽样→轨迹→洞察→质量评估→沉淀→剪枝，逻辑与 `consolidation.DreamConsolidator` 高度重叠。

**🔍问题 P3-13（重要）— 整个 dream.py 运行时孤立**：全项目 grep，`DreamDirector`/`DreamEngine`/`create_dream_director` **零外部引用**（仅 dream.py 自身 + memory/__init__ 重导出）。life_loop 用的是 `consolidation.DreamConsolidator`，不是 `dream.DreamDirector`。这 671 行是"梦境"概念的**第二份实现却从未接入**。其差异点（DreamEpisode/DreamReport 数据类、联想重组 `_generate_associative_traces`、DreamPhase 状态机）是有价值的设计，但要么接入要么删除。

**🔍问题 P3-14**：`dream.py:529` 调 `compute_novelty(insight=..., existing=..., threshold=0.85)` 用**关键字参数**，而 `semantic_novelty.compute_novelty` 签名是 `(insight, existing, threshold, config=None)`——参数名碰巧对得上能跑；但 `SemanticNoveltyCalculator.compute_novelty`（方法）签名是 `(insight_text, existing_texts, threshold)`——**参数名不同**。consolidation.py:195 用方法版传位置参数。两种调用风格 + 两套参数名，维护易错。
**🔍问题**：`_check_novelty` 降级路径做 `insight.get("claim","") == schema.claim` 精确字符串相等——几乎恒为 novel。

### 3.9 `familiarity.py` (890行) ⭐ 联想网络（最大文件）
**职责**：论文 §3.4.3 熟悉度信号 + 双阶段检索 + §3.10.4 梦境联想重组。三大组件：

**`AssociationEdge`/`AssociativeNode`/`AssociativeNetwork`**：有向带权图 G=(V,E)。节点=记忆（含 embedding/mood/stress/salience），边=联想。
- **5 种联想**（权重公式 `w = Σβ_i·w_i`，默认 β=[0.25共现, 0.30因果, 0.20情绪, 0.15语义, 0.10时间]）：
  - 共现（同 episode，`register_episode` 两两建边 boost 0.3）
  - 因果（`register_causal_link` action→result）
  - 情绪（`1 - 0.6·|Δmood| - 0.4·|Δstress|`，普鲁斯特效应）
  - 语义（嵌入余弦，映射[-1,1]→[0,1]）
  - 时间（1h内=1.0，之后指数衰减，>24h=0）
- **`propagate_activation`**（梦境用）：种子激活=1.0，沿边传播 `score·weight·0.7`，最多 3 步，阈值 0.3。
- **`find_associative_path`**：BFS 找两节点最短联想路径（梦境轨迹用）。
- **`get_proust_effect_memories`**：按当前 mood/stress 找相似情绪记忆 top10。
- **容量控制**：每节点 `max_associations=10`，超限替换权重最低边；`decay_associations` 全图衰减，低于 `association_threshold=0.2` 删边。

**`AssociativeMemory`**（管理器，被 EpisodicMemory 持有）：`add_episode_memory`（建节点+自动共现链接）、`retrieve_by_association`（语义70%+联想邻居30%+普鲁斯特 boost 0.2）、`generate_dream_assembly`（梦境联想重组，供 dream.py 调）。

**🔍问题 P3-15（🔴 重要）— 联想网络无法持久化**：`export_state` 实现了（序列化节点+边），但 `import_state` 是 **`pass`（空实现，L869-873，注释"完整恢复需要重建节点和边"）**。且 EpisodicMemory 恢复时（`_load_from_disk`）**不重建联想网络**——只在新 append 时增量加节点。结果：**每次重启，整个联想图（共现/因果/情绪链接）丢失，只能从重启后的新 episode 重新积累**。这违背了"跨会话记忆累积"（session_id=genesisx_persistent）的意图。
**🔍问题 P3-16**：默认嵌入 `_get_embedding` 是 `md5(text)→np.random.seed→randn`——**确定性伪随机，无语义**。同一段文本每次进程内相同（因 md5 seed），但不同文本的"相似度"纯随机。联想网络的"语义联想"权重组分是噪声（见 P3-7）。
**🔍问题**：`_compute_temporal_similarity` 用 `created_at`（wall-clock datetime）而非 tick——多 session 间 wall-clock 跳变会让时间联想失真；`add_episode_memory` 的双向共现链接（L668-676）会让边数翻倍且方向语义混乱（图本应有向）。

### 3.10 `semantic_novelty.py` (750行) — 嵌入后端（最完整）
**职责**：`SemanticNoveltyCalculator`——论文 §3.10.4 要求的"语义嵌入新颖度"的**正经实现**（对比 retrieval/familiarity 的伪嵌入）。支持 5 后端：`SENTENCE_TRANSFORMERS`(本地模型,推荐)/`OPENAI`/`DASHSCOPE`/`LOCAL_LLM`(Ollama)/`TFIDF`(回退,无依赖)。`EmbeddingConfig.from_env()` 读 `EMBEDDING_BACKEND` 等环境变量。

**新颖度公式**（论文）：`C_nov = 1 - max_{s∈Schema} cos(emb(insight), emb(s))`。`compute_novelty`/`compute_novelty_batch` 返回 `(score, is_novel)`。带内存缓存(FIFO,max_cache_size)+可选磁盘缓存(`.npy`+索引 json)。

**🔍问题 P3-17**：模块级便利函数 `compute_novelty(insight, existing, ...)`（L727）**每次调用都 `new` 一个 `SemanticNoveltyCalculator`**——缓存全失效，且若 backend=sentence-transformers 会重复加载模型。dream.py 走的就是这个函数。
**🔍问题 P3-18（设计）**：`EmbeddingConfig.auto_detect_backend` 是**实例方法却用 `cls` 参数名**（L253 `def auto_detect_backend(cls)`），且 `EmbeddingConfig.from_env` 不调用它——自动检测形同虚设，默认 `EmbeddingBackend.TFIDF`。当前运行环境(.env 是 stepfun **chat** 模型)无 embedding API 配置，实际走 TF-IDF（字符三元组哈希到 384 维，比 MD5 好但仍是浅嵌入）。
**🔍问题**：`_compute_embedding_local` 解析 Ollama 响应 `result.get("embedding", result.get("embeddings",[])[0])`——若 key 都不在会 `KeyError`/`IndexError`；`compute_embedding` 的 backend 分支用 `.endswith("api")` 字符串判定，CUSTOM_API 匹配但 OPENAI 也被显式列出，逻辑冗余。

### 3.11 `salience.py` (82行) — 显著性公式
**职责**：`compute_salience(episode)` 实现论文 §3.10.4：`Sal = a_δ·|δ| + a_u·(1-Prog) + a_n·Novelty`，默认权重 `a_δ=1.0/a_u=0.5/a_n=0.3`，温度 `κ_sal=3.0` 做 sigmoid 缩放到 [0,1]。

**v15 适配**：用 5 维价值系统做代理——`unmet_score` 用 `episode.gaps["competence"]`（任务未完成代理），`novelty_score` 用 `episode.gaps["curiosity"]`（新颖性代理）。

**🔍问题 P3-19**：被 consolidation.py 导入使用，但**全项目无其他运行时调用方**（grep `compute_salience` 仅 consolidation + tests）——即显著性公式只在"巩固时对全量 episode 重算"，写入 episode 时（PHASE 12）并不计算存储 salience 字段。EpisodicMemory 的 `query_high_salience` 用的是 `|delta|` 不是这个公式——**两套"显著性"定义并存**。
**🔍问题**：`competence`/`curiosity` gap 作为代理是论文公式的近似，proxy 质量存疑（competence gap 高 ≠ 目标未完成）。

### 3.12 `personality_encoding.py` (624行) 🔍 孤立 — 论文§3.4.4
**职责**：论文 §3.4.4"人格调制的记忆编码"完整实现。4 个调制器：
- `PersonalityModulatedTagging`：`tag_intensity = |mood|·(1+stress)·(1+λ_es·ES_t)`
- `CrossDomainAssociationCalculator`：`P_cross = P_base·(1+λ_et·ET_t)`（高探索倾向→更多跨域联想）
- `PersonalityModulatedConsolidation`：`θ = θ_base·(1+λ_ct·CT_t)`（高保守倾向→巩固阈值更高）
- `NoveltySensitivityCalculator`：`sensitivity = base·(1+λ_et·ET_t)`
- `PersonalityModulatedEncoder.encode()` 整合四者；`update_personality_from_experience` 慢速更新 ET/CT。

**🔍问题 P3-20（重要）— 整个文件运行时孤立**：全项目 grep `PersonalityModulatedEncoder`/`create_encoder` **零外部引用**（仅自身 + memory/__init__ 重导出 + 测试）。即论文 §3.4.4 的整套人格调制编码机制**写了但没接进 life_loop 的记忆写入路径**（PHASE 12 episodic.append 不调它）。`PersonalityMiddleVars`(ET/CT/ES) 与 axiology/personality.py 的大五人格→中间变量是**两套并行的人格中间变量定义**（见第2章 P2-x 相关）。
**🔍问题**：`MemoryDomain` 枚举有 `PROCEDURAL`/`SEMANTIC` 但 CLS 实际只有 episodic/schema/skill 三层——域映射未实现。

### 3.13 `gates.py`(187) + `pruning.py`(363) + `indices.py`(274) — 🔍 孤立三件套
> 三者都在 `tests/test_memory.py` 有覆盖，但**运行时基本不接入**（life_loop 不用）。是 CLS 记忆的"第二套基础设施"，与 episodic/schema/skill 的内置方法功能重叠。

**`gates.py` `MemoryGate`**：海马门控——`should_store_episodic`(新颖度/显著性/|δ|/容量惩罚)、`should_consolidate_to_schema`(频次≥3 或 reward>0.8)、`should_extract_skill`(成功率≥0.8)。`get_priority_score` = `0.3·novelty+0.4·reward+0.3·delta`。
- **🔍问题**：life_loop PHASE 12 无条件 `episodic.append`（不调 gate）——**写入门控完全没启用**，所有 episode 都进 episodic。门控阈值默认 `novelty_threshold=0.6` 等魔法数硬编码。

**`pruning.py` `MemoryPruner`**：容量管理（N_ep=50000/N_sch=1000/N_sk=300，与论文 Appendix A.7 对齐——**这是容量常数的另一处定义**，见第1章 P1-3 三重定义问题）。`select_episodes_to_prune`(按 importance=`0.3reward+0.2delta+0.2recency+0.3novelty`)、`consolidate_episodes`(聚类→schema)、`extract_skills`(按 tool_id 成功率)。
- **🔍问题 P3-21**：与 `schema._evict_lowest_confidence`/`skill._evict_lowest_performing`/`episodic.prune_disk_by_salience` 功能重叠——**剪枝逻辑三套**（pruning.py 通用版 + 各记忆类内置版 + consolidation._prune_episodes）。archivist_organ 引用 pruning 但实际容量淘汰走各记忆类内置。

**`indices.py` `MemoryIndex`**：多索引（time/value/tag/embedding）快速检索。`retrieve_by_time/value/tag/similarity`。
- **🔍问题**：与 `EpisodicMemory` 的内置 `_by_tick`/`_sorted_ticks`/`query_by_*` **完全重叠**——EpisodicMemory 自己维护了 tick 索引，MemoryIndex 又做一遍。snapshot.py/eval 引用 indices 但主检索路径走 retrieval.py。**双重索引基础设施**。

### 3.14 `organ_guide_manager.py` (382行) — 器官使用指南
**职责**：`OrganGuideManager`——为器官/肢体/插件生成并存储"使用指南"（JSON，存 `memory/limb_guides/data/organ_guides.json`）。`OrganGuide.to_llm_prompt()` 把指南格式化给 LLM（"我有什么器官，怎么用"）。被 `core/growth/growth_manager.py` 调用（生成新肢体时注册指南）。

**🔍问题**：与 `core/capability_*`（能力管理三件套，见第8章 P8-19）概念重叠——"器官能力描述"散落 organ_guide_manager / capability_manager / plugins/growth 多处。`_generate_usage_examples` 关键词表硬编码（get/fetch/post/read/write...）。

### 3.15 `skills/`(7文件) + `limb_guides/`(5文件) — 🔍 严重重复
> 两包名义上分工：`skills/`=外部工具技能（网上下载，调第三方API）；`limb_guides/`=肢体指南（自己生成，调自己的器官）。**但实际是逐字节复制的死代码**。

**`skills/`**（活的）：`base.py`(BaseSkill/SkillResult/SkillCost/SkillRegistry **非线程安全版**) + `skill_registry.py`(SkillRegistry **线程安全版** + 全局单例) + 4 个具体技能(file/web/pdf/analysis，各自调 `tools.tool_executor.LLMToolExecutor`)。

**🔍问题 P3-22（🔴 重要，死代码 + 导入即崩）**：
1. **`limb_guides/` 4 个指南文件与 `skills/` 4 个技能文件逐字节相同**（已用 md5 校验：file_ops_guide≡file_skill、web_fetcher_guide≡web_skill、pdf_processing_guide≡pdf_skill、data_analysis_guide≡analysis_skill）——连**类名都没改**（指南文件里类名仍是 `FileSkill`/`WebSkill`/`AnalysisSkill`/`PDFSkill`）。
2. **`limb_guides/__init__.py` 导入不存在的名字**：它 `from .file_ops_guide import FileOpsGuide` 等，但文件里定义的是 `FileSkill`——**`import memory.limb_guides` 必抛 ImportError**。
3. 因此 `memory/__init__.py:48` 的 `try: from .limb_guides import ...` **恒走 except**，`_limb_guides_available=False`，警告被收集但运行时静默——**整个 limb_guides 包是死的**。
4. 即便修复导入，4 个"指南"也只是 4 个"技能"的副本，`limb_guides/` 包存在的意义（区别于 skills/）完全没体现。

**🔍问题 P3-23**：`skills/` 内有**两个 `SkillRegistry` 类**——`base.py:SkillRegistry`(172-247, 非线程安全) 和 `skill_registry.py:SkillRegistry`(线程安全+全局单例)。`skills/__init__.py` 导出后者，但前者仍占 76 行死代码。

### 3.x memory/ 速查与调试点

**精读优先级**：`episodic.append`+持久化(数据落盘) > `consolidation.consolidate`(知识压缩链路) > `retrieval.retrieve_episodes`(检索质量) > `familiarity` 联想网络(最大的创新点也是最大死代码风险)。

**接入真相表**（life_loop PHASE 对应）：
| memory 模块 | life_loop 接入 | 状态 |
|---|---|---|
| EpisodicMemory | PHASE 12 `append` + PHASE 3 检索 | ✅ 接入，持久化正常 |
| SchemaMemory | consolidation 写入 | ⚠️ 接入但**不持久化**(P3-5) |
| SkillMemory | consolidation 写入 | ⚠️ 接入但**不持久化**(P3-5) |
| MemoryRetrieval | PHASE 3 | ✅ 接入 |
| DreamConsolidator | PHASE 15 周期触发 | ✅ 接入 |
| smart_retrieval | PHASE 3 决策 | ✅ 接入(规则版) |
| AssociativeMemory | episodic 内部持有 | ⚠️ 写入接入但**不持久化**(P3-15) |
| semantic_novelty | consolidation/dream 调用 | ✅ 接入(默认TF-IDF) |
| dream.py(DreamDirector) | — | 🔴 **完全孤立**(P3-13) |
| personality_encoding | — | 🔴 **完全孤立**(P3-20) |
| gates.py | — | 🔴 **完全孤立**(仅测试) |
| pruning.py | archivist 引用 | 🟡 半孤立(P3-21) |
| indices.py | snapshot/eval 引用 | 🟡 半孤立(P3-21) |
| limb_guides/ | — | 🔴 **导入即崩→静默禁用**(P3-22) |
| organ_guide_manager | growth_manager | ✅ 接入 |

**高危区**：
1. **CLS 第2/3层不持久化**（P3-5）——schema/skill 重启清零，知识无法跨会话累积
2. **联想网络不持久化**（P3-15）——重启丢失全部联想链接
3. **伪嵌入污染检索/联想**（P3-6/P3-7/P3-16）——默认后端无语义，semantic_weight 是噪声
4. **证据门虚设**（P3-10）——巩固的"强证据"要求几乎总满足
5. **大量孤立代码**（P3-13/P3-20/P3-21/P3-22）——dream.py/personality_encoding/gates/limb_guides 共 ~1900 行死/半死代码

**与论文的对应**：CLS 三层 = §3.4；检索 = §3.4（混合）；熟悉度/联想/普鲁斯特 = §3.4.3；人格调制编码 = §3.4.4；显著性 = §3.10.4；梦-反思-洞察 = §3.10.4；容量 N_ep/N_sch/N_sk = Appendix A.7。

---

## 4. 认知/感知/代谢 — 待续

> ⏳ `cognition/`(7文件,规划/目标/验证) + `perception/`(8文件,观察/上下文/新颖性) + `metabolism/`(5文件,昼夜节律/恢复/无聊)。共 20 文件/4672 行。
> **续写提示**：cognition 重点 `planner.py`/`goal_compiler.py`；metabolism 重点 `circadian.py`(昼夜节律)。

---

## 5. 器官层 `organs/`

> 15 文件/7956 行。论文 §3.8（动态器官分化）+ §3.9（价值驱动的器官选择）+ §3.4.2（黑板/共享大脑）的落地。器官是**决策主体**（propose_actions），区别于 tools/ 的"执行手段"（详见第6章）。每 tick PHASE 7：价值权重排序器官 → 器官各自 propose → 汇总成 proposed_actions。
>
> **核心创新**：每个器官可挂独立 LLM 会话（论文 §3.4.2"器官作为判断器官"）。三种模式（independent/shared/disabled）决定器官是"自己思考"还是"共享大脑"还是"走规则"。
>
> **目录结构**：
> ```
> organs/
> ├── organ_llm_session.py (1043) ⭐⭐ 器官LLM会话系统(三模式+选择性记忆,核心)
> ├── unified_organ.py      (581)  ⭐ 新架构: 统一器官(UnifiedOrgan/BuiltinOrgan/Limb/Plugin)
> ├── organ_manager.py      (346)  ⚠️ 旧管理器(实际接入,但依赖被禁用的drives)
> ├── organ_interface.py    (251)  🔍 孤立(仅测试)
> ├── base_organ.py         (212)  BaseOrgan 基类 + MountedOrgan 占位符
> ├── organ_selector.py     (232)  🔍 孤立(仅测试,与 core/differentiate 重复)
> ├── __init__.py           (215)  导出口+废弃别名类+全局单例
> ├── internal/                    6 个内置器官(全部接入)
> │   ├── mind_organ.py     (884)  ⭐ 思维器官: 9策略规划+用户响应
> │   ├── scout_organ.py    (850)  ⭐ 侦察器官: 8模式探索+知识前沿
> │   ├── immune_organ.py   (930)  ⭐ 免疫器官: 9策略安全+5级safety_mode+5信任级
> │   ├── builder_organ.py  (900)  ⭐ 构建器官: 9策略项目管理+里程碑
> │   ├── archivist_organ.py(754)  ⭐ 档案器官: 8策略记忆管理
> │   ├── caretaker_organ.py(588)  ⭐ 照护器官: 稳态维持+昼夜节律
> │   └── __init__.py       (21)
> └── limbs/
>     └── __init__.py       (149)  🔍 Limb 类(Docker肢体,全是TODO占位符)
> ```

### 5.1 三类器官（命名与来源）—— ⚠️ 易混
项目里"器官"一词指代**三组不同的东西**，理解代码前必须分清：

| 概念 | 位置 | 是什么 | 接入状态 |
|---|---|---|---|
| **内置器官 (BuiltinOrgan/Internal Organ)** | `organs/internal/*.py` | 6 个代码写死的"内脏"（mind/scout/immune/builder/archivist/caretaker） | ✅ **真正接入**（life_loop PHASE 7 调 propose_actions） |
| **驱动力器官 (Drive)** | `axiology/drives/*.py`（不在 organs/！） | 5 维驱动力信号生成器（好奇心/胜任力/稳态/依恋/安全） | 🟡 **被禁用**（见 P2-5）；但 `OrganManager`（旧）仍持有它们 |
| **统一器官 (UnifiedOrgan)** | `organs/unified_organ.py` | 新架构抽象：BuiltinOrgan + Limb + Plugin 三源统一 | 🟡 **半接入**（注册了但从不查询执行） |

`organs/__init__.py` 里还有 4 个 `CuriosityOrgan`/`CompetenceOrgan`/`HomeostasisOrgan`/`AttachmentOrgan` **废弃别名类**（继承自 axiology.drives，构造即发 DeprecationWarning）——是驱动力器官的历史命名残留。**看到这些名字要意识到它们是驱动力不是真器官。**

### 5.2 `organ_llm_session.py` (1043行) ⭐⭐ 核心创新——器官LLM会话三模式

**职责**：论文 §3.4.2"器官作为判断器官"。让每个器官拥有独立（或共享）的 LLM 会话，使器官从"规则脚本"升级为"会思考的判断器官"。这是 GenesisX 区别于"LLM 当全能大脑"架构的关键。

**`create_llm_manager(mode, ...)` 工厂**（life_loop:297 `_init_organ_llm_manager` 调用）按 `organ_llm.yaml` 的 `mode` 字段返回三种管理器之一：

| 模式 | 管理器类 | 每器官会话 | 对话历史 | organ_llm.yaml 配置键 | 特点 |
|---|---|---|---|---|---|
| `independent`（默认） | `OrganLLMManager` | ✅ 独立 | 独立 | `organs.<name>.{llm,temperature,...}` | 器官间互不污染；**每器官可单独配 LLM**（如 mind 用 GPT-4，scout 用便宜模型） |
| `shared` | `SharedBrainManager` → `SharedBrainSession` + `OrganProxy` | ❌ 共享一个 | 统一 | `shared.{llm,use_default_llm,...}` | 所有器官共用一个"大脑"，用 `[器官名]` 标记区分；省 token，但器官人格会被共享上下文稀释 |
| `disabled` | `None` | — | — | — | 不用 LLM，器官纯走规则（`_propose_actions_impl`） |

**`OrganLLMSession`**（独立模式的核心，L62-340）：
- `ORGAN_PERSONALITIES`：6 个器官的人格系统提示词（mind=深度思考/scout=探索好奇/...），中文人格描述
- `session_id = f"{organ}_{uuid8}"`（每次进程重启新建，不持久）
- `think(prompt, include_history, temperature)`：带历史上下文调 LLM；**历史截断** `max_history*2`（config 默认 20 轮）
- `respond(prompt)`：无历史快速调用
- `reflect()`：让器官反思自己的思考历史（**life_loop 不调用，孤立方法**）

**`SharedBrainSession` + `OrganProxy`**（共享模式，L426-689）：
- `SharedBrainSession.think(organ_name, prompt)`：在 prompt 前加 `[MIND]`/`[SCOUT]` 标记，喂给单一会话
- `OrganProxy`：包装共享会话，对外伪装成独立会话（同 `think`/`respond`/`get_history` 接口）——**但 `clear_history()` 实际清空整个共享历史**（L681 有 warning）
- `get_organ_history(organ_name)`：从共享历史里按 `[器官名]` 标记过滤出该器官的对话（O(n) 扫描）

**`OrganMemoryWriter`**（选择性记忆，L706-1007）——论文要求"器官思考选择性写入记忆"：
- `evaluate_thought(organ, thought, context)` → `MemoryWorthiness{should_save,importance,category,reason,summary}`
- 两级判断：① `_quick_check_exclude`（关键词"正在/继续/待机/如常/重复"直接跳过，不经 LLM）② `_llm_evaluate`（LLM 判断 insight/decision/learning/observation/routine，返回 JSON）或 `_keyword_evaluate`（LLM 不可用时关键词匹配 fallback）
- `save_if_worthwhile`：构造一个 `Action(type="THINK")` 的 `EpisodeRecord` 写入 episodic（session_id=`organ_<name>`）

**🔍问题 P5-1（重要，真接入但条件脆弱）**：life_loop:1088-1106 `process_organ` 取 `organ.get_last_thought()`，`save_organ_thought` 调 `_save_organ_thought_to_memory`。**但整个 `save_organ_thought`/`_organ_memory_writer` 路径的前提是 `_init_organ_llm_manager` 成功创建了 `_organ_memory_writer`**（L420）。`_save_organ_thought_to_memory` 只在 `_organ_memory_writer` 非 None 时执行——若 organ_llm.yaml `memory.enabled=false` 或初始化任何一步异常（L428 try/except 吞掉），器官思考就静默不入记忆。需确认 writer 在运行时确实非 None。
**🔍问题 P5-2**：`SharedBrainSession._history` 是**所有器官共享的单一列表**，截断到 `max_history*2`。当 6 个器官轮流 think，20 轮历史里其实是 ~3 轮"每器官一次"——独立模式每器官有 20 轮自己的历史，共享模式历史稀释 6 倍。共享模式的设计意图（器官互相感知）与"稀释"是 trade-off，但文档未标注。
**🔍问题 P5-3**：`OrganLLMSession.think` 调 `self.llm_client.chat(...)` 但**不解析 `reasoning_content`**（同 action_executor 的 P8-12 同源问题）。step-3.7-flash 的推理内容被丢弃，器官只看到 `content`。
**🔍问题 P5-4（重要，LLM 失败无降级信号）**：`think()` 失败返回 `""`（空串）。器官的 `_propose_actions_with_llm` 见空串则 `actions=[]` → 走 `if not actions: actions = self._propose_actions_impl(...)` fallback 到规则。**这个 fallback 静默**——没有任何日志/指标区分"这次器官走 LLM"还是"LLM 失败降级走规则"。无法监控器官实际是否在"思考"。
**🔍问题 P5-5**：`OrganMemoryWriter._llm_evaluate` 解析 LLM 返回的 JSON 用 `find("{")...rfind("}")` 提取——若 LLM 输出多个 JSON 块或代码块含 `{}`，会提取错误区间。`summary=result.get("summary","")[:200]` 截断但 thought 存了 `[:500]`（L963），两处截断长度不一致。

### 5.3 `unified_organ.py` (581行) ⭐ 新架构统一器官（注册但不执行）

**职责**：v2.0 重构——把三种能力来源（内脏/肢体/插件）统一为 `UnifiedOrgan` 抽象。

**类型体系**：
- `OrganSource(Enum)`：BUILTIN/LIMB/PLUGIN（+废弃 GROWN/PLUGGED 别名）
- `OrganType(Enum)`：INTERNAL（纯Python）/EXTERNAL（需API/容器）/HYBRID
- `OrganInfo`(dataclass)：name/description/source/type/capabilities/version/created_at + growth 专属（generation_prompt/parent_organ）

**三个具体器官类**（L225-431）：
- `BuiltinOrgan`：内脏基类，source=BUILTIN。**但 `organs/internal/` 的 6 个器官继承的是 `BaseOrgan` 不是 `BuiltinOrgan`**——life_loop:248 用 `isinstance(organ, BuiltinOrgan)` 判断，**全部 False**，走 else 分支用 `WrappedBuiltinOrgan` 动态子类包装（L256-273）。**即 6 个真器官没一个是 BuiltinOrgan 实例，全靠动态包装塞进统一管理器**。
- `Limb`：肢体，source=LIMB。`_create_instance` 用 `exec(self.code, namespace)` **无沙箱**执行 LLM 生成的代码（与第8章 P8-17 同源安全问题）。`execute_capability` 反射调用实例方法。
- `Plugin`：插件，source=PLUGIN/HYBRID。与 Limb 几乎逐字节相同（同样 exec 无沙箱）。

**`UnifiedOrganManager`**（L438-581）：
- `_capability_index: Dict[cap, organ_name]`：能力→器官反查索引
- `add_builtin_organ/add_limb/add_plugin`（+废弃别名 add_grown_organ/add_plugged_organ）
- `propose_all_actions`：遍历所有器官收集 propose_actions（返回 `List[(organ_name, Action)]`）

**🔍问题 P5-6（🔴 重要，统一管理器是只写死代码）**：life_loop 只调 `add_builtin_organ` 注册器官，**从不调 `propose_all_actions`/`execute_capability`/`has_capability`/`list_all_capabilities`/`get_organ_by_capability`**。PHASE 7 的器官提案走的是 `self.organs` 字典（L1086 `organ.propose_actions`），不是 `unified_organ_manager`。即 **UnifiedOrganManager 注册了器官却从不被用来查询或执行——整个新架构是只写脚手架**。growth/plugins 系统"注册为器官"（见第8章 8.8/8.9）写到这个管理器，但 life_loop 不从它读。这是 organs 层最大的架构债：新架构（UnifiedOrganManager）与旧架构（`self.organs` 字典 + `OrganManager`）并行，旧的活、新的死。
**🔍问题 P5-7**：`Limb`/`Plugin` 的 `propose_actions` 恒返回 `[]`（L332/L425）——肢体/插件**不提议动作**，只被动执行能力。但统一管理器的 `propose_all_actions` 会遍历它们，浪费（虽然现在没人调）。
**🔍问题 P5-8**：6 个真器官用 `WrappedBuiltinOrgan` 动态子类包装（life_loop:256-273），每次 `_init_organs_and_tools` 在循环里定义同一个类——类对象重复创建 6 次。且包装后丢失原器官的 `_llm_session`/`get_last_thought` 等属性（只代理 `propose_actions`），若统一管理器真被调用会拿不到 LLM 思考。

### 5.4 `organ_manager.py` (346行) ⚠️ 旧管理器（接入但依赖被禁用的 drives）

**职责**：`OrganManager`——管理"驱动力器官"（axiology.drives 的 5 个）+ 肢体。life_loop 实际持有它（`self.organ_manager`）。

**实际被调用的方法**（grep 确认 life_loop 用了 3 个）：
- `get_all_drive_signals(state, context)`（PHASE 4.5, L920）：遍历 5 个 Drive 调 `generate_drive_signal`，返回 `{name: DriveSignal}`。**但这些 Drive 类来自 `axiology.drives`，而 P2-5 指出整个 drives/ 在 life_loop 顶部被注释禁用**——需确认这里是否也受影响（见 P5-9）。
- `format_drives_for_llm(state, context)`（PHASE 4.5, L922）：把驱动力格式化成 `## 当前驱动力状态` 提示文本，塞进 context["drives_prompt"]。
- `list_all_capabilities()`（PHASE 4.7/能力缺口, L524/L958）：从挂载的 limbs 列能力。

**未被调用的方法**：`get_dominant_drive`/`has_capability`/`execute_capability`/`mount_limb`/`unmount_limb`/`record_interaction`/`record_exploration`/`record_achievement`——全项目 grep 仅自身定义或 backup 文件引用。

**🔍问题 P5-9（🔴 重要，驱动力器官的矛盾状态）**：`OrganManager.__init__` 硬编码实例化 5 个 Drive（`CuriosityDrive()` 等，L36-40）。但 CODE_MAP 第2章 P2-5 记录 `axiology/drives/` 在 `life_loop.py` **顶部被注释禁用**。这里的矛盾是：**OrganManager 不受 life_loop 顶部注释影响**（它在 organs 包内独立 import），所以 drives 仍在 OrganManager 内被实例化和调用——life_loop:920 仍在每 tick 调 `get_all_drive_signals` 生成 drive_signals。即 **drives 实际是"半禁用"：life_loop 不直接用 Drive 类，但通过 OrganManager 间接用了**。需厘清：drive_signals 到底有没有喂给器官？答案见下条。
**🔍问题 P5-10**：`drive_signals`/`drives_prompt` 写入 context（L921-922），但**器官的 `propose_actions(state, context)` 是否真的读 context["drives_prompt"]？** 逐个查 6 个器官的 `_propose_actions_impl`/`_build_thinking_prompt`——**没有一个读 context["drives_prompt"] 或 context["drive_signals"]**。器官读的是 `state`（field_snapshot）里的 energy/mood/stress 等。即 **PHASE 4.5 算出的驱动力信号被算出来、塞进 context、然后没有任何器官消费它**——驱动力→器官的传导链路断了。这是 organs 层最隐蔽的正确性问题。
**🔍问题 P5-11**：`record_exploration`（L339）写 `self.curiosity._explored_topics.add(topic)`——直接访问私有属性 `_explored_topics`，且 `ScoutOrgan` 也有同名字段但两者完全独立（OrganManager 的 curiosity 是 Drive，ScoutOrgan 是真器官）。探索记录分散两处。

### 5.5 `base_organ.py` (212行) — BaseOrgan 基类
`BaseOrgan(ABC)`：器官最小契约。`propose_actions`(默认空)/`execute_capability`(默认失败)/`has_capability`(默认False)/`get_capabilities`(默认[])/`set_enabled`。`value_dimension` 字段关联价值维度。

文件尾部 `MountedOrgan` 占位符类（L121-212）：limbs 导入失败时的 fallback，Docker mount/unmount 全是模拟（`self._is_mounted=True` 不真启动容器）。

**🔍问题**：`BaseOrgan` 与 `UnifiedOrgan`（unified_organ.py）**两套器官基类并存**——6 个真器官继承 BaseOrgan，而统一架构用 UnifiedOrgan。接口几乎相同（propose_actions/execute_capability/has_capability）但无继承关系。这是 v2.0 重构未完成的痕迹。

### 5.6 `organ_selector.py` (232行) + `organ_interface.py` (251行) — 🔍 孤立双子
**🔍问题 P5-12（重要）— 两者运行时完全孤立**：全项目 grep 确认 `OrganSelector`/`OrganInterface` **仅在 `tests/test_organs.py` 引用**，life_loop 不 import 它们。
- `OrganSelector`：按 signal_type→器官映射 + stage/mode 偏好选器官。**但实际器官选择走的是 `core/differentiate.py` 的 `select_organs`**（基因组基因表达，见第8章 8.3）。这是**第三套器官选择逻辑**（OrganSelector 信号映射版 + differentiate 基因组版 + life_loop 的价值权重排序版 PHASE 7）。OrganSelector 是最早期的版本，已被取代。
- `OrganInterface`：进程信号→器官的统一接口（process_signal/execute_action/assess_risk）。它自己 `__init__` 里实例化 6 个器官（无 LLM session），与 life_loop 的 `self.organs` 字典**完全独立的两套器官实例**。assess_risk 的 `tool_risks` 表（web_search=0.2/file_write=0.7/code_exec=0.9...）与 safety/ 的风险计算重复。

### 5.7 `limbs/__init__.py` (149行) — 🔍 Docker 肢体（全是 TODO 占位）
**职责**：`Limb` 类——"被吞噬的外部工具"运行在 Docker 容器。`mount()`/`unmount()` 注释 `# TODO: 实现 Docker 容器启动`，实际只 `self._is_mounted=True` 模拟。`execute_capability` 恒返回 `success=False, "已定义但未实现（占位符）"`。

**注意**：这是 `organs/limbs/Limb`（BaseOrgan 子类，Docker 肢体），**与 `unified_organ.py` 的 `Limb`（UnifiedOrgan 子类，LLM 生成代码）同名但完全不同**。两个 `Limb` 类并存——organs/__init__.py 导出的是后者（unified_organ.Limb），limbs/__init__.py 的是前者。**极易混淆**（见 P5-13）。

**🔍问题 P5-13（命名冲突）**：`organs/limbs/Limb`（Docker 肢体，BaseOrgan 子类）与 `organs/unified_organ.Limb`（代码肢体，UnifiedOrgan 子类）**同名**。`organs/__init__.py:31` 导出 unified_organ 的 Limb，`base_organ.py:118` 和 `organ_manager.py:14` 导入 limbs 的 Limb 作 MountedOrgan。两个 Limb 概念不同（Docker 容器 vs exec 代码），文档注释里"肢体"指哪个含糊。
**🔍问题 P5-14**：`organs/limbs/Limb` 整个 mount/unmount 是 TODO 模拟，`execute_capability` 恒失败——**这个类实际上什么都不能做**。OrganManager 持有它却用不了（mount 成功但 execute 失败）。配合 P5-6（统一管理器只写），limbs/ 这个包是**完全无效的能力来源**。

### 5.8 六个内置器官（`internal/`）—— 共性架构

> 6 个器官（588-930 行/个）结构高度一致，先讲共性，再逐个讲个性。

**共性骨架**（每个器官都有）：
```
__init__(llm_session=None)              ← 可选 LLM 会话
propose_actions(state, context)         ← 入口：有 LLM 走 LLM，无走规则
 ├─ _propose_actions_with_llm()         ← LLM 模式
 │   ├─ _build_thinking_prompt()        ← 构建中文思考提示(含状态/目标)
 │   ├─ llm_session.think(prompt)       ← 调 LLM(organ_llm_session)
 │   ├─ _parse_llm_thought_to_actions() ← 关键词匹配 thought→Action
 │   └─ if not actions: fallback 规则   ← LLM 无效输出降级
 └─ _propose_actions_impl()             ← 规则模式：9个_should_xxx策略门
get_last_thought()/clear_last_thought() ← 选择性记忆用
```

**LLM 思考的统一流程**：每个器官 `_build_thinking_prompt` 把 state（精力/压力/心情...）+ 器官专属信息格式化成中文 prompt → LLM 返回一段中文思考 → `_parse_llm_thought_to_actions` 用**中文关键词匹配**把思考转成 Action（如 thought 含"探索/了解/发现"→EXPLORE 动作）。**LLM 的思考只是"生成一段文字"，真正决定 Action 类型的是关键词匹配**——LLM 在这里更像"提供叙事理由"而非"决策"。

**🔍问题 P5-15（🔴 重要，LLM 思考→Action 的解析极脆弱）**：所有 6 个器官的 `_parse_llm_thought_to_actions` 都用 `any(kw in thought_lower for kw in [...])` 中文关键词匹配。问题：① LLM 用英文或同义词（如"研究"vs"调研"、"实施"vs"构建"）会漏匹配 ② 一个 thought 可能同时含多组关键词，生成多个 Action（如既"探索"又"反思"）③ 关键词表硬编码，无配置。**实质上器官决策权在关键词表而非 LLM**——LLM 输出基本被降级为"填进 Action.params['thought'] 的叙事"。若关键词全不匹配，mind 退到 `THINK` 动作、scout/builder/immune 退到默认 EXPLORE/GROW/REFLECT。
**🔍问题 P5-16**：6 个器官的 `_propose_actions_impl`（规则模式）都实现了一套"9 策略 + `_should_xxx` 门"的复杂逻辑，但**当 LLM 模式启用时（默认），这些规则逻辑几乎永不被执行**（只在 LLM 返回空时 fallback）。即每个器官 ~600-900 行里，规则模式那大半代码是"LLM 挂了才用"的冷路径。而当前 .env 配的是可用的 stepfun LLM，规则模式实际是死代码。

### 5.9 `mind_organ.py` (884行) ⭐ 思维器官（competence）
**职责**：深度思考/规划/推理。**唯一会生成 CHAT 动作的器官**（用户响应）。

**规则模式 9 策略**：strategic(战略)/tactical(战术)/reactive(反应)/exploratory(探索)/reflective(反思)/creative(创造) 规划 + goal_decomposition(目标分解) + adapt_from_history(历史适应)。每策略有 `_should_use_xxx` 门（energy/stress/cognitive_load 阈值）。

**用户响应**（L849-884）：`_should_respond_to_user` 检查 context["observations"] 有无 `user_chat` 类型观察 → `_generate_user_response` 生成 `CHAT` 动作（message 留空，由 chat.py 填）。**这是对话能力的入口**。

**🔍问题 P5-17**：`_should_respond_to_user` 检查 `obs.type == "user_chat"`——但 Observation 模型（common/models.py）的 type 字段是否真用 "user_chat" 字符串？需对齐（action_executor 的拦截逻辑也依赖此）。若类型字符串不匹配，**用户消息永远不会触发 CHAT 动作**。
**🔍问题 P5-18**：`record_plan_outcome`/`successful_patterns`/`failed_patterns`/`strategy_success_rates` 学习机制——**life_loop 从不调用 `record_plan_outcome`**（grep 零外部引用）。即 mind 的"从历史学规划"功能写好了但没接入，`_adapt_from_history` 永远因 `len(plan_history)<10` 而不触发。

### 5.10 `scout_organ.py` (850行) ⭐ 侦察器官（curiosity）
**职责**：探索/学习/好奇心。8 模式探索：breadth_first/depth_first/random_walk/frontier/consolidation/targeted 等。

**探索主题生成**：`_generate_diverse_topics`/`_generate_random_topic` 从硬编码主题表（science/philosophy/... 或 novel_ideas/emerging_patterns/...）随机选。`_extract_topic_from_thought` 用中文分词（split 空格）提关键词——**中文 LLM 输出通常无空格分词，此函数对中文几乎无效**。

**🔍问题 P5-19**：`_extract_topic_from_thought`（L228）`thought.split()` 按空格分词——**中文文本无空格**，split 返回整段作为一个 word，因 `len>=2` 通过但 keywords 只有一个整句。探索主题变成一整段中文句子（如"我现在最想了解的是量子计算的本质"），不是有意义的 topic。mind_organ 的 `_extract_topic_from_thought`（L265）同病。
**🔍问题**：`record_exploration_outcome` 更新 `topic_interest_scores`/`knowledge_frontier`/`mode_success_rates`——但**life_loop 不调 `record_exploration_outcome`**（同 P5-18，学习机制未接入）。`explored_topics` 只在 record 时更新，EXPLORE 动作执行后无反馈→scout 不知道自己探索过什么。

### 5.11 `immune_organ.py` (930行) ⭐ 免疫器官（safety）
**职责**：安全/完整性/威胁检测。最大的器官。5 级 safety_mode（permissive→balanced→cautious→strict→lockdown）+ 5 级 trust + 5 类威胁。

**独特方法**（其他器官没有）：
- `veto_risky_action(action, state)`（L741）：按当前 safety_mode + action.risk_level 判断是否否决动作。lockdown 否决一切>RISK_MINIMAL，strict 否决>MODERATE...
- `assess_action_risk(action, context)`（L794）：基础风险 + 信任调整 × safety_mode 倍率（lockdown×2.0/permissive×0.8）。
- `update_action_trust(action_type, success)`（L874）：根据动作结果更新信任分（成功+0.05，失败-0.1）。

**🔍问题 P5-20（🔴 重要，veto/assess 实际未接入）**：`veto_risky_action`/`assess_action_risk`/`update_action_trust` **life_loop 全不调用**（grep 零外部引用）。PHASE 9 的安全检查走的是 `safety/` 模块（见第7章），不是 immune 器官。即 **immune 器官的"否决权"和"风险评估"是摆设**——它只在 PHASE 7 提议 REFLECT（stress_management/anomaly_investigation）动作，真正拦截动作的是 safety/。论文设计里 immune 应是安全执行者，但实现上被 safety/ 取代。`update_action_trust` 不被调→`action_trust_scores` 恒为默认 0.5→信任校准形同虚设。
**🔍问题**：`_detect_anomalies`（L562）用行为基线（`behavior_baseline` 每 metric 存最近 50 样本）算均值/标准差，`>2σ` 判异常——但 `behavior_baseline` 只在 `_update_behavior_baseline`（每 tick 调）填充，且 std_dev≈0 时跳过（已有 guard，good）。魔法数 2σ/50样本/10样本阈值硬编码。

### 5.12 `builder_organ.py` (900行) ⭐ 构建器官（competence）
**职责**：项目执行/里程碑管理。9 策略：project_init/milestone_planning/focused_sprint/parallel/incremental/quality_review/unblock/adapt/milestone_completion。

**项目管理状态**：`active_projects`(dict)/`task_queue`/`blocked_tasks`/`task_dependencies`/`milestone_history`/`work_sessions`/`productivity_scores`。`create_project`/`add_task`/`complete_task`/`block_task` 是管理 API。

**🔍问题 P5-21（🔴 重要，项目状态全在器官内存，永不持久化）**：builder 的 `active_projects`/`task_queue`/`completed_tasks` 全是实例属性，**life_loop shutdown 不保存**（同 schema/skill 的 P3-5 模式）。重启后所有"项目/任务/里程碑"清零。且 `record_work_session`/`complete_task`/`block_task` **life_loop 不调用**——即 builder 的项目状态在运行时也几乎不更新（只有 `_should_start_new_project` 在 goal 含 build/create 时初始化空项目）。builder 器官的"项目管理"功能基本是死的。
**🔍问题**：`_should_start_new_project` 检测 goal 含 "build/create/develop/implement/construct/design"（英文关键词），但 goal 多为中文→几乎不触发项目初始化。

### 5.13 `archivist_organ.py` (754行) ⭐ 档案器官（curiosity）
**职责**：记忆管理/整理/索引。8 策略：emergency_consolidation/periodic_consolidation/pruning/semantic_integration/indexing/pattern_recognition/compression/adaptive_strategy。

**🔍问题 P5-22（🔴 重要，archivist 与 memory/consolidation 职责完全重叠）**：archivist 器官的 `EPISODIC_CONSOLIDATION_THRESHOLD=50`/`PRUNING_THRESHOLD=100`/`CRITICAL_MEMORY_OVERLOAD=200` + 整套 consolidation/pruning 逻辑——**与 `memory/consolidation.py`(DreamConsolidator) + `memory/pruning.py`(MemoryPruner) + 各记忆类内置淘汰 功能三重重叠**（见第3章 P3-21）。更糟的是 archivist 器官**只提议 REFLECT 动作**（purpose="memory_consolidation" 等），真正执行记忆整理的是 PHASE 15 的 DreamConsolidator。archivist 的 `memory_count`/`episodic_count` 是它自己的本地计数器（`_update_archivist_state` 从 state 读），与真实 EpisodicMemory.count() 不同步。即 **archivist 是"记忆管理的影子系统"，提议了动作但动作执行走另一套**。
**🔍问题**：`add_memory`/`access_memory`/`categorize_memory`/`mark_consolidation_quality` 这些 API **life_loop 不调用**——archivist 的记忆索引（memory_index/memory_tags/retention_scores）在运行时永远空。

### 5.14 `caretaker_organ.py` (588行) ⭐ 照护器官（homeostasis）
**职责**：稳态维持/健康。优先级最高（P0），紧急情况可覆盖其他器官。监测 energy/fatigue/stress/boredom/mood，提 SLEEP/REFLECT/EXPLORE 动作。

**多级紧急系统**：CRITICAL(energy<0.15/fatigue>0.85/stress>0.85)→HIGH→MODERATE→LOW，各级有阈值常量。`assess_health_status` 算 health_score（energy×0.3+(1-stress)×0.25+...）。

**昼夜节律**：`preferred_sleep_start=22`/`_end=7`，`_is_sleep_time` 判断是否在睡眠窗口。`_should_suggest_sleep` 综合时间窗+能量+疲劳+距上次睡眠>100tick。

**🔍问题 P5-23**：caretaker 的 sleep 时间窗靠 `tick * tick_duration / 3600 % 24` 估算当前小时——**tick_duration 从 context.get("tick_duration",10) 取**，但 life_loop 传给器官的 context 是否真有 tick_duration？若没有则默认 10 秒/tick，当前小时估算依赖此假设。且这是"模拟时间"不是 wall-clock，与 metabolism/circadian.py（第4章）的真实昼夜节律可能不一致。
**🔍问题**：caretaker 与 metabolism/（第4章）+ core/handlers/caretaker_mode.py（第8章 CaretakerMode 安全降级）概念重叠——"照护"职责散落三处。器官版提 SLEEP 动作，CaretakerMode 是禁用其他器官只留 caretaker，metabolism 算能量恢复。

### 5.x organs/ 速查与调试点

**精读优先级**：`organ_llm_session.py`(三模式是核心) > `unified_organ.py`(看架构债) > 6 器官的 `_parse_llm_thought_to_actions`(看 LLM 如何降级为关键词)。

**接入真相表**：
| organs 模块 | life_loop 接入 | 状态 |
|---|---|---|
| 6 个 internal 器官 propose_actions | PHASE 7 `self.organs[name].propose_actions` | ✅ 接入（LLM 或规则） |
| OrganLLMSession/Manager | `_init_organ_llm_manager` + `get_session` | ✅ 接入（三模式） |
| OrganMemoryWriter | `_save_organ_thought_to_memory` | ⚠️ 条件接入（依赖 writer 初始化成功） |
| OrganManager（旧） | PHASE 4.5 drive_signals + 能力查询 | 🟡 接入但**驱动力无人消费**(P5-10) |
| UnifiedOrganManager（新） | 仅 `add_builtin_organ` 注册 | 🔴 **只写死代码**(P5-6) |
| OrganSelector | — | 🔴 **完全孤立**(仅测试, P5-12) |
| OrganInterface | — | 🔴 **完全孤立**(仅测试, P5-12) |
| organs/limbs/Limb | OrganManager 持有 | 🔴 **mount 是模拟, execute 恒失败**(P5-14) |
| immune.veto_risky_action/assess_action_risk | — | 🔴 **完全孤立**(P5-20, 被 safety/ 取代) |
| 各器官学习 API（record_plan_outcome 等） | — | 🔴 **完全孤立**(P5-18/P5-19/P5-21) |

**高危区**：
1. **新架构只写**（P5-6）：UnifiedOrganManager 注册器官从不查询——growth/plugins"注册为器官"写了等于没写
2. **驱动力传导断裂**（P5-10）：PHASE 4.5 算的 drive_signals 没有任何器官消费
3. **LLM 思考被关键词降级**（P5-15）：6 器官决策权在硬编码中文关键词表，LLM 沦为叙事生成器
4. **immune 否决权虚设**（P5-20）：安全执行被 safety/ 取代，immune 只提 REFLECT
5. **器官状态不持久**（P5-21）：builder/archivist/scout 的学习状态重启清零
6. **三套器官选择逻辑**（P5-12）：OrganSelector(信号) + differentiate(基因) + life_loop(价值权重) 并存

**与论文的对应**：器官分化 = §3.8；价值驱动器官选择 = §3.9（PHASE 7 的 `organ_priority_by_value`）；器官作为判断器官（LLM 会话）= §3.4.2；共享大脑 = §3.4.2 黑板；6 器官优先级 caretaker>immune>mind>scout>builder>archivist = Genome 默认基因 priority。

---

## 6. 工具层 `tools/` — 待续

> ⏳ 23 文件/9837 行。LLM API 统一接口 + 工具执行引擎 + Mind Field 黑板(`blackboard.py` 1370行) + 安全代码执行 + 视觉/语音/嵌入。
> **续写提示**：`llm_api.py`(多 provider 适配,495行)→`tool_executor.py`(643行)→`blackboard.py`(1370行,论文3.4.2)→`safe_executor.py`(515行,AST安全)→`embeddings.py`。**注意当前 .env 配的是 stepfun step-3.7-flash，llm_api.py 的 provider 适配是否覆盖需验证。**

---

## 7. 安全 + 持久化 — 待续

> ⏳ `safety/`(7文件,预算/风险/契约/沙箱/幻觉检测) + `persistence/`(6文件,回放引擎3模式/事件日志/快照)。共 13 文件/2604 行。

---

## 8. 核心引擎 `core/` ⭐最重要

> 43 文件/18338 行——**全系统最大模块**。`LifeLoop.tick()` 是编排一切的中枢（17 阶段流水线），向下驱动 axiology/affect/memory/cognition/organs/safety 全部子系统。本章逐文件梳理，并在末尾汇总本章新发现的 20 项问题（P8-1 ~ P8-20）。
>
> **目录结构**：
> ```
> core/
> ├── life_loop.py        (1883)  ⭐主循环，LifeLoop 类
> ├── life_loop_backup.py (2565)  🔍备份(可删)
> ├── differentiate.py    (633)   器官分化/基因表达
> ├── tick.py             (62)    TickContext 数据载体
> ├── state.py            (409)   GlobalState 全局状态聚合
> ├── abstract_state.py   (478)   LLM 切换时的抽象状态层
> ├── invariants.py       (63)    运行时不变量检查
> ├── exceptions.py       (587)   🔍异常体系(未被使用)
> ├── resource_config.py  (249)   resources.yaml 加载
> ├── scheduler.py        (451)   🔍调度器(孤立未用)
> ├── autonomous_scheduler.py (707) 闲时自主任务守护进程
> ├── exploration.py      (412)   探索任务模板库
> ├── emotion_decay.py    (615)   🔍精细情绪衰减(未接入)
> ├── capability_*.py     (×3)    能力管理三件套(见下)
> ├── handlers/   action_executor(1461)+chat+caretaker+gap
> ├── stores/     fields+slots+signals+ledger+factory
> ├── evolution/  (8文件,默认禁用) clone→mutate→eval→transfer→archive
> ├── growth/     (4文件) LLM 生成肢体(新能力)
> └── plugins/    plugin_manager+templates/ 预制能力
> ```

### 8.1 `life_loop.py` (1883行) ⭐⭐ 编排中枢

**职责**：`LifeLoop` 类——数字生命的心脏。`__init__` 分 8 个阶段初始化全部子系统；`run_session()` 跑 tick 循环并做错误降级；`tick()` 执行 17 阶段完整流水线；`shutdown()` 持久化状态。继承 `GapDetectorMixin`（而非组合，见 8.5）。

#### 8 阶段初始化（`__init__` → `_init_*` 方法链）
```
① basic_config  → session_id / run_dir / replay_mode / 进度回调
② stores        → FieldStore + SlotStore + SignalBus + MetabolicLedger + _init_state_from_config
③ memories      → Episodic/Schema/Skill + MemoryRetrieval + DreamConsolidator + 恢复tick/聊天历史
④ cognition     → GoalCompiler + Planner + PlanEvaluator + Verifier
⑤ organs_tools  → 器官LLM会话 + 6器官 + ToolRegistry + 动态工具 + 双器官管理器
⑥ advanced      → 进化(默认关)/插件/成长/能力管理器/缺口检测器
⑦ affect        → ValueFunction + RPEComputer + WeightUpdater + ValueLearner + 昼夜节律 + 情感调制
⑧ loggers       → JSONLWriter(episodes/states/tool_calls) + ActionExecutor + ChatHandler + CaretakerMode
```
关键设计：器官创建时注入 `llm_session`（来自 `_organ_llm_manager`，三模式 independent/shared/disabled，见 8.x organs 章）；未走 LLM 的器官回退规则模式。

#### `run_session(max_ticks)` — 论文 §3.13 错误降级
逐 tick 调用，对 `Exception` **按错误消息字符串匹配**分四类处理：
- 含 "tool" → 连续 3 次进 CaretakerMode（只保留 caretaker 器官）
- 含 "memory" → 紧急巩固（budget 5000, salience 0.4，激进清理）
- 含 "value"/"parameter" → `caretaker_mode.reset_to_safe_defaults()`
- 其他 → 连续 3 次进 CaretakerMode
⚠ 注意：自定义异常类 `ToolExecutionError`/`MemoryOverflowError`（`core/exceptions.py`）**从未被 raise**，这里的判断全靠 `str(e)` 子串匹配——脆弱（见 P8-6）。

#### `tick(t)` — 17 阶段完整流水线（⭐最核心，逐阶段）
```
PHASE 0   caretaker_mode.check_and_exit()          — 维护模式退出检查
PHASE 1   _update_body(dt)                          — 代谢:能量/疲劳恢复(昼夜节律调制), 无聊增长×0.5
PHASE 2   observe_environment(...)                  — 观察:field_snapshot + 可选 user_input
PHASE 3   smart_retrieval.analyze_retrieval_need    — 智能检索决策(none/basic/semantic), 按需检索 episodes/schemas/skills
PHASE 4   build_context(...)                        — 构建 context, 含 observations/drive_signals/drives_prompt
PHASE 4.5 drive_state → organ_manager.get_all_drive_signals  — 驱动力信号(旧版)
PHASE 4.6 evolution_system.check_evolution_trigger  — 进化检查(默认禁用, AttributeError 吞掉)
PHASE 4.7 gap_detector.update_known_capabilities    — 能力缺口检测器刷新已知能力
PHASE 5   axiology: features→gaps→WeightUpdater→weights→utilities  — 价值计算(含软优先级覆盖)
PHASE 6   goal_compiler.compile_multi_goal(max=3)   — 多目标编译(冲突协调)
PHASE 7   select_organs + 器官 propose_actions      — 器官分化+提案(serial/mixed/parallel 三模式)
PHASE 8   plan_evaluate + H4 单外部动作强制          — 评估+最多1个外部动作(论文红线)
PHASE 9   safety: 9a完整性 9b验证器 9c风险 9d预算 9e能力缺口  — 五重安全检查
PHASE 10  action_executor.execute(action, context)  — 动作执行 + ledger 扣成本 + 同步到 state
PHASE 11  compute_reward + value_function.update + compute_rpe + 维度级RPE + mood/stress更新 + AffectModulation  — 奖励与情感闭环
PHASE 12  episodic.append(EpisodeRecord)            — 写记忆
PHASE 13  check_invariants                          — 不变量检查
PHASE 14  value_learner.update(每 interval ticks)   — 价值学习(更新 setpoints)
PHASE 15  条件触发 consolidator.consolidate(梦境巩固) — 巩固+重置疲劳
PHASE 16  持久化 override 状态                        — 优先级覆盖状态落盘
```
**性能**：各阶段计时，>1s 时输出最慢 3 阶段。PHASE 7（器官）通常最慢，受 `ORGAN_PARALLEL_MODE` 影响（serial ~40-60s / mixed ~15-25s 默认 / parallel ~8-15s）。

**器官并行三模式**（PHASE 7，环境变量 `ORGAN_PARALLEL_MODE`）：
- `serial`：按价值权重排序逐个处理，最稳
- `mixed`（默认）：按依赖分 3 组（`[scout,builder,archivist]`→`[mind,caretaker]`→`[immune]`），组内并行组间串行
- `parallel`：全并行（有依赖风险）

**特殊 hack（PHASE 11）**：成功的 CHAT 动作被**强制注入正向 RPE**——`delta_per_dim["attachment"]=abs(...)+0.05`、`competence +0.03`，外加 `reward += 0.2`。注释明确这是为了让对话成功产生正情绪的临时手段。🔍这类硬编码修正散落多处，说明纯 axiology 计算对"社交成功"的奖励信号建模不足。

#### `shutdown()` — 优雅关闭
关闭两个 JSONLWriter → 持久化 override 状态 → 持久化 value 参数 → `_persist_final_state()`。每步 try/except 独立，保证一个失败不阻断其余。

#### 状态恢复（跨重启）
- `_restore_tick_from_history()`：从 episodes.jsonl 读最大 tick，设为 max+1
- `_restore_chat_history()`：从历史 CHAT episode 重建 chat_history 槽位，**只保留最近 2 条**（注释：避免文学风格污染）

**🔍问题 P8-1（重要）**：`life_loop.py:48` `from tools.capability import CapabilityManager` 与 `:71` `from .capability_manager import CapabilityManager, create_capability_manager` **重名导入**——后者覆盖前者。`tools.capability.CapabilityManager`（基于 CapabilityToken 的轻量类）从未被使用，是**死导入**。

**🔍问题 P8-2**：`life_loop_backup.py`(2565行) 比 `life_loop.py`(1883行) 还大。备份文件长期堆积，疑似可删。需 git 确认是否已被新版取代后删除。

---

### 8.2 `tick.py` (62行) + `invariants.py` (63行) + `state.py` (409行)

#### `tick.py` — TickContext 数据载体
`@dataclass TickContext`：贯穿一个 tick 所有阶段的可变载体。字段 `t/dt/phase/obs_batch/retrieved/proposed_actions/metadata` 等。方法仅 `advance_phase`/`add_observation`/`cache_feature`。
**🔍问题 P8-3**：TickContext **没有存放 PHASE 7 的器官分化结果**（expressed_organs/priorities 留在 life_loop 局部变量里），与"上下文贯穿所有阶段"的设计意图不一致。

#### `invariants.py` — 运行时不变量
`check_invariants(state, weights, ledger, actions)` 返回 Dict：权重单纯形（和≈1）、账本非负、单外部动作、状态字段范围检查。
**🔍问题**：`check_single_external_action` 硬编码 `SLEEP/REFLECT` 为"内部"（黑名单式），若新增内部动作类型会误判为外部。应改为白名单（外部= `{USE_TOOL, CHAT}`）或 Action 加 `is_external` 标志。注释还提"8 个维度"但现在是 5 维，tolerance `1e-3` 可能过松。

#### `state.py` ⭐ GlobalState — 全局状态聚合 `S_t`
论文 §3.2 状态向量 `⟨O_t, X_t, M_t, K_t, θ, ω_t⟩` 的实现。dataclass，**可序列化**（`to_dict`/`from_dict`）。
- **真实系统资源**（psutil）：`compute`(CPU%)、`memory`(占用率)、`resource_pressure=0.6·compute+0.4·memory`，紧急阈值 0.35
- **活动疲劳** `activity_fatigue`（替代旧 energy/fatigue 语义）
- **情感** mood[-1,1] / stress / relationship / arousal / boredom
- **价值系统** weights(5维,默认0.2) / gaps / setpoints(HOMEOSTASIS0.7/ATTACHMENT0.7/CURIOSITY0.6/COMPETENCE0.75/SAFETY0.8)
- **覆盖状态**（论文§3.6.4）：`override_active:set` / `override_trigger_time` / `gaps_at_trigger`
- **兼容属性**：`energy`↔`1-activity_fatigue`、`fatigue`↔`activity_fatigue`、`bond`/`trust`↔`relationship`

**🔍问题 P8-4（重要）— GlobalState 与 FieldStore 双重真相源**：7 个情感标量字段（energy/mood/stress/fatigue/bond/trust/boredom）**同时存在于 `GlobalState` 和 `FieldStore`**，靠 life_loop 的 `_sync_state_to_global`/`_sync_fields_to_global` **手工同步**。FieldStore 是运行时活态（snapshot 传给器官/特征提取），GlobalState 是可序列化聚合。两套真相源 + 手工同步 = 高危区。
**🔍问题 P8-5**：`update_body()` 每 tick 调 `psutil.cpu_percent(interval=0.1)` —— **阻塞 100ms**，拖慢主循环。
**🔍问题 P8-6**：dataclass 默认值与 `from_dict` 回退值不一致（mood: 0.0 vs 0.5；stress: 0.15 vs 0.2；boredom: 0.30 vs 0.0）——默认 GlobalState 经 `to_dict→from_dict` 往返会**静默改变值**，影响持久化正确性。
**🔍问题**：`trust` setter 是 `relationship=(relationship+value)/2`（有损平均），而 `bond` setter 是直接赋值——不对称，`g.trust=x; g.trust≠x`。

---

### 8.3 `differentiate.py` (633行) — 器官分化/基因表达

**职责**：论文"器官分化"的实现——基于发育阶段(stage)、活动模式(mode)、状态标量、信号，决定每个 tick 哪些器官被"表达"(expressed)。

**核心类**：
- `Stage(Enum)`：EMBRYO/JUVENILE/ADULT/ELDER；`advance_stage(current, ticks)` 阈值 100/500/5000
- `Gene`：`express_conditions`/`suppress_conditions`（字符串 DSL）+ `priority`。`should_express(context)` 抑制优先于表达
- `Genome`：6 个默认基因（caretaker p0 / immune p1 / mind p2 / scout p3 / builder p4 / archivist p5）。`differentiate(context)` 任一基因表达则器官表达
- `Differentiator(config)`：`select_organs(stage, mode, state, signals)` 主入口

**基因条件 DSL**：字符串如 `"fatigue > 0.9 and stage == 'adult'"`，用 **AST 白名单 + `eval`** 执行（屏蔽 Import/dunder，限制嵌套深度 5，长度上限 200）。

**🔍问题 P8-7（重要，真实 bug）— 自定义基因被缓存吞掉**：模块级 `_get_differentiator()` 用**空 config `{}`** 实例化并缓存；legacy shim `select_organs(...)`（life_loop 实际导入的）用这个缓存实例——所以 `config["genome"]["custom_genes"]` **在器官选择时被静默忽略**。而 life_loop:1015 另建 `Differentiator(config)` 只为调 `advance_stage`，用完即弃。结果：自定义基因永不生效。

**🔍问题 P8-8**：life_loop 每 tick 新建一个 `Differentiator` 实例（只为 `advance_stage`），默认基因重复注册，浪费。
**🔍问题**：`Mode` 枚举有 `PLAY` 但无默认基因使用它（死枚举值）；`_get_nesting_depth` 的 `ast.Call` 分支永不执行（Call 不在白名单）；`can_organ_override` legacy shim 的 `action` 参数未使用。

---

### 8.4 `abstract_state.py` (478行) — LLM 配置切换的抽象状态层

**职责**：论文 §3.4.2 抽象状态层 𝕊_t——模型无关的表示（情绪/目标/记忆指针/上下文摘要），用于在不同 LLM 配置（single/core5/full7）间保持连续性。

**核心类**：`AbstractState`(组合 `AbstractEmotionalState`/`AbstractGoal`/`AbstractMemoryPointer`/`AbstractContextSummary`) + `StateTransitionManager` + `BlackboardWithAbstractState`。

**🔍问题 P8-9（重要）— 抽象层基本未实现**：
- `to_concrete(target_config)` **忽略其参数**，产出与配置无关的相同 dict——配置特定具象化（该层存在的全部意义）未实现
- `stress = 1.0 - valence`（L270）——把 stress 和 mood 当作同一轴的有损重建，语义错误
- `update_from_concrete` 只更新情绪/目标，记忆指针和上下文摘要**永不填充**
- L462 `Blackboard = None` 注释"将在导入时处理"但**从未赋值**——死符号
- 抽象层有 `to_dict` 但无 `from_dict`（不对称持久化）

**结论**：这 478 行是为"LLM 热切换"预留的脚手架，但核心转换逻辑未完成，且未被 life_loop 调用。**疑似死代码或半成品。**

---

### 8.5 `handlers/` — 动作落地与功能拆分（4 文件）

> 从原 LifeLoop 拆分出的功能模块。`ActionExecutor`/`ChatHandler`/`CaretakerMode` 用**组合**（`__init__(life_loop)`），`GapDetectorMixin` 用**混入**（继承）——同一包内模式不一致。

#### `handlers/action_executor.py` (1461行) ⭐ 动作执行关键路径
`execute(action, context)` 按 `action.type` 分派：`SLEEP/EXPLORE/REFLECT/CHAT/LEARN_SKILL/USE_TOOL/OPTIMIZE`。

**CHAT 路径（`_execute_chat`, 最复杂，~230行）**——"Claude Code 风格" Agentic Loop：
1. 能力门控（查 `"qianwen_chat"` 工具，硬编码 tool_id）
2. 硬编码拦截：消息含"生成/肢体/器官"→罐头拒绝；疲劳>0.8 且含"生成/创建/写一个/帮我做/分析/整理"→"我累了"
3. 构建 system_prompt + chat_history(limit=10)
4. 成本预估：`estimated_tokens=max(1000, len(prompt)+len(msg)+Σlen(history))`，money=`tokens×0.000001`
5. **Agentic 循环**（max_rounds=50, max_tokens=100000）：
   - `_call_llm` → 累加 tokens → 若无 `tool_calls` 则模型认为完成，break → 否则 `_execute_tool_calls`（并行 ThreadPoolExecutor max_workers=5, 每调用 timeout=30s）→ 截断 history(max 15条) → 继续
6. `_process_embedded_tool_calls`（正则解析 `TOOL:..`/`tool_code(...)` 文本嵌入调用，降级方案）
7. 扣 ledger 成本、增疲劳（`0.02·rounds+0.00005·tokens`）、改社交字段（bond+0.01/trust+0.005/boredom-0.05）

**🔍问题 P8-10（重要，真实 bug）— 多轮响应被覆盖**：`_execute_chat` L342 `llm_response = round_response`（注释却写"累积"）——每轮非空响应**覆盖**而非拼接，前几轮的正文被静默丢弃。多轮工具调用场景下，用户只能看到最后一轮的文字。

**🔍问题 P8-11（重要，真实 bug）— 能力缺口检测的 tool/tool_id 键不一致**：`gap_detector._check_action_capability` L243 读 `action.params.get("tool","")`，而 `action_executor._execute_use_tool` L505 读 `action.params.get("tool_id","")`。USE_TOOL 动作的能力缺口检查**永远拿到空 tool_name**，缺口永不触发 → 成长系统不会被 USE_TOOL 驱动。

**🔍问题 P8-12**：`_call_llm` **不传 timeout**——若 LLM provider 挂起，整个 tick 卡死（只有工具调用有 30s 超时，LLM HTTP 调用本身无超时）。配合 CHAT_TIMEOUT=180s 环境变量，实际超时靠底层 `tools/llm_client.py`。
**🔍问题 P8-13**：未知 ActionType 返回 `{"success":True}`（L87）——分派 bug 被静默成成功。
**🔍问题**：`tool_executor.execute()` 调用签名不一致——`_execute_use_tool` 用 kwargs(`tool_id=,params=`)，`_execute_tool_calls` 用位置参数(`tool_name, arguments`)。
**🔍问题**：无 `tool_executor` 时 USE_TOOL 返回 mock 成果（L553）——静默降级。
**🔍问题**：大量硬编码魔法数（token价/轮数/历史长度/疲劳系数/社交增量/相似度阈值）；`_execute_chat` 单方法 ~230 行应拆分。

**⚠ 注意**：CHAT 路径**不解析 `reasoning_content`**。step-3.7-flash 的推理内容（若有）必须在 `tools/llm_client.py` 内部处理，executor 把 LLM 当不透明对象。

#### `handlers/chat_handler.py` (205行)
构建 CHAT 系统提示词（中文人格"你是 Genesis X…"，嵌入 energy/mood/stress 等带状描述）+ 管理 chat_history 槽位。
**🔍问题**：`generate_contextual_greeting`（英文）与 `action_executor._generate_contextual_greeting` **逐字节重复**；`search_relevant_memory` 是 deprecated 空桩（返回""）；历史长度三处不一致（fetch 10 / save 50 / SLEEP trim 10）。

#### `handlers/caretaker_mode.py` (125行)
安全降级模式（论文§3.13）。`enter()` 禁用除 caretaker 外所有器官；`check_and_exit()` 当 tick-进入≥10 且 stress<0.5 时退出；`reset_to_safe_defaults()` 钳制状态+重置权重。
**🔍问题**：魔法数全硬编码（recovery 10/stress 0.5/energy 0.3/mood 0.5）；`reset_to_safe_defaults` 的 energy 逻辑只升不降（`max(0.3, current)`）——energy=0.95 的"漂移"不被修正。

#### `handlers/gap_detector.py` (278行) — `GapDetectorMixin`
LifeLoop 继承的混入，从用户请求/驱动信号/探索历史三源汇总能力缺口，排名后返回 evolution_need。`_check_action_capability` 是执行前能力检查。
**🔍问题**：`any(cap.lower() in str(known_capabilities).lower() ...)`（L247等）——**把 set 转字符串做子串匹配**，会产生误报（如 capability `"file"` 匹配 `"profile"` 的子串）；中文关键词→领域表硬编码；与 action_executor 的 tool_id 键不一致（见 P8-11）。

---

### 8.6 `stores/` — 四大状态存储（6 文件）

> 一个 tick 的可变状态骨干。`life_loop._init_stores` 创建四件套。

| Store | 存什么 | 生命周期 | 关键方法 |
|---|---|---|---|
| `FieldStore` | 8 个有界标量(energy/mood/stress/fatigue/bond/trust/boredom/curiosity) | 跨 tick 持久 | `get/set/increment/snapshot` |
| `SlotStore` | 工作记忆(current_goal/plans/milestones/chat_history 等) | 持久,可回放 | `get/set/append/clear` |
| `SignalBus` | 命名的时间衰减信号(半衰期,指数/线性) | 瞬时,自动过期 | `set/get/add/tick/cleanup` |
| `MetabolicLedger` | 资源预算(cpu_tokens/io_ops/net_bytes/money/risk_score),reserve→spend→refund | 持久 | `can_reserve/reserve/spend/refund/normalize_all` |

**tick 数据流**：器官读 `fields.snapshot()`+`signals.get_all()`+`slots.get("current_goal")` → 选动作 → `ledger.reserve` 预算 → 执行 → `ledger.spend` 实际扣 → `fields.set` 写回效应 → `signals.tick(dt)` 推进时间。

**文件**：`fields.py`(BoundedScalar/Valence/Prob)、`slots.py`、`signals.py`(Signal 半衰期衰减)、`ledger.py`(ResourceBudget, 默认 cpu_tokens 无限)、`factory.py`(从 resources.yaml 建 ledger)、`__init__.py`。

**🔍问题 P8-14**：`FieldStore` 与 `GlobalState` 重复存 7 个字段（见 P8-4）。
**🔍问题**：`MetabolicLedger.from_dict` **不恢复 `unlimited` 标志**——重载后无限资源状态丢失；`spend()` 不检查 unlimited（无限资源仍累计 spent，语义怪）；`Valence` 类定义但 FieldStore 全用 Prob（死类）；字段初始值(0.8/0.5/0.2…)硬编码非配置驱动。

---

### 8.7 `evolution/` (8 文件, 默认禁用) — 自我进化引擎

> ⚠️ **整体默认关闭**（`EVOLUTION_ENABLED=False`）。虽禁用但代码完整，记录其设计意图。

**完整流水线**（`EvolutionEngine.evolve`，9 步）：
```
CLONE   clone_manager.create_clone  — shutil.copytree 整个项目到 ../evolution_instances/, 分配端口(8000+)
MUTATE  mutation_manager.apply      — 选 MutationType → LLM/模板生成 proposal → 写入 clone → py_compile 校验
EVALUATE evaluation_manager.evaluate — 10 项检查(语法/核心文件/工具/记忆/响应时间/错误率/人格保留/记忆完整性/价值对齐), overall_score≥0.7 才 transfer
TRANSFER transfer_manager.transfer  — 备份 core/config/memory → 复制 target_files 回项目
ARCHIVE  archive_manager.archive    — zip 旧体+metadata → ../evolution_archives/, 增 generation 计数
RETIRE   clone_manager.cleanup_clone — 停进程+rmtree
```

**关键区分**（每文件 docstring 强调）：**Growth=同一个体变强；Evolution=复制-变异-选择产生新一代**。

**🔍问题 P8-15（重要）— 进化管道实际是空操作**：
- `mutation_manager._generate_with_llm` 有 `# TODO: 实现 JSON 解析`——LLM 响应**未解析**，proposal 的 `changes={}` 恒空
- `apply_mutation` 对空 changes 返回 True（成功）——**无操作变异"成功"**
- `transfer` 遍历空 `target_files`——**transfer 也是空操作**
- 即便启用，整个变异-迁移链什么都没做。evaluation 的"人格保留"靠**基因组 YAML 文件大小比**（非内容），value_alignment 靠文件是否存在——信号极弱。

**🔍问题**：`clone_id=f"clone_{int(time.time())}"` 秒级时间戳，同秒两次进化碰撞；引擎无锁，并发 `evolve()` 会覆盖 `current_clone`；`TESTING` 枚举值定义但流程跳过（MUTATE→EVALUATE 无 TEST 阶段）；`validate_mutation` 定义但 `evolve` 从不调用（死方法）；`evaluation_manager.get_stats` 对非空历史会 `TypeError`（`to_dict` 多了 `overall_score` 键，dataclass 重建失败）。

---

### 8.8 `growth/` (4 文件) — 肢体(新能力)生成

> ✅ **已启用**。LLM 驱动生成新能力模块（对比 plugins 是预制的）。与 evolution 的区别：growth 是同体增强。

**核心流**（`LimbGenerator`）：
1. `identify_requirement(context)` — 扫描用户消息关键词(api/http/爬取→EXTERNAL；csv/excel/数据→INTERNAL)
2. `_generate_from_llm` — 中文 prompt(可嵌入相似 plugin 的代码≤800 字符作参考) → LLM → 正则提取代码 → 提取第三方 imports → 自动判定 INTERNAL/EXTERNAL
3. `_test_limb` — 仅 `compile()` 语法检查（**不执行**）
4. `_save_limb` — 写 `artifacts/limbs/{name}/__init__.py`+`metadata.json`
5. `_register_limb` — 内存注册；可选 `LimbBuilder` 建 Docker 容器
6. `GrowthManager.generate_limb` 额外：注册为 `organs.Limb` 器官到 UnifiedOrganManager + 写使用指南到记忆

**V32 "吞噬/生长/灵活" API**：`devour(path)` 读文件、`grow(task)` 生成代码、`flex(filepath)` 沙箱执行（危险模式字符串黑名单）。

**🔍问题 P8-16**：`limb_builder.list_limbs` 按 `label=genesisx.limb=true` 过滤，但 `deploy_limb` 从不设该 label → **list_limbs 恒返回空**。
**🔍问题 P8-17（安全）**：`Plugin._create_instance` 和 `load_limb` 用 `exec(code, namespace)` **无沙箱执行**插件/肢体代码；`devour(".")` 可读当前目录任意文件；`flex_limb_v32` 危险模式黑名单不全（漏 `os.remove` 等，且误拦 `subprocess.run`）。
**🔍问题**：`devour` 的 `save_to_memory` 参数被接受但从未使用（死参数）；类名推导逻辑(`_to_class_name`)在 limb_generator 和 plugin_manager 重复；魔法数遍布(800字符/温度0.2/0.3/好奇度0.7阈值等)。

---

### 8.9 `plugins/` (2 文件 + templates/) — 预制能力加载

> ✅ 已启用。预制的能力模块（对比 growth 是 LLM 现写的）。两个内置：`http_api`(get/post/put/delete)、`data_processor`(pandas: read_csv/process_data/to_excel)。文件系统插件从 `core/plugins/templates/` 读 `{name}/__init__.py`+`metadata.json`。

**v2.0 集成**：加载时自动注册为 `organs.Plugin` 器官 + 写使用指南。`get_similar_plugin_for_learning` 三级匹配（精确子集→最大重叠→关键词），供 growth 系统作代码参考。

**🔍问题**：`exec(self.code, namespace)` 无沙箱（同 P8-17）；`get_similar_plugin_for_learning` 的关键词表只认 http_api/data_processor；`_register_as_plugged_organ` 是 `_register_as_organ` 的无说明别名；`SKIP_PATTERNS` 在 clone_manager 和 archive_manager 重复（且 `.pyc` vs `*.pyc` 不一致）。

---

### 8.10 孤立/半孤立模块（⚠️ 清理候选）

精读发现 **大量 core 模块未被 life_loop 接入**，按孤立程度分类：

| 文件 | 行数 | 状态 | 说明 |
|---|---|---|---|
| `exceptions.py` | 587 | 🔴**完全孤立** | 大型异常体系(CircuitBreaker/RetryWithBackoff/ErrorHandler)+get_error_handler() 单例，**全项目无人 import**。且 `common/error_handler.py` 是**另一套**并行未用的错误框架 |
| `scheduler.py` | 451 | 🔴**完全孤立** | Scheduler 类(在线/离线+定时任务)，零调用者。被 autonomous_scheduler 取代 |
| `capability_router.py` | 252 | 🔴**完全孤立** | 第三个能力门面(skill→organ→evolution, 产 OpenAI function schema)，从未被 import |
| `emotion_decay.py` | 615 | 🟡**半孤立** | 精细情绪衰减(论文3.7.3, 多维指数衰减+Proust效应)，最精致但 **life_loop 用 `affect.*` 不用它**。仅 __init__ 重导出 + benchmark 引用 |
| `exploration.py` | 412 | 🟡**半孤立** | 探索任务模板库，仅 autonomous_scheduler 懒加载它，且**方法名不匹配**（调 `generate_exploration_tasks` 但实际是 `generate_tasks`）——集成是坏的 |
| `abstract_state.py` | 478 | 🟡**半孤立** | 见 8.4，核心转换未实现，未被 life_loop 调用 |

**🔍问题 P8-18（重要）— 6 个模块共 ~2793 行孤立代码**：`exceptions.py`+`scheduler.py`+`capability_router.py` 完全死；`emotion_decay.py`+`exploration.py`+`abstract_state.py` 半死。这是 core 的**最大技术债**。优化时优先决策：删除 / 接入 / 标记实验性。

**🔍问题 P8-19（重要）— 能力管理三件套碎片化**：
- `capability_manager.py` ✅接入（plugin→limb→growth 查找）
- `capability_gap_detector.py` ✅接入（检测缺口→喂 growth）
- `capability_router.py` ❌孤立（skill→organ→evolution，产 function schema）
三者 API 重叠（`list_*capabilities`/`has_capability`）却互不引用。只有前两者构成连贯活管道。

**🔍问题 P8-20**：`autonomous_scheduler.py` 仅被 `chat_interactive.py` 用，**不在 tick 路径**。它与 `scheduler.py`(死)、life_loop 自己的 inline 离线逻辑——**三套重叠的"调度"概念**。

---

### 8.x core/ 速查与调试点

**精读优先级**：`life_loop.tick()`(17阶段必懂) > `action_executor._execute_chat`(对话落地) > `differentiate.select_organs`(器官分化) > stores 四件套 > handlers 其余。

**高危区**：
1. **状态同步**（P8-4/P8-6）：GlobalState↔FieldStore 双真相源 + 往返不一致——任何动 mood/stress 的修改都要两边改
2. **能力缺口→成长链路**（P8-11）：tool/tool_id 键不一致导致 USE_TOOL 永不驱动成长
3. **多轮对话**（P8-10）：响应覆盖 bug 让多轮工具调用丢正文
4. **自定义基因**（P8-7）：缓存吞掉 config，器官分化配置失效
5. **参数来源**：core 内魔法数遍地（阈值/系数/超时/价格），与第1章 P1-3 的"参数三重定义"问题叠加

**与论文的对应**：tick 17 阶段 ≈ 论文 Algorithm 1；PHASE 5 axiology = 论文 §3.5-3.6；PHASE 11 = 论文 §3.7；PHASE 9 = 论文 §3.13；override 状态 = §3.6.4；value learning = §3.12。

---

## 9. 入口 + Web — 待续

> ⏳ `lifecycle/`(3文件) + `web/app.py`(Flask,40+路由) + `web/websocket_server.py` + 顶层 `run.py`/`daemon.py`/`chat_interactive.py`。
> **续写提示**：`web/app.py` 的 40+ 路由要分类整理（状态/聊天/配置/器官/记忆/守护进程/主动消息）。initiative messaging（主动发消息）是特色功能。

---

## A. 全局问题清单（按优先级）

> 精读 Phase 1-2(common+axiology+affect) + Phase 8(core) + Phase 3(memory) 发现的问题。`🔴高危` `🟡中` `🟢低`。新会话优化时按此排序。

### 🔴 高优先级（影响正确性/可维护性）

| ID | 问题 | 位置 | 影响 |
|---|---|---|---|
| P1-3 | **参数三重定义不一致**：τ 在 constants.py=2.0、value_setpoints.yaml=4.0、parameters.py=4.0。k_+/k_- 同样散落三处 | common/constants.py + config + axiology | 论文复现不可靠，调参时改了一处另一处覆盖 |
| P2-3 | **axiology 严重代码重复**：value_dimensions.py(799行) 与 feature_extractors.py+utilities_unified.py 功能重叠 | axiology/ | 改一处忘另一处，行为不一致 |
| P2-5 | **drives/ 5维驱动力被禁用**：life_loop.py 顶部注释禁用，但代码存在 | axiology/drives/ | 死代码或半成品，需决策启用/删除 |
| P1-4 | **两套配置加载体系并存**：config.py(load_config→dict) vs config_manager.py(ConfigManager→对象)，且都有 load_config() 同名函数 | common/ | 极易混淆，维护负担 |
| P8-4 | **GlobalState 与 FieldStore 双真相源**：7 个情感标量字段同时存于两处，靠 life_loop 手工 `_sync_*` 同步 | core/state.py + core/stores/fields.py + life_loop.py | 两套真值，动 mood/stress 必须两边改，遗漏即不一致 |
| P8-10 | **多轮 CHAT 响应被覆盖**：`llm_response = round_response`(注释却写"累积")，前几轮正文丢弃 | core/handlers/action_executor.py:342 | 多轮工具调用场景用户只能看到最后一轮文字 |
| P8-11 | **tool/tool_id 键不一致**：gap_detector 读 `params["tool"]`，executor 读 `params["tool_id"]` | core/handlers/{gap_detector:243,action_executor:505} | USE_TOOL 的能力缺口检查永远拿空值，成长系统不被 USE_TOOL 驱动 |
| P8-7 | **自定义基因被缓存吞掉**：`_get_differentiator()` 用空 config 缓存，legacy `select_organs` 用它，custom_genes 永不生效 | core/differentiate.py | 器官分化配置失效 |
| P8-18 | **6 模块共 ~2793 行孤立代码**：exceptions/scheduler/capability_router 完全死；emotion_decay/exploration/abstract_state 半死 | core/ | core 最大技术债，需决策删除/接入 |
| P3-5 | **Schema/Skill 永不持久化**：life_loop 用 `SchemaMemory()`/`SkillMemory()` 无参构造，shutdown 不调 save_to_disk，巩固产物重启清零 | memory/{schema,skill}.py + core/life_loop.py:190-191 | CLS 第2/3层知识无法跨会话累积，违背论文核心目标 |
| P3-15 | **联想网络无法持久化**：`import_state` 是 `pass` 空实现，EpisodicMemory 重启不重建联想图 | memory/familiarity.py:869 | 重启丢失全部共现/因果/情绪/语义联想链接 |
| P3-22 | **limb_guides/ 导入即崩 + 与 skills/ 逐字节重复**：4 个指南文件类名仍是 FileSkill 等，__init__ 导入 FileOpsGuide 必抛 ImportError→静默禁用整个包 | memory/limb_guides/ | ~600 行死代码（含 P3-22 的副本） |
| P3-6/P3-7 | **嵌入实现散落3处且2处是伪嵌入**：retrieval 用 MD5 伪嵌入、familiarity 用 md5-seed 伪随机，仅 semantic_novelty 有真嵌入 | memory/{retrieval,familiarity,semantic_novelty}.py | 默认后端下语义检索/联想是噪声 |
| P5-6 | **UnifiedOrganManager 是只写死代码**：life_loop 只 `add_builtin_organ` 注册，从不查询/执行；PHASE 7 走 `self.organs` 字典而非统一管理器 | organs/unified_organ.py + core/life_loop.py | 新架构完全无效，growth/plugins"注册为器官"写了等于没写 |
| P5-10 | **驱动力→器官传导链路断裂**：PHASE 4.5 算的 drive_signals/drives_prompt 塞进 context，但 6 个器官的 propose_actions 无一读取它 | organs/internal/* + core/life_loop.py:920-922 | 驱动力信号被算出后无人消费，价值→驱动力→行为链断在最后一步 |
| P5-15 | **LLM 思考被中文关键词降级**：6 器官的 `_parse_llm_thought_to_actions` 用硬编码关键词把 LLM 输出转 Action，LLM 沦为叙事生成器 | organs/internal/*_organ.py | 器官决策权在关键词表而非 LLM；同义词/英文漏匹配→退化默认动作 |
| P5-20 | **immune 否决权/风险评估未接入**：veto_risky_action/assess_action_risk/update_action_trust life_loop 全不调，安全执行被 safety/ 取代 | organs/internal/immune_organ.py | immune 只提 REFLECT 动作，信任校准恒为默认 0.5 |
| P5-21 | **器官学习/项目状态全不持久化**：builder 的 active_projects/task_queue、archivist 的索引、scout/mind 的学习历史重启清零，且 record_* API life_loop 不调 | organs/internal/{builder,archivist,scout,mind}_organ.py | 器官"从经验学习"功能形同虚设 |

### 🟡 中优先级（技术债）

| ID | 问题 | 位置 |
|---|---|---|
| P1-1 | Goal.priority(deprecated float) 与 priority_level(新int) 并存 | common/models.py |
| P2-1 | axiology/__init__.py 含 210 行 fallback UtilityCalculator 兼容类 | axiology/__init__.py |
| P2-2 | compute_weights(纯函数) 与 WeightUpdater.update_weights 逻辑重复 | axiology/weights.py |
| P2-4 | setpoint 管理散落 3 处(setpoints/dynamic_setpoints/axiology_config) | axiology/ |
| P1-7/P1-9 | auth.py(699行)+models/(786行) 多用户 Web 模块疑似过度工程 | common/+models/ |
| P1-8 | database.py 仅 12 行形同虚设，SQLAlchemy 依赖可能可移除 | common/ |
| P8-6 | GlobalState dataclass 默认值与 from_dict 回退值不一致(mood/stress/boredom)，to_dict→from_dict 往返静默改值 | core/state.py |
| P8-9 | abstract_state 抽象层核心转换未实现(to_concrete 忽略参数, stress=1-valence 语义错)，未被接入 | core/abstract_state.py |
| P8-12 | `_call_llm` 不传 timeout，LLM provider 挂起会卡死整个 tick | core/handlers/action_executor.py |
| P8-13 | 未知 ActionType 返回 success:True，分派 bug 被静默 | core/handlers/action_executor.py:87 |
| P8-15 | 进化管道实际空操作：mutation LLM 响应未解析(changes 恒空)→transfer 遍历空→整体 no-op | core/evolution/mutation_manager.py |
| P8-17 | 插件/肢体代码无沙箱 exec（安全）；devour(".") 可读任意文件；flex 黑名单不全 | core/growth/ + core/plugins/ |
| P8-19 | 能力管理三件套碎片化：capability_router 孤立，三者 API 重叠互不引用 | core/capability_*.py |
| P8-20 | 三套重叠"调度"概念：scheduler(死)/autonomous_scheduler(仅chat)/life_loop inline 离线逻辑 | core/ |
| P3-13 | **dream.py(671行) 完全孤立**：DreamDirector/DreamEngine 是 consolidation.DreamConsolidator 的第二套实现，零运行时引用 | memory/dream.py | 决策接入或删除 |
| P3-20 | **personality_encoding.py(624行) 完全孤立**：论文§3.4.4人格调制编码写了但没接进 episodic.append 写入路径 | memory/personality_encoding.py | 论文功能未生效 |
| P3-10 | **巩固证据门虚设**：默认 min_user_confirmations=0，任意非CHAT action 即满足"强证据"；检查的 user_confirmed/rating/feedback 字段在 EpisodeRecord 不存在 | memory/consolidation.py | 高影响洞察的证据验证形同虚设 |
| P3-1/P3-2 | **持久化逻辑绕开 JSONLWriter 重写3套**：episodic/schema/skill 各自 orjson/json 手写，且 episodic 每 tick 一次 open/append/close | memory/{episodic,schema,skill}.py | IO 开销 + 序列化行为不一致 |
| P3-21 | **剪枝/索引逻辑三套重叠**：pruning.py 通用版 + 各记忆类内置版 + consolidation._prune_episodes；indices.py 与 EpisodicMemory 内置索引重复 | memory/{pruning,indices}.py + memory/{episodic,schema,skill}.py | 维护负担 |
| P3-9 | **smart_retrieval 的 LLM 决策(ai_decide_retrieval)是死代码**，永远走规则；SEMANTIC/BASIC 关键词表重叠 | memory/smart_retrieval.py | 检索决策质量受限 |
| P3-18 | **EmbeddingConfig.auto_detect_backend 形同虚设**：实例方法误用 cls 参数名，默认 backend=TFIDF；当前环境无 embedding API | memory/semantic_novelty.py | 默认走浅嵌入(TF-IDF) |
| P3-14 | compute_novelty 模块函数(关键字参)与 SemanticNoveltyCalculator 方法(参数名不同)两种调用风格+两套参数名，dream.py 走函数版(每次新建calc) | memory/{dream,semantic_novelty}.py | 维护易错 |
| P3-16 | familiarity 默认嵌入是 md5-seed 的确定性伪随机(randn)，联想网络的"语义联想"是噪声 | memory/familiarity.py | 联想质量退化 |
| P5-12 | **OrganSelector/OrganInterface 完全孤立(仅测试)**：实际器官选择走 core/differentiate(基因) + life_loop(价值权重)，这是第三套被取代的版本 | organs/{organ_selector,organ_interface}.py |
| P5-9 | **驱动力器官半禁用矛盾**：drives/ 在 life_loop 顶部注释禁用，但 OrganManager 独立 import 仍实例化 5 个 Drive 并每 tick 调用 | organs/organ_manager.py + axiology/drives/ |
| P5-1 | OrganMemoryWriter 接入但条件脆弱：依赖 _init_organ_llm_manager 成功，organ_llm.memory.enabled=false 或初始化异常则器官思考静默不入记忆 | organs/organ_llm_session.py + core/life_loop.py |
| P5-4 | LLM 失败无降级信号：organ think() 失败返回空串→静默 fallback 规则，无日志/指标区分"走LLM"还是"降级规则" | organs/organ_llm_session.py + organs/internal/* |
| P5-2 | 共享大脑模式历史稀释 6 倍：6 器官共享单一 _history(20轮)，每器官实际只 ~3 轮上下文 | organs/organ_llm_session.py SharedBrainSession |
| P5-3 | OrganLLMSession.think 不解析 reasoning_content，step-3.7-flash 推理内容被丢弃 | organs/organ_llm_session.py |
| P5-13/P5-14 | 两个同名 Limb 类(Docker肢体 vs 代码肢体)；organs/limbs/Limb mount 是 TODO 模拟、execute 恒失败 | organs/limbs/__init__.py + organs/unified_organ.py |
| P5-16 | 6 器官规则模式(_propose_actions_impl)是 LLM 启用时的冷路径死代码，每器官大半代码不执行 | organs/internal/*_organ.py |
| P5-19 | scout/mind 的 _extract_topic_from_thought 用 split() 按空格分词，中文无空格→主题变整段句子 | organs/internal/{scout,mind}_organ.py |
| P5-22 | archivist 器官与 memory/consolidation+pruning 职责三重重叠，只提 REFLECT 动作，本地计数器与真实 EpisodicMemory 不同步 | organs/internal/archivist_organ.py |
| P5-17 | _should_respond_to_user 检查 obs.type=="user_chat"，需对齐 Observation.type 实际值，否则用户消息永不触发 CHAT | organs/internal/mind_organ.py |

### 🟢 低优先级（清理项）

| ID | 问题 | 位置 |
|---|---|---|
| P1-2 | Goal.is_expired 参数 current_tick 未使用 | common/models.py |
| P1-6 | error_handler 与 utils.retry_on_failure 重试逻辑重复 | common/ |
| P8-1 | life_loop.py:48 与 :71 重名导入 CapabilityManager，前者死导入 | core/life_loop.py |
| P8-2 | life_loop_backup.py(2565行) 比正本还大，疑似可删 | core/life_loop_backup.py |
| P8-3 | TickContext 无器官分化结果字段，与"贯穿所有阶段"设计意图不符 | core/tick.py |
| P8-5 | update_body 每 tick 调 psutil.cpu_percent(interval=0.1) 阻塞 100ms | core/state.py |
| P8-8 | life_loop 每 tick 新建 Differentiator(仅用 advance_stage)，默认基因重复注册 | core/life_loop.py:1015 |
| P8-14 | MetabolicLedger.from_dict 不恢复 unlimited 标志；FieldStore 初始值硬编码非配置驱动 | core/stores/{ledger,fields}.py |
| P8-16 | limb_builder.list_limbs 按 label 过滤但 deploy 从不设 label，恒返回空 | core/growth/limb_builder.py |
| P3-3 | `_persist_episode` 用 print 调试输出而非 logger，每条 episode 都打印 | memory/episodic.py |
| P3-4 | schema_id 用 claim+scope 哈希，文字微差产生新 id 撑爆容量；模板 claim 的 reward 微变即新建 | memory/schema.py |
| P3-8 | retrieve_episodes 与 retrieve_by_semantic_similarity 两套语义检索入口重叠 | memory/retrieval.py |
| P3-11 | `_extract_skills` 只存单条 action 快照(非真序列)，skill 名按 action_type 去重导致同类型只留首条 | memory/consolidation.py |
| P3-12 | `_prune_episodes`(阈值0.3) 与 `_sample_episodes`(质量阈值) 两处阈值语义不同易混 | memory/consolidation.py |
| P3-17 | 模块级 `compute_novelty` 每次调用 new 一个 calculator，缓存全失效/重复加载模型 | memory/semantic_novelty.py |
| P3-23 | skills/ 内有两个 SkillRegistry 类(base.py 非线程安全 + skill_registry.py 线程安全)，前者76行死代码 | memory/skills/base.py |
| P3-19 | compute_salience 仅被 consolidation 用；写入 episode 时不存 salience 字段，query_high_salience 另用 \|delta\|——两套"显著性"定义 | memory/salience.py |
| P5-5 | OrganMemoryWriter._llm_evaluate 用 find("{")/rfind("}") 提取 JSON，多 JSON 块/代码块含{} 会误提取；summary[:200] 与 thought[:500] 截断不一致 | organs/organ_llm_session.py |
| P5-7/P5-8 | Limb/Plugin.propose_actions 恒返回[]；6 真器官用 WrappedBuiltinOrgan 动态子类重复创建6次且丢失 _llm_session 等属性 | organs/unified_organ.py + core/life_loop.py |
| P5-11 | OrganManager.record_exploration 直接访问私有 _explored_topics，与 ScoutOrgan 同名字段完全独立，探索记录分散两处 | organs/organ_manager.py |
| P5-18 | mind 的 record_plan_outcome/successful_patterns 学习机制 life_loop 不调，_adapt_from_history 永不触发 | organs/internal/mind_organ.py |
| P5-23 | caretaker sleep 时间窗靠 tick×tick_duration/3600 估算，context 是否传 tick_duration 不确定；与 metabolism/circadian 真实节律可能不一致 | organs/internal/caretaker_organ.py |

---

## B. 新会话上手指南

### 如何使用本文档
1. **开新会话时**：对 AI 说"读 CODE_MAP.md，继续写第 X 章"（X 见下方路线图）
2. **优化某个模块时**：先读对应章节 + A 节相关问题，再动手
3. **调试运行时问题时**：先看"0.项目概览"的 tick 流水线，定位问题在哪个阶段

### 续做路线图（按推荐顺序）
```
新会话1: "读 CODE_MAP.md，续写第8章 core/"     ✅ 已完成
新会话2: "读 CODE_MAP.md，续写第3章 memory/"   ✅ 已完成
新会话3: "读 CODE_MAP.md，续写第5章 organs/"   ✅ 已完成
新会话4: "读 CODE_MAP.md，续写第6章 tools/"   ← 下一个推荐
新会话5: "读 CODE_MAP.md，续写第4章(认知感知代谢)+第7章(安全持久化)"
新会话6: "读 CODE_MAP.md，续写第9章(入口Web) + 更新A节问题清单"
```
每章续写后，AI 应：①填充"待续"章节 ②如发现新问题追加到 A 节 ③更新本文件顶部的"最后更新"日期。

### 快速验证环境（任何会话开始前）
```bash
cd .../GitHub/GenesisX
cat .env          # 确认 LLM 配置（当前 stepfun step-3.7-flash）
git status        # 确认工作区干净
python run.py --ticks 1   # 冒烟测试，确认能跑
```

### 当前运行环境快照（2026-07-06）
- **LLM**: stepfun step-3.7-flash（OpenAI 兼容，`https://api.stepfun.com/step_plan/v1`）
- **LLM_MAX_TOKENS**: 8000（推理模型需要更大输出空间）
- **CHAT_TIMEOUT**: 180s（推理模型较慢）
- **ORGAN_PARALLEL_MODE**: mixed（器官混合并行）
- **session_id**: genesisx_persistent（记忆跨重启累积）
- **注意**: step-3.7-flash 是推理模型，响应含 `reasoning_content`，正式回答在 `content`。默认思考模式关闭。

---

*文档状态：Phase 1-2(common/axiology/affect, 46文件/14k行) + Phase 8(core/, 43文件/18338行) + Phase 3(memory/, 29文件/8733行) + Phase 5(organs/, 15文件/7956行) 已完成精读。Phase 4,6,7,9 待续。全局问题清单已收录 14 + 20 + 23 + 23 = 80 项（P1/P2/P3/P5/P8 系列）。*


