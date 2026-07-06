# GenesisX 代码地图与技术说明

> **文档目的**：供 AI/开发者在新会话中快速建立对整个项目的精确认知，直接进入优化工作。
> **覆盖范围**：逐模块、逐文件梳理 242 个 Python 文件（约 84k 行），标注设计意图、数据流、模块耦合与潜在问题。
> **生成方式**：通读源码 + 论文对照，标注 `🔍问题` 为值得后续迭代的点。
> **版本基准**：v1.3.0，5 维价值系统（已从早期 9 维精简）。
> **最后更新**：2026-07-06
> **进度**：✅ 第1-2章已完成精读（46文件/14k行） ⏳ 第3-9章待续（148文件/56k行）

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
- [8. 核心引擎 `core/`](#8-核心引擎-core) ⏳待续
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

## 8. 核心引擎 `core/` — 待续 ⭐最重要

> ⏳ 43 文件/18338 行——**全系统最大模块**。`life_loop.py`(主循环) + `differentiate.py`(器官分化) + `tick.py` + `stores/`(字段/槽位/信号/账本) + `evolution/`(进化引擎,默认禁用) + `growth/`(肢体生成) + `handlers/`(动作执行910行/聊天/缺口检测) + `plugins/`。
> **续写提示（最重要）**：`life_loop.py` 的 8 阶段初始化 + `run_session()`/`tick()` 主循环必须逐行精读——这是编排一切的中枢。然后 `tick_loop.py`(17阶段) + `differentiate.py`(基因表达)。`handlers/action_executor.py`(910行)是动作落地的关键。`evolution/` 虽禁用但代码完整(clone→mutate→transfer)，值得记录。
> **已知线索**：`life_loop.py` 顶部注释显示 5 维 Drive 系统被注释禁用；`core/life_loop_backup.py` 是备份文件（疑似可删）。

---

## 9. 入口 + Web — 待续

> ⏳ `lifecycle/`(3文件) + `web/app.py`(Flask,40+路由) + `web/websocket_server.py` + 顶层 `run.py`/`daemon.py`/`chat_interactive.py`。
> **续写提示**：`web/app.py` 的 40+ 路由要分类整理（状态/聊天/配置/器官/记忆/守护进程/主动消息）。initiative messaging（主动发消息）是特色功能。

---

## A. 全局问题清单（按优先级）

> 精读 Phase 1-2 发现的问题。`🔴高危` `🟡中` `🟢低`。新会话优化时按此排序。

### 🔴 高优先级（影响正确性/可维护性）

| ID | 问题 | 位置 | 影响 |
|---|---|---|---|
| P1-3 | **参数三重定义不一致**：τ 在 constants.py=2.0、value_setpoints.yaml=4.0、parameters.py=4.0。k_+/k_- 同样散落三处 | common/constants.py + config + axiology | 论文复现不可靠，调参时改了一处另一处覆盖 |
| P2-3 | **axiology 严重代码重复**：value_dimensions.py(799行) 与 feature_extractors.py+utilities_unified.py 功能重叠 | axiology/ | 改一处忘另一处，行为不一致 |
| P2-5 | **drives/ 5维驱动力被禁用**：life_loop.py 顶部注释禁用，但代码存在 | axiology/drives/ | 死代码或半成品，需决策启用/删除 |
| P1-4 | **两套配置加载体系并存**：config.py(load_config→dict) vs config_manager.py(ConfigManager→对象)，且都有 load_config() 同名函数 | common/ | 极易混淆，维护负担 |

### 🟡 中优先级（技术债）

| ID | 问题 | 位置 |
|---|---|---|
| P1-1 | Goal.priority(deprecated float) 与 priority_level(新int) 并存 | common/models.py |
| P2-1 | axiology/__init__.py 含 210 行 fallback UtilityCalculator 兼容类 | axiology/__init__.py |
| P2-2 | compute_weights(纯函数) 与 WeightUpdater.update_weights 逻辑重复 | axiology/weights.py |
| P2-4 | setpoint 管理散落 3 处(setpoints/dynamic_setpoints/axiology_config) | axiology/ |
| P1-7/P1-9 | auth.py(699行)+models/(786行) 多用户 Web 模块疑似过度工程 | common/+models/ |
| P1-8 | database.py 仅 12 行形同虚设，SQLAlchemy 依赖可能可移除 | common/ |

### 🟢 低优先级（清理项）

| ID | 问题 | 位置 |
|---|---|---|
| P1-2 | Goal.is_expired 参数 current_tick 未使用 | common/models.py |
| P1-6 | error_handler 与 utils.retry_on_failure 重试逻辑重复 | common/ |

---

## B. 新会话上手指南

### 如何使用本文档
1. **开新会话时**：对 AI 说"读 CODE_MAP.md，继续写第 X 章"（X 见下方路线图）
2. **优化某个模块时**：先读对应章节 + A 节相关问题，再动手
3. **调试运行时问题时**：先看"0.项目概览"的 tick 流水线，定位问题在哪个阶段

### 续做路线图（按推荐顺序）
```
新会话1: "读 CODE_MAP.md，续写第8章 core/"     ← 最重要，先搞清主循环
新会话2: "读 CODE_MAP.md，续写第3章 memory/"
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

*文档状态：Phase 1-2 已完成精读（46文件/14k行），Phase 3-9 待续。全局问题清单已收录 14 项。*


