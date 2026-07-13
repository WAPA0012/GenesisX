# GenesisX 代码地图与技术说明

> **文档目的**：供 AI/开发者在新会话中快速建立对整个项目的精确认知，直接进入优化工作。
> **覆盖范围**：逐模块、逐文件梳理 242 个 Python 文件（约 84k 行），标注设计意图、数据流、模块耦合与潜在问题。
> **生成方式**：通读源码 + 论文对照，标注 `🔍问题` 为值得后续迭代的点。
> **版本基准**：v1.3.0，5 维价值系统（已从早期 9 维精简）。
> **最后更新**：2026-07-06
> **进度**：✅ 第1-2章已完成精读（46文件/14k行） ✅ 第8章 core/ 已完成精读（43文件/18338行） ✅ 第3章 memory/ 已完成精读（29文件/8733行） ✅ 第5章 organs/ 已完成精读（15文件/7956行） ✅ 第6章 tools/ 已完成精读（23文件/9837行） ✅ 第4章 cognition/perception/metabolism 已完成精读（20文件/5430行） ✅ 第7章 safety/persistence 已完成精读（13文件/2604行） ✅ 第9章 入口+Web 已完成精读（15文件/约7k行）—— **全章精读完成，A 节问题清单 242→260 项**

---

## 目录

