# GenesisX 代码地图与技术说明

> **文档目的**：供 AI/开发者在新会话中快速建立对整个项目的精确认知，直接进入优化工作。
> **覆盖范围**：逐模块、逐文件梳理 242 个 Python 文件（约 84k 行），标注设计意图、数据流、模块耦合与潜在问题。
> **生成方式**：通读源码 + 论文对照，标注 `🔍问题` 为值得后续迭代的点。
> **版本基准**：v1.3.0，5 维价值系统（已从早期 9 维精简）。
> **最后更新**：2026-07-06
> **进度**：✅ 第1-2章已完成精读（46文件/14k行） ✅ 第8章 core/ 已完成精读（43文件/18338行） ⏳ 第3-7,9章待续（105文件/38k行）

---

## 目录

- [0. 项目概览与心智模型](#0-项目概览与心智模型)
- [1. 基础层 `common/` + `models/`](#1-基础层-common--models) ✅
- [2. 核心理论层 `axiology/` + `affect/`](#2-核心理论层-axiology--affect) ✅
- [3. 记忆层 `memory/`](#3-记忆层-memory) ⏳待续
- [4. 认知/感知/代谢 `cognition/` + `perception/` + `metabolism/`](#4-认知感知代谢) ⏳待续
- [5. 器官层 `organs/`](#5-器官层-organs) ⏳待续
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

## 3. 记忆层 `memory/` — 待续

> ⏳ **本章节待新会话续写。** memory/ 含 29 文件/8733 行，是项目第三大模块。
> **续写提示**：精读顺序 `episodic.py`→`schema.py`→`skill.py`→`retrieval.py`→`consolidation.py`→`dream.py`→`familiarity.py`(890行,联想网络)→`semantic_novelty.py`(750行)→`personality_encoding.py`→`gates.py`→`pruning.py`→`salience.py`。
> **已知线索**：`memory/skills/` 和 `memory/limb_guides/` 有代码重复（README 已提及）。CLS 三层记忆架构，容量 Episodic 50k/Schema 1k/Skill 300。

---

## 4. 认知/感知/代谢 — 待续

> ⏳ `cognition/`(7文件,规划/目标/验证) + `perception/`(8文件,观察/上下文/新颖性) + `metabolism/`(5文件,昼夜节律/恢复/无聊)。共 20 文件/4672 行。
> **续写提示**：cognition 重点 `planner.py`/`goal_compiler.py`；metabolism 重点 `circadian.py`(昼夜节律)。

---

## 5. 器官层 `organs/` — 待续

> ⏳ 15 文件/7956 行。6 个内部器官(caretaker/immune/mind/scout/builder/archivist) + 器官管理 + **器官 LLM 会话系统**(核心创新)。
> **续写提示**：先读 `base_organ.py`(器官基类)→`organ_manager.py`→`unified_organ.py`→`organ_llm_session.py`(LLM会话,核心)→6 个 internal 器官。**器官 LLM 三模式(independent/shared/disabled)是理解这个项目的关键之一。**

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

> 精读 Phase 1-2(common+axiology+affect) 与 Phase 8(core) 发现的问题。`🔴高危` `🟡中` `🟢低`。新会话优化时按此排序。

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

---

## B. 新会话上手指南

### 如何使用本文档
1. **开新会话时**：对 AI 说"读 CODE_MAP.md，继续写第 X 章"（X 见下方路线图）
2. **优化某个模块时**：先读对应章节 + A 节相关问题，再动手
3. **调试运行时问题时**：先看"0.项目概览"的 tick 流水线，定位问题在哪个阶段

### 续做路线图（按推荐顺序）
```
新会话1: "读 CODE_MAP.md，续写第8章 core/"     ✅ 已完成
新会话2: "读 CODE_MAP.md，续写第3章 memory/"   ← 下一个推荐
新会话3: "读 CODE_MAP.md，续写第5章 organs/"
新会话4: "读 CODE_MAP.md，续写第6章 tools/"
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

*文档状态：Phase 1-2(common/axiology/affect, 46文件/14k行) + Phase 8(core/, 43文件/18338行) 已完成精读。Phase 3-7,9 待续。全局问题清单已收录 14 + 20 = 34 项。*