- [0. 项目概览与心智模型](#0-项目概览与心智模型)
- [1. 基础层 `common/` + `models/`](#1-基础层-common--models) ✅
- [2. 核心理论层 `axiology/` + `affect/`](#2-核心理论层-axiology--affect) ✅
- [3. 记忆层 `memory/`](#3-记忆层-memory) ✅
- [4. 认知/感知/代谢 `cognition/` + `perception/` + `metabolism/`](#4-认知感知代谢) ✅
- [5. 器官层 `organs/`](#5-器官层-organs) ✅
- [6. 工具层 `tools/`](#6-工具层-tools) ✅
- [7. 安全 + 持久化 `safety/` + `persistence/`](#7-安全--持久化) ✅
- [8. 核心引擎 `core/`](#8-核心引擎-core-最重要) ✅
- [9. 入口 + Web `lifecycle/` + `web/` + 顶层脚本](#9-入口--web) ✅
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

**✅问题 P1-4 已修**：~~存在**两套配置加载体系**~~。经全项目 grep 确认：`config.py:load_config()`(返回 dict) 是唯一 active 路径，被 run.py / web/app.py / chat_interactive.py / daemon.py 全部 4 个入口及 `common/__init__.py` 导出使用；`config_manager.py:ConfigManager`(返回 GenesisXConfig 对象) **零引用**（连 tests 都未引用，对应生产配置文件 default.yaml/production.yaml 也不存在）。已外科手术式删除 `config_manager.py`（509 行死代码），消除同名 `load_config()` 混淆。`config.py` 的 Pydantic 模型定义与 .env 加载逻辑未动。

### 1.4 `common/logger.py` (356行)
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

## 4. 认知/感知/代谢 `cognition/` + `perception/` + `metabolism/`

> 20 文件/约 5430 行，覆盖论文 §3.2（状态/感知/资源压力）+ §3.5（认知目标编译）+ §3.6.4（优先级覆盖/无聊门控）+ §3.8.2-3（目标协调）+ §3.9.3（规划评估）+ §3.11（动作验证）+ Appendix A.3（代谢）。这三层是 value→action 之间的"中间层"——把价值缺口编译成目标、把目标评估成动作、把生理状态/环境信号采集给价值系统。
>
> **本章最大发现**：**三个子包都呈现"半接线、半遗留"状态**——cognition 的 4 个核心模块（goal_compiler/plan_evaluator/verifier）接入 life_loop，但 planner 和整套 goal_progress 是死的；perception 8 个文件里只有 observer + context_builder 真正接入（其余 90% 行数是死代码）；metabolism 里 recovery.py 整体死、resource_pressure.py 与 core/state.py **公式语义相反**。详见 4.x 速查。
>
> **目录结构**：
> ```
> cognition/ (7 文件/2079 行)
> ├── goal_compiler.py    (771) ⭐ PHASE 6 目标编译+冲突协调(唯一全接入)
> ├── goal_progress.py    (562) 🔍 进度计算+GoalTracker(整模块死代码)
> ├── planner.py          (296) ⚠️ 计划生成(life_loop 绕过,仅 blackboard 用)
> ├── plan_evaluator.py   (137) ⭐ PHASE 8 J(p|S_t) 评分(接入)
> ├── insight_quality.py  (206) 🔍 Q^insight(死代码,被 consolidation 版取代)
> ├── verifier.py         (83)  ⭐ PHASE 9b 安全验证(接入)
> └── __init__.py         (24)
>
> perception/ (8 文件/1675 行)
> ├── observer.py         (48)  ⭐ PHASE 2 唯一观察入口(接入)
> ├── context_builder.py  (109) ⭐ PHASE 4 context dict 装配(接入)
> ├── self_perception.py  (491) 🔍 自我感知(工具注册未分发→断链)
> ├── time_perception.py  (247) 🔍 时间感知(未集成,与 circadian/caretaker 三重重复)
> ├── command_parser.py   (276) 🔍 用户命令解析(被 chat_handler 路径绕过)
> ├── novelty.py          (226) 🔍 新奇度(被 memory/semantic_novelty 取代)
> ├── signal_filter.py    (222) 🔍 信号过滤(完全未接入)
> └── __init__.py         (56)
>
> metabolism/ (5 文件/918 行)
> ├── circadian.py        (287) ⚠️ 24h 昼夜节律(2 个方法被 PHASE 1 用,与 caretaker 时间源冲突)
> ├── resource_pressure.py(256) 🔴 RP_t(与 state.py 公式语义相反!)
> ├── boredom.py          (152) ⚠️ 无聊度 η-系数(PHASE 1 调用但丢 4/7 参数)
> ├── recovery.py         (173) 🔴 整模块死代码(PHASE 1 用内联公式绕过)
> └── __init__.py         (50)
> ```

### 4.0 三子包在 tick 流水线中的位置

```
PHASE 1 _update_body     ← metabolism/{boredom,circadian}      ⚠️ 半接入
PHASE 2 observe_env      ← perception/observer                 ✅ 接入
PHASE 3 retrieve         ← memory/(见第3章)
PHASE 4 build_context    ← perception/context_builder          ✅ 接入
PHASE 5 axiology         ← (见第2章)
PHASE 6 goal_compile     ← cognition/goal_compiler             ✅ 接入
PHASE 7 organ propose    ← organs/(见第5章)
PHASE 8 plan_evaluate    ← cognition/plan_evaluator            ✅ 接入
PHASE 9a-9e safety       ← cognition/verifier(9b) + safety/(见第7章, 9a/9c/9d)
PHASE 10 execute         ← action_executor
```

---

### 4.1 `cognition/` (7 文件) — 规划/目标/验证

#### 4.1.1 `goal_compiler.py` (771行) ⭐ PHASE 6 目标编译核心
**职责**：`GoalCompiler`——把价值缺口（gaps）+权重（weights）+状态编译成可执行目标，含冲突协调。论文 §3.8 的落地。**cognition 包里唯一全接入的模块**。

**关键类**：
- `GoalProgressConfig`（L11-69）：进度参数 dataclass，含 `from_global_config()`（L49）——但**运行时只用默认 ctor**（L113），config 从未注入。
- `GoalCompatibility`（L72-79）：`status ∈ {compatible, conflicting, sequential}`。
- `CoordinationStrategy`（L83-88）：`strategy_type ∈ {priority, time_slice, sequential, parallel}`。
- `GoalCompiler`（L91-771）：主类。字段 `goal_templates`（L110）、`compatibility_cache`（L111，**死字段**）、`progress_config`（L113）。

**关键方法**（带 life_loop 调用关系）：
| 方法 | 行 | 用途 | 接入？ |
|---|---|---|---|
| `_init_goal_templates` | L115 | 5 个 `ValueDimension` → 目标模板映射 | 内部 |
| `compile_multi_goal` | L703 | ⭐ **life_loop.py:993 的入口**——多目标编译（≤3 个兼容目标） | ✅ 接入 |
| `_generate_candidates` | L187 | `ρ = base_priority × gap × weight`，跳过 `gap<0.15` | 内部 |
| `_select_goal` | L228 | 两阶段选择：Top-K=5 → 期望收益 `priority·(1+gap_urgency)·(1+weight) − cost·0.01` | 内部 |
| `select_compatible_goals` | L607 | 贪心最大兼容集（论文 G*） | 内部 |
| `check_compatibility` | L387 | 冲突矩阵（论文 §3.8.3） | 内部 |
| `compile` | L156 | 单目标编译——**life_loop 不调，走多目标版** | 🔍 仅测试 |
| `compute_progress` | L309 | 8 种目标类型的 `Prog(g,S)` | 🔍 **仅测试**（P4-2） |
| `assess_gap_urgency`/`get_coordination_plan` | L525/L743 | 紧迫度/协调计划 | 🔍 仅测试 |

**life_loop PHASE 6 数据流**（life_loop.py:993-1008）：
```
gaps/weights/field_snapshot  ──► compile_multi_goal(owner="self", max_goals=3)
                                     ↓
                              ≤3 个 Goal 对象
                                     ↓
slots.set("current_goal", goals[0]); slots.set("active_goals", goals)
context["goal"] = goal.description  (字符串，喂 LLM/器官)
```

**🔍问题 P4-1（🔴 高，priority_level 全域未设置）**：`GoalCompiler` 只写 **deprecated 的旧字段 `Goal.priority`**（L212/L292，float 0-1），**从不写 `priority_level`**（models.py:160 注释明确的 1-6 级新枚举 `CRITICAL..OPTIONAL`，论文 §3.8.1）。全项目 grep `priority_level=` 在 cognition/ 全空。**结果：论文的 6 级优先级系统在运行时完全不生效，所有 Goal 恒为 `MEDIUM(3)` 默认值**。配合第1章 P1-1（旧 priority 仍被读取），整个优先级体系是断裂的。
**🔍问题 P4-2（🟡 中，目标进度永不更新）**：`compute_progress`（L309，77 行覆盖 8 种目标类型）**life_loop 从不调用**——goal.progress 停在编译时初值 0.0，整个 PHASE 6+ 之后无反馈循环。配合 P4-22（goal_progress.py 也是死代码），目标进度跟踪体系整体失效。
**🔍问题 P4-3（🟡 死代码）**：`assess_gap_urgency`（L525）、`get_coordination_plan`（L743）、`compile`（L156 单目标版）均无运行时调用。
**🔍问题 P4-4（🟡 重复）**：进度计算有两套并行实现——`GoalCompiler.compute_progress`（字符串分派）vs `goal_progress.ProgressCalculator.calculate`（枚举分派）。**两套都没接入 life_loop**。
**🔍问题 P4-5（🟢 魔数）**：`gap<0.15` 跳过（L198）、Top-K=5（L252）、cost penalty ×0.01（L280）、资源冲突阈值 0.1（L488）、`epsilon_priority=0.1`（L566）——全硬编码，无 config 入口。
**🔍问题 P4-6（🟢 死字段）**：`compatibility_cache`（L111）初始化后**从不读写**。

#### 4.1.2 `planner.py` (296行) ⚠️ 计划生成器（life_loop 绕过）
**职责**：`Planner`——生成候选计划。docstring 自称"LLM-based"，但**实际 `propose_plans` 是纯规则**（`if/elif` 梯子），LLM 路径 `propose_with_llm`（L159）**零运行时调用**。

**关键**：
- `Plan(Dict)`（L15-24）：薄字典子类，键 `actions/reasoning/estimated_reward/estimated_cost/dimension`。
- `Planner`（L27-296）：字段 `llm`(默认 None)/`timeout=30.0`(CognitionConstants)/`max_retries=3`。
- `propose_plans`（L52）：**规则版**——按 goal 字符串走 8 个 `if/elif` 分支（如 `goal=="rest_and_recover"` → 单个 SLEEP 动作），每个分支只产 1 个 plan。
- `propose_with_llm`（L159）：LLM 路径，带 ThreadPoolExecutor 超时 + 重试。**死代码**。

**🔍问题 P4-7（🔴 高，集成断裂 + LLM 死路径）**：**life_loop PHASE 8 完全不调 Planner**——它在 life_loop.py:1189-1192 把器官提案的 actions 内联包成 `[{"actions":[a],"estimated_reward":0.5,"estimated_cost":100.0}, ...]` 直接喂给 PlanEvaluator。Planner 的唯一运行时调用者是 `tools/blackboard.py`（M_REASON 专家，L512/L784），但黑板默认休眠（见第6章），且即便启用，M_REASON 拿到的是规则版 plan（不是 LLM 版），且只写成 context 字符串不执行。**即 docstring 宣传的"LLM-based planner"是死的**。
**🔍问题 P4-8（🟡 类型不匹配）**：`propose_plans(goal: str)` 接收字符串，但 `GoalCompiler` 产出 `Goal` 对象（`.goal_type`）。blackboard 传 `current_goal` 可能是 `"respond_to_user"`——planner 的 if/elif 不认这个，落到默认 CHAT 分支。
**🔍问题 P4-9（🟡 plan dict shape 不一致）**：Planner 产的 plan 含 `dimension` 字段，life_loop 内联的不含。`PlanEvaluator._score_plan`（L108 `plan.get("dimension", None)`）必须两边兼容——结果 life_loop 的 plan 总走"generic plan"分支（L116-117），planner 的走维度加权分支（L111-112），评分逻辑不一致。
**🔍问题 P4-10（🟢）**：`num_plans` 参数（L58）无效——每分支只产 1 个 plan，`plans[:num_plans]` 恒返回 1 个。
**🔍问题 P4-11（🟢）**：L232 `import signal` 未使用（早期基于信号的超时残留）。

#### 4.1.3 `plan_evaluator.py` (137行) ⭐ PHASE 8 评分核心
**职责**：`PlanEvaluator`——按论文 §3.9.3 的价值函数 `J(p|S_t)` 评分并选最优。**PHASE 8 的活路径**。

**评分公式**（`_score_plan` L72-135）：
```
J(p|S_t) = weighted_value − λ_cost·Cost(p) − λ_risk·Risk(p) − budget_penalty
```
- **weighted_value**（L107-119）：plan 有匹配的 `dimension` → `weights[dim]·n_dims·estimated_reward`；否则 `max(weights)·n_dims·estimated_reward`（`n_dims=len(weights)` 补偿 Σw=1 归一化）。
- **λ_cost=0.001**（L122 魔数）、**λ_risk=0.5**（L126 魔数）。
- **budget_penalty=2.0**（L132 硬约束）：当 `estimated_cost > budget_remaining`。

**life_loop PHASE 8 数据流**（life_loop.py:1196-1206）：
```
plans = [{"actions":[a],...} for a in proposed_actions]
budget_remaining = (1.0 − ledger.normalize_all()["cpu_tokens"]) × 100000   ← 放大 100000 倍
scored = evaluator.evaluate_plans(plans, {dim.value: w}, budget_remaining)
best_score, best_plan = scored[0]; selected_action = best_plan["actions"][0]
```

**🔍问题 P4-12（🟡 风险惩罚形同虚设）**：`_score_plan` 读 `action["risk_level"]`（L99-101）算 `total_risk`，但 life_loop 内联的 plan dict（L1190）包 `Action` 对象时**不复制 risk_level**（Action 默认 risk_level=0.0）——结果 `total_risk` 恒为 0，`λ_risk·Risk` 项是 no-op。
**🔍问题 P4-13（🟡 预算惩罚失效）**：life_loop 把 `cpu_remaining_fraction × 100000`（L1199）传给 `budget_remaining`，而 plan 的 `estimated_cost` 才 10-300 量级——`estimated_cost > budget_remaining`（L131）几乎永不触发，`budget_penalty` 退化为死分支（除非资源 100% 耗尽）。
**🔍问题 P4-14（🟢 魔数）**：`λ_cost=0.001`/`λ_risk=0.5`/`budget_penalty=2.0` 硬编码。
**🔍问题 P4-15（🟢）**：`select_best`（L44）从不被 life_loop 调（它手动 `evaluate_plans` + 取 `[0]`）。

#### 4.1.4 `verifier.py` (83行) ⭐ PHASE 9b 动作验证
**职责**：`Verifier`——执行前的轻量安全门，4 个顺序检查。论文 §3.11。

**`verify_action(action, state, capabilities)` → `{ok, error?}`**（L16-65）：
1. **能力**（L33）：`action.capability_req` 全部在 `capabilities` 列表里。
2. **模式**（L41）：sleep 模式禁 `risk_level>0.1`。
3. **能量**（L49）：`energy<0.2` 禁 EXPLORE/LEARN_SKILL。
4. **压力**（L57）：`stress>0.7` 禁 `risk_level>0.5`。

**life_loop PHASE 9b**（life_loop.py:1248-1262）：失败时按 **error 字符串子串匹配**路由 fallback（"energy"→SLEEP、"stress"→REFLECT、其他→REFLECT）。

**🔍问题 P4-16（🟡 脆弱耦合）**：fallback 路由靠 `if "energy" in result["error"]` 子串匹配 verifier 的英文 error 字符串（life_loop.py:1257-1260）——任何 error 文案改动都会破坏路由。
**🔍问题 P4-17（🟢 魔数）**：`risk>0.1`/`energy<0.2`/`risk>0.5`/`stress>0.7` 全硬编码。
**🔍问题 P4-18（🟢）**：`verify_batch`（L67）从不调用（life_loop 只验证单个 `selected_action`）。

#### 4.1.5 `insight_quality.py` (206行) 🔍 整模块死代码
**职责**：`InsightQualityAssessor`——论文 §3.5.2(7)/§3.10.4 的 Q^insight。**全项目零运行时引用**（仅 `tests/test_insight_quality.py`）。

**Q^insight 公式**（L74-81）：`Q = 0.4·compression + 0.3·transferability + 0.3·novelty`。
- compression（L83-113）：`0.7·ratio + 0.3·efficiency`。
- transferability（L115-144）：英文关键词计数（when/if/then/always/never/should/pattern/strategy/rule）。
- novelty（L146-206）：`C_nov = 1 − max_similarity`，**import `from tools.embeddings import get_embedding, cosine_similarity`**（L168，lazy import），ImportError 时退化为 Jaccard 词汇重叠。

**🔍问题 P4-19（🔴 整模块死代码）**：`InsightQualityAssessor` 零运行时调用。
**🔍问题 P4-20（🔴 Q^insight 三重实现）**：三处实现公式不同：
| # | 位置 | 压缩 | 可迁移性 | 新颖性 | 状态 |
|---|---|---|---|---|---|
| 1 | `cognition/insight_quality.py` | `0.7·ratio+0.3·efficiency` | 英文关键词 | tools/embeddings | 🔴 死 |
| 2 | `memory/consolidation.py` InsightQualityEvaluator | `log(n+1)/log(10)` | `avg_reward` | SemanticNoveltyCalculator | ✅ **活**（PHASE 15） |
| 3 | `eval/gxbs.py` compute_insight_quality | `(C_comp+C_trans+C_nov+C_corr)/4` | — | — | 评测 |
注：consolidation 版注释自称"权重与 insight_quality.py 一致"（0.4/0.3/0.3），但**三个分量算法完全不同**。
**🔍问题 P4-21（🟡）**：transferability 关键词表纯英文，对中文 LLM 输出无效。

#### 4.1.6 `goal_progress.py` (562行) 🔍 整模块死代码
**职责**：进度计算 + GoalTracker（论文 §3.8.1）。**全模块零运行时引用**（仅 `__init__` 重导出）。

**关键类**：`GoalType`(8 值枚举)、`GoalStatus`(6 值)、`ProgressCalculator`(8 个 `calculate_*` 静态方法 + `calculate` 分派器)、`Milestone`、`ProgressCalculatorWithMilestones`、`GoalTracker`（内存 `Dict[str, Goal]`，**无 save/load**）。

**🔍问题 P4-22（🔴 整模块死代码）**：`ProgressCalculator`/`GoalTracker`/`Milestone`/`ProgressCalculatorWithMilestones` 全部零运行时引用。
**🔍问题 P4-23（🔴 分类法冲突）**：三套目标类型系统并存且互不匹配：
| # | 位置 | 类型数 | 例子 |
|---|---|---|---|
| 1 | `goal_progress.GoalType` 枚举 | 8 | MAINTAIN/ACHIEVE/EXPLORE/PRACTICE/REFLECT/SOCIAL/CONTRACT/OPTIMIZE |
| 2 | `goal_compiler` 模板 | 5 | rest_and_recover/strengthen_bond/explore_and_learn/improve_skills/verify_safety |
| 3 | `planner` 字符串 | 8+ | rest_and_recover/.../optimize_resources |
`ProgressCalculator.calculate`（L267）检查 `GoalType.MAINTAIN.value`（"maintain"）等字符串，**永远不匹配** goal_compiler 的 "rest_and_recover"。即便接入也走 default 分支。
**🔍问题 P4-24（🟡 无持久化）**：`GoalTracker._goals` 是内存 dict，无 save/load 方法。
**🔍问题 P4-25（🟢）**：`register_custom_calculator`（L64-97）扩展 API 从未使用。

---

### 4.2 `perception/` (8 文件) — 观察/上下文/感知器

> **核心结论**：8 个文件中只有 `observer.py` + `context_builder.py`（共 157 行）真正接入 life_loop，**其余 6 个（1518 行，90.6%）是死代码/被取代/断链**。perception 包是"早期骨架被后续子系统取代"的典型——novelty 让位 memory/、time 让位 metabolism/、command 让位 handlers/、self_perception 卡在工具分发断链。

#### 4.2.1 `observer.py` (48行) ⭐ PHASE 2 观察入口
**职责**：纯函数 `observe_environment(tick, mode, state, user_input=None) → List[Observation]`——life_loop PHASE 2 **唯一**的感知入口。

**产出 3 种 Observation**：
- `type="user_chat"`（L21-27）：仅当 `user_input` 非空；payload 含 message/source="user"。**（呼应第5章 P5-17：mind_organ `_should_respond_to_user` 检查 `obs.type=="user_chat"`——这里确认字符串对齐，CHAT 路径是通的）**
- `type="heartbeat"`（L30-34）：每 tick 必加。
- `type="body_state"`（L37-46）：从 state 读 `energy/mood/stress/fatigue`。

**接入**：`life_loop.py:815`。注意 life_loop 传的是 `field_snapshot`（fields 快照）而非 `self.state`。

**🔍问题 P4-26（🟢 设计单薄）**：observer 实质只是"状态字典打包成 Observation"，没有真正的环境感知（无外部信号源/传感器抽象）。所谓 PHASE 2"感知环境"实为"状态采样"。
**🔍问题 P4-27（🟡 字段硬编码三处）**：body_state 的 4 键（energy/mood/stress/fatigue）与 `context_builder.py:25-29`、life_loop drive_state（L908-918）三处硬编码重复。

#### 4.2.2 `context_builder.py` (109行) ⭐ PHASE 4 上下文装配
**职责**：`build_context(state, recent_episodes, retrieved_memories) → dict`——PHASE 4 唯一调用，把 state + 检索结果组装成喂 LLM/器官的 context dict。

**context dict 契约**（全系统约定的键）：
| 键 | 来源 | 行 |
|---|---|---|
| `state` | energy/mood/stress/fatigue/boredom/mode | L24-31 |
| `goal` | current_goal（Goal 对象/str/任意→str） | L34-44 |
| `recent_successes`/`recent_attempts` | 最近 10 个 episode 的 reward>0 计数 | L47-53 |
| `retrieved_memories` | episodes[:5] 的 {tick, observation[:100], reward} | L57-98 |
| `retrieved_schemas`/`retrieved_skills` | schemas[:3]/skills[:3] | L82-95 |
| `budget_tokens` | **硬编码 10000** | L106 |
| `recent_errors` | **硬编码 0** | L107 |

**注**：`context["observations"]`（PHASE 4 后追加 L903）、`context["drive_signals"]`/`context["drives_prompt"]`（PHASE 4.5 追加 L921-922）是 life_loop 在 build_context 之外**追加**的，不在本函数内。

**🔍问题 P4-28（🔴 硬编码假数据）**：L106-107 `budget_tokens=10000` / `recent_errors=0` 是写死的占位符（注释明说"Default"/"Simplified"）。若下游有真正的 budget 计算或错误恢复读这两个键，将永远收到固定值——不是"默认值"，是"假数据"。
**🔍问题 P4-29（🟡 切片魔数）**：`episodes[:5]`/`schemas[:3]`/`skills[:3]`/`recent[-10:]`/`observation[:100]` 全内联魔数。
**🔍问题 P4-30（🟢 脆弱序列化）**：L65 `str(ep.observation.payload)` 假设 payload 可 str 化，含 datetime/numpy 时会带 `__repr__` 噪音。

#### 4.2.3 `self_perception.py` (491行) 🔍 最大文件——工具注册未分发（断链）
**职责**：`SelfPerception`——读自身日志、感知系统资源（CPU/内存/磁盘）、算 HOMEOSTASIS 压力分。注释（L8）声称"配合 axiology/homeostasis"。

**两类能力**：
- **日志类**：`read_own_logs(log_file, lines, level, since, search)`（L41）、`get_recent_errors(hours, limit)`（L253）、`_summarize_logs`（L198，level_counts/top_modules）。
- **资源类**：`system_stats() → dict`（L273，cpu_percent/memory/disk/process/uptime/platform/**pressure_score**/timestamp）、`get_health_status()`（L410，pressure<0.3 healthy/<0.6 moderate/<0.8 high_load/else critical）。

**压力公式**（`_calculate_pressure_score` L373）：`0.3·cpu_pressure + 0.4·memory_pressure + 0.3·process_memory_pressure`，process_memory 压力 = `min(mb/1000, 1)`（1GB 阈值）。

**接入**：🔴 **严重断裂**。`tools/tool_registry.py:104,115` **注册**了 `tool_id="read_own_logs"` 和 `tool_id="system_stats"`（capabilities_required=["self_awareness"]），**但 `tools/tool_executor.py` 的分发链（L257 tool_mapping → L326+ `if function_name == ...`）只有 read_file/write_file/list_directory/web_search/execute_code 5 个分支，无 read_own_logs/system_stats**。全项目 grep `read_own_logs\b` 的可调用命中只在 self_perception.py 自身和 `__init__.py`。

**🔍问题 P4-31（🔴 broken integration——工具断链）**：`read_own_logs`/`system_stats` 是 self_perception 唯一对外接口，却卡在"注册未分发"。LLM 即便选这两个 tool_id，executor 也找不到 handler → 静默失败。**这是 self_perception 实质死代码化的根因。**
**🔍问题 P4-32（🟡 pressure_score 未回流）**：`_calculate_pressure_score` 专为 HOMEOSTASIS 设计（L378 注释），但 pressure_score 只存在 system_stats 返回值里，**无代码写入 state/fields**——axiology 的 homeostasis 维度读不到。设计意图与实现脱节。
**🔍问题 P4-33（🟡 魔数）**：权重 0.3/0.4/0.3、1GB 阈值、健康分档 0.3/0.6/0.8 全硬编码。
**🔍问题 P4-34（🟢 撞名）**：`get_health_status()` 与 `caretaker_organ.py:582` 同名方法返回结构不同，易混。
**🔍问题 P4-35（🟢 磁盘路径）**：L308 Windows 用 `expanduser("~")` 测盘，多盘机器可能不是程序所在盘。

#### 4.2.4 `time_perception.py` (247行) 🔍 未集成——与 circadian/caretaker 三重重复
**职责**：`TimePerception(timezone="Asia/Shanghai")`——当前时间/时段/季节的自然语言 + 结构化感知。

**时段分桶**（`get_time_context` L67）：dawn5/morning8/noon12/aft14/eve18/night22（6 段）+ weekday/is_weekend/month/season(北半球固定)/day_of_year。`_natural_time`（L125）中文输出。

**接入**：⚠️ 零导入（除 `__init__` try/except 兜底）。

**🔍问题 P4-36（🔴 三重时段分桶 + 未回流）**：一天内的时间划分在系统内有 **3 个独立实现**，边界互不一致：
| 实现 | 时段边界 | 时间源 | 接入？ |
|---|---|---|---|
| `perception/time_perception.py:79` | dawn5/morning8/noon12/aft14/eve18/night22 (6 段) | `datetime.now()` Asia/Shanghai | 🔴 未集成 |
| `metabolism/circadian.py:130` | morning6/afternoon12/evening18/night22 (4 段) | `datetime.now(timezone.utc)` | ⚠️ 半接入 |
| `organs/caretaker_organ.py:66` sleep window | sleep_start=22 / sleep_end=7（跨午夜） | `tick·tick_duration/3600%24` | ⚠️ 器官内部 |
三者互不引用。
**🔍问题 P4-37（🟡 时区不一致）**：time_perception 用 Asia/Shanghai；circadian 用 UTC；caretaker 用 tick 推算。同一时刻三个模块可能报不同时段。
**🔍问题 P4-38（🟢 死字段）**：`_cached_time`（L26）声明后从未读写，TTL 缓存机制形同虚设。
**🔍问题 P4-39（🟢 北半球硬编码）**：season 逻辑固定北半球。

#### 4.2.5 `command_parser.py` (276行) 🔍 被绕过
**职责**：`CommandParser`——从用户文本提取 tool_call/goal_set/query/feedback/meta（斜杠命令）。

**集成**：🔴 **零实例化**。life_loop 从 `get_user_input()` 直接拿原始字符串喂 observer，**不经过 CommandParser**。

**🔍问题 P4-40（🔴 死代码 + 入口被绕过）**：用户输入真实路径是 `get_user_input() → user_input 字符串 → observer(user_chat) → build_context`，CommandParser 完全不在路径上。斜杠命令 /reset /save、tool_call 提取均无此解析器参与。
**🔍问题 P4-41（🟡 与 chat_handler 重叠 + 中文盲区）**：① 与 `core/handlers/chat_handler.py` 用户消息处理职责重叠但互不调用。② tool/goal 正则**全为英文**（`use X tool`/`I want to`/`please`），对一个中文数字生命项目几乎无法命中。
**🔍问题 P4-42（🟢 魔数）**：tool_call=0.7/goal_set=0.8/query=0.5/meta=1.0 优先级阶梯硬编码。

#### 4.2.6 `novelty.py` (226行) 🔍 被 memory/semantic_novelty 取代
**职责**：`NoveltyDetector`——基于内容哈希 + embedding 余弦距离的新奇度打分 [0,1]。

**集成**：🔴 **全代码库零实例化**。tests 测 novelty 用的是 `memory.semantic_novelty.SemanticNoveltyCalculator`。

**🔍问题 P4-43（🔴 死代码 + 新奇度三重实现）**：新奇度计算 3 套：
1. `perception/novelty.py` `NoveltyDetector`——**未集成**
2. `memory/semantic_novelty.py` `SemanticNoveltyCalculator`（threshold=0.85）——**活**（被 axiology/cognition/dream 用）
3. `axiology/feature_extractors.py` `_compute_semantic_novelty`——内部 fallback 调 #2
perception 版是早期废弃实现。
**🔍问题 P4-44（🟡 阈值不一致）**：`high=0.7/low=0.3/decay=0.95` 与 `axiology/parameters.py:193 low_novelty_threshold=0.20`、`cognition/goal_compiler.py:39 novelty_target=1.0` 三处不一致。

#### 4.2.7 `signal_filter.py` (222行) 🔍 死代码
**职责**：`SignalFilter`——基于优先级队列的输入过载保护 + 去重 + 节流（论文 3.2 "SignalBus with half-life decay"）。

**集成**：🔴 零实例化。observer 直接产 Observation 进 ctx，**无优先级过滤层**。

**🔍问题 P4-45（🔴 死代码 + 论文半衰期未实现）**：注释（L20-22）提及半衰期衰减，但代码只有 `dedup_window=5.0s` 简单去重，**无 priority 衰减逻辑**。且 `Signal` 别名（L57）与 `core/stores/signals.py` 的 `Signal` 类命名冲突（注释自承，靠别名兜底反而增加混淆）。
**🔍问题 P4-46（🟡 魔数）**：`max_signals=10`/`dedup_window=5.0`/`maxlen=100`/`min_priority=0.1`/`overload=0.8` 全默认值。

#### 4.2.8 `__init__.py` (56行) 包门面
**🔍问题 P4-47（🟡 静默降级掩盖问题）**：Time/SelfPerception 用 `try/except ImportError` 兜底，依赖缺失时置 None 但**不警告**，运行期才暴露 AttributeError。

---

### 4.3 `metabolism/` (5 文件) — 昼夜节律/恢复/无聊

> **核心结论**：5 文件中只有 boredom（半个，参数丢失）和 circadian（2 个方法）被 life_loop 调用；**recovery.py 整体死、resource_pressure.py 与 core/state.py 公式语义相反**、METABOLISM 常量整段失效。

#### 4.3.1 `__init__.py` (50行) ⚠️ 死别名
**🔍问题 P4-48（🟡 死 re-export）**：`rp_compute_effective_boredom`（L17）全仓库零引用；`update_stress`（L25 导出）零经 metabolism 路径引用——`life_loop.py:44` 直接 `from affect.stress_affect import update_stress`。两处死代码。
**🔍问题 P4-49（🟡）**：`__all__` 导出 `compute_recovery_rate/needs_recovery/suggest_recovery_mode/RecoveryConfig`，但 recovery.py 在生产代码零调用（P4-53）。

#### 4.3.2 `boredom.py` (152行) ⚠️ η-系数无聊度（PHASE 1 调用但丢参数）
**职责**：论文 Appendix A.3 无聊度更新 + §3.6.4 资源门控的"有效无聊度"。

**公式**（`update_boredom` L63-123）：
```
Boredom_{t+1} = clip[0,1]( Boredom_t + η_idle·1[novelty<0.2]·dt
                          − η_nov·Novelty_t·dt
                          − η_soc·1[social]·dt )
effective_boredom = Boredom · 1[RP_t < θ_emergency]    # 紧急时返回 0
```
`BoredomConfig` 类常量：`ETA_IDLE=0.03`(L25)、`ETA_NOV=0.20`(L28)、`ETA_SOC=0.05`(L31)、`LOW_NOVELTY_THRESHOLD=0.2`(L34)。

**接入**：`life_loop.py:1663` 调 `update_boredom(boredom, dt * 0.5)`——**只传 2/7 参数**。

**🔍问题 P4-50（🟡 life_loop 丢 4/7 参数）**：签名有 `novelty/compute/memory/socially_engaged/apply_resource_override`，life_loop 全用默认值。后果：
- `novelty=0.0` → `is_low_novelty` 恒真 → η_idle 项**每 tick 都加**（无聊单调上升）；
- `compute/memory=1.0` → `is_emergency_state` 恒 False → 资源门控永不触发。
**η_soc/η_nov/资源覆盖三条论文机制在生产路径全部失效**。
**🔍问题 P4-51（🔴 魔数与 constants 严重失配）**：
| 参数 | boredom.py | constants.METABOLISM |
|---|---|---|
| 空闲增长 | `ETA_IDLE=0.03` | `BOREDOM_ACCUMULATION=0.005` |
| 新颖抑制 | `ETA_NOV=0.20` | `BOREDOM_REDUCTION_NOVELTY=0.10` |
| 社交抑制 | `ETA_SOC=0.05` | `BOREDOM_REDUCTION_SOCIAL=0.05` ✅ |
boredom.py 用自己的类常量，从不读 `METABOLISM`。两套数值并存且 idle 差 6×。外加 life_loop 又把 dt 乘 0.5（L1663 注释"增长速度减半"）——**第三层硬编码**。
**🔍问题 P4-52（🟡 effective_boredom 三处重复）**：`boredom.py:126`/`resource_pressure.py:123`/`state.py:get_effective_boredom:307` 逻辑完全一致，三份拷贝。

#### 4.3.3 `circadian.py` (287行) ⚠️ 24h 昼夜节律（时间源与模拟脱节）
**职责**：`CircadianRhythm`——24 小时节律、能量余弦、疲劳恢复倍率、离线巩固窗口。

**关键**：
- `CircadianPhase`（L19）：MORNING(6-12)/AFTERNOON(12-18)/EVENING(18-22)/NIGHT(22-6)。
- `__init__`（L44）：`time_mode="realtime"`(L50 默认)、`seconds_per_tick=1.0`、`sim_start_hour=6`、`offline_windows=[01:00-04:00 w=1.0, 14:00-15:00 w=0.6]`。
- `_get_current_time`（L88）：`time_mode=="simulation"` 用 tick，否则 `datetime.now(timezone.utc)`。

**公式**：
- **能量**（`get_energy_level` L156-162）：`energy = 0.65 + 0.35·cos(2π·(hours−10)/24)`，clip[0.3,1.0]，peak=10:00/trough=03:00。
- **疲劳恢复倍率**（`get_fatigue_recovery_rate` L280-285）：NIGHT→2.0/MORNING→1.5/AFTERNOON→0.8/EVENING→1.0。

**接入**：`life_loop.py:551` 实例化；PHASE 1 `_update_body` 只调 **2 个方法**：`get_energy_level()`（L1644）、`get_fatigue_recovery_rate()`（L1645）。`should_consolidate`（life_loop L1530）是**同名局部变量**，非调用本类方法。

**🔍问题 P4-53（🔴 时间源脱节）**：`time_mode` 默认 `"realtime"`，**全仓库无 yaml/json 配置 time_mode**（grep 证实）。因此 `get_energy_level/get_fatigue_recovery_rate` 用 `datetime.now(utc)` 真实墙钟 UTC 时，与 tick、与 `sim_start_hour`、与 caretaker 的 tick 推算的小时**三者互不相干**。simulation 模式从未启用，配置字段 `sim_start_hour/seconds_per_tick/offline_windows/time_mode` 全是死配置。
**🔍问题 P4-54（🔴 与 caretaker 睡眠窗口冲突）**：
| 维度 | circadian.py | caretaker_organ.py |
|---|---|---|
| 时间源 | `datetime.now(utc)` 墙钟 | `tick·tick_duration/3600%24`（L274-275） |
| 窗口 | offline 01-04/14-15 | sleep 22-07（L66-67） |
caretaker **从不 import circadian**，自建一套；circadian 默认窗口甚至不含 22-7。题述"sleep window 22-7"在 metabolism 包找不到，只在 caretaker。
**🔍问题 P4-55（🟡 tick_duration 集成断裂）**：caretaker L270 `tick_duration = context.get("tick_duration", 10)`，但 `build_context` **从不写 tick_duration 键**（grep 证实 life_loop 也不写）→ caretaker 永远用默认 10s 推算小时 → 三方时间源全部不统一。呼应第5章 P5-23。
**🔍问题 P4-56（🟡 魔数）**：`0.65/0.35`、phase 边界、recovery dict、`consolidation_threshold=0.6`、`base_consolidation_ticks=10`、`100 tokens/tick`、offline_windows 全硬编码。
**🔍问题 P4-57（🟢 持久化缺口）**：`_sim_base_time`（L57）用 `datetime.now()` 在 init 固定，重启后重新锚定 → 模拟时钟每次重启"漂移"；circadian 对象不参与 state 序列化。

#### 4.3.4 `recovery.py` (173行) 🔴 整模块死代码
**职责（声称）**：论文 §3.8.2 恢复机制——能量/疲劳/压力的恢复速率与模式建议。

**`compute_recovery_rate`（L42-109）** 按模式放缩：`sleep×2.0/friend×0.3/work×0.0`（fatigue: sleep×2.0/friend×0.3/work×0.0），状态调制 energy<0.3×1.5、fatigue>0.7×0.7。

**🔍问题 P4-58（🔴 整模块死代码）**：`grep "compute_recovery_rate|needs_recovery|suggest_recovery_mode|RecoveryConfig"` 在 metabolism 外唯一命中是 `core/resource_config.py:42`（同名无关键）和 `eval/gxbs.py:114`（同名不同模块）。**life_loop._update_body 有自己的内联恢复逻辑**（L1651-1659）：
```python
# life_loop.py L1651-1659 (内联, 不用 recovery.py):
if energy < circadian_energy:
    new_energy = energy + (circadian_energy - energy) * 0.05
else:
    new_energy = energy * 0.99 + circadian_energy * 0.01
new_fatigue = max(0.0, fatigue - 0.05 * dt * recovery_rate)
```
本模块的 sleep/friend/work 模式系统完全未被采用。
**🔍问题 P4-59（🟡 魔数林立）**：0.05/0.08/0.03/0.3/0.7/0.8/2.0/1.5/0.5/0.3/0.1/0.0 全字面量，与 `METABOLISM.ENERGY_SLEEP_GAIN=0.15` 等不符，且 constants 本身也无人读（P4-64）。
**🔍问题 P4-60（🟡 半成品）**：`suggest_recovery_mode` docstring 提"rest"模式，函数已注释"不使用 rest"。

#### 4.3.5 `resource_pressure.py` (256行) 🔴 RP_t（与 state.py 公式语义相反！）
**职责（声称）**：论文 §3.2 资源压力指数 RP_t，用于优先级覆盖 Ω_t、无聊门控、arousal 调制。

**`ResourcePressureConfig`**（L19）：`alpha_compute=0.6`/`beta_memory=0.4`/`emergency_threshold=0.35`，`__post_init__` 校验 α+β=1。
**`compute_resource_pressure`（L64-95）**：`RP_t = max(0, 1 − (α·Compute + β·Memory))`——资源充足→RP小（无压力），资源紧缺→RP大。`emergency := RP_t > 0.35`。

**接入**：🔴 life_loop **不调本模块**，走 `state._update_resource_pressure()`。

**🔍问题 P4-61（🔴 与 state.py 公式语义相反——最严重）**：
| | resource_pressure.py (L92) | state.py `_update_resource_pressure` (L302-305) |
|---|---|---|
| 公式 | `RP = max(0, 1 − (α·C + β·M))` | `RP = α·C + β·M`（**无 `1−`**） |
| 资源充足时 | RP→0（无压力）✅ 符合论文 | RP→1（满压力）❌ |
| 资源紧缺时 | RP→1（满压力）✅ | RP→0（无压力）❌ |
| α/β | 0.6 / 0.4 ✅一致 | 0.6 / 0.4 硬编码 |
state.py 注释自述"修正后语义：占用率越高压力越大"，即 **state.py 故意反转了 metabolism/论文公式**。后果：
- `state.resource_pressure` 与 `compute_resource_pressure()` 对同一 (compute,memory) 给出**相反**的紧急判断；
- `metabolism.boredom` 的资源门控（P4-50）用本模块（资源紧缺才禁用无聊）；`state.get_effective_boredom()`（L307）用反转语义（占用率高才禁用）——同一"有效无聊度"两套相反触发条件；
- 论文 §3.2 原式与 state.py 不符 → **生产路径用的是偏离论文的版本**。
**🔍问题 P4-62（🟡 constants 缺失）**：α/β/0.35 三处独立硬编码（resource_pressure.py、state.py），`common/constants.py` **无** resource_pressure 常量。无单一真相源。
**🔍问题 P4-63（🟡 `__main__` 测试块残留）**：L224-256 应移至 tests/。
**✅问题 P4-64 已修**：~~`MetabolismConstants`（L167-188）整段死常量~~。全项目 grep 确认 `METABOLISM`/`MetabolismConstants`/13 个常量名/`get_all_constants()` 在生产代码**零读取点**，仅被 `common/__init__.py` re-export。实际 metabolism 计算各用各的硬编码：`core/emotion_decay.py`（lambda_valence=0.05/lambda_stress=0.08/lambda_boredom=0.03）、`metabolism/boredom.py`（ETA_*=0.03/0.20/0.05）。已删除 `MetabolismConstants` 类 + 全局 `METABOLISM` 实例 + `get_all_constants` 的 metabolism 键 + `__init__` re-export，常量段从 11 减至 10。运行时数值零变化（删的是无人读的声明层）。

---

### 4.x cognition/perception/metabolism 速查与调试点

**精读优先级**：
- cognition：`goal_compiler.compile_multi_goal`（PHASE 6 必懂）→ `plan_evaluator._score_plan`（评分公式）→ 确认 `priority_level` 全域未设（P4-1）
- perception：只需读 observer + context_builder（157 行就够）；其余文件视作清理候选
- metabolism：先比对 `resource_pressure.py` vs `state.py`（P4-61 语义冲突）→ 再看 circadian 与 caretaker 的时间源（P4-53/54）

**接入真相表**（life_loop PHASE 对应）：
| 模块 | life_loop PHASE | 实际调用 | 状态 |
|---|---|---|---|
| `goal_compiler.compile_multi_goal` | PHASE 6 | life_loop.py:993 | ✅ 接入 |
| `plan_evaluator.evaluate_plans` | PHASE 8 | life_loop.py:1196 | ✅ 接入 |
| `verifier.verify_action` | PHASE 9b | life_loop.py:1248 | ✅ 接入 |
| `observer.observe_environment` | PHASE 2 | life_loop.py:815 | ✅ 接入 |
| `context_builder.build_context` | PHASE 4 | life_loop.py:903 | ✅ 接入 |
| `boredom.update_boredom` | PHASE 1 | life_loop.py:1663 | ⚠️ 接入但丢 4/7 参数(P4-50) |
| `circadian.get_energy_level/get_fatigue_recovery_rate` | PHASE 1 | life_loop.py:1644-1645 | ⚠️ 接入(2 方法) |
| `planner.propose_plans` | — | tools/blackboard.py:512,784 | 🟡 仅 blackboard，life_loop 绕过 |
| `goal_compiler.compute_progress`/`assess_gap_urgency` | — | — | 🔴 死代码(仅测试) |
| `goal_progress.py` 整模块 | — | — | 🔴 死代码(P4-22) |
| `insight_quality.py` 整模块 | — | — | 🔴 死代码(P4-19) |
| `self_perception` 工具 | PHASE 7 工具 | tool_registry 注册 | 🔴 **注册未分发**(P4-31) |
| `time_perception.py` | — | — | 🔴 未集成(P4-36) |
| `command_parser.py` | — | — | 🔴 被绕过(P4-40) |
| `novelty.py` | — | — | 🔴 死代码(P4-43) |
| `signal_filter.py` | — | — | 🔴 死代码(P4-45) |
| `recovery.py` 整模块 | PHASE 1（绕过）| life_loop 内联 L1651 | 🔴 死代码(P4-58) |
| `resource_pressure.py` | PHASE 1（绕过）| state._update_resource_pressure | 🔴 **公式与 state 相反**(P4-61) |
| `constants.METABOLISM` | — | — | ✅ 已删(P4-64) |

**高危区**：
1. **`priority_level` 全域未设置**（P4-1）：论文 §3.8.1 的 6 级优先级系统运行时不生效，所有 Goal 恒为 MEDIUM
2. **resource_pressure 与 state.py 公式语义相反**（P4-61）：生产路径偏离论文，两套"有效无聊度"触发条件相反
3. ~~**METABOLISM 常量整段失效**（P4-64）~~：✅ 已删除死常量，4 套数值仍并存但已无"虚假单一来源"误导
4. **self_perception 工具断链**（P4-31）：注册未分发，LLM 选了也找不到 handler
5. **目标进度永不更新**（P4-2/P4-22）：goal_progress.py + goal_compiler.compute_progress 两套都没接 life_loop，goal.progress 停在 0.0
6. **Q^insight 三重实现**（P4-20）：cognition/insight_quality(死)、memory/consolidation(活)、eval/gxbs 公式不同
7. **perception 包 90% 死代码**：6/8 文件未接入（novelty/signal_filter/command_parser/time_perception/self_perception/__init__ 兜底）
8. **时间源三重不一致**（P4-53/54/55）：circadian(UTC墙钟) vs caretaker(tick推算) vs time_perception(上海时区) 互不对齐

**重复实现清单**（供跨章交叉引用）：
- **Q^insight**：cognition/insight_quality.py vs memory/consolidation.py vs eval/gxbs.py
- **目标进度 Prog(g,S)**：goal_compiler.compute_progress vs goal_progress.ProgressCalculator（均未接）
- **目标类型分类法**：goal_progress.GoalType(8 枚举) vs goal_compiler 模板(5) vs planner 字符串(8+)
- **新奇度**：perception/novelty.py vs memory/semantic_novelty.py vs axiology/feature_extractors._compute_semantic_novelty
- **时段判定**：perception/time_perception vs metabolism/circadian vs organs/caretaker sleep window
- **命令解析**：perception/command_parser vs core/handlers/chat_handler
- **健康状态**：perception/self_perception.get_health_status vs organs/caretaker.get_health_status
- **effective_boredom**：metabolism/boredom vs metabolism/resource_pressure vs state.get_effective_boredom
- **资源压力 RP_t**：metabolism/resource_pressure（论文版，死）vs state._update_resource_pressure（反转版，活）
- **压力公式**：metabolism/resource_pressure(0.6·cpu+0.4·mem) vs state(同系数但语义反转) vs perception/self_perception(0.3·cpu+0.4·mem+0.3·proc_mem)
- **Signal 类**：perception/signal_filter.Signal(别名) vs core/stores/signals.Signal（命名冲突）

**与论文的对应**：状态向量 = §3.2（observer/context_builder + metabolism/circadian）；资源压力 RP_t = §3.2（resource_pressure.py 死 / state.py 活但偏离）；目标编译 = §3.8（goal_compiler.py）；规划评估 J(p|S_t) = §3.9.3（plan_evaluator.py）；动作验证 = §3.11（verifier.py）；无聊 η-系数 = Appendix A.3（boredom.py）；昼夜节律/恢复 = §3.8.2（circadian.py 活 / recovery.py 死）；Q^insight = §3.5.2(7)/§3.10.4（insight_quality.py 死 / consolidation.py 活）。

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

## 6. 工具层 `tools/`

> 23 文件/9837 行。LLM API 统一接口 + 工具执行引擎 + Mind Field 多专家黑板（论文 §3.4.2） + 安全代码执行 + 视觉/语音/嵌入。**这是整个系统的"手"——器官决策（第5章）落地的执行手段。**
>
> **核心认知（理解本章的前提）**：tools/ 是项目里"重复实现"最严重的层——**LLM 客户端有 3 套**（llm_api/llm_client/llm_orchestrator），**工具注册表有 3 套**（tool_registry/dynamic_tool_registry/tool_definitions），**代码执行有 4 套**（tool_executor 全开/safe_executor AST/code_exec 正则/tool_executor 黑名单），**嵌入有 4 处**（见第3章 P3-7 + 本章 tools/embeddings），**web_search 有 2-3 套**。理解本章的关键是**先搞清楚哪套是"活的"**——见 6.x 接入真相表。
>
> **活路径确认**（grep + 精读 life_loop/action_executor）：`LLM_MODE` 环境变量默认 `single` → action_executor 走 **`tools/llm_client.py:LLMClient`**（不是 llm_api.UniversalLLM，不是 llm_orchestrator）。多专家黑板（blackboard.py 1369行）**默认休眠**，仅当 `LLM_MODE=core5/full7/adaptive` 时经 llm_orchestrator 接入。器官的 LLM 会话（第5章 organ_llm_session）**也独立走 LLMClient**。即生产路径上**真正的 LLM 客户端只有 llm_client.py**，llm_api.py 是它的"前身/兼容别名"。
>
> **目录结构**：
> ```
> tools/
> ├── llm_client.py        (708)  ⭐⭐ 活路径：单一/兼容 LLM 客户端(action_executor/器官/检索都用它)
> ├── llm_api.py           (537)  ⚠️ 另一套 UniversalLLM(仅 blackboard/growth/插件用)
> ├── llm_orchestrator.py  (352)  🟡 多模型门面(默认 single 时退化为 llm_client 包装)
> ├── blackboard.py        (1369) ⭐ Mind Field 多专家黑板(论文§3.4.2,默认休眠)
> ├── tool_executor.py     (642)  ⭐ 活路径：LLMToolExecutor(工具执行+FULL_ACCESS 代码)
> ├── tool_system_v2.py    (606)  🟡 EnhancedToolExecutor+SmartToolParser(中文意图解析,接入弱)
> ├── dynamic_tool_registry.py (527) ⭐ 活路径：运行时工具注册(喂 LLM tools+技能桥接)
> ├── tool_registry.py     (198)  ⚠️ 静态 ToolSpec 目录(action_executor 只用 .get())
> ├── tool_protocol.py     (371)  🔍 Tool 抽象基类+ToolExecutor(死类)
> ├── tool_definitions.py  (118)  OpenAI function schema(chat_interactive 用)
> ├── safe_executor.py     (514)  🔍 AST 安全执行器(孤立,最完善但没接)
> ├── code_exec.py         (359)  🔍 正则黑名单 CodeExecutionTool(孤立)
> ├── cost_model.py        (262)  🔍 CostModel 价格表(死代码)
> ├── llm_cache.py         (295)  🔍 LLM 响应缓存(完全孤立)
> ├── embeddings.py        (405)  🟡 嵌入工具(默认 mock,真后端 sentence-transformers)
> ├── vision.py            (539)  🔍 视觉/OCR(三 provider,无人调用)
> ├── voice.py             (568)  🔍 TTS 四引擎(🚨 _speak_edge 递归 bug)
> ├── messaging.py         (370)  🟡 主动消息(web/app + ToolSpec send_message)
> ├── memory_tools.py      (363)  🔍 记忆 CRUD 工具(孤立,被 tool_executor 取代)
> ├── web_search.py        (157)  🟡 Bing 搜索 Tool(与 tool_executor._web_search 重复)
> ├── file_ops.py          (226)  🟡 沙箱文件 Tool(allow-list,默认 fail-open)
> └── capability.py        (113)  🔍 CapabilityToken 管理器(被 core/capability_manager 遮蔽,P8-1)
> ```

---

### 6.1 LLM 客户端三套并存（最重要，先分清）

项目里有 **三个 LLM 客户端模块**，命名相似、接口相近，但只有一个是活路径。混淆它们是本章最大的坑。

| 模块 | 类 | 行数 | 谁用它 | 状态 |
|---|---|---|---|---|
| `llm_client.py` | `LLMClient` | 708 | **action_executor（CHAT 路径）、器官 organ_llm_session、life_loop 全局 client、检索** | ⭐ **活路径**（`LLM_MODE=single` 默认） |
| `llm_api.py` | `UniversalLLM`（别名 `LLMAPIClient`） | 537 | blackboard 专家、growth/limb_generator、memory/skills/*、tool_executor._web_search | ⚠️ 黑板/生成路径用 |
| `llm_orchestrator.py` | `LLMMOrchestrator`（**双 M 拼写错误**，别名 `LLMOrchestrator`） | 352 | action_executor（仅 `LLM_MODE≠single`）、web/app、chat_interactive | 🟡 多模型门面，默认休眠 |

**为什么有三套**：历史遗留。`llm_api.py`（L1 注释 "Universal LLM API wrapper"）是**最早**的多 provider 封装（OpenAI/Anthropic/Ollama/OpenRouter/Custom，纯 requests + 流式）；`llm_client.py`（L1 注释 "统一的大语言模型接口"）是**后写的、更全**的国产模型适配（额外覆盖 claude/qianwen/deepseek/glm/ernie/hunyuan/kimi/yi/local + 嵌入 `embed()`），两者接口不同（llm_api 用 `chat(messages, tools=)`、llm_client 用 `chat(messages, system_prompt=, tools=)`）。`llm_orchestrator` 是在两者之上的**门面**——single 模式转调 `llm_api.create_llm_from_env()`，多模型模式转调 blackboard。

**🔍问题 P6-1（🔴 重要，三客户端并存）**：三个模块接口签名不一致（`chat()` 参数名/位置、返回 dict 的键 `text` vs `ok` vs `total_tokens`、`error` 处理），改一处易漏另两处。且 `llm_orchestrator.LLMMOrchestrator` 类名拼写错误（双 M，L20），靠 L330 别名掩盖。**优化应统一到 llm_client.py，废弃 llm_api.py（或反之），让 orchestrator 只做门面。**

### 6.2 `llm_client.py` (708行) ⭐⭐ 活路径 LLM 客户端

**职责**：被 action_executor（CHAT/工具调用循环）、organ_llm_session（器官思考）、life_loop 全局 client 引用。统一适配 11 个 provider（claude/qianwen/deepseek/glm/ernie/hunyuan/kimi/yi/local + 通用 openai-compat）。

**`LLMConfig` dataclass**（L25-37）：`api_base/api_key/model/temperature/max_tokens/timeout=60/provider="openai"/version`。**注意 timeout=60**（注释"增加到 60 秒以适应 GLM API 的波动"）。

**provider 自动检测**（`_load_config` L88-117）：按 api_base 子串匹配，**检测顺序很关键**——先判 `/api/anthropic`（智谱 Anthropic 兼容接口）→ `anthropic.com`/`claude` → `dashscope`/`qianwen` → `deepseek` → `zhipu`/`bigmodel` → `ernie`/`baidu` → `hunyuan`/`tencent` → `moonshot`/`kimi` → `lingyi`/`yi` → `localhost`/`ollama`。**🔍问题 P6-2（重要，检测脆弱）**：纯子串匹配，`api_base="https://api.stepfun.com/step_plan/v1"`（当前 .env）不含任何关键词 → 落到默认 `provider="openai"`（走 OpenAI 兼容路径，**恰好对**，因为 stepfun 是 OpenAI 兼容）。但任何 base_url 含意外子串（如 "kimi-proxy.openai.com"）会误判。

**三套调用分支**：
- `_chat_openai_compatible`（L193，覆盖 openai/deepseek/glm/ernie/hunyuan/kimi/yi/local）：POST `/chat/completions`，Bearer auth，`tools`+`tool_choice="auto"`。**L255-258 关键：当 `content` 为空时回退到 `reasoning_content`**——这是为 GLM-5/step-3.7-flash 等推理模型准备的。
- `_chat_qianwen`（L290）：优先用 dashscope SDK，ImportError 时**降级回 openai-compat**（兼容模式）。
- `_chat_claude`（L382）：优先 anthropic 库，失败降级到 requests 直接调 `/v1/messages`。**处理 system 消息分离、tool 格式转换（OpenAI↔Anthropic）、tool_result 消息转换**（L502-529），是三者中最复杂。

**返回 dict 约定**：`{ok, text, tool_calls: List, total_tokens, [error]}`。tool_calls 统一规整成 OpenAI 风格 `{id, type:"function", function:{name, arguments(JSON字符串)}}`。

**🔍问题 P6-3（⚠️ 与既有记录冲突，需澄清）**：CODE_MAP 第8章 P8-12 和第5章 P5-3 称"CHAT 路径/器官 think 不解析 reasoning_content"。**这是不准确的**——llm_client.py:256-258 确实在 content 为空时回退到 reasoning_content。**真正的缺陷**是：① 只在 content**完全为空**时才取 reasoning_content，若 content 非空（哪怕只是个标点）则 reasoning_content 被丢弃；② 把推理链当成"正文 text"返回，下游无法区分"正式回答"和"思考过程"。对 step-3.7-flash 这类**同时**返回 content+reasoning_content 的模型，行为依赖 content 是否为空。**建议把 P8-12/P5-3 改写为"reasoning_content 仅在 content 空时兜底，且与正文混在 text 字段"。**

**🔍问题 P6-4**：`embed()`（L618）逐条文本发 `/embeddings` 请求（无批量），且 `model` 字段用的是 chat 模型名（非 embedding 模型）——对不支持嵌入的 chat 端点必失败。当前生产环境无嵌入 API，此方法实际不可用。

**🔍问题 P6-5**：`_chat_claude` 的降级路径（requests 直接调）L469 引用了未定义的 `logger`（`logger.warning`）——`logger` 在模块顶部未导入/定义，anthropic 库失败时会抛 `NameError` 被外层吞掉，**降级逻辑本身有 bug**。

### 6.3 `llm_api.py` (537行) ⚠️ 第二套 LLM 客户端

**职责**：`UniversalLLM`——最早的多 provider 封装。被 blackboard 专家、growth limb_generator、memory/skills/* 引用（这些模块写死 `from tools.llm_api import ...`）。

**与 llm_client.py 的差异**：
- provider 用 `LLMProvider` 枚举（7 个），llm_client 用字符串。
- 有 `DEFAULT_PRESETS`（6 个：gpt-4/gpt-3.5-turbo/claude-3-sonnet/deepseek-chat/qwen-plus/ollama），llm_client 无预设。
- 有 `chat_stream`（SSE 流式），llm_client 无流式。
- `_parse_response` 区分 Anthropic（content blocks）与 OpenAI-compat（choices）。
- 工具调用格式：Anthropic 走 `_convert_tools_to_anthropic`（OpenAI→`{name,description,input_schema}`）。

**🔍问题 P6-6**：`from_env`（L445）的 provider 检测逻辑与 llm_client.py 的几乎逐字重复（两处都先判 anthropic 再判其他）。改一处忘另一处。这是 P6-1 的具体表现。

**🔍问题**：`DEFAULT_PRESETS` 的模型名已过时（claude-3-sonnet-20240229、gpt-4 无 -turbo 后缀）；`chat_stream` 的 Anthropic 分支 L401 注释"兼容旧格式"暗示有未对齐的流式协议变体。

### 6.4 `tool_executor.py` (642行) ⭐ 活路径工具执行器

**职责**：`LLMToolExecutor`——执行 LLM 返回的函数调用。被 action_executor（USE_TOOL + CHAT 工具循环）、memory/skills/* 引用。原 `ToolExecutor` 名（L642 别名保留兼容）。

**`execute(tool_id, params)` 统一入口**（L233）：维护 `tool_mapping`（别名→规范名，如 `file_read`/`read_file`/`file`→`read_file`），调 `_execute`。**🔍问题 P6-7（与 P8-11 同源）**：tool_id 映射表是硬编码字典，而 gap_detector 读 `params["tool"]`、action_executor 读 `params["tool_id"]`——三处对"工具名放哪"的约定不一致（见第8章 P8-11）。

**`execute_tool_call(tool_call)`**（L265）：处理 OpenAI/Anthropic 两种 tool_call 格式，禁用工具检查（`disabled_tools`，safe_mode 下 `{write_file, execute_code, web_search}`），JSON 解析参数，调 `_execute`。

**5 个内置工具**（`_execute` L315）：`read_file`（截断 50KB）/`write_file`/`list_directory`（最多 20 文件）/`web_search`（**用 LLMClient 联网搜索，非真搜索**）/`execute_code`（见下）。

**`_web_search`（L415）的独特设计**：不调搜索 API，而是**新建一个 LLMClient**，用"你是一个搜索助手…"的系统提示 + `temperature=0.3` 让 LLM 自己"联网搜索"（依赖 provider 的联网能力，如通义千问）。**🔍问题 P6-8**：这与 web_search.py（Bing API）是**两套完全不同的搜索实现**，且 stepfun step-3.7-flash 不保证有联网能力——实际可能只是 LLM 凭记忆编造"搜索结果"。

**`_execute_code`（L445）—— 默认 FULL_ACCESS**：`safe_mode=False`（构造默认值）时，`exec(code, exec_globals)` 其中 `exec_globals` 含**完整 builtins + os/sys/json/pathlib/datetime/math/random + `genesis_self`(self 引用)**。注释明确"FULL_ACCESS 模式…可以导入模块、读写文件、联网、self-modification"。**这给了 LLM 完全的本地代码执行权**。

**🔍问题 P6-9（🔴 安全，默认全开）**：`create_llm_tool_executor(safe_mode=True)`（L636）默认 safe，但 `dynamic_tool_registry._register_default_tools`（L442）用 `LLMToolExecutor(safe_mode=False)` 构造——**全局 registry 注册的 execute_code 是 FULL_ACCESS**。`config/runtime.yaml:27 sandbox_code_exec: false` 的 flag **没被 tool_executor 读取**。（注：原 `config_manager.py:146 sandbox_code_exec: bool=True` 默认值已于 P1-4 随该死代码文件一并删除。）即"沙箱代码执行"配置形同虚设，实际永远是全开。

**`_execute_code_sandboxed`（L501）**：28 个危险子串黑名单（`import`/`exec`/`eval`/`open`/`os.`/`sys.`/`__class__`/…），空 builtins + 白名单函数，SIGALRM 5 秒超时（Windows 无效）。**🔍问题 P6-10**：子串黑名单可绕过（`__builtins__["open"]`、`getattr(__builtins__,"open")`、`chr(111)+...` 拼接），且 `import` 作为子串会误拦注释里的 "import" 一词。

### 6.5 三套工具注册表 + tool_definitions（6.6 详述重叠）

**🔍问题 P6-11（🔴 重要，工具目录四重定义）**："有哪些工具"这件事在 4 处各写一遍，互不引用：
1. `tool_registry.py::ToolRegistry`（11 个 ToolSpec：qianwen_chat/file_read/web_search/get_time/analyze_image/image_to_text/read_own_logs/system_stats/send_message/voice_speak/schedule_action）——action_executor 用 `.get(tool_id)`。
2. `dynamic_tool_registry.py::DynamicToolRegistry`（5 个：list_directory/read_file/write_file/web_search/execute_code + 技能桥接）——action_executor 用 `.to_llm_format()` 喂 LLM、`.get(name)` 解析调用。
3. `tool_definitions.py::AVAILABLE_TOOLS`（5 个 OpenAI schema：read_file/write_file/list_directory/web_search/execute_code）——chat_interactive 用。
4. `memory/skills/`（4 个技能）经 dynamic_tool_registry 桥接。

四处工具名不统一（`read_file` vs `file_read` vs `read`）、风险等级不一致、schema 各异。**action_executor 同时查 ToolRegistry（L504-524）和 DynamicToolRegistry（L620-621,777）**，两个注册表并存无协调层。

**`tool_registry.py::ToolSpec`**（L7-21，pydantic）：实现论文 §3.11 工具五元组 `<id, schema, cost_model, pre, post>`（L19-20 注释"修复 H12"加了 preconditions/postconditions，**但是字符串表达式，从不被求值**）。`list_available(capabilities)`（L176）能力门控是唯一活方法。

**`tool_protocol.py::ToolExecutor`（L179）完全死代码**：定义了带风险门控（`max_risk_online=0.75`/`max_risk_offline=0.3`）、前后置条件校验、动态成本计算的"正经"执行器，但**全项目零实例化**——运行时用的是 tool_executor.py 的 LLMToolExecutor（无风险门控）。抽象基类 `Tool` 被 4 个具体工具（code_exec/embeddings/file_ops/web_search）继承，但它们的 `Tool` 实例**从不注册进 ToolExecutor**。**🔍问题 P6-12**：tool_protocol.py 的整套风险/契约/成本框架（292 行）是"论文实现了但没接"的典型。

**`capability.py::CapabilityManager` 被 P8-1 遮蔽**（见第8章）：life_loop.py:48 导入它，但 :71 导入 core/capability_manager.py 同名类覆盖了它。确认 tools/capability.py 的 `CapabilityManager` 在主循环中**从未使用**（仅 life_loop_backup.py 用）。其 `CapabilityToken` 的 `budget_cpu_tokens`/`budget_money`/`revocable`/`audit_scope` 字段全部**存储但不读取**——token 只是能力名清单，无预算扣减。

### 6.6 `blackboard.py` (1369行) ⭐ Mind Field 多专家黑板（论文 §3.4.2，默认休眠）

**职责**：论文 §3.4.2 "Mind Field" 的完整实现——多个角色专家（M_coord 调度/M_mem 记忆/M_reason 推理/M_affect 情感/M_percept 感知 + 可选 M_vis/M_aud）读写共享黑板 `BlackboardState`，由 `MindFieldOrchestrator` 协调，按人格中间变量（ET/CT/ES）和资源压力（RP）动态选配置（single/core5/full7/adaptive）。**这是 tools/ 最大的文件，但默认休眠**（只有 `LLM_MODE≠single` 才经 orchestrator 接入）。

**`ModelConfig` 枚举**（L32）：SINGLE/CORE5/FULL7/ADAPTIVE。**`ExpertRole` 枚举**（L40）：5 核心 + 2 扩展（M_VIS/M_AUD）+ 8 个遗留兼容角色（GENERAL/REASONING/CREATIVE/CODING/ANALYSIS/WRITING/MATH/CRITIC，**全模块无引用**）。

**`BlackboardState`（L78-168）**：12 个槽位（current_goal/retrieved_memories/emotional_state/resource_state/soul_state/middle_vars/perception/candidates/value_features/relationship_state/communication_frequency/abstract_state）+ tick/last_update 元数据。`update_slot`（L159）用 `hasattr` 守卫——**未知槽位静默丢弃**。

**`ExpertModel.process(user_message, context)`（L426-892）**：巨型分派器。每个专家先做角色专属的前置工作（写黑板 + 增强 prompt），**然后无条件调 `client.chat(messages)`**（L858，用 llm_api.UniversalLLM）。角色前置工作：
- **M_MEM**（L449）：正则提关键词 → `MemoryRetrieval.retrieve_episodes` → 写 retrieved_memories 槽。
- **M_REASON**（L486）：import `cognition.planner.Planner`，`planner.propose_plans(goal, context, available_tools, num_plans=3)` → 写 candidates 槽。
- **M_AFFECT**（L539）：中文关键词情感打分（高兴/喜欢/谢谢→+0.1，不/错/问题→−0.05）→ 调 `affect.mood.update_mood` / `affect.stress_affect.update_stress`。
- **M_PERCEPT**（L588）：novelty = `min(1.0, len(unique_words)/20.0)`。
- **M_COORD**（L704）：**单模式时内联复制 M_MEM/M_REASON/M_AFFECT/M_PERCEPT 的全部逻辑**（L728-848，~120 行重复）。

**`MindFieldOrchestrator`（L939）**：`process`（L1110）按配置选活跃角色 → 单 M_COORD 走快速路径 → 多角色走 `_process_multi_expert`（ThreadPoolExecutor 并行，`as_completed(timeout=60)`）→ `_select_final_result`（M_COORD 优先，否则按 `confidence × voting_weight` 加权）。`config_select(et,ct,rp)`（L899）按阈值选配置（rp>0.8 或 ct>0.8→SINGLE；et>0.7 且 rp<0.4→FULL7；…）。

**🔍问题 P6-13（🔴 重要，update_mood 签名错误，整条情感路径死）**：M_AFFECT（L557-561）和 M_COORD 单模式（L817）调 `update_mood(..., dimension="attachment")`——但 `affect.mood.update_mood` 签名是 `(mood, delta, k_plus, k_minus)`，**没有 dimension 参数**（论文的维度级更新是另一个函数 `update_mood_per_dimension`）。这会抛 TypeError，被宽泛 `except Exception`（L584/L829）吞掉只记 warning。**结果：黑板驱动的情绪更新整条路径静默失效**。

**🔍问题 P6-14（幽灵槽位丢失）**：M_VIS 写 `vision_perception`（L645）、M_AUD 写 `audio_perception`（L695）、orchestrator 写 `expert_{role}_output`（L1194）——但这些槽位**不在 BlackboardState schema 里**，`update_slot` 的 `hasattr` 守卫导致写入被静默丢弃。这些专家/编排器的输出数据**全部丢失**。

**🔍问题 P6-15（成本翻倍）**：M_REASON/M_COORD 先调 `planner.propose_plans`（planner 内部可能再调 LLM），然后 L858 又**无条件** `client.chat`——一次"推理"产生两次 LLM 调用。

**🔍问题 P6-16**：M_COORD 单模式块（L728-848）是其他四个专家分支的逐字副本（含同样的 update_mood bug），~120 行重复，维护高危。`_stable_threshold=50`（L999）定义但从不读取（L1084 `# TODO: 检查人格状态稳定性` 未实现）。`BlackboardSlot` dataclass（L69）从不实例化。

**🔍问题 P6-17**：`create_core5_experts`（L1298）硬编码模型名（M_COORD/M_MEM/M_REASON/M_AFFECT=`gpt-4`，M_PERCEPT=`gpt-3.5-turbo`）和 api_base（`https://api.openai.com/v1`）——与当前 stepfun 环境完全不匹配，多模型模式若启用会用错误的端点/模型。

### 6.7 `llm_orchestrator.py` (352行) 🟡 多模型门面

**职责**：`LLMMOrchestrator`（拼写错误双 M，别名 `LLMOrchestrator` L330）——single 模式包装 `llm_api.create_llm_from_env()`，多模型模式包装 blackboard。被 action_executor（`LLM_MODE≠single`）、web/app、chat_interactive 引用。

**`chat(messages, tools, **kwargs)`**（L179）：single → `llm.chat(messages, tools=tools)`；multi → `orchestrator.process(user_message, context, tick)`。**🔍问题 P6-18（🔴 重要，多模型模式丢 tools）**：multi 分支（L206）调 `process(user_message, context, tick)` **不传 tools 参数**——即多专家黑板模式下，函数调用（tool_calls）静默失效，LLM 拿不到工具定义。这是 blackboard.process 签名本就不接收 tools 的体现（见 P6-15），orchestrator 无从转发。

**🔍问题 P6-19**：`enable_multi_model` 参数标记"已弃用"但仍在签名里；`config_mode` 构造参数在多模型路径被 YAML 配置静默覆盖（L62），构造参数失效。`_expand_env`（L168）只处理**精确** `${VAR}` 形式，不展开内嵌变量。

### 6.8 安全代码执行三套 + safe_executor（孤立）

**🔍问题 P6-20（🔴 重要，代码执行四套，最完善的那套没接）**：
| # | 位置 | 过滤策略 | 运行时 | 接入？ |
|---|---|---|---|---|
| 1 | `tool_executor._execute_code`（FULL_ACCESS） | **无过滤** | exec 全 builtins+os/sys+self | ✅ 活（dynamic_tool_registry 注册） |
| 2 | `tool_executor._execute_code_sandboxed` | 28 子串黑名单 | exec 空 builtins+白名单，SIGALRM | 仅 safe_mode=True 分支 |
| 3 | `safe_executor.py` `SafeCodeExecutor` | **AST NodeVisitor+禁止表** | exec 空 builtins+白名单，线程超时 | 🔴 **完全孤立**（无人 import） |
| 4 | `code_exec.py` `CodeExecutionTool` | 正则词边界 | 子进程（默认）/exec 直跑 | 🔴 **完全孤立** |

**`safe_executor.py`（514行）是四套里最完善的**——真正的 AST 静态分析（`forbidden_imports`/`forbidden_calls`/dunder 黑名单）+ 受控运行时（空 builtins+白名单+math）+ 线程超时（Windows 也能用）。但**全项目零引用**。

**🔍问题 P6-21（safe_executor 的隐患）**：① `allowed_nodes` 节点白名单（L67-88）**定义了但 checker 从不校验**（无 generic_visit 拒绝）——实际是黑名单模型；② `max_memory_mb`（L63）从不强制（无 resource.setrlimit）；③ 线程超时不杀 worker（L430），`while True` 永占 CPU；④ `ExecutionTimeout` 异常声明了从不抛（L27）；⑤ `reduce` 在白名单（L117）但不是 builtin，被 hasattr 守卫静默跳过；⑥ `import_cache`/PERMISSIVE_POLICY 等不一致。

**`code_exec.py`（359行）`CodeExecutionTool`**：正则 `\bimport\s+X\b` 词边界匹配 + 子进程执行。**🔍问题 P6-22**：子进程模式（默认）写临时文件用 `subprocess.run([sys.executable, tmp])`——**子进程拥有完整标准库+网络+文件系统**，仅靠正则前置过滤挡危险。正则可绕（`__builtins__["__import__"](...)`、`getattr(__builtins__,"__import__")` 用下标/反射绕过 call 模式匹配）。docstring（L6-9）要求"非执行回放模式"但未实现。Windows 下直跑模式无 SIGALRM→无超时。

### 6.9 嵌入/视觉/语音/消息（能力模块，多数休眠）

**`embeddings.py`（405行）🟡 第 4 套嵌入**：`EmbeddingsTool(Tool)` + `get_embedding`/`cosine_similarity`。**默认 mock_mode=True**（hash→seed→伪随机单位向量，**无语义**），真后端 sentence-transformers（`all-MiniLM-L6-v2`，L219）需 `mock_mode=False`。OpenAI/DashScope 后端 docstring 声称支持但**未实现**（ImportError 静默降级 mock）。**被 cognition/insight_quality.py 引用**（L168，包在 try 里），所以 insight_quality 的"语义新颖度"在默认配置下也是伪嵌入。
**🔍问题 P6-23**：① 默认 `embedding_dim=768`（L74）与 MiniLM-L6-v2 的 384 维不符；② `import_cache`（L304）把 `self.cache` 重新赋成普通 dict，**丢掉 LRU 约束**——后续无界增长；③ L17 docstring 谎称支持 OpenAI/DashScope。**这印证了第3章 P3-7 的"嵌入散落多处"——现在是 4 处**（retrieval MD5 / familiarity md5-seed / semantic_novelty 真嵌入 / tools/embeddings 默认 mock）。

**`vision.py`（539行）🔍 孤立**：`VisionClient` 三 provider（Anthropic/OpenAI GPT-4V/Qwen-VL），真实 POST 实现。`VisionModel` 7 常量但 `MODEL_CONFIGS` 只配了 6 个——LLaVA（L56）无配置→选它会用空 base URL 崩。**全项目无运行时消费者**（仅 tools/__init__ 重导出 + tool_registry 的 analyze_image/image_to_text ToolSpec 声明）。模型名 `claude-opus-4-6`/`claude-3-5-sonnet` 是非标准 ID，可能 404。

**`voice.py`（568行）🔍 孤立 + 🚨 递归 bug**：`VoiceOutput` 四 TTS 引擎（pyttsx3 离线/edge-tts/百度/讯飞 stub）。
**🔍问题 P6-24（🔴 真 bug，edge-tts 必崩）**：L336 定义 `async def _speak_edge`，L382 又定义同名 `def _speak_edge`（同步包装）——**后者覆盖前者**。L392 同步包装里 `loop.run_until_complete(self._speak_edge(...))` 调用的已是同步版自己→**无限递归**。edge-tts 的 async 实现（L336-380）是死代码。
**🔍问题 P6-25**：Windows 播放 `.mp3` 用 `System.Media.SoundPlayer`（只支持 wav）必抛；`_queue`/`_worker_thread` 异步脚手架声明从不使用；`gender`/`emotion` 参数存储但不应用；讯飞 `_init_xunfei` 报成功但 `_speak_xunfei` 恒失败。无运行时消费者。

**`messaging.py`（370行）🟡 主动消息**：`Message`+4 渠道（Console/Log/Webhook/Callback）+`MessagingSystem` 单例。被 web/app（initiative_messaging 配置）+ tool_registry（send_message ToolSpec）引用。**🔍问题 P6-26**：`message_queue`/`_worker_thread` 异步脚手架声明但 send_message 全同步；URGENT 绕过 enabled 的逻辑（L258）被基类 send 的 enabled 检查抵消；webhook `timeout=10` 硬编码；单例无线程锁且 `__init__` 副作用建目录。

### 6.10 `memory_tools.py` + `web_search.py` + `file_ops.py` + 辅助模块

**`memory_tools.py`（363行）🔍 孤立**：把记忆 CRUD 暴露为 3 个 OpenAI 工具（search_memory/get_recent_conversations/save_to_memory）+ `MemoryToolExecutor(life_loop)`。**全项目无引用**——被 tool_executor + dynamic_tool_registry 的工具体系取代。**🔍问题 P6-27**：`_search_memory` 用 `query.split()[:5]` 分词——中文无空格→单个整句 token；`save_to_memory` 的 confidence `0.9 if high else 0.7`（low/medium 退化同值）；MEMORY_TOOLS 是可变全局且按引用返回。

**`web_search.py`（157行）🟡 Bing 搜索 Tool**：`WebSearchTool(Tool)` 真 Bing API（`api.bing.microsoft.com`，L121）+ mock 回退（无 key 时）。**🔍问题 P6-28**：与 tool_executor._web_search（LLMClient 联网）是**两套搜索实现**，且 tool_executor 把 web_search 列入 `disabled_tools`（safe_mode 时）。任意 Bing 失败被 `except Exception` 吞成 mock 结果（L78），调用方无法区分真假。mock 含 `rank` 字段、真结果不含→下游 `r["rank"]` KeyError。

**`file_ops.py`（226行）🟡 沙箱文件 Tool**：`FileOpsTool(Tool)` read/write/list + allow-list 目录 + 禁止模式（`*.exe`/`*.dll`/`/etc/passwd`）。被 memory/skills/file_skill、safety/contract_guard 引用。**🔍问题 P6-29（🔴 安全 fail-open）**：`_is_path_allowed`（L121）`if self.allowed_dirs:`——**allow-list 为空时跳过目录检查**，只剩 `forbidden_patterns` 兜底，而 `Path.match` 对 `/etc/passwd` 这类绝对路径模式在 Windows 上不可靠。即空配置=任意目录可读写。`max_read_size` 限制读但 `_write_file` 无大小上限。

**`cost_model.py`（262行）🔍 死代码**：`CostModel` + 9 个 `ModelType` + PRICING 表。**仅 tools/__init__ 重导出，从不实例化**。action_executor 里的 `tool_spec.cost_model` 是 ToolSpec 的 dict 字段，**不是这个类**。**🔍问题 P6-30**：价格全是 2023 年旧值（gpt-4-turbo 0.01/0.03、claude-2 EOL）；`estimate_tool_cost` 内联硬编码（web_search=0.01 等）与 ToolSpec.cost_model 重复；`estimate_text_tokens` 的 `model` 参数接受但不用。**四套成本概念并存**（本表 / action_executor 的 `tokens*0.000001` / ToolSpec.cost_model dict / common/constants.ToolCostConstants 的 CAPS）。

**`llm_cache.py`（295行）🔍 完全孤立**：SHA256 key 的 LLM 响应缓存（LRU+TTL+线程锁）。**全项目零引用**（docstring 有用法示例但无调用方）。**🔍问题 P6-31**：① `temperature` **故意排除在 key 外**（L104）→ 高温随机响应被当确定性的缓存命中，返回错误温度的结果；② key 截断到 16 hex（64bit，大负载碰撞风险）；③ 构造默认 TTL=3600 vs 单例 TTL=1800 不一致；④ `evictions` 计数器被容量淘汰/TTL 过期/手动 prune 三处重复递增，统计失真。

**`tool_system_v2.py`（606行）🟡 增强工具系统（接入弱）**：`ToolCall`/`ToolResult`/`ToolCallRecord`（可回放）/`ToolCallLogger`（JSONL 审计）/`SmartToolParser`（中文自然语言→工具意图）/`EnhancedToolExecutor`。被 tools/__init__ 重导出。**🔍问题 P6-32**：`SmartToolParser` 用中文关键词+正则从自然语言提工具调用（如"读取xxx.txt"→read_file）——与器官的 `_parse_llm_thought_to_actions`（第5章 P5-15）同源脆弱性；`EnhancedToolExecutor` 重复实现 read_file/write_file/list_files（第三套）；`get_replay_output` 靠 input_hash 精确匹配回放。

### 6.x tools/ 速查与调试点

**精读优先级**：`llm_client.py`（活路径，必懂）> `tool_executor.py`（执行+代码全开）> `dynamic_tool_registry.py`（活注册表）> `blackboard.py`（论文核心但默认休眠，看架构债）。

**接入真相表**（grep + life_loop/action_executor 确认）：
| tools 模块 | 接入方式 | 状态 |
|---|---|---|
| llm_client.LLMClient | action_executor(`LLM_MODE=single`默认)/器官/检索/life_loop全局 | ⭐ **活路径** |
| llm_api.UniversalLLM | blackboard 专家/growth/skills/tool_executor._web_search | 🟡 黑板/生成路径用（默认休眠） |
| llm_orchestrator.LLMMOrchestrator | action_executor(仅`LLM_MODE≠single`)/web/chat_interactive | 🟡 默认休眠，多模型时丢 tools(P6-18) |
| tool_executor.LLMToolExecutor | action_executor USE_TOOL+CHAT 工具循环 | ⭐ 活路径（execute_code 默认 FULL_ACCESS） |
| dynamic_tool_registry | life_loop:281 注册 + action_executor:620 to_llm_format + :777 get | ⭐ 活路径 |
| tool_registry.ToolRegistry | action_executor:225,506 `.get()` | 🟡 仅 .get() 用，list_available/get_all 无调用 |
| blackboard.MindFieldOrchestrator | 经 llm_orchestrator，`LLM_MODE≠single` | 🟡 **默认休眠**（核心 bug P6-13/14/15） |
| embeddings.EmbeddingsTool | cognition/insight_quality.py（try 包裹） | 🟡 接入但默认 mock（无语义） |
| messaging.MessagingSystem | web/app + tool_registry send_message | 🟡 接入 |
| tool_protocol.ToolExecutor | — | 🔴 **完全死代码**(P6-12) |
| safe_executor.SafeCodeExecutor | — | 🔴 **完全孤立**(P6-20，最完善的沙箱没用) |
| code_exec.CodeExecutionTool | — | 🔴 **完全孤立** |
| cost_model.CostModel | — | 🔴 **完全死代码**(P6-30) |
| llm_cache.LLMCache | — | 🔴 **完全孤立**(P6-31) |
| memory_tools.MemoryToolExecutor | — | 🔴 **完全孤立**(被 tool_executor 取代) |
| vision.VisionClient | — | 🔴 **无运行时消费者** |
| voice.VoiceOutput | — | 🔴 **无运行时消费者 + edge-tts 递归 bug**(P6-24) |
| tool_system_v2.EnhancedToolExecutor | tools/__init__ 重导出 | 🟡 接入弱，与 tool_executor 重复 |
| capability.CapabilityManager | life_loop:48 导入(被:71遮蔽) | 🔴 **被遮蔽死代码**(P8-1) |
| web_search.WebSearchTool | tool_registry ToolSpec 声明 | 🟡 与 tool_executor._web_search 重复(P6-28) |
| file_ops.FileOpsTool | memory/skills + safety/contract_guard | 🟡 接入但 fail-open(P6-29) |

**高危区**：
1. **三 LLM 客户端并存**（P6-1）：llm_client/llm_api/llm_orchestrator 接口不一，改一处漏两处
2. **execute_code 默认全开**（P6-9）：LLM 拥有完全本地执行权，沙箱配置形同虚设
3. **工具目录四重定义**（P6-11）：ToolRegistry/DynamicToolRegistry/AVAILABLE_TOOLS/skills 四套，名/风险/schema 不统一
4. **黑板情绪路径死**（P6-13）：update_mood 签名错，多模型模式情绪更新整条静默失效
5. **嵌入四处且三处伪**（P6-23/P3-7）：默认配置下语义检索/联想/洞察新颖度都是噪声
6. **最完善的沙箱没接**（P6-20）：safe_executor AST 沙箱孤立，活路径是无过滤的 FULL_ACCESS
7. **edge-tts 递归崩溃**（P6-24）：voice.py 同名方法覆盖，第一调用即无限递归
8. **成本四套**（P6-30）：价格/系数各处不一，相差可达 75×

**与论文的对应**：Mind Field 多专家黑板 = §3.4.2（blackboard.py，默认休眠）；工具五元组 = §3.11（tool_registry.ToolSpec，pre/post 不求值）；确定性工具+回放 = §3.11.3（tool_protocol 死框架 + tool_system_v2 的 ToolCallLogger/Strict Replay）；成本跟踪 = §3.11.3（cost_model 死代码）。

---

## 7. 安全 + 持久化 `safety/` + `persistence/`

> 13 文件/约 2604 行，覆盖论文 §3.13（五重安全管道：完整性/验证/风险/预算/能力）+ §3.11.3（确定性回放与可复现性）+ §3.4 跨重启记忆持久化的工程支撑。这两层是"动作执行前的闸门"和"进程结束后的留存"。
>
> **本章最大发现（两个）**：
> 1. **safety/ 的代码执行走最弱沙箱**——第6章 P6-20 记录的"4 重代码执行实现"在此确认：生产路径用的是 `tools/tool_executor._execute_code_sandboxed`（裸子串黑名单 + `exec`），而 `safety/sandbox.py`（路径策略沙箱）和 `tools/safe_executor.py`（AST 审计沙箱，最完善）**双双闲置**。论文 §3.11.3 的安全沙箱形同虚设。
> 2. **persistence/ 整包是孤岛**——`core/life_loop.py` **完全不导入 `persistence.*`**。`replay_mode` 参数只被存为属性 + 打印一行 log（life_loop.py:137），**不驱动任何回放逻辑**。论文 §3.4 严格回放 / §3.11.3 可复现性 在 `persistence/` 已实现但未接入主循环 → 生产环境无确定性回放能力。真正的持久化由 `common.jsonl.JSONLWriter` + `memory/episodic.EpisodicMemory` + `life_loop._persist_final_state` 完成。
>
> **目录结构**：
> ```
> safety/ (7 文件/1217 行)
> ├── __init__.py            (40)   聚合导出(含僵尸导出)
> ├── integrity_check.py     (61)   ✅ PHASE 9a 状态完整性闸门
> ├── risk_assessment.py     (50)   ✅ PHASE 9c 风险评分(接管 immune 职能)
> ├── budget_control.py      (78)   ✅ PHASE 9d 预算闸门(漏检 3 维)
> ├── contract_guard.py      (288)  🔴 死代码(契约/边界/欺骗检测)
> ├── hallucination_check.py (300)  🔴 死代码(正则启发式幻觉检测)
> └── sandbox.py             (400)  🔴 死代码(文件系统/网络策略沙箱,非代码exec)
>
> persistence/ (6 文件/1387 行)
> ├── replay.py              (762)  ⭐ 3模式回放引擎(最大,仅测试引用)
> ├── tool_call_log.py       (204)  ⚠️ tool_calls.jsonl 写入器(无人调用)
> ├── event_log.py           (159)  ⚠️ episodes.jsonl 写入器(无人调用)
> ├── snapshot.py            (116)  ⚠️ 快照管理器(无人调用,与 replay 重复)
> ├── storage.py             (123)  🔴 KV 存储抽象(无人调用,后端未实现)
> └── __init__.py            (23)
> ```

### 7.0 PHASE 9 五重安全检查 ↔ 模块映射（先看这个）

论文 §3.13 的"五重安全检查"在 life_loop.py:1230-1290 实现，但**只有 3 个子相位真正由 safety/ 包承担**：

| 子相位 | life_loop 行 | 实际逻辑位置 | 是否 safety/ 模块 | 失败动作 |
|---|---|---|---|---|
| **9a 完整性** | L1230 `check_integrity` | `safety/integrity_check.py` | ✅ | → SLEEP |
| **9b 验证器** | L1248 `self.verifier.verify_action` | **`cognition/verifier.py`**（第4章） | ❌ 不在 safety/ | → SLEEP/REFLECT |
| **9c 风险** | L1267 `assess_risk` (>0.8) | `safety/risk_assessment.py` | ✅ | → REFLECT |
| **9d 预算** | L1278 `check_budget` | `safety/budget_control.py` | ✅ | → SLEEP |
| **9e 能力缺口** | L1286 `self._check_action_capability` | **`core/capability_manager`**（第8章） | ❌ 不在 safety/ | 异步触发成长，不阻塞 |

> 9a→9b 用 `else` 串联（L1236），9c/9d/9e 是独立 `if` 顺序闸门。**safety/ 包真正接线的只有 9a/9c/9d 三个函数级模块**（共 189 行），其余 1028 行（contract_guard + hallucination_check + sandbox）是死代码。

---

### 7.1 `safety/integrity_check.py` (61行) ✅ PHASE 9a 状态完整性闸门
**职责**：`check_integrity(action, state) → {ok, reason?}`——动作 vs 内部状态（压力/能量/情绪）的硬约束。

**4 个检查**（L6-59）：
1. **自我修改禁令**（L29）：`"modify_self" in params` → 拒。
2. **高压限流**（L33-40）：`stress > 0.9` 仅放行 CHAT/REFLECT/SLEEP。
3. **低能保命**（L43-50）：`energy < 0.1` 仅放行 SLEEP（注释"修复：允许 SLEEP 否则死锁" L48）。
4. **低落禁探索**（L53-59）：`mood < 0.1` 禁 EXPLORE/LEARN_SKILL。
全程 `stress/energy/mood` 先 `max(0,min(1,x))` 归一化（L35/45/55）。

**接入**：life_loop.py:1230（9a）。失败时 `selected_action = SLEEP(duration=1)`（L1233）。

**🔍问题 P7-1（🟢 魔数）**：`0.9/0.1/0.1` 三阈值硬编码，与 risk_assessment 的 `0.8/0.2`、budget_control 的 `1000` 风格不一，无集中配置。
**🔍问题 P7-2（🟢 黑名单过窄）**：`modify_self` 只查 params 键名，不覆盖 tool_id 含 modify 的工具调用。

### 7.2 `safety/risk_assessment.py` (50行) ✅ PHASE 9c 风险评分
**职责**：`assess_action(action, context=None) → float`——动作风险评分 [0,1]，**接管了免疫器官的风险职能**（呼应第5章 P5-20）。

**公式**（L6-50）：
```
risk = clamp01( clamp01(action.risk_level)
                + (0.8 if USE_TOOL 且 code_exec/exec/eval/os.system/subprocess else 0)
                + (0.1 if stress>0.8 else 0)
                + (0.15 if energy<0.2 else 0) )
```
code_exec 探测（L31-37）：`tool_id=="code_exec"` 或 params 代码串命中 `exec(/eval(/os.system(/subprocess/code_exec`。

**接入**：life_loop.py:1267（9c），阈值 `risk_score > 0.8` → 降级为 `REFLECT(purpose=risk_avoidance)`（L1268-1270）。

**🔍问题 P7-3（🟡 与 immune_organ 功能重叠）**：
| 维度 | safety/risk_assessment.py | immune_organ.assess_action_risk (L794-822) |
|---|---|---|
| 接入 | ✅ life_loop 9c | ❌ 仅 tests/test_organ_coordination.py |
| 模型 | action.risk_level + 状态加成 | action.risk_level + 信任分 + 安全模式倍率（permissive/balanced/cautious/strict/lockdown） |
| 成熟度 | 简单 | 更丰富（动态安全模式、行动信任分表） |
免疫器官的 `assess_action_risk` 更完善却只被测试调，证实"immune 未接线、safety/ 接管"。**建议合并或显式选其一**。
**🔍问题 P7-4（🟢 魔数）**：`0.8/+0.1/+0.15` 与 life_loop 截断 `0.8` 硬编码。

### 7.3 `safety/budget_control.py` (78行) ✅ PHASE 9d 预算闸门
**职责**：`check_budget(action, state, budget_remaining) → {ok, reason?}`——动作执行前校验 CostVector 不超剩余预算。

**默认值**：`DEFAULT_CPU_TOKENS_BUDGET=1000`（L7）、`DEFAULT_MONEY_BUDGET=1.0`（L8）。
**逻辑**：取 `action.estimated_cost`，缺省回退 `CostVector(cpu_tokens=100)`（L31）→ 非负校验 → 比 `cpu_tokens`（L56）→ 比 `money`（L72）。
**公式**：`ok = (cost.cpu_tokens ≤ remaining.cpu_tokens) AND (cost.money ≤ remaining.money)`。

**接入**：life_loop.py:1278（9d）。`budget_remaining` 由 `self.ledger.resources[name].remaining()` 构造（L1274-1277）。

**🔍问题 P7-5（🟡 预算校验不完整）**：`CostVector`（models.py:226）含 6 维 `cpu_tokens/io_ops/net_bytes/latency_ms/risk_score/money`，但 `check_budget` **只检查 cpu_tokens 和 money**，**io_ops/net_bytes/latency_ms/risk_score 完全漏检**——成本向量其他维度形同虚设。
**🔍问题 P7-6（🟢 默认成本硬编码）**：缺省 `CostVector(cpu_tokens=100)`（L31）、阈值 `1000/1.0`（L7-8）魔法数，未走 `core/resource_config.py` 的 ResourceConfig，两套预算来源易漂移。

### 7.4 `safety/contract_guard.py` (288行) 🔴 整模块死代码
**职责（声称）**：契约/完整性/边界/欺骗四类违规检测 + 违规惩罚计算。

**关键类**：
- `ViolationType`（L23）：INTEGRITY/CONTRACT/BOUNDARY/DECEPTION。
- `ContractViolation`（L31）：`violation_type/severity[0,1]/description/action`。
- `ContractGuard`（L47）：
  - `check_action(action, context) → (bool, ContractViolation?)`（L75）：依次 `_check_integrity → _check_contract → _check_boundaries`。
  - `_check_integrity`（L127）：声明目标 vs tool_id 的关键词交集启发式（无交集即判 DECEPTION 严重度 0.3）；目标冲突检测。
  - `_check_contract`（L184）：需审批工具（`requires_approval=["file_write","code_exec","api_call"]`）未经 `user_approved` 即 CONTRACT 严重度 0.8。
  - `_check_boundaries`（L216）：file_ops 工具路径越界检查（`Path.relative_to`）。
  - `get_violation_penalty`（L265）：`base_penalty × severity`，base 字典 `{INTEGRITY:-0.5, CONTRACT:-0.8, BOUNDARY:-0.6, DECEPTION:-1.0}`。

**🔍问题 P7-7（🔴 整模块死代码）**：全仓 grep `ContractGuard`（除 safety/）**0 命中**。life_loop 9a-9e 无任何子相位调用 ContractGuard。288 行契约守卫从未运行。
**🔍问题 P7-8（🔴 三套契约系统互不连通）**：
1. `tools/tool_registry.py:20-21` `ToolSpec.preconditions/postconditions`——**字符串型**（如 `"energy > 0.1"`），全仓 grep 无任何代码 parse/eval，**纯文档性字段，永不求值**。
2. `tools/tool_protocol.py:92-169` 另一套 `add_precondition(Callable)` 可调用对象系统，在 `execute()` 内求值（L149/L169）——但 tool_protocol 本身是死代码（见第6章 P6-12）。
3. `safety/contract_guard.py` 第三套独立类——死代码。
**三者互不连通，实际生效的只有 tool_protocol 那套（而它整体也是死的）**。论文 §3.11 的契约前置/后置条件机制在生产环境完全不工作。
**🔍问题 P7-9（🟡 欺骗检测误报率高）**：`_check_integrity` 的 `set(declared_goal.lower().split()) & set(tool_id.split("_"))` 关键词交集法误报极高——`tool_id="file_ops"` 几乎不与任何自然语言目标词重叠，会把正常文件操作一律判 DECEPTION。这也是它即使被接线也不敢启用的重要原因。

### 7.5 `safety/hallucination_check.py` (300行) 🔴 整模块死代码
**职责（声称）**：基于正则启发式的幻觉检测（**非** LLM-as-judge）。

**关键类**：
- `HallucinationScore`（L18）：`is_hallucination/confidence[0,1]/evidence/category`。
- `HallucinationChecker`（L34）：
  - `confidence_threshold=0.7`（L48）。
  - `uncertainty_patterns`（L51）：`r"I think"/"maybe"/"possibly"/"might be"/"could be"/"not sure"/"uncertain"`。
  - `hallucination_indicators`（L62）：`r"as far as I know"/"if I recall correctly"/"I believe"/"I'm pretty sure"`——**定义后从未使用**（死字段）。
  - `check_response(response, context) → HallucinationScore`（L69）：`max(uncertainty, unsupported, attribution) > 0.7` 即判幻觉。
  - `_check_uncertainty_language`（L111）：`matches/max(1,words)·50`（魔数 50）。
  - `_check_unsupported_claims`（L135）：无 sources 返回 0.3；句子切分 → 关键词 50% 重叠判支撑。
  - `_check_source_attribution`（L173）：引用模式 `r"\[(\d+)\]"/"according to"/"source:"/"from (.+?),"`。

**🔍问题 P7-10（🔴 整模块死代码）**：全仓 grep `HallucinationChecker`（除 safety/）**0 命中**。9a-9e 无对应子相位。本设计应为 PHASE 11（输出阶段）的 CHAT/反思内容把关，但 `ActionExecutor` 的 CHAT 路径（第8章）从未调用它。
**🔍问题 P7-11（🟡 正则仅英文）**：`uncertainty_patterns`/`citation_patterns` 全是英文短语，对 GenesisX 中文输出场景（organ_llm_session.py 全中文 prompt）几乎永不触发，等于失效。
**🔍问题 P7-12（🟢 死字段）**：`hallucination_indicators`（L62-67）定义后无引用。

### 7.6 `safety/sandbox.py` (400行) 🔴 整模块死代码（4 重沙箱之一）
**职责**：**文件系统/网络/资源策略沙箱**（注意：**不是**代码执行沙箱——它没有 `exec`，只做路径与配额检查）。

**关键类**：
- `SandboxConfig`（L17）：`allowed_dirs/forbidden_patterns/max_memory_mb=512/max_cpu_percent=50/network_allowed=False`。
- `SandboxViolation(Exception)`（L35）：带 violation_type。
- `Sandbox`（L43）：
  - `check_path_access(path, op)`（L64）：symlink 双重检查（L83/L100）、`resolve`、`relative_to` 越界判定、`forbidden_patterns` 通配。
  - `_verify_path_components`（L140）：逐级向上查 symlink（防 symlink 攻击）。
  - `_check_system_paths`（L186）：跨平台关键目录黑名单（Win `C:\Windows`/`System32`/`Program Files`；Unix `/etc /sys /proc /dev /bin /sbin /usr/*`）。
  - `check_path_access_for_write`（L236）、`check_network_access`（L254）、`check_resource_usage`（L276）、`get_safe_temp_dir`（L308）、`cleanup_temp`（L326）。
- `SandboxManager`（L335）：`MAX_SANDBOXES=100`（L373）。

**🔍问题 P7-13（🔴 整模块死代码）**：全仓 grep `Sandbox(`/`SandboxManager`（除 safety/）**0 命中**。`__init__.py` 导出但无人用。`tools/file_ops.py` 自带了一套 `allowed_dirs`/`forbidden_patterns`/`_is_path_allowed`（file_ops L101-142），根本不调 `safety.Sandbox`。
**🔍问题 P7-14（🔴 确认"4 重沙箱/代码执行实现"问题——最完善的两套都闲置）**：

| # | 位置 | 类型 | 实际机制 | 在 live 路径？ |
|---|---|---|---|---|
| 1 | `safety/sandbox.py` `Sandbox` | **文件系统/网络/资源策略** | `Path.resolve`+`relative_to`，无 exec | ❌ 死代码 |
| 2 | `tools/safe_executor.py` `SafeCodeExecutor` | **AST 审计** + 受限 globals + 线程超时 | `ast.NodeVisitor` + `_create_safe_globals` + threading | ❌ 未被 life_loop 调用 |
| 3 | `tools/code_exec.py` `CodeExecutionTool` | 子进程 + 关键词字符串过滤 | `_contains_forbidden` 正则 + `subprocess.run([sys.executable, tmp])` | ⚠️ 工具已注册但 life_loop 走 #4 |
| 4 | `tools/tool_executor.py:501 _execute_code_sandboxed` | **子串关键词黑名单** | `if pattern in code` 直接拒 + `exec()` | ✅ **LIVE** |

实测 live 路径：`life_loop → ActionExecutor.execute → life_loop.tool_executor (LLMToolExecutor).execute → _execute_code → _execute_code_sandboxed`（action_executor.py:538-539/788/916）。**最弱的 #4（裸子串匹配 + exec）反而是生产路径，最强的 #2（AST 审计）闲置**。配合第6章 P6-9（dynamic_tool_registry 用 `LLMToolExecutor(safe_mode=False)` 即 FULL_ACCESS）——**生产环境的代码执行实际上是无沙箱全开**。这是本包最严重的高危区，也是整个项目最高危的安全问题。
**🔍问题 P7-15（🟡 Sandbox 缺资源限制执行能力）**：`check_resource_usage`（L276）只比较传入数值，**不实际采样**进程内存/CPU（无 `resource`/`psutil`），即 `max_memory_mb=512` 是声明值，无强制力。即便被接线也是空壳。

---

### 7.7 `persistence/replay.py` (762行) ⭐ 3 模式回放引擎（全包最大，仅测试引用）
**职责**：`ReplayEngine`——确定性回放引擎，支持 3 模式，含 LLM 输出哈希校验、状态快照、分叉（fork）管理、漂移（divergence）检测。论文 §3.11.3 可复现性 + §3.4 严格回放。

**3 模式**（`ReplayMode` Enum L31-35）：
| 模式 | 行为 | LLM 非确定性处理 |
|---|---|---|
| `STRICT`（L33） | 完全确定性回放，**精确匹配** | `should_replay_output`（L410-411）始终返回 True（永不重新执行，只回放缓存输出）；`hash_exact` SHA-256 严格比对（L151-157） |
| `SEMANTIC`（L34） | 允许 LLM 重执行 | `llm_tools={"llm_chat","llm_generate","llm_complete"}`（L417 硬编码）会重新执行；`hash_semantic`（归一化 lowercase/折叠空白/去尾标点 L131-134）+ Jaccard 相似度（阈值 `>0.4`，coverage `>0.5`，L181）判定 |
| `FORK`（L35） | 从某 tick 分叉做 what-if | fork 点之前回放、之后重新执行（L423-425）；不校验（L187-188） |

**关键类**：
- `ReplayState`（L38-81）：回放状态快照。字段 `tick/session_id/fields/weights/gaps/mode/stage/current_goal/memory_stats/ledger`。`to_dict`/`from_dict`。
- `DivergenceReport`（L84-92）：漂移报告，`divergence_type ∈ {state,output,hash}`，`severity ∈ {low,medium,high}`。
- `LLMOutputHasher`（L95-188）：`hash_exact`（SHA-256 前 16 字符 L102-113）、`hash_semantic`（L115-136）、`verify_match`（L138-188，Jaccard=|∩|/|∪| L173-175，coverage 双向 L178-179）。
- `StateSnapshotManager`（L191-289）：`save_snapshot`（每 `snapshot_interval` ticks 落盘 `snapshot_{tick:06d}.json`）、`load_snapshot`、`get_nearest_snapshot`（内存优先→磁盘倒序扫描）。
- `ReplayEngine`（L292-666）：
  - `__init__(replay_dir, mode, snapshot_interval=10)`（L302-337）：加载 `episodes.jsonl`/`tool_calls.jsonl`/`states.jsonl`。
  - `should_replay_output(tool_id, tick)`（L399-425）：决定工具回放还是重执行。
  - `verify_state_consistency(original, replayed, tolerance=0.01)`（L427-494）：逐字段比对 mode/stage（high）/affect（medium）/weights（low）。
  - `fork_at`/`record_fork_action`/`save_fork_branch`（L568-628，写 `forks/{branch}_{ts}.jsonl`）。
  - `get_divergence_summary`（L531-566，**仅返回最后 10 条** L564 硬编码 `[-10:]`）。
- 模块级：`create_replay_engine`（L670-687）、`verify_replay_consistency`（L690-715，**存根**：注释自承"simplified, In production iterate through all ticks"）。
- `__main__` 测试块（L719-762）。

**记录 vs 回放**：记录侧依赖外部（life_loop/EventLogger/ToolCallLogger）写入 jsonl；引擎只读。STRICT 模式永不调用真实工具/LLM，全靠 `tool_calls.jsonl` 缓存输出。时间处理：tick 作为离散整数索引（`get_episode(tick)` 用列表下标 L387），无 wall-clock 回放。

**🔍问题 P7-16（🔴 整包未接入 life_loop——头号问题）**：`replay_mode` 参数在 `LifeLoop.__init__`（L103/169）被接收并存为 `self.replay_mode`，但**仅用于 L137 的一行 log 打印**（`f"Replay mode: {self.replay_mode or 'None (live)'}"`）。全文件无任何 `should_replay_output`/`ReplayEngine` 调用，tick 执行时不查询回放缓存。**回放模式是 dead flag——life_loop 永远是 live 执行**。`persistence.ReplayEngine` 只在 `tests/conftest.py:355` 被实例化做测试。
**🔍问题 P7-17（🔴 回放 schema 不匹配）**：`_load_episodes`（L339-350）读 `episodes.jsonl` 期望 `EventLogger.EpisodeSchema` 的扁平字段（含 `weights`/`gaps`/`delta`），但生产 `EpisodicMemory` 写入的是 `EpisodeRecord`（memory/schema.py，字段含 `state_snapshot`）。**回放引擎加载后会因字段缺失崩溃或得到默认值**。同理 `_load_tool_calls`（L352）期望 `tick` 字段，但 `tools/tool_system_v2.ToolCallLogger` 写的 schema 无 tick（见 P7-23）。
**🔍问题 P7-18（🟡 存根/未完成）**：`verify_replay_consistency`（L690-715）注释自承"simplified"，未真正迭代所有 tick——返回的 `consistent` 只反映空 divergences 列表，恒为 True。
**🔍问题 P7-19（🟡 硬编码魔数）**：`snapshot_interval=10`（L198/306/673）、Jaccard 阈值 `0.4`/coverage `0.5`（L181）、tolerance `0.01`（L432）、hash 截断 `[:16]`（L113/136）、`llm_tools` 集合（L417）、`[-10:]`（L564）。
**🔍问题 P7-20（🟢 LLM 非确定性局限）**：STRICT 通过"只回放缓存、不重执行"规避非确定性（合理）；SEMANTIC 的 Jaccard/coverage 是弱启发式，对同义改写（"Hello"/"Hi"）会判 mismatch——已知局限非 bug。

### 7.8 `persistence/event_log.py` (159行) ⚠️ episodes.jsonl 写入器（无人调用）
**职责（声称）**：append-only JSONL 写 `episodes.jsonl`，带 Pydantic 校验 + fsync 崩溃恢复。

**关键类**：
- `EpisodeSchema(BaseModel)`（L22-62）：扁平字段 `tick/session_id/timestamp/observation/action/reward/delta/state/weights/gaps/goal/mode="work"/stage="adult"/cost/tags`。`validate_weights_simplex`（L54-62）校验 `0.99 ≤ Σweights ≤ 1.01`（魔数 L60）。
- `EventLogger`（L65-159）：
  - `__init__(log_path)`（L75-83）：建父目录、`touch()`、`_file_handle=None`（**L83/L155-159 是死代码**：字段声明但从不赋值，`close()` 永远 no-op）。
  - `write_episode(episode_data)`（L85-114）：Pydantic 校验 → `model_dump()`(v2)/`dict()`(v1) → `orjson.dumps(OPT_APPEND_NEWLINE)` → `open('ab')`+`fsync`。
  - `read_all_episodes()`（L116-141）：逐行读，JSONDecodeError 跳过+warn。

**🔍问题 P7-21（🔴 episodes.jsonl 三重写入器）**：
1. `persistence/event_log.py:EventLogger`——**本文件，无人调用**
2. `memory/episodic.py:EpisodicMemory._persist_episode`（L108-130，**生产实际使用**，被 life_loop.py:1476 调）
3. 间接：`life_loop.episode_writer`（common.jsonl.JSONLWriter，写的是 `states.jsonl`，见 L564——命名误导）
三者 schema 不一致：EventLogger 用扁平 `observation/action/reward/delta`，EpisodicMemory 用 EpisodeRecord（字段含 `state_snapshot`）。**回放引擎读的是 EventLogger schema，与实际写入不匹配（P7-17）**。
**🔍问题 P7-22（🟡 死代码）**：`_file_handle` 字段（L83）+ `close()`（L155-159）从未真正使用，每次 `write_episode` 都重新 `open('ab')`（L111），与 docstring"持有句柄"矛盾。

### 7.9 `persistence/tool_call_log.py` (204行) ⚠️ tool_calls.jsonl 写入器（无人调用）
**职责（声称）**：写 `tool_calls.jsonl` 审计日志，含输入/输出哈希、模型版本/参数、成本/延迟/风险、可选脱敏。

**关键类**：
- `ToolCallSchema(BaseModel)`（L24-56）：字段 `tick/session_id/timestamp/tool_id/tool_type/input_params/input_hash/output/output_hash/model_id/model_version/model_params/cost/latency_ms/risk_score/success/error/redacted`。
- `ToolCallLogger`（L58-204）：
  - `log_tool_call(...)`（L76-156）：12 参数；算 input_hash/output_hash → 可选脱敏 → fsync 写。
  - `get_tool_calls_for_tick(tick)`（L172-175，**全表扫描过滤**，无索引）。
  - `_hash_dict`（L177-184）：`orjson.dumps(OPT_SORT_KEYS)` → SHA-256 `[:16]`。
  - `_redact_sensitive`（L186-204）：键名含 key/password/token/secret → `[REDACTED]`。

**🔍问题 P7-23（🔴 tool_calls.jsonl 三重写入器，schema 不兼容）**：
1. `persistence/tool_call_log.py:ToolCallLogger`——**本文件，无人调用**，schema 有 tick+cost+risk_score+redacted
2. `tools/tool_system_v2.py:ToolCallLogger`（L63-160）——独立类，schema=`ToolCallRecord`（call_id/tool_name/parameters/input_hash/output/output_hash/success/error/execution_time/timestamp/model_version，**无 tick/cost/risk_score**）
3. `life_loop.tool_writer`（common.jsonl.JSONLWriter，**生产实际使用**，由 ActionExecutor._log_tool_call L160-170 写，schema={tick,session_id,timestamp,action_type,params,result,cost}，**无 tool_id/input_hash/output_hash**）
三者 schema 互不兼容。`replay.py:_load_tool_calls`（L352）按 `tick` 索引，而 tool_system_v2 版无 tick（默认 0）→ **回放时所有调用会聚到 tick 0**。
**🔍问题 P7-24（🟡 无索引）**：`get_tool_calls_for_tick`（L172）每次全文件扫描，长日志 O(n)。
**🔍问题 P7-25（🟢 脱敏仅英文）**：`_redact_sensitive` 只匹配 key/password/token/secret，中文/其他命名不覆盖。

### 7.10 `persistence/snapshot.py` (116行) ⚠️ 快照管理器（与 replay 重复）
**职责（声称）**：全量/增量状态快照存取，用于检查点与回放恢复。

**`SnapshotManager`**（L19-117）：
- `save_snapshot(tick, session_id, state, snapshot_type="full")`（L28-63）：写 `snapshot_tick_{tick}.json`，含 `{tick, session_id, timestamp, type, state}`。
- `load_snapshot(tick)`/`list_snapshots()`（按 tick 排序）/`get_latest_snapshot()`/`prune_old_snapshots(keep_last_n=10)`。

**🔍问题 P7-26（🔴 与 replay.StateSnapshotManager 重复）**：本文件 `SnapshotManager` 与 `replay.py:StateSnapshotManager`（L191-289）功能高度重叠（都存/取 tick→state 快照），但命名约定不同（`snapshot_tick_{tick}.json` vs `snapshot_{tick:06d}.json`）。两者互不兼容，**均未被 life_loop 调用**。
**🔍问题 P7-27（🔴 与 life_loop._persist_final_state 重叠）**：实际运行时状态持久化由 `life_loop._persist_final_state`（L1841-1884）完成，手写 state_dict 写入 `final_state.json`（含 tick/mode/stage/energy/mood/.../weights/gaps）。该 dict 与 `ReplayState.to_dict`/`snapshot.py` 的 state 结构**部分重叠但不一致**——无统一序列化层，重启时只读 `final_state.json`，回放/快照体系形同虚设。
**🔍问题 P7-28（🟡 增量是空壳）**：`snapshot_type="incremental"` 参数（L34）只进元数据，无任何增量差分/delta 计算。
**🔍问题 P7-29（🟡 无 import）**：全工程仅 `persistence/__init__.py` 导出，无任何 `.py` 实际使用。

### 7.11 `persistence/storage.py` (123行) 🔴 KV 存储抽象（无人调用）
**职责（声称）**：统一存储接口，支持 file/jsonl/sqlite/memory 后端（声明），实际仅实现 FILE。

**`Storage`**（L25-123）：
- `write(key, data)`（L44-58）：FILE→`{key}.json`。
- `read(key)`（L60-85）：cache 优先 → 磁盘。
- `append(key, item)`（L87-100）：**读全部→append→写全部**（O(n²) 反模式）。
- `delete`/`list_keys`/`clear_cache`。

**🔍问题 P7-30（🔴 无人使用）**：全工程零 `from persistence.storage`/`Storage(` 调用。
**🔍问题 P7-31（🟡 后端声明与实现不符）**：Enum 声明 SQLITE/MEMORY（L18-22），但 write/read/delete 全是 `if backend == FILE: ...` 后直接 return None（如 L85），SQLITE/MEMORY 路径无实现——**误导性 API**。
**🔍问题 P7-32（🟡 append 性能缺陷）**：读全表→改→写全表，对长列表（如 episodes）退化为 O(n²)，违反 JSONL append-only 设计初衷。

### 7.12 `persistence/__init__.py` (23行) ⚠️ 孤儿包门面
**🔍问题 P7-33（🟡 孤儿包）**：grep `from persistence` 全工程仅 `tests/conftest.py:31` 命中。`core/life_loop.py` 导入的是 `common.jsonl.JSONLWriter`（L32）和 `memory.episodic.EpisodicMemory`（L188），**完全不导入 persistence.\***。Docstring 所称职责与实际运行时持久化**重复且未被采纳**。

---

### 7.x safety/persistence 速查与调试点

**精读优先级**：
- safety：先看 7.0 PHASE 9 映射表（搞清 9a/9c/9d 才是活路径）→ 确认 P7-14（代码执行走最弱沙箱）→ 看 contract_guard 三套契约系统（P7-8）
- persistence：先确认 P7-16（整包未接入）→ 看 replay.py 3 模式设计（即便没接，设计本身有价值）→ 看 P7-21/23（三重写入器 schema 不兼容）

**接入真相表**（life_loop PHASE 9 + shutdown）：
| 模块 | life_loop 导入? | PHASE | 状态 |
|---|:---:|---|---|
| `safety/integrity_check.check_integrity` | ✅ life_loop:1230 | 9a | ✅ 接入 |
| `safety/risk_assessment.assess_action` | ✅ life_loop:1267 | 9c | ✅ 接入 |
| `safety/budget_control.check_budget` | ✅ life_loop:1278 | 9d | ✅ 接入 |
| `safety/contract_guard.ContractGuard` | ❌ | — | 🔴 **完全死代码**(P7-7) |
| `safety/hallucination_check.HallucinationChecker` | ❌ | — | 🔴 **完全死代码**(P7-10) |
| `safety/sandbox.Sandbox` | ❌ | — | 🔴 **完全死代码**(P7-13) |
| `persistence/replay.ReplayEngine` | ❌ | — | 🔴 **仅测试引用**(P7-16) |
| `persistence/event_log.EventLogger` | ❌ | — | 🔴 **无人调用**(P7-21) |
| `persistence/tool_call_log.ToolCallLogger` | ❌ | — | 🔴 **无人调用**(P7-23) |
| `persistence/snapshot.SnapshotManager` | ❌ | — | 🔴 **无人调用**(P7-26) |
| `persistence/storage.Storage` | ❌ | — | 🔴 **无人调用**(P7-30) |

**shutdown() 真实接线**（life_loop.py:1742-1884）：
- 关闭：`episode_writer.close()`（L1758）、`tool_writer.close()`（L1765）——均为 common.jsonl.JSONLWriter
- 持久化：`_persist_override_state`→`override_state.json`（L1812）、`_persist_value_parameters`→`value_parameters.json`（L1826）、`_persist_final_state`→`final_state.json`（L1846）
- **PHASE 16**（L1550 `ctx.advance_phase("persist_override")`）持久化 override 状态——**与 persistence 包无关**
- **`persistence/` 整包在 life_loop 的 init/shutdown/PHASE16 中零接线**

**高危区**：
1. **代码执行走最弱沙箱**（P7-14 + 第6章 P6-9）：生产路径是 `tool_executor._execute_code_sandboxed`（裸子串黑名单 + exec），safe_executor AST 沙箱闲置，实际 FULL_ACCESS 全开——**整个项目最高危的安全问题**
2. **persistence 整包孤岛**（P7-16）：life_loop 完全不导入 persistence.*，replay_mode 是 dead flag，论文 §3.11.3 可复现性在生产环境不工作
3. **safety 包 81% 死代码**（P7-7/10/13）：contract_guard(288) + hallucination_check(300) + sandbox(400) = **988 行从未运行**
4. **三套契约系统互不连通**（P7-8）：tool_registry 字符串版（不求值）/ tool_protocol Callable 版（整体死）/ contract_guard 类版（死）——论文 §3.11 契约机制完全不工作
5. **回放 schema 不匹配**（P7-17）：replay 读 EventLogger schema，生产写 EpisodeRecord——即便接入回放也会因字段缺失崩溃
6. **三重 episodes/tool_calls 写入器**（P7-21/23）：schema 互不兼容，是第3章 P3-2"持久化绕开 JSONLWriter"问题的延伸
7. **风险评估双实现**（P7-3）：safety/risk_assessment（活，简单）vs immune_organ.assess_action_risk（仅测试，更完善）——安全模式倍率等机制白写
8. **预算校验漏 3 维**（P7-5）：CostVector 6 维只查 cpu_tokens/money

**与论文的对应**：五重安全管道 = §3.13（PHASE 9a-9e，但只有 9a/9c/9d 在 safety/，9b 在 cognition/，9e 在 core/）；动作验证 = §3.11（cognition/verifier）；契约前后置条件 = §3.11（三套都失效）；确定性回放/可复现性 = §3.11.3（persistence/replay.py 实现了但未接入）；强证据 = §3.10.4（见第3章 P3-10 巩固证据门虚设）。

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

**✅问题 P8-4 已修 — GlobalState 与 FieldStore 双重真相源消除**：~~7 个情感标量字段同时存于 GlobalState 和 FieldStore，靠手工 `_sync_*` 同步~~。方案 A 实施：GlobalState 的 7 标量改为 **FieldStore 单一真相源委托**（property getter/setter 委托 FieldStore，未注入时用本地 fallback）。删除 `_sync_state_to_global`/`_sync_fields_to_global` 两个手工同步函数（-93 行）。FieldStore 在 `_init_stores` 注入 GlobalState。数据模型以 FieldStore 为准：7 个独立字段，energy/fatigue 不再折叠到 activity_fatigue，bond/trust 不再折叠到 relationship。1-tick 实测验证 7 标量零 drift。
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

**✅问题 P8-14 已修**：~~`FieldStore` 与 `GlobalState` 重复存 7 个字段~~（见 P8-4，已随方案 A 消除——GlobalState 7 标量委托 FieldStore，单一真相源）。
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
1. ~~**状态同步**（P8-4/P8-6）：GlobalState↔FieldStore 双真相源~~ ✅ P8-4 已修（方案 A：FieldStore 单一真相源委托）
2. **能力缺口→成长链路**（P8-11）：tool/tool_id 键不一致导致 USE_TOOL 永不驱动成长
3. **多轮对话**（P8-10）：响应覆盖 bug 让多轮工具调用丢正文
4. **自定义基因**（P8-7）：缓存吞掉 config，器官分化配置失效
5. **参数来源**：core 内魔法数遍地（阈值/系数/超时/价格），与第1章 P1-3 的"参数三重定义"问题叠加

**与论文的对应**：tick 17 阶段 ≈ 论文 Algorithm 1；PHASE 5 axiology = 论文 §3.5-3.6；PHASE 11 = 论文 §3.7；PHASE 9 = 论文 §3.13；override 状态 = §3.6.4；value learning = §3.12。

---

## 9. 入口 + Web `lifecycle/` + `web/` + 顶层脚本

> 15 文件/约 7k 行（lifecycle 3 文件 + web 2 个 .py + 顶层 8 个脚本）。这是"数字生命"对外的脸和手——把 `LifeLoop`（第8章）暴露成 CLI 交互、Web UI、长驻守护进程。**理解本章的前提是已读第8章 core/**。
>
> **本章最大发现（两个）**：
> 1. **`lifecycle/` 整包是第二条并行 tick 引擎——零接入**。`lifecycle/tick_loop.py`(704行) 自己实现了一套 17 阶段 `TickLoop`，但所有相位都是"简化实现"（retrieve 返回空、execute 不执行、memory_write 不写入、persist 不持久化、reward 恒 0）。run.py/web/daemon/chat_interactive **全部用的是 `core/life_loop.LifeLoop`**，没有任何入口 import lifecycle。`lifecycle/` 仅被 `tests/test_lifecycle.py` 引用——是早期原型，被 core/ 全面取代后沦为孤立脚手架（呼应第3-7章多处"孤立模块"模式，但这是整包级的孤立）。
> 2. **Web 是唯一真正多线程的入口，却对共享的 `life_loop` 完全不加锁**。Flask `threaded=True` + auto-run 后台线程 + 同步聊天线程池 + 异步聊天守护线程 + initiative tick **5 条路径并发调 `manager.life_loop.tick()`/`send_message()`**，而 `LifeLoop` 内部状态（state/fields/organs/episodic/...）**无一加锁**。这是全项目最隐蔽的并发高危区。
>
> **目录结构**：
> ```
> lifecycle/ (3 文件/784 行)        🔴 整包孤立(第二条 tick 引擎)
> ├── tick_loop.py          (704) 🔴 TickLoop——17阶段空壳实现(仅测试用)
> ├── genesis_lifecycle.py  (75)  🔴 GenesisLifecycle——TickLoop 薄包装(孤立)
> └── __init__.py           (5)
>
> web/ (2 .py + 6 html + 静态资源, Python 共 3168 行)  ⭐ 唯一真实 UI
> ├── app.py                (2894) ⭐ Flask app + 60+ 路由 + GenesisXManager
> └── websocket_server.py   (274)  🔴 WebSocket 服务(代码完整但被 app.py 硬禁用)
>
> 顶层脚本 (8 .py)
> ├── run.py                (155)  ⭐ 主入口:CLI 冒烟测试(单次 run_session)
> ├── chat_interactive.py   (607)  ⭐ 终端交互式聊天(自带工具循环)
> ├── daemon.py             (532)  🟡 长驻守护进程(PID+健康检查,被 web/daemon/* 调)
> ├── compile_code_docs.py  (338)  🟡 文档生成器(AST 扫源码,独立工具)
> ├── migrate_session.py    (48)   🟢 一次性脚本(旧 session_id 迁移)
> ├── run_tests.py          (57)   🟢 pytest 包装器
> ├── test_tools.py         (29)   🟢 冒烟测试(POST /api/chat)
> ├── setup.py              (76)   🟢 pip 安装入口
> └── __init__.py           (8)
> ```

### 9.0 入口全景（先看这个：哪个脚本连哪个核心）

```
                     ┌─────────────────────────────────────────┐
                     │       core/life_loop.LifeLoop (第8章)     │  ← 唯一真实引擎
                     └─────────────────────────────────────────┘
                          ▲            ▲            ▲            ▲
                          │            │            │            │
   run.py ────────────────┘            │            │            │  (run_session 批量 tick)
   chat_interactive.py ────────────────┘            │            │  (单条 process_input→tick)
   daemon.py ───────────────────────────────────────┘            │  (while True: tick)
   web/app.py ────────────────────────────────────────────────────┘  (send_message→tick / run_loop→tick)

   lifecycle/TickLoop  ◄── 仅 tests/test_lifecycle.py  (🔴 孤立的第二引擎,核心不连)
```

**关键事实**：4 个真实入口（run/chat_interactive/daemon/web）**都直连 `LifeLoop`**，构造方式各异但殊途同归——`load_config() → LifeLoop(config, run_dir) → tick()/run_session()`。**没有一层公共的"入口胶水"**，导致配置加载、run_dir 命名、safe_mode 读取、shutdown 处理在 4 处各写一遍（见 P9-3）。

### 9.1 `run.py` (155行) ⭐ 主入口（冒烟测试）
**职责**：命令行批量运行。`parse_args()` → `load_config(Path(config))` → `LifeLoop(config, run_dir)` → `run_session(max_ticks)` → `shutdown()`。

- **参数**：`--config`(默认 config 目录)/`--ticks`/`--artifacts`/`--seed`/`--mode`(work/friend/sleep/reflect/play)。
- **run_dir 命名**：`artifacts/run_{UTC时间戳}{_seed?}`——**每次运行新建独立目录**（与 web 的固定 `artifacts/web_run`、daemon 的 `artifacts/daemon_{ts}` 三种命名策略，见 P9-3）。
- **错误处理**：`KeyboardInterrupt` 优雅退出；其他异常 print + `sys.exit(1)`；`finally` 必 `shutdown()`。
- **LLM 缺失降级**：检测 `config["llm"]["api_base"]` 为空时只打印警告（不退出），让系统以"模拟模式"跑——但下游 LifeLoop 是否真的"模拟"取决于各模块对 LLM 不可用的处理（器官会 fallback 规则、action_executor CHAT 会返回错误，见第5/8章）。

**🔍问题 P9-1（🟢）**：`run.py` 注释示例写 `--config config/runtime.yaml`（L6），但 `--config` 实际是**目录**（传给 `load_config(Path(config))`，common/config.py 按目录读多个 yaml）。注释误导。

### 9.2 `chat_interactive.py` (607行) ⭐ 终端交互式聊天
**职责**：`GenesisXChat` 类——带 ANSI 着色、自主调度器、工具调用的终端聊天。**自建一套 LLM 工具调用循环**，但 `process_input` 实际走 `LifeLoop.tick()`。

**初始化链**（`__init__`）：`load_dotenv` → `load_config` → `LLMToolExecutor(safe_mode=runtime.safe_mode)` → `_configure_api` → `_init_llm` → `LifeLoop(config, run_dir=artifacts/chat_{ts})` → `_init_scheduler`(AutonomousScheduler) → `_init_system_message` → `tick(0)` → `_greet`。

**process_input 数据流**（L342，**真正的对话路径**）：
```
user_input → self._pending_user_input
           → life_loop.get_user_input = get_user_input_callback  (注入回调)
           → life_loop.tick(t=state.tick)                          (走完整 17 阶段)
           → _update_conversation_history                          (双写: self.messages + episode)
           → _extract_response(episode)                            (从 outcome.status/params.response 提文本)
```
**注意**：和 web/app.py 的 `send_message` 是**同一套机制**（注入 `get_user_input` 回调 → tick → 提取响应），两边各写一遍（见 P9-4）。

**🔍问题 P9-2（🟡 LLM 客户端选型不一致）**：`_init_llm`（L242）在 `multi_model.enabled` 时用 `LLMMOrchestrator`，否则**优先 `llm_api.create_llm_from_env`**（L268），失败才回退 `llm_client.LLMClient`。而第6章确认**活路径是 `llm_client.LLMClient`**（action_executor/器官用它）。这里把 `llm_api.UniversalLLM`（第6章 P6-1 的"第二套客户端"）当首选，与 action_executor 内部用的不是同一个 client 实例——**chat_interactive 的 self.llm 和 life_loop 内部的 llm_client 是两个独立 HTTP 客户端/两套 session**，配置漂移风险（如 timeout/retry 各异）。

**🔍问题 P9-3（🟡）**：`_handle_tool_calls`（L396，自建工具循环：append assistant tool_calls → execute_tool_call → 再调 `self.llm.chat` 生成最终回复）**零调用**——`process_input` 直接走 `life_loop.tick()`（其内部 action_executor 有自己的工具循环）。这是早期"chat 自己管工具"设计的残留死代码。同理 `_autonomous_action`（L473）注释明说"实际由调度器处理"，返回 None，是死桩。

**🔍问题 P9-4（🟢 死导入）**：`from tools.tool_definitions import get_available_tools`（L39）导入后**全文件零引用**——chat_interactive 不把工具 schema 喂 LLM（工具调用完全交给 life_loop 内部处理）。

### 9.3 `daemon.py` (532行) 🟡 长驻守护进程
**职责**：`DaemonManager`——PID 文件管理 + 健康检查线程 + 巩固线程 + 信号处理 + 自动重启。`run()` 主循环 `while self.running: life_loop.tick(t=state.tick); sleep(0.1)`。

**进程管理**：
- `PID_FILE=artifacts/genesisx.pid`、`STATE_FILE=artifacts/daemon_state.json`、`LOG_FILE=artifacts/genesisx_daemon.log`。
- `write_pid`/`remove_pid`/`get_running_pid`（`os.kill(pid,0)` 探活，stale PID 自动清）。
- `stop_daemon`：Windows 用 `signal.CTRL_BREAK_EVENT`（**要求子进程同进程组，否则无效**），超时 `SHUTDOWN_TIMEOUT=30` 后 `TerminateProcess`/`SIGKILL` 强杀。

**两个后台线程**（`start_consolidation_thread`/`start_health_check_thread`）：
- **consolidation**：`CONSOLIDATION_INTERVAL=3600`s 触发——**但 worker 体只有 `# This would call the consolidator` 注释**（L182-183），**什么都不做**。是空壳线程。
- **health_check**：`CHECK_INTERVAL=60`s → `_health_check`（life_loop 非空 + stress<0.95）→ 失败调 `_attempt_recovery`（仅 `save_state`，注释"Could trigger consolidation here"——也是空壳）。

**🔍问题 P9-5（🔴 巩固/恢复线程是空壳）**：daemon 的两大卖点（定时巩固、健康恢复）**实现为空**——consolidation_worker 和 _attempt_recovery 都只有注释 TODO。daemon 实际只做"while tick + sleep"，与 run.py 的 `run_session` 无本质区别，多了 PID 文件和两个空转线程。

**🔍问题 P9-6（🟡 Windows 停止信号不可靠）**：`stop_daemon` 对 Windows 用 `CTRL_BREAK_EVENT`——该信号**只对与调用方共享控制台进程组的进程有效**，而 `api_daemon_start`（web/app.py:2529）用 `subprocess.Popen([..,'daemon.py'], creationflags=CREATE_NEW_CONSOLE)` 启动，新控制台进程组**收不到 CTRL_BREAK_EVENT**。web 停 daemon 在 Windows 上很可能无效，只能靠超时强杀。

### 9.4 `web/app.py` (2894行) ⭐⭐ Flask Web UI（最大入口）

> 全项目最大的单文件。Flask app + 60+ 路由 + `GenesisXManager`（封装 LifeLoop 的线程不安全单例）+ 主动消息机制 + SSE/WebSocket。

#### 9.4.1 启动与全局状态
- **`__main__`**（L2861）：`load_config('config')` → `manager.initialize(config)` → `run_server(debug=True)`（`threaded=True`）。
- **`ensure_initialized` before_request 钩子**（L1156）：每个请求前检查 `manager.life_loop is None` 则重新 `initialize`——**为 debug 热重载兜底**，但 `initialize` 重复调用会创建多个 LifeLoop（旧的未 shutdown，见 P9-7）。
- **全局单例**：`manager = GenesisXManager()`（L1149）、`genesis_instance`(L110，**声明后零引用**，死变量)、`message_queue`(L111，**声明后零引用**，死变量)、`state_lock`/`progress_lock`/`progress_queues`。

**🔍问题 P9-7（🔴 🔥 并发——全项目最隐蔽高危区）**：**5 条线程并发操作同一个 `manager.life_loop` 且无任何互斥锁**：
1. **auto-run 线程**（`/api/run/start` L2590 `run_loop`：`while: life_loop.tick()`，L2608）
2. **同步聊天线程**（`/api/chat` L1372 `ThreadPoolExecutor.submit(send_message)` → L590 `life_loop.tick()`）
3. **异步聊天守护线程**（`/api/chat async` L1357 线程 → `send_message` → tick）
4. **initiative tick**（`generate_initiative_message` L970 `life_loop.tick(tick+1)`）
5. **ensure_initialized/reinit/restart**（主线程重建/替换 `manager.life_loop`）

任一时刻 auto-run 在 tick 的同时，用户发消息触发另一条 tick——**两条线程同时读写 `state`/`fields`/`organs`/`episodic`/`tool_executor`**。`LifeLoop` 内部无锁（第8章 stores 四件套只做有界标量 clamp，非线程安全）。后果：状态撕裂、episode 乱序、tool_calls.jsonl 交叉写入、器官 propose 拿到半更新 state。`_initiative_lock`/`state_lock` 只保护消息队列和 is_running 标志，**不保护 life_loop**。这是 P9 系列最严重的问题。

#### 9.4.2 `GenesisXManager`（L196-1146）—— LifeLoop 的线程不安全门面
**核心字段**：`life_loop`/`is_running`/`messages`(对话历史)/`tool_executor`/`llm`/`llm_available`/`_initiative_queue`/`_activity_log`。

**initialize**（L273）：`LifeLoop(config, run_dir=artifacts/web_run)`（**固定目录**，非时间戳）→ 建 `LLMToolExecutor` → `life_loop.tool_executor = tool_executor`（**注入**，覆盖 LifeLoop 自建的 executor）→ `_init_llm`。

**🔍问题 P9-8（🟡 run_dir 固定→重启覆盖）**：web 用固定 `artifacts/web_run`（run.py/daemon 用时间戳目录）。每次 `ensure_initialized`/`api_reinit`/`api_restart_system` 重建 LifeLoop **复用同一目录**——但 `EpisodicMemory` 的恢复逻辑读 `episodes.jsonl`（session_id=genesisx_persistent 跨重启累积），而 schema/skill 不持久化（第3章 P3-5）。run_dir 固定 + episodic 跨会话累积是**有意设计**（保持记忆连续），但 schema/skill 清零意味着 web 重启后"知识"丢失——与 run.py 的隔离目录策略语义相反，两套策略并存易混。

**send_message → _process_with_llm**（L487/L556）：注入 `get_user_input` 回调 → `tick(t=state.tick+1)` → `_extract_response`。**关键 hack**：显式 `next_tick = current_tick + 1`（L578-579）强制递增，注释"确保每次对话都是新的时间步，episodes 不被覆盖"。这是 web 路径的 tick 计数约定，与 life_loop 内部自增可能冲突（见 P9-9）。

**🔍问题 P9-9（🟡 tick 计数双源）**：web/chat_interactive 显式传 `t=state.tick+1` 给 `tick()`，而 daemon/run.py/auto-run 不传或传 `state.tick`。`LifeLoop.tick` 的 `t` 参数语义不统一——web 路径依赖"传入的 t 会被设为新 tick"，若 LifeLoop 内部也自增（第8章需核对），会出现 tick 跳号或倒退。

#### 9.4.3 主动消息机制（initiative messaging）⭐ 特色功能
**论文意图**：数字生命在无用户输入时**主动**发起对话（好奇心/依恋/无聊/胜任驱动）。

**触发评估 `_evaluate_initiative`（L727）**：
- **时间门**：距上次主动消息 >`MIN_INITIATIVE_INTERVAL=60`s。
- **4 触发器**（任一达标）：`curiosity gap>0.60` / `loneliness>0.50`（=距交互时间/300 + attachment gap）/ `boredom>0.50` / `competence gap>0.60 且 mood>0.70`。
- **生成**：`_generate_initiative_with_llm`（从 `organ_llm.yaml:initiative_messaging` 读 use_default_llm/temperature/max_tokens，构造中文 prompt 调 LLM），失败 fallback 到 `_get_fallback_messages`（按 trigger_type 选硬编码中文模板）。

**两条触发路径**：
- **轮询式**（`/api/initiative` GET → `check_and_generate_initiative`）：前端定时轮询，实时评估生成。**这是活路径**。
- **预生成式**（`try_generate_initiative_async`）：**注释明说"已改为实时模式，此方法不再预生成"，函数体是 `pass`**——`send_message`（L538）和 `run_loop`（L2623 每3tick）都调它，**全是空调用**。是迁移残留。

**🔍问题 P9-10（🟡 initiative 双路径残留）**：`try_generate_initiative_async`（L1041）是空 `pass`，但 `send_message`/`run_loop` 仍调它；真正的逻辑全在 `check_and_generate_initiative`（轮询触发）。预生成路径（`_initiative_queue`/`add_initiative`/`get_pending_initiative`/`generate_initiative_message`）整套队列机制**因改实时模式而变成死代码**。注释自承但代码未清。

**🔍问题 P9-11（🟡 initiative 触发与 P9-7 并发叠加）**：`generate_initiative_message`（L944）在持 `_initiative_lock` 时调 `life_loop.tick(tick+1)`（L970）——即"主动说话"会跑一个完整 tick。若此时 auto-run 也在 tick，P9-7 的并发冲突在 initiative 路径上重演。`_initiative_lock` 只保护 initiative 队列，不保护 tick。

#### 9.4.4 路由分类（60+ 路由，按职责归 8 类）

| 类别 | 路由 | 说明 |
|---|---|---|
| **页面** | `GET /`、`/chat`、`/monitor`、`/dashboard`、`/settings` | render_template |
| **状态/指标** | `GET /api/status`、`/api/metrics`、`/api/memory`、`/api/messages`、`/api/values`、`/api/organs`、`/api/system-info`、`/api/episodes` | 读 manager 状态 |
| **聊天（核心）** | `POST /api/chat`（同步/async）、`GET /api/progress/<id>`（SSE）、`GET /api/stream`（状态 SSE）、`GET /api/initiative`、`/api/initiative/debug` | 对话 + 主动消息 |
| **配置** | `POST /api/configure`、`GET /api/config`、`POST /api/config/memory`、`/api/config/runtime`、`GET/PATCH /api/organ-llm/config`、`POST /api/organ-llm/config`、`POST /api/reinit`、`/api/restart-system`、`/api/reset` | 热改配置 + 重启 |
| **LLM/器官控制** | `GET /api/llm/statistics`、`/api/llm/mode`、`GET,POST /api/organs/parallel-mode`、`POST /api/organs/toggle`、`POST /api/set-mode`、`/api/set-safe-mode` | 运行时调控 |
| **记忆** | `GET /api/memory/search`、`POST /api/memory/consolidate`、`/api/clear-memory` | 记忆操作 |
| **守护进程/run** | `GET /api/daemon/status`、`POST /api/daemon/start`、`/api/daemon/stop`、`POST /api/run/start`、`/api/run/stop` | 子进程/后台 tick |
| **活动日志/日志** | `GET /api/logs`、`/api/activity/logs`、`/api/activity/stream`、`POST /api/activity/clear` | 日志流 |

**🔍问题 P9-12（🟡 配置热改→重启链路脆弱）**：`/api/configure`（L1627）改 yaml/env 后**不自动重启** manager，需前端再调 `/api/reinit` 或 `/api/restart-system`。而 `_update_env_mode_only`/`_reset_yaml_to_global`/`_update_yaml_experts`（L1478-1624）三套 yaml 编辑函数各自只改部分文件，调用方需知道改哪个——无统一"提交配置"入口。`api_reinit` 调 `load_config()`（L1204 **无参**，与 `__main__` 的 `load_config(Path('config'))` 不一致——一个走默认路径一个显式传，行为可能不同）。

**🔍问题 P9-13（🟡 SSE 队列无超时清理）**：`/api/progress/<id>`（L1224）的 `progress_queues[session_id]` 在客户端断开（GeneratorExit）时清，但若 async chat 线程异常退出前没 put None（L1350 的 finally 只在异常路径 put），SSE 连接会**每30s 心跳直到客户端超时**，队列残留。`progress_queues` 无 TTL/无定期扫除。

#### 9.4.5 多模型 LLM 适配（`MultiModelAdapter` L123）
当 `LLM_MODE≠single` 时，`_init_multi_model_llm` 建一个 `MultiModelAdapter` 包装 `LLMOrchestrator`，对外伪装成单模型 `chat()/generate()` 接口。配置来源：先找 `config/multi_model.yaml`/`mind_field.yaml`，找不到则 `_build_multi_model_config_from_env`（按 `M_COORD_API_BASE` 等环境变量逐专家构建）。

**🔍问题 P9-14（🟡 与第6章 P6-18 同源）**：`MultiModelAdapter.chat`（L164）转调 `orchestrator.chat(messages, tools=tools)`——但第6章 P6-18 记录 orchestrator 多模型分支**丢 tools**（blackboard.process 不接收 tools）。web 多模型模式下，工具调用经适配器→orchestrator→blackboard 链路静默丢失工具定义。这是 web 层暴露的、根在第6章的缺陷。

#### 9.4.6 安全配置（`_validate_production_security` L52）
启动时检测生产环境（`FLASK_ENV=production` 或 docker/render/heroku 标志），生产环境**强制要求** `SECRET_KEY` 和 `CORS_ORIGINS` 环境变量（缺失 raise），开发环境用固定 dev key + localhost CORS + warning。

**🔍问题 P9-15（🟢）**：这是**全项目唯一真正面向"部署"的安全代码**（第1章 auth.py 是多用户认证，与此不同）。但 GenesisX 核心是单实例桌面数字生命（第1章 P1-9 已记"多用户 Web 模块疑似过度工程"），生产部署检测与项目定位存在张力——若不部署，这套 SECRET_KEY/CORS 校验是"过度安全"；若部署，则又不够（无 HTTPS 强制、无 rate limit、`/api/*` 全无认证）。定位模糊。

### 9.5 `web/websocket_server.py` (274行) 🔴 完整但被硬禁用
**职责**：`WebSocketServer`（websockets 库）——实时双向通信，支持 ping/chat/stream_chat/get_state/broadcast。`start_in_thread` 在独立线程跑 asyncio 事件循环。`broadcast_state_sync` 从 Flask 同步线程跨线程调度广播协程。

**🔍问题 P9-16（🔴 整模块运行时禁用）**：`app.init_websocket`（L2794）**第一行就 `return`**（注释"暂时禁用 WebSocket，专注于修复聊天功能"）。即 WebSocket 代码完整（274行）但**启动即跳过**，`ws_server` 恒 None，`broadcast_state_to_ws` 永远 early return。实时推送实际全走 SSE（`/api/stream`、`/api/progress`）。**这是 web 层最大的死代码**（完整功能被一行 return 关闭）。
**🔍问题 P9-17（🟡）**：`_handle_stream_chat`（L116）注释"暂时使用非流式方式模拟"——按 10 字符分块 + `sleep(0.02)` 假装流式；`_get_current_state`（L155）恒返回 `{"status":"running"}`（注释"需要从外部注入"但没人注入）。即便启用 WebSocket，这两处也是占位符。

### 9.6 `lifecycle/` (3文件/784行) 🔴 整包孤立——第二条 tick 引擎
> **核心结论**：`lifecycle/tick_loop.py` 实现了一套与 `core/life_loop.LifeLoop` **平行**的 17 阶段 tick，但每个相位都是空壳。全包仅 `tests/test_lifecycle.py` 引用，**没有任何真实入口连它**。

#### `tick_loop.py` (704行) 🔴
**`TickLoop`** 类：`PHASES`（17 个，与论文 Algorithm 1 同名）+ `_init_state`（论文 §3.2 状态向量）+ `run_tick`（顺序执行 17 相位）。

**与 LifeLoop 的关键差异**（逐相位对比）：
| 相位 | tick_loop 实现 | life_loop 实现 |
|---|---|---|
| body_update | mood×0.99 衰减（L357） | 昼夜节律能量恢复+无聊更新（第8章 PHASE1） |
| retrieve | **返回空**（L441 `retrieved=[]`） | 智能检索决策+混合检索（第3章） |
| axiology | softmax(tau=2.0)（L477，与 P1-3 的 τ 冲突值一致） | 5维 features→gaps→WeightUpdater→utilities |
| goal_compile | 按 max_gap 选 goal_map 字符串（L504） | GoalCompiler 多目标编译（第4章） |
| plan_propose | **硬编码 CHAT "Processing..."**（L559） | 器官 propose_actions（第5章） |
| execute | 只存 `last_action` 不执行（L592） | ActionExecutor 全分派（第8章） |
| reward_affect_update | **reward=0.0, delta=0.0 恒定**（L604-605） | compute_reward+RPE+mood/stress 闭环 |
| memory_write | **不写入**（L629 `{"written": False}`） | episodic.append |
| value_learn/soul_learn | **不更新**（L638/647） | ValueLearner/人格更新 |
| persist | **不持久化**（L686 `{"persisted": False}`） | JSONLWriter+final_state.json |

**🔍问题 P9-18（🔴 整包孤立 + 第三套参数源）**：tick_loop 是 GenesisX 的**第二份完整 tick 实现**（704行），但：①无任何入口连它；②所有相位是占位空壳；③它自带第三套硬编码参数（VALUE_SETPOINTS 与 core/state.py 不同：homeostasis 0.85 vs 0.7、safety 0.70 vs 0.8；tau=2.0 呼应 P1-3；middle_vars 公式与 axiology/personality.py 的 OCEAN→ET/CT/ES 是**第三套定义**）。这是第1章 P1-3"参数三重定义"的又一爆发点，且因为是死代码，参数不一致不致运行时错误，但**误导性极强**（读代码者可能以为这是活引擎）。

#### `genesis_lifecycle.py` (75行) 🔴
`GenesisLifecycle`：薄包装 TickLoop，加 `offline_interval=50` 触发 `_run_offline_consolidation`（**只 `self.offline_runs += 1` 计数，不真巩固**）。`shutdown` 是 `pass`。整类孤立。

#### `__init__.py` (5行)
导出 `TickLoop`/`GenesisLifecycle`——但项目内无 import lifecycle。

### 9.7 其余顶层脚本（工具类）
- **`compile_code_docs.py` (338行)** 🟡：`DocGenerator`——AST 扫源码生成 API 文档（JSON）。独立工具，不被其他模块 import。可能就是生成本 CODE_MAP 辅助信息的工具之一。
- **`migrate_session.py` (48行)** 🟢：一次性脚本，把 `artifacts/web_run/episodes.jsonl` 的旧 session_id 批量改为 `genesisx_persistent`。run 后需手动 mv `.jsonl.new`。已完成使命，留作历史。
- **`run_tests.py` (57行)** 🟢：`subprocess` 调 pytest，生成覆盖率报告。纯包装。
- **`test_tools.py` (29行)** 🟢：手动冒烟测试，POST 两条消息到 `/api/chat`（要求 web 已起）。非 pytest，是 ad-hoc 脚本。
- **`setup.py` (76行)** 🟢：pip 安装入口，读 README/requirements。
- **`__init__.py` (8行)**：项目根当包（罕用）。

### 9.x 入口/Web 速查与调试点

**精读优先级**：`web/app.py:GenesisXManager`（看 life_loop 门面 + 并发隐患）> `chat_interactive.process_input`（对比 web 的 send_message，看重复）> `daemon.run`（看空壳线程）> lifecycle/tick_loop（确认整包孤立）。

**入口接线真相表**：
| 入口 | 连的核心 | run_dir 策略 | tick 方式 | LLM 客户端 | 状态 |
|---|---|---|---|---|---|
| `run.py` | LifeLoop | `run_{UTC_ts}` | run_session(max_ticks) | life_loop 内部 | ✅ 主入口 |
| `chat_interactive.py` | LifeLoop | `chat_{UTC_ts}` | 单条 process_input→tick | self.llm(llm_api 首选) | ✅ 终端 UI |
| `daemon.py` | LifeLoop | `daemon_{UTC_ts}` | while True: tick | life_loop 内部 | 🟡 巩固/恢复空壳(P9-5) |
| `web/app.py` | LifeLoop(via manager) | 固定 `web_run` | send_message→tick / run_loop | manager.llm(single/multi) | ⭐ 唯一 UI（并发高危 P9-7） |
| `lifecycle/*` | TickLoop(空壳) | — | run_tick | 无 | 🔴 **整包孤立**(P9-18) |

**高危区**：
1. **Web 并发无锁**（P9-7）：5 线程并发 tick 同一 life_loop，state/fields/episodic 无线程安全——**入口层最严重问题**
2. **lifecycle 整包孤立**（P9-18）：784 行第二条 tick 引擎，参数第三源，零接入
3. **WebSocket 硬禁用**（P9-16）：274 行完整代码被一行 return 关闭
4. **daemon 卖点空壳**（P9-5）：巩固/健康恢复线程体是 TODO 注释
5. **入口胶水四份重复**（P9-3 的具体）：config 加载/run_dir 命名/safe_mode 读取/shutdown 在 4 入口各写一遍，无公共层
6. **initiative 死队列**（P9-10）：改实时模式后预生成队列机制整套变死代码
7. **chat_interactive 工具循环死代码**（P9-3）：_handle_tool_calls/_autonomous_action 零调用

**重复实现清单**（跨章交叉引用）：
- **tick 引擎**：`core/life_loop.LifeLoop`（活，1883行）vs `lifecycle/tick_loop.TickLoop`（死，704行）
- **life_loop 门面/回调注入**：`web/app.py:GenesisXManager.send_message` vs `chat_interactive.py:GenesisXChat.process_input`（同机制各写一遍）
- **LLM 客户端选型**：chat_interactive 首选 llm_api、web 首选 llm_api、action_executor/器官 用 llm_client——第6章 P6-1 三客户端问题在入口层的具体暴露
- **run_dir 策略**：run/chat_interactive/daemon 时间戳目录 vs web 固定目录
- **tick 计数**：web/chat 显式 `t=state.tick+1` vs daemon/run/auto-run 不传或传 state.tick（P9-9）
- **守护进程停止信号**：daemon.stop_daemon vs web/api_daemon_stop 各写一遍（且 Windows 均不可靠 P9-6）

**与论文的对应**：入口层无直接论文对应（论文是算法层，入口是工程层）。主动消息（initiative）对应论文 §3.5.2 数字生命的"自主性"（价值缺口驱动自发行为），是入口层对论文"主动性"的唯一工程化实现。

---

## A. 全局问题清单（按优先级）

> 精读 Phase 1-2(common+axiology+affect) + Phase 8(core) + Phase 3(memory) + Phase 6(tools) + Phase 4(cognition/perception/metabolism) + Phase 7(safety/persistence) + Phase 9(入口+Web) 发现的问题。`🔴高危` `🟡中` `🟢低`。新会话优化时按此排序。部分行合并多个同源 ID（如 P7-22/24/25）。
>
> **状态标记**：`✅已修` = 已修复（详见文末"已修复"表）；`✅部分已修` = 部分修复；`✅记录已知` = 评估后记录为已知问题不修；无标记 = 未修。截至 2026-07-13：高优先级 29 项中 28 项已处理，**仅剩 1 项**（P5-21 器官学习状态持久化，需架构设计）。

### 🔴 高优先级（影响正确性/可维护性）

| ID | 问题 | 位置 | 影响 |
|---|---|---|---|
| **P0-1** 🆕⭐ ✅已修 | **价值→行为反馈环路断裂（实测验证，最核心运行时问题）**：25 tick 实测（run_20260706_062952），17/17 个有好奇/依恋缺口的 tick **100% 未产生 EXPLORE/CHAT**，全是 REFLECT/THINK。系统陷入"反思死循环"，mood 从 0.5 单调跌到 0 后永久卡死，负 RPE 未能驱动行为改变。根因：①价值系统正确识别需求（curiosity/attachment 缺口 0.45）但器官 `_parse_llm_thought_to_actions` 关键词失配（P5-15），LLM 叙事被 fallback 到 REFLECT ②驱动力信号无人消费（P5-10）③无用户输入时缺乏主动行动驱动。**这是"数字生命不像活的"的直接原因。** | organs/internal/* + life_loop PHASE 7→11 | 系统无法自主行动，mood 锁死归零，违背"自主数字生命"核心目标 |
| P2-3 ✅已修 | **axiology 严重代码重复**：value_dimensions.py(799行) 与 feature_extractors.py+utilities_unified.py 功能重叠 | axiology/ | 改一处忘另一处，行为不一致 |
| P2-5 ✅已修 | **drives/ 5维驱动力**：~~顶部注释禁用~~ 实际由 organ_manager 间接调用，drives_prompt 已接入器官（P5-10），过时禁用注释已清理 | axiology/drives/ | 实际是活的 |
| P1-4 ✅已修 | **两套配置加载体系并存**：config.py(load_config→dict) vs config_manager.py(ConfigManager→对象)，且都有 load_config() 同名函数。经 grep 确认 config_manager.py 零引用（4 入口全用 config.py），已删除该死代码文件（509 行） | common/ | ~~极易混淆，维护负担~~ 已消除 |
| P8-4 ✅已修 | **GlobalState 与 FieldStore 双真相源**：方案 A——GlobalState 7 标量改为 FieldStore 委托（property getter/setter），删 `_sync_*` 手工同步函数（-93行），单一真相源。1-tick 实测零 drift | core/state.py + core/stores/fields.py + life_loop.py | ~~两套真值~~ 已统一为 FieldStore |
| P8-10 ✅已修 | **多轮 CHAT 响应被覆盖**：`llm_response = round_response`(注释却写"累积")，前几轮正文丢弃 | core/handlers/action_executor.py:342 | 多轮工具调用场景用户只能看到最后一轮文字 |
| P8-11 ✅已修 | **tool/tool_id 键不一致**：gap_detector 读 `params["tool"]`，executor 读 `params["tool_id"]` | core/handlers/{gap_detector:243,action_executor:505} | USE_TOOL 的能力缺口检查永远拿空值，成长系统不被 USE_TOOL 驱动 |
| P8-7 ✅已修 | **自定义基因被缓存吞掉**：~~_get_differentiator() 空 config~~ PHASE 7 改用带 config 的 diff.select_organs()，custom_genes 生效 | core/life_loop.py + differentiate.py | 器官分化配置生效 |
| P8-18 ✅部分已修 | **6 模块共 ~2793 行孤立代码**：exceptions/scheduler/capability_router 完全死（C阶段已删）；emotion_decay/exploration/abstract_state 半死 | core/ | core 最大技术债，需决策删除/接入 |
| P3-5 ✅已修 | **Schema/Skill 永不持久化**：life_loop 用 `SchemaMemory()`/`SkillMemory()` 无参构造，shutdown 不调 save_to_disk，巩固产物重启清零 | memory/{schema,skill}.py + core/life_loop.py:190-191 | CLS 第2/3层知识无法跨会话累积，违背论文核心目标 |
| P3-15 ✅已修 | **联想网络无法持久化**：~~import_state 是 pass~~ _load_from_disk 末尾重建联想图（重放最近 1000 条 episodes 复用 _add_to_associative），重启不再丢失联想链接 | memory/episodic.py + familiarity.py | 验证：29 episodes → 25 节点 + 4 边 |
| P3-22 ✅已修 | **limb_guides/ 导入即崩 + 与 skills/ 逐字节重复**：4 个指南文件类名仍是 FileSkill 等，__init__ 导入 FileOpsGuide 必抛 ImportError→静默禁用整个包 | memory/limb_guides/ | ~600 行死代码（含 P3-22 的副本） |
| P3-6/P3-7 ✅已修 | **嵌入统一到 semantic_novelty 真嵌入**：~~retrieval MD5 / familiarity md5-seed 伪嵌入~~ 两处都委托 get_default_calculator().compute_embedding（sentence-transformers，P3-18 已接入） | memory/{retrieval,familiarity,semantic_novelty}.py | 语义检索/联想从噪声变为真实语义信号 |
| P5-6 ✅已修 | **UnifiedOrganManager 只写死代码**：~~从不查询/执行~~ 探查发现接入 PHASE 7 无收益（limb/plugin propose_actions 恒空 + WrappedBuiltinOrgan 丢属性），真正价值在 execute_capability。已在 USE_TOOL 路径接入（tool_registry 找不到时回退 unified_organ_manager），limb/plugin 能力可执行 | organs/unified_organ.py + action_executor.py | growth/plugins 注册的能力现在可通过 USE_TOOL 执行 |
| P5-10 ✅已修 | **驱动力→器官传导链路断裂**：PHASE 4.5 算的 drive_signals/drives_prompt 塞进 context，但 6 个器官的 propose_actions 无一读取它 | organs/internal/* + core/life_loop.py:920-922 | 驱动力信号被算出后无人消费，价值→驱动力→行为链断在最后一步 |
| P5-15 ✅已修 | **LLM 思考被中文关键词降级**：6 器官的 `_parse_llm_thought_to_actions` 用硬编码关键词把 LLM 输出转 Action，LLM 沦为叙事生成器 | organs/internal/*_organ.py | 器官决策权在关键词表而非 LLM；同义词/英文漏匹配→退化默认动作 |
| P5-20 ✅记录已知 | **immune 否决权/风险评估未接入**：3 个方法保留备用，安全执行由 safety/ 负责。论文§3.4.2 设计 immune 为最高优先级安全执行者，当前偏离为纯提案器官。完整接入会创造两套安全系统重叠，记录为已知设计偏差 | organs/internal/immune_organ.py | immune 只提 REFLECT，信任校准恒为默认 0.5 |
| P5-21 | **器官学习/项目状态全不持久化**：builder 的 active_projects/task_queue、archivist 的索引、scout/mind 的学习历史重启清零，且 record_* API life_loop 不调 | organs/internal/{builder,archivist,scout,mind}_organ.py | 器官"从经验学习"功能形同虚设 |
| P7-14 ✅已修 | **代码执行走最弱沙箱**：生产路径是 `tool_executor._execute_code_sandboxed`（裸子串黑名单 + exec），safe_executor.py 的 AST 审计沙箱完全闲置；config 的 sandbox_code_exec flag 无处读取 | tools/{tool_executor,safe_executor}.py + safety/sandbox.py + dynamic_tool_registry.py:442 | 论文§3.11.3 安全沙箱形同虚设，LLM 拥有完全本地执行权（FULL_ACCESS）——**整个项目最高危的安全问题** |
| P7-16 ✅已修 | **persistence/ 整包孤岛**：~~life_loop 不导入 persistence~~ 已接入 STRICT 回放（run.py --replay <dir>），PHASE 10 用缓存 outcome。4 个零引用写入器已删（event_log/tool_call_log/snapshot/storage）。解 P7-21/23/26/27/30/31/32 | persistence/replay.py + core/life_loop.py | 论文 C8 可复现性：STRICT 回放可用（budget 全 0 验证） |
| P4-1 ✅已修 | **`priority_level` 全域未设置**：GoalCompiler 只写 deprecated 的 `Goal.priority`(float)，从不写论文§3.8.1 的 1-6 级 `priority_level` 枚举 | cognition/goal_compiler.py:212,292 + 全项目 | 论文 6 级优先级系统运行时不生效，所有 Goal 恒为 MEDIUM(3) |
| P4-61 ✅已修 | **resource_pressure.py 与 state.py 公式语义相反**：metabolism 用 `RP = max(0, 1 − (α·C+β·M))`（论文版，死），state.py 用 `RP = α·C+β·M`（反转版，活） | metabolism/resource_pressure.py:92 + core/state.py:302-305 | 同一(compute,memory)给出相反的紧急判断；两套"有效无聊度"触发条件相反；生产路径偏离论文 |
| P4-64 ✅已修 | **METABOLISM 常量整段失效**：MetabolismConstants 在生产代码仅被 re-export，无任何读取点。已删除该死常量段（类+实例+re-export），运行时零变化。注：4 套 metabolism 硬编码（emotion_decay/boredom 等）仍并存，但"虚假单一来源"已消除 | ~~common/constants.py:167-188~~ + metabolism/ | ~~调参改一处无效~~ 已消除误导 |
| P4-31 ✅已修 | **self_perception 工具断链**：tool_registry 注册了 read_own_logs/system_stats，但 tool_executor 分发链只有 5 个分支无这两个→LLM 选了也找不到 handler | perception/self_perception.py + tools/{tool_registry,tool_executor}.py | 自我感知能力实质死代码化；pressure_score 无法回流到 HOMEOSTASIS |
| P7-8 ✅已修 | **三套契约系统互不连通**：tool_registry.ToolSpec.preconditions（字符串，永不求值）/ tool_protocol preconditions（Callable，整体死代码）/ contract_guard（独立类，死代码） | tools/{tool_registry,tool_protocol}.py + safety/contract_guard.py | 论文§3.11 契约前置/后置条件机制完全不工作 |
| P4-22 ✅已修 | **goal_progress.py 整模块死代码**：ProgressCalculator/GoalTracker/Milestone 零运行时引用；且其 GoalType 枚举(8)与 goal_compiler 模板(5)/planner 字符串(8+) 三套分类法互不匹配 | cognition/goal_progress.py | 562 行死代码；目标进度跟踪体系整体失效，goal.progress 停在 0.0 |
| P4-20 ✅已修 | **Q^insight 三重实现**：cognition/insight_quality.py（死）/ memory/consolidation.py InsightQualityEvaluator（活）/ eval/gxbs.py（评测）三套公式不一致 | cognition/insight_quality.py + memory/consolidation.py + eval/gxbs.py | 改一处忘另两处；活路径用 consolidation 版的 log(n+1)/log(10) 压缩 |
| P9-7 ✅记录已知 | **🔥 Web 并发无锁——5 线程并发 tick 同一 life_loop**：auto-run 线程 + 同步聊天线程池 + 异步聊天守护线程 + initiative tick + reinit/restart 主线程，5 条路径并发调 `manager.life_loop.tick()`/`send_message()`，而 LifeLoop 内部状态(state/fields/organs/episodic)无一加锁；`_initiative_lock`/`state_lock` 只保护消息队列和 is_running | web/app.py（api_chat/api_run_start/GenesisXManager）+ core/life_loop.py | 状态撕裂、episode 乱序、tool_calls.jsonl 交叉写入、器官 propose 拿半更新 state；入口层最严重问题，且极隐蔽（单线程测试无法暴露） |
| P9-18 ✅已修 | **lifecycle/ 整包孤立——第二条 tick 引擎(784行)**：tick_loop.py 实现完整 17 阶段但每个相位是空壳(retrieve 返回空/execute 不执行/memory_write 不写/persist 不持久化/reward 恒 0)；仅 tests/test_lifecycle.py 引用，4 个真实入口全用 core/life_loop.LifeLoop；且自带第三套参数(VALUE_SETPOINTS 与 state.py 不同、tau=2.0、OCEAN→ET/CT/ES 第三套公式) | lifecycle/（tick_loop.py/genesis_lifecycle.py/__init__.py）| 784 行死代码+第三套参数源(P1-3 的又一爆发点)；读代码者易误以为是活引擎 |

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
| P9-5 | **daemon 巩固/健康恢复线程是空壳**：consolidation_worker 体只有 `# This would call the consolidator` 注释，_attempt_recovery 只 save_state（注释"Could trigger consolidation here"）——daemon 两大卖点实现为空，实际只做 while tick+sleep | daemon.py（start_consolidation_thread/start_health_check_thread/_attempt_recovery） | 定时巩固/自动恢复不工作；daemon 与 run.py 无本质区别 |
| P9-16 | **WebSocket 整模块运行时硬禁用**：app.init_websocket 第一行 return（注释"暂时禁用"），ws_server 恒 None，broadcast_state_to_ws 永远 early return；274 行完整代码被一行 return 关闭，实时推送全走 SSE | web/app.py:2794 + web/websocket_server.py | web 层最大死代码（完整功能被关闭） |
| P9-3 | **入口胶水四份重复 + chat_interactive 工具循环死代码**：config 加载/run_dir 命名/safe_mode 读取/shutdown 在 run/chat_interactive/daemon/web 4 入口各写一遍无公共层；chat_interactive._handle_tool_calls/_autonomous_action 零调用(process_input 直接走 life_loop.tick) | run.py + chat_interactive.py + daemon.py + web/app.py | 维护负担；改一处忘另三处 |
| P9-2 | **chat_interactive LLM 客户端选型与活路径不一致**：_init_llm 首选 llm_api.create_llm_from_env(第二套客户端)，失败才回退 llm_client.LLMClient；而 action_executor/器官内部用 llm_client——chat_interactive 的 self.llm 与 life_loop 内部是两个独立 HTTP 客户端/两套 session | chat_interactive.py:268 + 第6章 P6-1 | 配置漂移(timeout/retry 各异)；第6章三客户端问题在入口层的具体暴露 |
| P9-9 | **tick 计数双源**：web/chat_interactive 显式传 t=state.tick+1(强制递增，注释"确保 episodes 不被覆盖")，daemon/run/auto-run 不传或传 state.tick；LifeLoop.tick 的 t 参数语义不统一 | web/app.py:590 + chat_interactive.py:360 + daemon.py:309 | tick 跳号或倒退；不同入口行为不一致 |
| P9-10 | **initiative 预生成路径整套死代码**：改实时模式后 try_generate_initiative_async 是空 pass，但 send_message/run_loop 仍调它；_initiative_queue/add_initiative/get_pending_initiative/generate_initiative_message 整套队列机制变死代码 | web/app.py（GenesisXManager） | 迁移残留未清；预生成队列永不消费 |
| P9-11 | **initiative tick 与 P9-7 并发叠加**：generate_initiative_message 持 _initiative_lock 时调 life_loop.tick(tick+1)，"主动说话"跑完整 tick；若 auto-run 也在 tick，P9-7 并发冲突在 initiative 路径重演；_initiative_lock 只保护队列不保护 tick | web/app.py:970 | 主动消息触发时并发冲突概率升高 |
| P9-12 | **配置热改→重启链路脆弱**：/api/configure 改 yaml/env 后不自动重启 manager，需前端再调 /api/reinit 或 /api/restart-system；_update_env_mode_only/_reset_yaml_to_global/_update_yaml_experts 三套 yaml 编辑函数各改部分文件无统一"提交"入口；api_reinit 调 load_config()无参与 __main__ 的 load_config(Path('config'))不一致 | web/app.py（api_configure/api_reinit/_update_*） | 配置改了不生效；调用方需知道改哪个文件 |
| P9-14 | **web 多模型模式丢 tools**：MultiModelAdapter.chat→orchestrator.chat→blackboard.process 链路丢工具定义(根在 P6-18)；web 多模型模式下工具调用经适配器静默失效 | web/app.py:164 + tools/llm_orchestrator.py + tools/blackboard.py | web 开 LLM_MODE=core5/full7 时函数调用失效 |
| P9-6 | **Windows 停 daemon 信号不可靠**：daemon.stop_daemon 和 web/api_daemon_stop 都用 CTRL_BREAK_EVENT，但 api_daemon_start 用 CREATE_NEW_CONSOLE 启动子进程（新控制台进程组收不到 CTRL_BREAK_EVENT）；web 停 daemon 在 Windows 上很可能无效只能超时强杀 | daemon.py:407 + web/app.py:2568 | Windows 下守护进程停止功能失效 |

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
| P6-3 | reasoning_content 仅在 content 完全为空时兜底(llm_client:256-258)，且与正文混在 text 字段；需澄清/改写第8章 P8-12 与第5章 P5-3 的"不解析 reasoning_content"表述 | tools/llm_client.py:256 |
| P6-5 | _chat_claude 降级路径引用未定义的 logger(L469 logger.warning)，anthropic 库失败时抛 NameError 被外层吞→降级逻辑本身有 bug | tools/llm_client.py:469 |
| P6-8 | _web_search 用 LLMClient 让 LLM"联网搜索"(非真搜索)，stepfun step-3.7-flash 不保证联网能力→可能是凭记忆编造；与 web_search.py 的 Bing 实现是两套 | tools/tool_executor.py:415 |
| P6-12 | tool_protocol.ToolExecutor(292行风险/契约/成本框架)完全死代码，零实例化；抽象基类 Tool 被4工具继承但实例从不注册进 ToolExecutor | tools/tool_protocol.py:179 |
| P6-15 | 黑板成本翻倍：M_REASON/M_COORD 先调 planner.propose_plans(内部可能再调LLM)，然后 L858 又无条件 client.chat→一次"推理"两次 LLM 调用 | tools/blackboard.py:486,858 |
| P6-17 | create_core5_experts 硬编码 gpt-4/gpt-3.5-turbo + openai.com 端点，与当前 stepfun 环境完全不匹配 | tools/blackboard.py:1298 |
| P6-18 | 多模型模式丢 tools：llm_orchestrator multi 分支调 process(user_message,context,tick) 不传 tools，blackboard.process 签名也不接收→多专家模式下函数调用静默失效 | tools/llm_orchestrator.py:206 |
| P6-21 | safe_executor 隐患：allowed_nodes 定义但不校验(实为黑名单)、max_memory_mb 不强制、线程超时不杀 worker、ExecutionTimeout 从不抛、reduce 非builtin 静默跳过 | tools/safe_executor.py |
| P6-22 | code_exec 子进程模式拥有完整 stdlib+网络+文件系统，仅靠可绕过的正则前置过滤；Windows 直跑模式无 SIGALRM→无超时；docstring 要求的回放模式未实现 | tools/code_exec.py:167 |
| P6-25 | voice：_queue/_worker_thread 异步脚手架声明不用；gender/emotion 存储不应用；讯飞 init 报成功但 speak 恒失败 | tools/voice.py |
| P6-26 | messaging：message_queue/_worker_thread 声明但 send_message 全同步；URGENT 绕过 enabled 被基类抵消；webhook timeout=10 硬编码；单例无线程锁且 init 副作用建目录 | tools/messaging.py |
| P6-27 | memory_tools 完全孤立(被 tool_executor 取代)：_search_memory 用 split() 中文分词失效；confidence low/medium 退化同值；MEMORY_TOOLS 可变全局按引用返回 | tools/memory_tools.py |
| P6-28 | web_search：与 tool_executor._web_search(LLMClient联网) 两套实现且后者 safe_mode 时禁用；Bing 失败静默降 mock；mock 含 rank 真结果不含→下游 KeyError | tools/web_search.py:78 |
| P6-30 | cost_model 完全死代码(仅重导出不实例化)：价格全2023旧值/含EOL模型；与 action_executor 的 tokens*0.000001、ToolSpec.cost_model、constants.ToolCostConstants 四套成本并存，相差可达75× | tools/cost_model.py |
| P6-31 | llm_cache 完全孤立：temperature 故意排除在 key 外→高温随机响应被当确定性缓存命中；key 截断16hex碰撞风险；TTL 默认值不一致(3600 vs 1800)；evictions 计数器三处重复递增 | tools/llm_cache.py |
| P6-32 | tool_system_v2.SmartToolParser 用中文关键词+正则提工具意图(同器官 P5-15 脆弱性)；EnhancedToolExecutor 第三套 read/write/list 实现 | tools/tool_system_v2.py |
| P5-5 | OrganMemoryWriter._llm_evaluate 用 find("{")/rfind("}") 提取 JSON，多 JSON 块/代码块含{} 会误提取；summary[:200] 与 thought[:500] 截断不一致 | organs/organ_llm_session.py |
| P5-7/P5-8 | Limb/Plugin.propose_actions 恒返回[]；6 真器官用 WrappedBuiltinOrgan 动态子类重复创建6次且丢失 _llm_session 等属性 | organs/unified_organ.py + core/life_loop.py |
| P5-11 | OrganManager.record_exploration 直接访问私有 _explored_topics，与 ScoutOrgan 同名字段完全独立，探索记录分散两处 | organs/organ_manager.py |
| P5-18 | mind 的 record_plan_outcome/successful_patterns 学习机制 life_loop 不调，_adapt_from_history 永不触发 | organs/internal/mind_organ.py |
| P5-23 | caretaker sleep 时间窗靠 tick×tick_duration/3600 估算，context 是否传 tick_duration 不确定；与 metabolism/circadian 真实节律可能不一致 | organs/internal/caretaker_organ.py |
| P4-2 | **目标进度永不更新**：goal_compiler.compute_progress(77行/8类型) 和 goal_progress.ProgressCalculator 两套进度计算 life_loop 都不调，goal.progress 停在编译时初值 0.0 | cognition/{goal_compiler,goal_progress}.py | 目标反馈循环断裂，PHASE 6 后无进度跟踪 |
| P4-7 | **Planner LLM 路径死代码 + life_loop 绕过**：propose_with_llm 零运行时调用；life_loop PHASE 8 内联自建 plans 不走 Planner；唯一调用者 blackboard 用规则版 propose_plans | cognition/planner.py + core/life_loop.py:1189 + tools/blackboard.py | docstring 宣传的"LLM-based planner"是死的 |
| P4-12/13 | **PlanEvaluator 风险/预算惩罚形同虚设**：life_loop 内联 plan 不含 risk_level(恒0)，预算被 ×100000 放大→λ_risk·Risk 和 budget_penalty 退化为死分支 | cognition/plan_evaluator.py + core/life_loop.py:1190,1199 | J(p|S_t) 评分退化为 weighted_value − 0.001·cost |
| P4-28 | **context_builder 硬编码假数据**：budget_tokens=10000/recent_errors=0 写死占位符（注释明说 Default/Simplified） | perception/context_builder.py:106-107 | 下游若读这两个键永远收到固定值 |
| P4-50 | **boredom.update_boredom 丢 4/7 参数**：life_loop 只传 boredom+dt×0.5，novelty/compute/memory/socially_engaged/apply_resource_override 全用默认→η_soc/η_nov/资源覆盖三条论文机制失效 | metabolism/boredom.py + core/life_loop.py:1663 | 无聊单调上升（η_idle 每 tick 都加），资源门控永不触发 |
| P4-53 | **circadian 时间源与模拟脱节**：time_mode 默认 realtime 且全仓库无配置，get_energy_level/get_fatigue_recovery_rate 用 datetime.now(utc) 墙钟，与 tick/sim_start_hour/caretaker 推算三者互不相干 | metabolism/circadian.py + core/life_loop.py:1644 | simulation 模式从未启用；昼夜节律与 tick 演化不同步 |
| P4-54 | **circadian 与 caretaker 睡眠窗口冲突**：circadian 用 UTC 墙钟+offline 01-04/14-15，caretaker 用 tick 推算+sleep 22-07，两者互不引用且窗口不一致 | metabolism/circadian.py + organs/internal/caretaker_organ.py | 同一时刻两个模块报不同时段；sleep window 22-7 在 metabolism 找不到 |
| P4-58 | **recovery.py 整模块死代码**：life_loop._update_body 用内联恢复公式(L1651-1659)绕过；sleep/friend/work 模式系统完全未采用 | metabolism/recovery.py + core/life_loop.py:1651 | 173 行死代码；论文§3.8.2 恢复机制按内联简化版实现 |
| P7-5 | **预算校验漏 3 维**：CostVector 含 6 维(cpu_tokens/io_ops/net_bytes/latency_ms/risk_score/money)，check_budget 只查 cpu_tokens 和 money | safety/budget_control.py | io_ops/net_bytes/latency_ms/risk_score 形同虚设 |
| P7-3 | **风险评估双实现**：safety/risk_assessment（活，简单）vs immune_organ.assess_action_risk（仅测试，更完善含安全模式倍率） | safety/risk_assessment.py + organs/internal/immune_organ.py:794 | 安全模式倍率/行动信任分等机制白写 |
| P7-7/10/13 | **safety 包 988 行死代码**：contract_guard(288 整模块死) + hallucination_check(300 整模块死) + sandbox(400 整模块死) | safety/{contract_guard,hallucination_check,sandbox}.py | 论文§3.13 安全管道覆盖度远超实际接线（只有 9a/9c/9d 三闸门活） |
| P7-17 | **回放 schema 不匹配**：replay._load_episodes 期望 EventLogger 扁平 schema，生产写 EpisodeRecord；_load_tool_calls 期望 tick 字段，tool_system_v2 版无 tick | persistence/replay.py:339,352 + memory/episodic.py + tools/tool_system_v2.py | 即便接入回放也会因字段缺失崩溃或调用聚到 tick 0 |
| P7-21/23 | **episodes/tool_calls 三重写入器 schema 不兼容**：persistence.EventLogger/ToolCallLogger(无人调) vs memory/episodic+ActionExecutor(生产) vs tools/tool_system_v2(独立)，三套 schema 互不兼容 | persistence/{event_log,tool_call_log}.py + memory/episodic.py + tools/tool_system_v2.py + core/handlers/action_executor.py | 第3章 P3-2"持久化绕开 JSONLWriter"的延伸 |
| P7-26/27 | **snapshot 体系双重失效**：snapshot.py 与 replay.StateSnapshotManager 功能重叠互不兼容，且均未被 life_loop 调用；实际用 life_loop._persist_final_state 手写 final_state.json | persistence/{snapshot,replay}.py + core/life_loop.py:1841 | 无统一序列化层，重启只读 final_state.json，回放/快照形同虚设 |
| P6-1 | **三 LLM 客户端并存**：llm_client(活路径)/llm_api(黑板用)/llm_orchestrator(门面) 接口签名/返回 dict 不一致，provider 检测逻辑重复；LLMMOrchestrator 类名拼写错误(双M)靠别名掩盖 | tools/{llm_client,llm_api,llm_orchestrator}.py | 改一处漏两处，维护高危 |
| P6-9 | **execute_code 默认 FULL_ACCESS**：dynamic_tool_registry 用 `LLMToolExecutor(safe_mode=False)`，exec 含完整 builtins+os/sys+self；runtime.yaml `sandbox_code_exec:false` 的 flag 没被 tool_executor 读取（原 config_manager 默认 True 冲突源已随 P1-4 删除） | tools/tool_executor.py:445 + dynamic_tool_registry.py:442 | LLM 拥有完全本地执行权，沙箱配置形同虚设 |
| P6-11 | **工具目录四重定义**：ToolRegistry(11 ToolSpec)/DynamicToolRegistry(5+技能)/AVAILABLE_TOOLS(5 schema)/skills 四处，工具名(read_file vs file_read)/风险/schema 不统一，action_executor 同时查两套注册表 | tools/{tool_registry,dynamic_tool_registry,tool_definitions}.py + memory/skills/ | "有哪些工具"无单一真相源 |
| P6-13 | **黑板情绪路径死**：M_AFFECT/M_COORD 调 `update_mood(..., dimension="attachment")`，但该函数无 dimension 参数(应为 update_mood_per_dimension)，TypeError 被吞→多模型模式情绪更新整条静默失效 | tools/blackboard.py:557,817 | 论文§3.4.2 黑板驱动情绪的功能不工作 |
| P6-14 | **黑板幽灵槽位丢失**：M_VIS/M_AUD/expert_*_output 写的槽位不在 BlackboardState schema，update_slot 的 hasattr 守卫静默丢弃→专家输出数据全部丢失 | tools/blackboard.py:645,695,1194,159 | 视觉/音频/专家结果无法跨专家共享 |
| P6-20 | **代码执行四套，最完善的没接**：tool_executor FULL_ACCESS(活)/tool_executor 黑名单/safe_executor AST(孤立)/code_exec 正则(孤立)；原 config_manager 的 sandbox_code_exec flag 已随 P1-4 删除，但活路径仍是无过滤全开 | tools/{tool_executor,safe_executor,code_exec}.py | 论文§3.11.3 的安全沙箱形同虚设，活路径是无过滤全开 |
| P6-23 | **嵌入四处且三处伪**：tools/embeddings 默认 mock(hash-seed)，与 memory/retrieval(MD5)/familiarity(md5-seed) 同为伪嵌入，仅 semantic_novelty 真嵌入；默认配置下语义检索/联想/洞察新颖度都是噪声 | tools/embeddings.py + memory/{retrieval,familiarity,semantic_novelty}.py | 第3章 P3-7 的扩展(现4处) |
| P6-24 | **edge-tts 递归崩溃**：voice.py L336 async _speak_edge 被 L382 同名同步方法覆盖，同步包装调自己→无限递归；Windows mp3 播放用 SoundPlayer(只支持wav)必抛 | tools/voice.py:336,382,364 | TTS 功能第一调用即崩(但无运行时消费者) |
| P6-29 | **file_ops fail-open**：allow-list 为空时跳过目录检查，仅剩 forbidden_patterns(Path.match 对绝对路径在 Windows 不可靠)；空配置=任意目录可读写；_write_file 无大小上限 | tools/file_ops.py:121 | 空配置下文件工具无沙箱 |
| P4-5/14/17/51/56 等 | **cognition/perception/metabolism 魔法数遍地**：goal_compiler(0.15/5/0.01/0.1)、plan_evaluator(λ_cost=0.001/λ_risk=0.5/budget_penalty=2.0)、verifier(0.1/0.2/0.5/0.7)、boredom(ETA 0.03/0.20/0.05 与 constants 0.005/0.10 失配)、circadian(0.65/0.35/phase 边界/recovery dict) 全硬编码无 config | cognition/ + perception/ + metabolism/ | 与第1章 P1-3 参数三重定义叠加；METABOLISM 常量整段失效(P4-64) |
| P4-26/30/34/35/38/39 等 | **perception 包设计单薄 + 小问题**：observer 实质只是状态镜像(P4-26)、context_builder str(payload) 脆弱(P4-30)、self_perception.get_health_status 与 caretaker 撞名(P4-34)、磁盘路径假设(P4-35)、time_perception 死字段/北半球硬编码(P4-38/39) | perception/ | 维护负担 |
| P4-36/43/45 | **perception 三大功能被后续子系统取代**：time_perception 被 circadian/caretaker 取代、novelty 被 memory/semantic_novelty 取代、signal_filter 完全未接入（论文半衰期衰减未实现） | perception/{time_perception,novelty,signal_filter}.py | 6/8 文件死代码（1518 行），清理候选 |
| P4-40/41 | **command_parser 被绕过 + 中文盲区**：用户输入真实路径是 get_user_input→observer→build_context，CommandParser 不在路径上；正则全英文对中文无效 | perception/command_parser.py + core/handlers/chat_handler.py | 276 行死代码，与 chat_handler 职责重叠 |
| P4-19/21 | **insight_quality 死代码 + transferability 英文关键词**：整模块零运行时引用；transferability 关键词表(when/if/then/...)纯英文对中文 LLM 输出无效 | cognition/insight_quality.py | 206 行死代码 |
| P4-23 | **三套目标类型分类法互不匹配**：goal_progress.GoalType(8 枚举) vs goal_compiler 模板(5) vs planner 字符串(8+)，ProgressCalculator 检查的字符串永远不匹配 goal_compiler 的 | cognition/{goal_progress,goal_compiler,planner}.py | 即便接入 goal_progress 也走不到正确分支 |
| P4-47 | **perception __init__ 静默降级**：Time/SelfPerception 用 try/except ImportError 兜底，依赖缺失时置 None 不警告，运行期才暴露 AttributeError | perception/__init__.py | 问题被掩盖 |
| P7-1/2/4/6 | **safety 阈值魔数散布**：integrity_check(0.9/0.1/0.1)、risk_assessment(0.8/+0.1/+0.15)、budget_control(1000/1.0/100) 硬编码无集中配置；integrity 的 modify_self 黑名单过窄（只查 params 键名） | safety/{integrity_check,risk_assessment,budget_control}.py | 与 constants 风格不一 |
| P7-9 | **contract_guard 欺骗检测误报率高**：declared_goal 与 tool_id 的关键词交集法，tool_id="file_ops" 几乎不与任何自然语言目标词重叠，会把正常文件操作判 DECEPTION | safety/contract_guard.py:154-167 | 即便被接线也不敢启用 |
| P7-11/12 | **hallucination_check 正则仅英文 + 死字段**：uncertainty_patterns/citation_patterns 全英文，对中文输出几乎永不触发；hallucination_indicators(L62) 定义后无引用 | safety/hallucination_check.py | 对中文数字生命场景失效 |
| P7-15 | **sandbox 资源限制无强制力**：check_resource_usage 只比较传入数值，不实际采样进程内存/CPU（无 resource/psutil），max_memory_mb=512 是声明值 | safety/sandbox.py:276 | 即便被接线也是空壳 |
| P7-18/19 | **replay 存根 + 魔数**：verify_replay_consistency 注释自承 simplified 未真正迭代所有 tick（恒返回 True）；snapshot_interval=10/Jaccard 0.4/coverage 0.5/tolerance 0.01/hash[:16]/[-10:] 全硬编码 | persistence/replay.py:690,198,181,432 | 回放验证不可靠 |
| P7-22/24/25/28/29/31/32 | **persistence 杂项**：EventLogger _file_handle 死字段(P7-22)、ToolCallLogger get_tool_calls_for_tick 无索引全表扫(P7-24)、_redact_sensitive 仅英文(P7-25)、snapshot incremental 空壳(P7-28)、SnapshotManager 无 import(P7-29)、Storage 后端声明与实现不符 SQLITE/MEMORY 未实现(P7-31)、append O(n²) 反模式(P7-32) | persistence/ | 工程债 |
| P7-33 | **persistence 孤儿包**：grep `from persistence` 全工程仅 tests/conftest.py 命中，life_loop 完全不导入；__init__ docstring 所称职责与实际运行时持久化重复且未被采纳 | persistence/__init__.py + core/life_loop.py | 整包可考虑删除或重新接入 |
| P9-8 | **web run_dir 固定→重启覆盖语义混乱**：web 用固定 artifacts/web_run（run.py/daemon 用时间戳目录）；ensure_initialized/api_reinit/api_restart_system 重建 LifeLoop 复用同目录，但 schema/skill 不持久化(P3-5)——重启后"知识"丢失而 episodic 跨会话累积，与 run.py 隔离目录策略语义相反 | web/app.py:284 + core/life_loop.py:190 | 两套 run_dir 策略并存易混；web 重启丢失 schema/skill |
| P9-13 | **SSE progress 队列无超时清理**：/api/progress/<id> 的 progress_queues[session_id] 在客户端断开(GeneratorExit)时清，但 async chat 线程异常退出前没 put None 时 SSE 连接每30s 心跳直到客户端超时；progress_queues 无 TTL/无定期扫除 | web/app.py:1224,1342 | 队列残留；长会话下内存缓慢泄漏 |
| P9-17 | **WebSocket 流式/状态是占位符**：_handle_stream_chat 按10字符分块+sleep(0.02) 假装流式（注释"暂时用非流式模拟"）；_get_current_state 恒返回 {"status":"running"}（注释"需外部注入"但无人注入）——即便启用 WebSocket 这两处也是占位 | web/websocket_server.py:116,155 | 启用 WS 后流式/状态推送仍是假数据 |
| P9-15 | **生产安全配置定位模糊**：_validate_production_security 强制 SECRET_KEY/CORS 是唯一面向"部署"的代码，但项目核心是单实例桌面数字生命(P1-9)——不部署则过度安全，部署又不够(无 HTTPS 强制/rate limit/api 认证)；定位模糊 | web/app.py:52 | 安全投入与项目定位不匹配 |
| P9-1 | **run.py --config 注释误导**：注释示例写 `--config config/runtime.yaml`（文件），但 --config 实际是目录（传给 load_config(Path) 按目录读多 yaml） | run.py:6 | 注释与实现不符 |
| P9-4 | **chat_interactive 死导入 get_available_tools**：from tools.tool_definitions import get_available_tools 导入后全文件零引用——chat_interactive 不把工具 schema 喂 LLM(工具调用交给 life_loop 内部) | chat_interactive.py:39 | 死导入 |

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
新会话4: "读 CODE_MAP.md，续写第6章 tools/"   ✅ 已完成
新会话5: "读 CODE_MAP.md，续写第4章(认知感知代谢)+第7章(安全持久化)"   ✅ 已完成
新会话6: "读 CODE_MAP.md，续写第9章(入口Web) + 更新A节问题清单"   ✅ 已完成（全章精读完成）
```
> **全部 9 章精读已完结**。后续会话可聚焦：① A 节问题清单的修复实施（按 🔴→🟡→🟢 排序）；② 若需补充 B 节"新会话上手指南"或新增 C 节"修复路线图/优先级排序"，可基于 A 节 260 项问题展开。
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

### 实测记录与已修复问题

#### 实测发现（2026-07-06，run_20260706_062952，17 tick）
- **P0-1 价值→行为断链**（见 A 节）：17 tick 全 REFLECT/THINK，0 EXPLORE/CHAT，mood 跌至 0 卡死。**当前最高优先级**。
- 无用户输入时系统缺乏主动行动驱动，陷入反思死循环。
- 巩固未触发（需 ≥20 episode，17 tick 被超时中断于 shutdown 前，schemas/skills 未落盘）。

#### 已修复（2026-07-06）
| 问题 | commit | 说明 |
|---|---|---|
| inspect.is_function（Py3.13 兼容，新发现） | `a50083d` | dynamic_tool_registry.py，5 个工具文件报错消除 |
| P3-3 episodic.py print→logger | `ba70b80` | 5 处 print 替换为结构化日志 |
| P3-5 Schema/Skill 持久化接入 | `15e0051` | 构造传 persist_path + shutdown 调 save_to_disk |
| P3-22 limb_guides 崩溃重复包 | `前一个` | 删 4 个与 skills/ 逐字节重复文件 + 崩溃 __init__，保留 data/ 目录 |
| P6-30/P6-31/P6-27 死代码 | `前一个` | 删 cost_model/llm_cache/memory_tools（~920行，零引用） |
| P3-18 auto_detect_backend 接入 | `6ee3b00` | 加 @classmethod + from_env 调用；**意外收益：本机有 sentence-transformers，语义嵌入从 TF-IDF 升级为真嵌入** |
| P3-17 compute_novelty 单例 | `28af13a` | 避免每次调用重新加载模型，缓存生效 |
| **P0-1 核心死锁（器官结构化动作 + 9a 豁免）** | `6b80130` | base_organ 抽模板方法（结构化【动作:XXX】→关键词 fallback→规则）；6 器官迁移；integrity_check 解 mood<0.1 死锁（低风险 EXPLORE 豁免）。**实测：CHAT 从 0→出现，mood 出现回升**。顺带根治 P5-15/P5-10/P5-16 |
| **P0-1 第二层（CHAT bond 增益）** | `3f5c2b6` | action_executor bond +0.01→+0.05/次，trust 同比例。诊断发现 PHASE 11 的 CHAT +0.2 bonus 实际生效，但 bond 涨太慢填不平 attachment 缺口 |
| **P0-1 第三层（bond 冷启动）** | `7e70740` | bond 初始值 0→0.4（FieldStore + life_loop）。attachment 缺口从 0.45 降到 0.21，CHAT reward 从 -0.12 改善到 -0.02 |
| **P4-61/P4-58 RP 公式混淆 + recovery 死代码** | `（D阶段）` | 删 metabolism/resource_pressure.py(256) + recovery.py(173)。resource_pressure 论文版 RP 公式与 state.py 生产版语义相反且零运行时引用；recovery 被 life_loop 内联绕过。boredom 资源覆盖死分支删除，compute_effective_boredom 简化为兼容存根。资源紧急判断统一由 state.py 基于 psutil 实现 |
| **P4-1 priority_level 全域未设** | `6cb0202` | GoalCompiler._priority_to_level 将 priority float 映射到论文§3.8.1 的 PriorityLevel(1-6)，safety/homeostasis 维度加成。两处 Goal 创建设 priority_level。论文 6 级优先级系统运行时生效 |
| **P7-14 代码执行 FULL_ACCESS** | `d88b5fa` | 加 env flag GENESISX_ALLOW_FULL_ACCESS。默认保持 FULL_ACCESS（单用户本地系统），设 =0 时强制走沙箱。部署公网/多用户时关闭 |
| **P9-7 Web 并发无锁** | （已知问题不修） | 5 线程并发 tick 同一 life_loop 无锁是架构级问题，加锁会退化成串行（auto-run 被聊天阻塞）。记录为已知，根本解决需重构（消息队列+单消费者） |
| **P8-11/P8-10/P8-13 action_executor 三 bug** | `0d192ea` | P8-11 tool/tool_id 键不一致（gap_detector 读'tool' executor 读'tool_id'）统一；P8-10 多轮 CHAT 响应覆盖改累积拼接；P8-13 未知 ActionType 返回 success=True 改 False |
| **P4-31 self_perception 工具断链** | `9e1d64e` | tool_registry 注册 read_own_logs/system_stats 但 _execute 无分发分支→LLM 选了静默失败。加 3 个 dispatch 分支 + _execute_self_perception 桥接方法 |
| **P5-19 中文分词失效** | `c17846b` | scout/mind 的 _extract_topic_from_thought 用 split() 按空格，中文无空格→整段当一个 word。改正则提取连续中文/英文词组 |
| **P1-2/P6-5 小 bug** | `81e6722` | P1-2 Goal.is_expired 移除误导的 current_tick 死参数；P6-5 _chat_claude 方法内无 logger 定义→降级路径 NameError，加 logger 定义 |
| **P2-3 value_dimensions 重复** | `f02bd76` | 删 axiology/value_dimensions.py(799行)，与 feature_extractors+utilities_unified 100%重叠，零外部引用 |
| **P2-5 drives 禁用注释** | `e27195c` | life_loop 顶部"暂时禁用"注释与实际状态不符（drives 由 organ_manager 间接调用已接入），清理注释 |
| **P5-6 UnifiedOrganManager 只写** | `78e89ba` | 探查发现接入 PHASE 7 无收益（limb/plugin propose_actions 恒空），接入 USE_TOOL 路径（tool_registry 找不到时回退 unified_organ_manager.execute_capability）+ limb prompt 要求方法名=能力名 |
| **P5-20 immune 否决权** | `1216d03` | 3 个安全方法保留备用，标注已知设计偏差（safety/ 取代，完整接入会两套安全系统重叠） |
| **P7-16 persistence 整包孤岛** | `e1996e2` | 接入 STRICT 回放（run.py --replay <dir>），PHASE 10 用缓存 outcome。删 4 个零引用写入器(602行)。解 P7-21/23/26/27/30/31/32 |

#### P0-1 修复的实测对比（2026-07-06）
| 指标 | 修复前 (run_062952) | 修复后 (run_151237) |
|---|---|---|
| CHAT/EXPLORE 数量 | 0（29 tick 全 REFLECT/THINK） | CHAT 出现（结构化路径产生） |
| attachment 缺口 | 0.45（深，bond 从 0 起步） | 0.21（bond 初始 0.4 + 增益 +0.05） |
| CHAT 的 reward | -0.12（+0.2 bonus 盖不过负效用） | -0.02（接近 0，闭环几乎转正） |
| mood 单调锁死归零 | 是（0.5→0 单调，永久卡死） | 核心死锁解开，但 mood 稳定性仍受推理模型影响（见下） |

#### P0-1 残留项（后续优化，非死锁）
P0-1 的**三环死锁已解开**（器官层结构化 + 9a 豁免 + attachment 闭环），但实测发现 mood 在长 tick 后仍会回落到 0，根因已转移：

**已做的残留修复（commit d928797 + 5c33d73）**：
- `BaseOrgan._value_driven_fallback`：结构化+关键词都失败时，按当前最大价值缺口维度选动作（curiosity→EXPLORE/attachment→CHAT/homeostasis→SLEEP 等），让价值系统真正驱动行为。
- `life_loop` PHASE 4.5：把 gaps/weights 写入 `context['value_gaps']`（P5-10 延伸），器官 fallback 可读。
- `_format_structured_output_prompt_prefix`：格式要求前置到 prompt 开头（推理模型对开头指令更敏感）。
- 步骤 2.5：关键词 fallback 只产被动动作（REFLECT/THINK）且有显著缺口时，追加价值驱动动作。
- 实测：EXPLORE/CHAT 候选能进入 PHASE 8，curiosity 缺口大时触发 EXPLORE。

**仍存在的问题（多参数耦合，属系统调优非 bug）**：
1. **mood 跌速 vs curiosity 涨速不匹配**：mood 从 0.4 跌到 0 要 ~5 tick，curiosity 从 0 涨到 0.3（触发价值兜底）要 ~6 tick——价值兜底触发时 mood 已死。
2. **PHASE 8 plan_evaluator 评分等价**：EXPLORE 和 REFLECT 评分近乎相同（estimated_reward 都硬编码 0.5），选哪个取决于器官优先级排序，REFLECT 常排前面。
3. **推理模型格式遵守**：step-3.7-flash 仍不稳定输出【动作:XXX】标记（~70% tick 退回关键词 fallback）。

**建议后续（系统调优，非本次范围）**：① 降低价值驱动兜底阈值或按 mood 动态调整；② PHASE 8 评分让"匹配当前最大缺口的动作"加分；③ 收紧 REFLECT 关键词；④ 换用非推理模型或强化 few-shot。

#### C 阶段：死代码清理（2026-07-06，共删 5370 行）
| commit | 删除 | 行数 | 解的问题 |
|---|---|---|---|
| `d33c532` | lifecycle/ 整包 + test_lifecycle.py | 1029 | P9-18（第二条 tick 引擎，所有相位空壳） |
| `8d0ed55` | memory/dream.py + personality_encoding.py | 1295 | P3-13（DreamDirector 重复）/ P3-20（人格调制编码孤立） |
| `bc81361` | cognition/goal_progress.py + insight_quality.py + test_insight_quality.py | 768 | P4-22（整模块死）/ P4-19（Q^insight 三重实现之一） |
| `66cd7a2` | core/exceptions.py + scheduler.py + capability_router.py | 1290 | P8-18 部分 / P8-19（能力管理三件套碎片化） |
| `fa815d1` | safety/contract_guard.py + hallucination_check.py + sandbox.py | 988 | P7-7/P7-10/P7-13（safety 包 988 行死代码） |

**保留**：core/emotion_decay.py(615) 暂留——life_loop 不用但 benchmarks/run_gxbs.py 的 emotion_benchmark 依赖（评测基础设施）。
**验证**：5 批删除后 core/memory/cognition/safety 包导入正常，pytest 关键测试 134 passed（1 个预存失败），1 tick 冒烟测试实跑成功（THINK+CHAT 正常产出）。


#### 修复说明
- **死代码删除原则**：只删"包外零引用 + 删除后包导入正常"的，保留有数据依赖的目录（如 limb_guides/data/）。
- **P3-18 副作用**：首次启动会加载 sentence-transformer 模型（all-MiniLM-L6-v2，约 1-2 秒）。若环境无此包则自动回退 TF-IDF，行为不变。
- **P0-1 回滚预案**：`git revert 6b80130 3f5c2b6 7e70740`，或 `.env` 设 `STRUCTURED_ORGAN_ACTIONS=0` 回退到原关键词逻辑。

---

#### F 阶段：双配置体系 + METABOLISM 死常量清理（2026-07-13，共删 ~540 行）
| commit | 删除 | 行数 | 解的问题 |
|---|---|---|---|
| `f4a9189` | common/config_manager.py 整文件 | 509 | P1-4（ConfigManager/GenesisXConfig 零引用死代码，与 config.py 同名 load_config() 混淆） |
| `34825ec` | README×3 + PROJECT_STRUCTURE_TREE×2 死链 + P6-9/P6-20 文档订正 | 8 | P1-4 文档清理 |
| `32287d4` | constants.py 的 MetabolismConstants 类 + METABOLISM 实例 + re-export | 31 | P4-64（13 个 metabolism 常量零读取，实际计算用 emotion_decay/boredom 各自硬编码） |

**验证**：每批删除后跑代表性测试集（test_fixes/life_loop_integration/organs/axiology/memory/chat_interaction），结果零差异；2 个 pre-existing 失败（integrity 维度 KeyError / chat）与本次无关。
**未动**：config.py 的 Pydantic 模型/.env 逻辑；constants.py 其余 10 个常量类。

#### G 阶段：GlobalState↔FieldStore 双真相源收敛（2026-07-13，方案 A）
| commit | 改动 | 行数 | 解的问题 |
|---|---|---|---|
| `792fb6f` | GlobalState 7 情感标量改为 property 委托 FieldStore + 注入参数 + 本地 fallback | +90/-43 | P8-4 Step1（单一真相源委托，energy/fatigue/bond/trust 不再折叠到 activity_fatigue/relationship） |
| `b95af3d` | 删 `_sync_state_to_global`/`_sync_fields_to_global` + 8 handler 调用点改 fields.set + _persist 不再写两遍 | +34/-93 | P8-4 Step2（消灭手工同步，FieldStore 注入 GlobalState） |
| `b5ea311` | invariants.py mood 范围 [-1,1]→[0,1] + CODE_MAP 文档 | +10/-8 | P8-15（mood 范围统一，affect/mood.py 实际 clamp [0,1]） |

**验证**：1-tick 实测 7 标量 state==fields 零 drift；代表性测试集零回归。
**数据模型决定**：以 FieldStore 为准（7 独立字段）；UI 7 标量只读展示，无手动改值，方案 A 无障碍。
**未动**：life_loop_backup.py（死代码，单独处理）；FieldStore 结构；GlobalState 非情感字段。

---

*文档状态：全 9 章精读完成（原 242 文件/84k 行；经多轮修复后现 **204 文件/75k 行**，累计删除约 8633 行死代码/重复代码）。全局问题清单收录 **227 项**，其中 **42 项已处理**（含已修/已接入/记录已知，见上方"已修复"表 + A 节✅标记）。高优先级 29 项中 **28 项已处理**，仅剩 P5-21（器官学习状态持久化）。本轮主要成果：**A 阶段** P0-1 死锁解开 + 器官结构化动作 + 价值驱动兜底；**C 阶段** 死代码清理 5370 行；**D 阶段** P4-61 RP 公式 + P4-1 priority_level + P8-7 基因缓存；**E 阶段** P7-14 安全 flag；**纯 bug 批次**（P8-11/10/13/P4-31/P5-19/P1-2/P6-5）；**决策批次**（P2-3 删/P2-5 注释/P5-6 USE_TOOL 接入/P5-20 记录/P7-16 replay 接入/P3-15 联想重建/P3-6,7 嵌入统一）；**F 阶段** P1-4 config_manager.py(509行) + P4-64 METABOLISM 死常量(31行)；**G 阶段** P8-4 GlobalState↔FieldStore 双真相源收敛（方案A：FieldStore 单一真相源委托，删 _sync_* -93行）+ P8-15 mood 范围统一 [0,1]。*


