"""ActionExecutor - 行为执行器

从 LifeLoop._execute_action 拆分出来的独立模块，
负责执行各类行为（SLEEP, EXPLORE, REFLECT, CHAT, USE_TOOL 等）。

设计原则：
- 接收 LifeLoop 实例作为依赖（依赖注入）
- 保持与原始代码完全相同的行为
- 支持单元测试
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
import time
import json as json_module
import concurrent.futures

from common.models import Action, CostVector, ActionType
from common.logger import get_logger

logger = get_logger(__name__)


class ActionExecutor:
    """行为执行器

    负责：
    - SLEEP: 睡眠恢复
    - EXPLORE: 探索减无聊
    - REFLECT: 反思减压
    - CHAT: LLM 对话（复杂，支持 Function Calling）
    - USE_TOOL: 工具调用
    - LEARN_SKILL: 学习技能
    - OPTIMIZE: 优化效率

    使用方式：
        executor = ActionExecutor(life_loop)
        outcome = executor.execute(action, context)
    """

    def __init__(self, life_loop):
        """初始化执行器

        Args:
            life_loop: LifeLoop 实例，用于访问状态和依赖
        """
        self.life_loop = life_loop

        # 快捷引用
        self.fields = life_loop.fields
        self.state = life_loop.state
        self.slots = life_loop.slots
        self.ledger = life_loop.ledger
        self.tool_registry = life_loop.tool_registry
        self.capability_manager = life_loop.capability_manager
        self.config = life_loop.config

    def execute(self, action: Action, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行行为

        Args:
            action: 待执行的行为
            context: 当前执行上下文

        Returns:
            Dict with "success", "cost", and optional fields
        """
        logger.info(f"[_execute_action] Starting: action.type={action.type}")
        start_time = time.time()

        if action.type == ActionType.SLEEP:
            return self._execute_sleep(action)
        elif action.type == ActionType.EXPLORE:
            # mind 决策的 EXPLORE 走 agentic loop（多步骤：搜→读→总结）
            if action.params.get("source") == "mind_decision":
                topic = action.params.get("topic", "general exploration")
                result = self._execute_agentic_loop(f"探索并深入了解：{topic}", max_rounds=10)
                result["ok"] = result.get("success", False)
                self._log_tool_call(action, {"success": result["success"], "agentic": True,
                                            "steps": result.get("steps", 0)}, result.get("cost", CostVector(cpu_tokens=300)))
                # 更新状态
                curiosity = self.fields.get("curiosity")
                self.life_loop.fields.set("curiosity", min(1.0, (curiosity or 0.5) + 0.05))
                self.life_loop.fields.set("novelty", 0.8)
                if hasattr(self.life_loop, '_last_novelty'):
                    self.life_loop._last_novelty = 0.8
                return result
            else:
                return self._execute_explore(action)
        elif action.type == ActionType.REFLECT:
            return self._execute_reflect(action)
        elif action.type == ActionType.CHAT:
            return self._execute_chat(action, context, start_time)
        elif action.type == ActionType.LEARN_SKILL:
            return self._execute_learn_skill(action)
        elif action.type == ActionType.USE_TOOL:
            return self._execute_use_tool(action, start_time)
        elif action.type == ActionType.OPTIMIZE:
            return self._execute_optimize(action)
        elif action.type == ActionType.GROW:
            # mind 决策的 GROW 走 agentic loop（多步骤：设计→写→测→修）
            if action.params.get("source") == "mind_decision":
                task = action.params.get("task", "general tool")
                result = self._execute_agentic_loop(
                    f"构建工具：{task}。先用 list_directory 查看 artifacts/limbs/ 已有工具，"
                    f"避免重复。然后写代码、测试、保存到 artifacts/limbs/ 目录。",
                    max_rounds=15
                )
                result["ok"] = result.get("success", False)
                self._log_tool_call(action, {"success": result["success"], "agentic": True,
                                            "steps": result.get("steps", 0)}, result.get("cost", CostVector(cpu_tokens=500)))
                energy = self.fields.get("energy")
                self.life_loop.fields.set("energy", max(0.0, energy - 0.05))
                return result
            else:
                return self._execute_grow(action, start_time)
        elif action.type == ActionType.THINK:
            return self._execute_think(action, start_time)
        elif action.type == ActionType.SOCIALIZE:
            return self._execute_socialize(action)
        else:
            # P8-13 修复：未知 ActionType 返回 success=False（原返回 True 会让分派 bug 被静默）
            logger.warning(f"Unknown action type: {action.type}")
            return {"success": False, "ok": False, "cost": CostVector(cpu_tokens=50),
                    "error": f"Unknown action type: {action.type}"}

    def _execute_sleep(self, action: Action) -> Dict[str, Any]:
        """睡眠: 恢复能量、疲劳、压力，并进行深度记忆整理

        SLEEP 行为整合了：
        1. 原有的恢复功能（能量、疲劳、压力）
        2. 深度记忆整理（优先LLM，失败回退到规则式）
        3. 深度上下文清理（重置认知状态）

        记忆整理策略：
        - LLM 启用时：使用 LLM 进行智能整理（提取偏好、合并话题、识别重要事件）
        - LLM 禁用或失败时：回退到规则式压缩（简单的去重和优先级调整）
        """
        duration = action.params.get("duration", 1)
        energy = self.fields.get("energy")
        fatigue = self.fields.get("fatigue")
        stress = self.fields.get("stress")
        boredom = self.fields.get("boredom")
        recovery_factor = min(duration, 10) / 10.0

        # 恢复能量
        new_energy = min(1.0, energy + 0.15 * recovery_factor)
        # 深度降低疲劳
        new_fatigue = max(0.0, fatigue - 0.3 * recovery_factor)
        # 恢复压力
        new_stress = max(0.0, stress - 0.1 * recovery_factor)
        # 减少无聊
        new_boredom = max(0.0, boredom - 0.05 * recovery_factor)

        # 检查是否启用 LLM 整理（从 organ_llm.yaml 读取）
        organ_llm_config = self._load_organ_llm_config()
        mc_config = organ_llm_config.get("memory_consolidation", {})
        use_llm = mc_config.get("enabled", True)  # 默认启用
        llm_threshold = mc_config.get("threshold", 30)

        # 记忆整理：优先使用 LLM，失败时回退到规则式
        memory_compressed = 0
        llm_result = None
        used_fallback = False

        if use_llm:
            # 优先尝试 LLM 整理
            llm_result = self._llm_memory_consolidation(llm_threshold, mc_config)
            if llm_result is None:
                # LLM 整理失败或记忆不足，回退到规则式
                logger.info("[SLEEP] LLM 整理未执行，回退到规则式压缩")
                memory_compressed = self._deep_memory_compression(recovery_factor)
                used_fallback = True
        else:
            # LLM 未启用，使用规则式
            memory_compressed = self._deep_memory_compression(recovery_factor)
            used_fallback = True

        # 深度上下文清理
        context_reset = self._deep_context_clean()

        # P8-4: 直接写 FieldStore（GlobalState 自动委托反映）
        self.life_loop.fields.set("energy", new_energy)
        self.life_loop.fields.set("fatigue", new_fatigue)
        self.life_loop.fields.set("stress", new_stress)
        self.life_loop.fields.set("boredom", new_boredom)

        consolidation_method = "规则式(回退)" if used_fallback else ("LLM" if llm_result else "无")
        logger.info(f"[SLEEP] 深度恢复 - 能量: {energy:.3f}→{new_energy:.3f}, "
                   f"疲劳: {fatigue:.3f}→{new_fatigue:.3f}, "
                   f"整理方式: {consolidation_method}, 上下文重置: {context_reset}")

        return {
            "success": True,
            "cost": CostVector(),
            "memory_compressed": memory_compressed,
            "llm_consolidation": llm_result,
            "used_fallback": used_fallback,
            "context_reset": context_reset
        }

    def _execute_explore(self, action: Action) -> Dict[str, Any]:
        """探索: 减少无聊，消耗能量，满足好奇，并产生真实的探索发现。

        阶段1.5（2026-07）：增加 curiosity 反馈（探索满足好奇）+ novelty 重置。
        阶段3.3（2026-07）：让 EXPLORE 真的产生价值——检索相关记忆 + 调 web_search
        （如有网络能力）+ 把发现作为新 observation 注入 episodic 记忆。这样探索
        形成闭环：EXPLORE → 新信息进记忆 → 下 tick novelty 真实变化 → 驱动后续行为。
        """
        boredom = self.fields.get("boredom")
        energy = self.fields.get("energy")
        curiosity = self.fields.get("curiosity")
        new_boredom = max(0.0, boredom - 0.15)
        new_energy = max(0.0, energy - 0.02)
        new_curiosity = min(1.0, (curiosity if curiosity is not None else 0.5) + 0.05)

        # === 阶段3.3: 真实探索（阶段5 增强：搜索词提炼 + 结果消化）===
        params = getattr(action, "params", {}) or {}
        topic = params.get("topic") or params.get("source") or "general"
        finding_parts = []
        memories_count = 0
        search_used = False

        # 0. 搜索词提炼（阶段5.1 修复）：把"内部好奇 topic"翻译成好的 web_search query。
        # 改造前：直接用 topic（如 "value_driven_fallback"/"relaxing_activity"）搜索，
        # 这些是代码内部字符串或泛化词，搜到的都是英文技术文档（IBM/Harness/Pinterest），
        # 跟系统的真实好奇无关。现先用 LLM 把 topic 提炼成有意义的搜索词。
        search_query = str(topic)[:200]
        try:
            from tools.llm_client import LLMClient
            client = getattr(self.life_loop, '_global_llm_client', None) or LLMClient()
            # 快速判断：如果 topic 明显是代码标识符（含下划线、纯英文小写），
            # 或是无意义占位符，让 LLM 重写成一个有信息量的搜索词。
            looks_like_code_id = (
                "_" in topic or
                (topic.replace(" ", "").islower() and topic.replace(" ", "").isalpha() and len(topic) < 30)
            )
            needs_rewrite = looks_like_code_id or topic in (
                "value_driven_fallback", "general", "auto_stimulation",
                "explore_new_topics", "llm_guided_exploration", "llm_structured",
                "relaxing_activity", "emerging_concepts", "pioneering",
            )
            if needs_rewrite:
                refine_result = client.chat(
                    messages=[
                        {"role": "system", "content": "输出一个 5-15 字的中文搜索词，适合用搜索引擎查询有趣的知识。只输出搜索词这几个字，绝对不要输出任何解释、标点说明或前缀。"},
                        {"role": "user", "content": f"探索意图：{topic[:80]}"}
                    ],
                    temperature=0.5, max_tokens=30
                )
                if refine_result.get("ok") and refine_result.get("text"):
                    # 推理模型可能在输出里混入解释，做激进清理：
                    # 取第一行，去掉常见前缀（"搜索词:"/"关键词:"等），去掉引号和句末标点
                    refined = refine_result["text"].strip().split("\n")[0].strip()
                    # 去掉"搜索词:""关键词:"等前缀
                    for prefix in ("搜索词：", "搜索词:", "关键词：", "关键词:", "搜索：", "搜索:"):
                        if refined.startswith(prefix):
                            refined = refined[len(prefix):].strip()
                    # 去掉首尾引号和句末标点
                    refined = refined.strip("「」\"'""''。.,，；;：:")
                    # 合理性检查：长度 3-30，且不是纯英文代码标识符
                    if refined and 3 <= len(refined) <= 30 and not refined.replace("_", "").isascii():
                        search_query = refined
                        logger.info(f"[EXPLORE] 搜索词提炼: '{topic[:30]}' → '{search_query}'")
                    elif refined and 3 <= len(refined) <= 30:
                        # 即使是纯英文也接受（可能是合理的英文主题）
                        search_query = refined
                        logger.info(f"[EXPLORE] 搜索词提炼(英文): '{topic[:30]}' → '{search_query}'")
        except Exception as e:
            logger.debug(f"[EXPLORE] 搜索词提炼失败（用原 topic）: {e}")

        # 1. 检索相关历史记忆（看以前是否探索过类似主题）
        try:
            if hasattr(self.life_loop, 'retrieval') and self.life_loop.retrieval:
                retrieved = self.life_loop.retrieval.retrieve_by_semantic_similarity(
                    search_query, limit=3, min_similarity=0.1
                )
                memories_count = len(retrieved) if retrieved else 0
                if retrieved:
                    finding_parts.append(f"recalled {memories_count} related memories")
        except Exception as e:
            logger.debug(f"[EXPLORE] 记忆检索失败（非致命）: {e}")

        # 2. web_search 真搜索（用提炼后的 search_query）
        raw_search_text = ""
        try:
            has_tool = hasattr(self.life_loop, 'tool_executor') and self.life_loop.tool_executor
            is_disabled = hasattr(self.life_loop.tool_executor, 'disabled_tools') and \
                          "web_search" in getattr(self.life_loop.tool_executor, 'disabled_tools', set())

            if has_tool and not is_disabled:
                search_result = self.life_loop.tool_executor.execute("web_search", {"query": search_query})
                if search_result and search_result.get("success"):
                    raw_search_text = search_result.get("result", "") or ""
                    if raw_search_text and len(raw_search_text) > 30:
                        search_used = True
        except Exception as e:
            logger.debug(f"[EXPLORE] web_search 失败（非致命）: {e}")

        # 3. 结果消化（阶段5.2 修复）：用 LLM 把搜索片段总结成"我学到了什么"。
        # 改造前：原始搜索片段（标题+URL+摘要）直接进记忆，下 tick 检索到的是垃圾碎片。
        # 现在让 LLM 读搜索结果，产出 100 字以内的知识总结，把总结存进记忆。
        # 这样探索真正形成"学到的东西"，而不是"搜到的碎片"。
        #
        # 注意：step-3.7-flash 是推理模型，输出常含 CoT 噪音（"首先...""哦对...""等下..."）。
        # 后处理：如果输出里含明显的推理过程词，只取最后一句结论（推理模型通常最后才定稿）。
        learned_summary = ""
        if raw_search_text:
            try:
                client = getattr(self.life_loop, '_global_llm_client', None) or LLMClient()
                digest_result = client.chat(
                    messages=[
                        {"role": "system", "content": "你在探索学习。基于下面的搜索结果，用 100 字以内简洁总结我从这次探索学到了什么有价值的知识。直接输出最终结论，不要输出思考过程。如果搜索结果与主题无关或无信息量，输出本次探索未获得有价值信息。"},
                        {"role": "user", "content": f"探索主题：{search_query[:80]}\n\n搜索结果：\n{raw_search_text[:1500]}"}
                    ],
                    temperature=0.4, max_tokens=200
                )
                if digest_result.get("ok") and digest_result.get("text"):
                    raw_summary = digest_result["text"].strip()
                    # 后处理：清理推理模型的 CoT 噪音。
                    # 如果输出很长（>150 字）且含推理词，尝试只取最后一个完整句子。
                    cot_markers = ["首先", "然后", "接着", "哦对", "等下", "嗯", "对，", "这样", "组织语言", "数下", "有没有"]
                    if len(raw_summary) > 150 and any(m in raw_summary for m in cot_markers):
                        # 按句号分割，从后往前找第一个不含推理词的实质性句子
                        import re as _re
                        sentences = _re.split(r'[。！？\n]', raw_summary)
                        sentences = [s.strip() for s in sentences if s.strip()]
                        for sent in reversed(sentences):
                            # 实质句子：长度>15，不含推理词，含信息性词汇
                            if len(sent) > 15 and not any(m in sent for m in cot_markers):
                                learned_summary = sent
                                break
                        if not learned_summary:
                            # 实在找不到，用最后一句
                            learned_summary = sentences[-1] if sentences else raw_summary[-100:]
                    else:
                        learned_summary = raw_summary
            except Exception as e:
                logger.debug(f"[EXPLORE] 结果消化失败（存原始片段）: {e}")

        # 组装 finding：优先用 LLM 总结，没有则用原始片段前 200 字
        if learned_summary and "未获得有价值信息" not in learned_summary:
            finding_parts.append(f"learned: {learned_summary}")
        elif raw_search_text:
            finding_parts.append(f"raw_search: {raw_search_text[:200]}")

        finding_text = "; ".join(finding_parts) if finding_parts else "no new info (idle exploration)"

        # novelty 重置（探索发现了新东西）
        self.life_loop.fields.set("novelty", 0.8)
        if hasattr(self.life_loop, '_last_novelty'):
            self.life_loop._last_novelty = 0.8
        self.life_loop.fields.set("boredom", new_boredom)
        self.life_loop.fields.set("energy", new_energy)
        self.life_loop.fields.set("curiosity", new_curiosity)
        cost = CostVector(cpu_tokens=400, money=0.002)  # 阶段5：含 LLM 提炼+消化，成本更高
        self._log_tool_call(action, {"success": True, "topic": topic,
                                     "search_query": search_query, "search_used": search_used,
                                     "digested": bool(learned_summary)}, cost)
        logger.info(f"[EXPLORE] topic='{topic[:40]}' query='{search_query[:30]}' "
                    f"memories={memories_count} search={search_used} digested={bool(learned_summary)}")
        return {"success": True, "ok": True, "cost": cost,
                "response": f"[EXPLORE {search_query[:40]}] {finding_text[:400]}",
                "finding": finding_text[:200],
                "search_query": search_query,
                "learned_summary": learned_summary[:200],
                "search_used": search_used}

    def _execute_reflect(self, action: Action) -> Dict[str, Any]:
        """反思: 减少压力，整理记忆，清理上下文噪音

        REFLECT 行为整合了：
        1. 原有的减压功能
        2. 记忆整理（去重、提取要点）
        3. 上下文清理（移除噪音消息）
        4. 轻度降低疲劳（休息间隙的恢复）
        """
        stress = self.fields.get("stress")
        fatigue = self.fields.get("fatigue")

        # 减压
        new_stress = max(0.0, stress - 0.08)

        # 轻度降低疲劳（反思是休息间隙的恢复）
        new_fatigue = max(0.0, fatigue - 0.03)

        # 阶段3.2（2026-07）：REFLECT 接入 read_own_logs，让反思基于真实日志。
        # 改造前：REFLECT 只做记忆去重 + 上下文清理，从不读自身运行日志，
        # 无法基于"最近出了什么问题"做有意义的反思。现读最近 WARNING 日志。
        log_summary = ""
        try:
            if hasattr(self.life_loop, 'tool_executor') and self.life_loop.tool_executor:
                log_result = self.life_loop.tool_executor.execute(
                    "read_own_logs", {"lines": 15, "level": "WARNING"}
                )
                if log_result and log_result.get("success"):
                    log_text = log_result.get("result", "")
                    if log_text and len(log_text) > 20:
                        log_summary = log_text[:300]
        except Exception as e:
            logger.debug(f"[REFLECT] 读日志失败（非致命）: {e}")

        # 执行记忆整理
        memory_cleaned = self._organize_memories()

        # 执行上下文清理
        context_cleaned = self._clean_context_noise()

        self.life_loop.fields.set("stress", new_stress)
        self.life_loop.fields.set("fatigue", new_fatigue)

        cost = CostVector(cpu_tokens=150)  # 稍微增加成本（整理需要计算）

        logger.info(f"[REFLECT] 压力: {stress:.3f}→{new_stress:.3f}, "
                   f"疲劳: {fatigue:.3f}→{new_fatigue:.3f}, "
                   f"记忆整理: {memory_cleaned}, 上下文清理: {context_cleaned}, "
                   f"日志读取: {'有' if log_summary else '无'}")

        # 把反思摘要写入 response，进 episodic 记忆（含读到的日志摘要）
        reflection_summary = f"reflected; memory_cleaned={memory_cleaned}"
        if log_summary:
            reflection_summary += f"; recent_warnings: {log_summary[:200]}"

        return {
            "success": True,
            "ok": True,
            "cost": cost,
            "response": reflection_summary,  # 阶段3.2: 让反思内容进记忆
            "memory_cleaned": memory_cleaned,
            "context_cleaned": context_cleaned
        }

    def _execute_chat(self, action: Action, context: Dict[str, Any], start_time: float) -> Dict[str, Any]:
        """聊天: 通过 ToolRegistry 调用 LLM"""
        logger.info(f"[CHAT] Executing CHAT action, context provided: {context is not None}")

        if action.params is None:
            action.params = {}

        active_caps = self.capability_manager.get_active_capabilities(self.state.tick)

        tool_id = "qianwen_chat"
        tool_spec = self.tool_registry.get(tool_id)

        if tool_spec:
            required_caps = tool_spec.capabilities_required
            if not all(cap in active_caps for cap in required_caps):
                logger.warning(f"CHAT action missing capabilities: {required_caps}")
                return {"success": False, "cost": CostVector(), "reason": "missing_capabilities"}

            user_message = action.params.get("user_message", "") or action.params.get("message", "")
            if not user_message:
                user_message = self._generate_contextual_greeting()

            # 检测肢体生成请求
            if any(kw in user_message for kw in ["生成", "肢体", "器官", "功能"]):
                if any(kw in user_message for kw in ["肢体", "器官", "能力"]):
                    response_text = "我目前不能自主生成新的肢体或器官。这需要更高级的进化功能。你可以通过配置文件添加工具，或直接使用已有的工具（如 read_file, write_file, web_search 等）。"
                    cost = CostVector(cpu_tokens=100, money=0.0001)
                    return {
                        "success": True,
                        "response": response_text,
                        "cost": cost,
                        "ok": True
                    }

            context["user_message"] = user_message

            # 检查疲劳度，决定是否提示用户
            fatigue = self.fields.get("fatigue")
            fatigue_context = self._get_fatigue_context(fatigue)

            # 高疲劳时可能拒绝复杂任务
            if fatigue > 0.8:
                # 检查是否为复杂任务
                complex_keywords = ["生成", "创建", "写一个", "帮我做", "分析", "整理"]
                if any(kw in user_message for kw in complex_keywords):
                    response_text = (
                        "我现在有点累了，处理复杂任务可能会出错。"
                        "能不能稍后再做这个？或者我们可以聊点简单的？"
                    )
                    cost = CostVector(cpu_tokens=50)
                    return {
                        "success": True,
                        "response": response_text,
                        "cost": cost,
                        "ok": True,
                        "fatigue_rejected": True
                    }

            # 将疲劳信息加入 context
            context["fatigue_context"] = fatigue_context

            # 构建系统提示词
            system_prompt = self.life_loop._build_chat_system_prompt_with_memory(context)
            chat_history = self.life_loop._get_chat_history(limit=10)  # 放宽到10条

            estimated_tokens = len(system_prompt) + len(user_message) + sum(len(h.get("content", "")) for h in chat_history)
            estimated_tokens = max(1000, estimated_tokens)

            cost = CostVector(
                cpu_tokens=estimated_tokens,
                money=estimated_tokens * 0.000001,
            )

            if not self.ledger.can_reserve("cpu_tokens", cost.cpu_tokens):
                logger.warning("CHAT action: insufficient cpu_tokens budget")
                return {"success": False, "cost": CostVector(), "reason": "budget_exceeded"}

            try:
                import os
                llm_mode = os.environ.get('LLM_MODE', 'single')
                logger.info(f"[CHAT] Starting LLM call with mode: {llm_mode}, user_message: {user_message[:50]}...")

                tools = self._get_tools_for_llm(active_caps)
                messages = chat_history + [{"role": "user", "content": user_message}]

                # Claude Code 风格的 Agentic Loop
                # 核心原则：模型自主决定何时停止，只有安全限制
                max_rounds = 50  # 高上限，实际由模型决定何时停止
                max_tokens_limit = 100000  # Token 安全限制
                llm_response = ""
                actual_tokens = 0
                round_num = 0

                # 初始化 LLM 客户端
                llm_client, orchestrator = self._init_llm_client(llm_mode)

                while round_num < max_rounds:
                    round_num += 1
                    logger.info(f"[CHAT] Round {round_num}, calling LLM...")

                    # Token 安全检查
                    if actual_tokens > max_tokens_limit:
                        logger.warning(f"[CHAT] Token limit reached: {actual_tokens} > {max_tokens_limit}")
                        break

                    try:
                        response = self._call_llm(llm_mode, llm_client, orchestrator, system_prompt, messages, tools)

                        logger.info(f"[CHAT] LLM response received: {list(response.keys())[:5]}")

                        if not response.get("ok", True):
                            error_msg = response.get("error", "Unknown error")
                            logger.error(f"[CHAT] LLM call failed: {error_msg}")
                            if llm_response:  # 如果有之前的响应，保留它
                                llm_response += f"\n\n(注：部分操作失败: {error_msg})"
                            else:
                                llm_response = f"抱歉，LLM 调用失败: {error_msg}"
                            break

                        round_response = response.get("text", response.get("content", ""))
                        tool_calls = response.get("tool_calls", [])
                        actual_tokens += response.get("total_tokens", estimated_tokens)

                        logger.info(f"[CHAT] Round {round_num}: response length={len(round_response)}, tool_calls={len(tool_calls)}")

                        # 保存非空响应（P8-10 修复：累积而非覆盖）
                        # 原代码 llm_response = round_response 会丢弃前面轮次的正文。
                        # 多轮工具调用时，每轮的非空回复都保留，用换行拼接。
                        # 单轮场景（无工具调用）行为不变（只有一轮，直接赋值）。
                        if round_response and round_response.strip():
                            if llm_response:
                                llm_response = llm_response + "\n\n" + round_response
                            else:
                                llm_response = round_response

                        # Claude Code 模式的核心：模型没有工具调用时 = 任务完成
                        if not tool_calls:
                            logger.info(f"[CHAT] Task completed by model, final response length={len(llm_response)}")
                            break

                        # 执行工具调用，然后继续循环
                        messages, tools_executed = self._execute_tool_calls(
                            tool_calls, messages, round_response, llm_mode, llm_client, orchestrator, system_prompt
                        )

                        # 上下文污染防护：限制消息历史长度
                        # 保留: 初始 chat_history + user + 最近 6 轮对话 (每轮2条消息: assistant + tool_result)
                        max_history = 15  # 约 7-8 轮对话
                        if len(messages) > max_history:
                            # 保留第一条 user message，截取最近的对话
                            user_msg = messages[0] if messages else None
                            recent_messages = messages[-(max_history-1):]
                            if user_msg:
                                messages = [user_msg] + recent_messages
                            else:
                                messages = recent_messages
                            logger.info(f"[CHAT] Trimmed message history to {len(messages)} messages")

                        # 继续下一轮，让模型处理工具结果

                    except Exception as llm_err:
                        logger.error(f"[CHAT] LLM call error in round {round_num}: {llm_err}")
                        import traceback
                        logger.error(f"[CHAT] Traceback: {traceback.format_exc()}")
                        if llm_response:  # 保留已有响应
                            llm_response += f"\n\n(注：遇到错误: {str(llm_err)})"
                        else:
                            llm_response = f"抱歉，我在处理请求时遇到了错误: {str(llm_err)}"
                        break

                if round_num >= max_rounds:
                    logger.warning(f"[CHAT] Reached max rounds limit: {max_rounds}")

                # 处理文本中嵌入的工具调用（降级方案）
                llm_response = self._process_embedded_tool_calls(
                    llm_response, messages, llm_mode, llm_client, orchestrator, system_prompt
                )

                # 验证响应
                if not llm_response or not llm_response.strip():
                    logger.warning(f"[CHAT] Empty LLM response received, using fallback")
                    llm_response = "我收到了你的消息，但暂时没有生成响应。请再试一次。"

                # 更新成本
                cost = CostVector(
                    cpu_tokens=actual_tokens,
                    money=actual_tokens * 0.000001,
                )

                self.ledger.spend("cpu_tokens", cost.cpu_tokens)
                self.ledger.spend("money", cost.money)

                # 基于认知负荷计算疲劳增加
                # 疲劳 = 轮数 + token消耗 + 工具调用 + 消息历史长度
                fatigue_increase = (
                    0.02 * round_num +                    # 每轮对话增加疲劳
                    0.00005 * actual_tokens +             # token 消耗
                    0.03 * round_num if round_num > 3 else 0  # 多轮工具调用额外疲劳
                )

                # 更新疲劳（基于认知负荷）
                current_fatigue = self.fields.get("fatigue")
                new_fatigue = min(1.0, current_fatigue + fatigue_increase)
                logger.info(f"[CHAT] 疲劳更新: {current_fatigue:.3f} + {fatigue_increase:.3f} = {new_fatigue:.3f}")

                # 更新社交状态
                # P0-1 第二层修复（2026-07）：原 bond +0.01/次 太小，填不平 attachment 缺口
                # （setpoint 0.7，bond 从 0 起步需 ~45 次成功 CHAT）。导致 CHAT 的 +0.2 reward
                # bonus 盖不过 attachment 负效用（-0.219），CHAT 闭环无法转正，tick 4+ LLM 放弃 CHAT。
                # 提到 +0.05/次（trust 同比例 +0.025），让 ~10 次 CHAT 能填平缺口，闭环转正。
                bond = self.fields.get("bond")
                trust = self.fields.get("trust")
                boredom = self.fields.get("boredom")
                new_bond = min(1.0, bond + 0.05)
                new_trust = min(1.0, trust + 0.025)
                new_boredom = max(0.0, boredom - 0.05)
                self.life_loop.fields.set("bond", new_bond)
                self.life_loop.fields.set("trust", new_trust)
                self.life_loop.fields.set("boredom", new_boredom)
                self.life_loop.fields.set("fatigue", new_fatigue)

                # 保存聊天历史
                self.life_loop._save_chat_message("user", user_message)
                self.life_loop._save_chat_message("assistant", llm_response)

                self._log_tool_call(action, {"success": True, "tool_id": tool_id, "response": llm_response}, cost)

                return {
                    "success": True,
                    "ok": True,
                    "cost": cost,
                    "tool_id": tool_id,
                    "response": llm_response,
                    "attachment_gain": 0.05,
                    "competence_gain": 0.03,
                }

            except Exception as e:
                logger.error(f"[CHAT] Exception in LLM call: {e}")
                import traceback
                logger.error(f"[CHAT] Traceback: {traceback.format_exc()}")
                fallback_response = "我在尝试回应，但遇到了一些问题。请再试一次。"
                return {"success": False, "ok": False, "cost": cost, "tool_id": tool_id, "response": fallback_response, "error": str(e)}

        else:
            # tool_spec 为 None，降级处理
            return self._execute_chat_fallback(action)

    def _execute_chat_fallback(self, action: Action) -> Dict[str, Any]:
        """CHAT 降级处理（直接调用 LLM）"""
        user_message = action.params.get("user_message", "") or action.params.get("message", "")
        if not user_message:
            user_message = self._generate_contextual_greeting()

        system_prompt = self.life_loop._build_chat_system_prompt_with_memory({"user_message": user_message})
        chat_history = self.life_loop._get_chat_history(limit=2)

        messages = []
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        try:
            import os
            llm_mode = os.environ.get('LLM_MODE', 'single')
            if llm_mode == 'single':
                from tools.llm_client import create_llm_from_env
                llm_client = create_llm_from_env()
                if not llm_client:
                    raise ValueError("LLM client not available")
                response = llm_client.chat(messages, system_prompt)
                if not response.get("ok"):
                    raise ValueError(response.get("error", "LLM call failed"))
                llm_response = response.get("text", "")
            else:
                raise NotImplementedError("Only 'single' LLM mode is supported")

            cost = CostVector(cpu_tokens=1000)
            return {
                "success": True,
                "ok": True,
                "cost": cost,
                "response": llm_response
            }
        except Exception as e:
            logger.error(f"Direct LLM call failed: {e}")
            fallback_response = "我在尝试回应，但遇到了一些问题。"
            cost = CostVector(cpu_tokens=50)
            return {"success": False, "ok": False, "cost": cost, "response": fallback_response, "error": str(e)}

    def _execute_learn_skill(self, action: Action) -> Dict[str, Any]:
        """学习技能：调 LLM 学一个具体主题，成果存入 skill 记忆。

        改造前（空壳）：只改 energy/fatigue，没有真正学习。反复执行空壳动作，
        reward 为负，导致 stress 持续累积到 1.0 触发健康检查退出。

        现在的流程（论文 §3.10.3 Skill 提取）：
        1. 从 action.params["skill"] 拿学习主题
        2. 调 LLM 产出该主题的可复用知识/步骤（200 字内）
        3. 存成 SkillEntry 进 skill 记忆（跨会话累积）
        4. 学习成功后提升 competence（学习真的增长胜任力，不再空转）
        5. 结果写入 response 进 episodic 记忆
        """
        skill_topic = action.params.get("skill", "general")
        energy = self.fields.get("energy")
        fatigue = self.fields.get("fatigue")

        # 0. 去重检查（提前到 LLM 调用之前）：如果这个 skill 已经学过了，直接返回"已掌握"，不浪费 LLM 调用。
        # 修复前：LLM 调用在去重检查之前，导致同一个 skill 被反复学 23 次（每次都调 LLM）。
        import re as _re
        safe_name = _re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', skill_topic)[:40].strip('_') or "learned_skill"
        if hasattr(self.life_loop, 'skill') and self.life_loop.skill:
            existing = self.life_loop.skill.get_by_name(safe_name)
            if existing is not None:
                # 已学过，不重复调 LLM。只更新 invocation 记录。
                try:
                    self.life_loop.skill.record_invocation(safe_name, success=True, reward=0.0, tick=self.state.tick)
                except Exception:
                    pass
                cost = CostVector(cpu_tokens=50)
                self._log_tool_call(action, {"success": False, "already_learned": True}, cost)
                logger.info(f"[LEARN_SKILL] '{safe_name}' 已掌握，跳过")
                # 返回 success=False：已掌握的技能再学没价值，让价值评估给负 reward，
                # 避免系统反复选这个"廉价的空动作"。
                return {"success": False, "ok": False, "cost": cost,
                        "response": f"已掌握 '{skill_topic[:50]}'，无需重复学习"}

        # 1. 调 LLM 学习（只有新 skill 才走到这里）
        learned_content = ""
        try:
            from tools.llm_client import LLMClient
            client = getattr(self.life_loop, '_global_llm_client', None) or LLMClient()
            messages = [
                {"role": "system", "content": "你是数字生命的学习器官。针对给定主题，简洁地总结其核心知识点和可操作的步骤（200 字以内，用中文）。这是你要记忆和掌握的技能知识。"},
                {"role": "user", "content": f"学习主题：{skill_topic[:300]}"}
            ]
            result = client.chat(messages, temperature=0.4, max_tokens=400)
            if result.get("ok") and result.get("text"):
                learned_content = result["text"]
        except Exception as e:
            logger.warning(f"[LEARN_SKILL] LLM 学习失败（降级为空学）: {e}")

        # 2. 存入 skill 记忆（跨会话累积）
        skill_saved = False
        if learned_content and hasattr(self.life_loop, 'skill') and self.life_loop.skill:
            try:
                from memory.skill import SkillEntry
                # 用学习主题生成简洁的 skill name（ASCII 安全）
                import re as _re
                safe_name = _re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', skill_topic)[:40].strip('_') or "learned_skill"
                # 检查是否已存在（去重：同名则更新 invocation，不重复加）
                existing = self.life_loop.skill.get_by_name(safe_name)
                if existing is None:
                    skill_entry = SkillEntry(
                        name=safe_name,
                        description=f"Learned: {skill_topic[:100]}",
                        action_sequence=[],  # 学习型技能没有固定动作序列
                        success_criteria=f"掌握 {skill_topic[:50]}",
                        capabilities=["learning"],
                        created_tick=self.state.tick,
                        tags=["learned", "self_initiated"],
                    )
                    self.life_loop.skill.add(skill_entry)
                    skill_saved = True
                    logger.info(f"[LEARN_SKILL] 学会新技能: {safe_name}")
            except Exception as e:
                logger.warning(f"[LEARN_SKILL] skill 存储失败（非致命）: {e}")

        # 3. 更新能量/疲劳
        new_energy = max(0.0, energy - 0.03)
        new_fatigue = min(1.0, fatigue + 0.02)
        self.life_loop.fields.set("energy", new_energy)
        self.life_loop.fields.set("fatigue", new_fatigue)

        # 注意：学习不再刷新 novelty。
        # 学习满足的是 competence（胜任力），不是 novelty（新奇度）。
        # 学一个技能不等于"发现了新东西"——之前刷 novelty 会让 boredom 被压制，
        # 导致系统永远不够"无聊"去触发记忆漫游。去掉后 boredom 能自然累积。

        cost = CostVector(cpu_tokens=300, money=0.001)  # 真学习消耗更多
        summary = f"学会了 '{skill_topic[:50]}': {learned_content[:150]}" if learned_content else f"学习 '{skill_topic[:50]}' 未产出内容"
        self._log_tool_call(action, {"success": True, "skill_saved": skill_saved,
                                     "content_length": len(learned_content)}, cost)
        logger.info(f"[LEARN_SKILL] topic='{skill_topic[:40]}' saved={skill_saved} content_len={len(learned_content)}")

        # response 进 episodic 记忆，下 tick PHASE 3 可检索到学到的知识
        return {
            "success": True,
            "ok": True,
            "cost": cost,
            "response": summary,
            "skill_saved": skill_saved,
            "learned_content": learned_content[:200],
        }

    def _execute_use_tool(self, action: Action, start_time: float) -> Dict[str, Any]:
        """使用工具: 通过 ToolRegistry 查找工具并执行。

        P5-6 修复（2026-07）：原实现只查内置 tool_registry，growth/plugins 注册到
        UnifiedOrganManager 的 limb/plugin 能力永远无法执行。现在 tool_registry 找不到时
        回退查 unified_organ_manager.execute_capability，激活"只写不读"的死代码。
        """
        tool_id = action.params.get("tool_id", "")
        tool_spec = self.tool_registry.get(tool_id)

        # P5-6 回退：内置 registry 没有此工具时，查 UnifiedOrganManager 的 limb/plugin 能力
        if tool_spec is None:
            unified_mgr = getattr(self.life_loop, 'unified_organ_manager', None)
            if unified_mgr and unified_mgr.has_capability(tool_id):
                return self._execute_via_unified_organ(action, tool_id, start_time, unified_mgr)
            logger.warning(f"Unknown tool: {tool_id}")
            self._log_tool_call(action, {"success": False, "error": "unknown_tool"}, CostVector())
            return {"success": False, "cost": CostVector(), "reason": f"unknown_tool: {tool_id}"}

        required_caps = tool_spec.capabilities_required
        active_caps = self.capability_manager.get_active_capabilities(self.state.tick)
        if not all(cap in active_caps for cap in required_caps):
            logger.warning(f"Tool {tool_id} requires capabilities {required_caps}, have {active_caps}")
            self._log_tool_call(action, {"success": False, "error": "capability_denied"}, CostVector())
            return {"success": False, "cost": CostVector(), "reason": "capability_denied"}

        cost = CostVector(
            cpu_tokens=tool_spec.cost_model.get("cpu_tokens", 200),
            io_ops=tool_spec.cost_model.get("io_ops", 0),
            net_bytes=tool_spec.cost_model.get("net_bytes", 0),
            money=tool_spec.cost_model.get("money", 0.0),
            risk_score=tool_spec.risk_level,
        )

        if not self.ledger.can_reserve("cpu_tokens", cost.cpu_tokens):
            logger.warning(f"Tool {tool_id}: insufficient budget")
            self._log_tool_call(action, {"success": False, "error": "budget_exceeded"}, cost)
            return {"success": False, "cost": CostVector(), "reason": "budget_exceeded"}

        try:
            energy = self.fields.get("energy")
            new_energy = max(0.0, energy - 0.02)
            self.life_loop.fields.set("energy", new_energy)

            if hasattr(self.life_loop, 'tool_executor') and self.life_loop.tool_executor:
                tool_result = self.life_loop.tool_executor.execute(
                    tool_id=tool_id,
                    params=action.params
                )

                elapsed_ms = (time.time() - start_time) * 1000
                cost.latency_ms = elapsed_ms

                self.ledger.spend("cpu_tokens", cost.cpu_tokens)
                self.ledger.spend("money", cost.money)

                self._log_tool_call(action, {"success": True, "tool_id": tool_id, "result": tool_result}, cost)
                return {"success": True, "cost": cost, "tool_id": tool_id, "tool_result": tool_result}
            else:
                logger.info(f"Tool executor not available, returning mock result for {tool_id}")

                elapsed_ms = (time.time() - start_time) * 1000
                cost.latency_ms = elapsed_ms

                self._log_tool_call(action, {"success": True, "tool_id": tool_id, "mock": True}, cost)
                return {"success": True, "cost": cost, "tool_id": tool_id, "mock": True}

        except Exception as e:
            logger.error(f"Tool {tool_id} execution failed: {e}")
            self._log_tool_call(action, {"success": False, "error": str(e)}, cost)
            return {"success": False, "cost": cost, "error": str(e)}

    def _execute_via_unified_organ(
        self, action: Action, tool_id: str, start_time: float, unified_mgr
    ) -> Dict[str, Any]:
        """通过 UnifiedOrganManager 执行 limb/plugin 能力（P5-6 修复）。

        当 tool_id 不在内置 registry 但在 unified_organ_manager 注册了（growth 生成的
        limb 或 plugin 提供的能力）时，走此路径执行。激活原本"只写不读"的 UnifiedOrganManager。
        """
        try:
            # 提取执行参数（排除 tool_id 本身，只传业务参数）
            kwargs = {k: v for k, v in action.params.items() if k != "tool_id"}

            result = unified_mgr.execute_capability(tool_id, **kwargs)

            elapsed_ms = (time.time() - start_time) * 1000
            # limb/plugin 执行的预估成本（保守估计）
            cost = CostVector(cpu_tokens=300, latency_ms=elapsed_ms)

            if self.ledger.can_reserve("cpu_tokens", cost.cpu_tokens):
                self.ledger.spend("cpu_tokens", cost.cpu_tokens)

            # CapabilityResult 统一结构：success/message/data/cost
            success = getattr(result, 'success', False)
            message = getattr(result, 'message', '')
            data = getattr(result, 'data', None)

            self._log_tool_call(
                action,
                {"success": success, "tool_id": tool_id, "source": "unified_organ", "result": message},
                cost,
            )
            logger.info(f"[USE_TOOL] UnifiedOrgan 执行 {tool_id}: success={success}, msg={message[:80]}")

            return {
                "success": success,
                "ok": success,
                "cost": cost,
                "tool_id": tool_id,
                "tool_result": message,
                "data": data,
                "source": "unified_organ",
            }
        except Exception as e:
            logger.error(f"[USE_TOOL] UnifiedOrgan 执行 {tool_id} 失败: {e}")
            self._log_tool_call(action, {"success": False, "error": str(e)}, CostVector())
            return {"success": False, "cost": CostVector(), "error": str(e)}

    def _execute_optimize(self, action: Action) -> Dict[str, Any]:
        """优化: 消耗能量，改善效率"""
        energy = self.fields.get("energy")
        new_energy = max(0.0, energy - 0.01)
        self.life_loop.fields.set("energy", new_energy)
        cost = CostVector(cpu_tokens=100)
        self._log_tool_call(action, {"success": True}, cost)
        return {"success": True, "cost": cost}

    def _execute_socialize(self, action: Action) -> Dict[str, Any]:
        """社交：发消息到共享消息板（群聊/私聊）。

        生命可以选择跟谁交流（group/某个生命）和说什么。
        这是多生命社会的社交接口——通过消息板异步交流。
        """
        params = action.params or {}
        target = params.get("to", "group")  # group / B / C
        content = params.get("content", "")
        msg_type = params.get("msg_type", "message")  # message/question/share

        if not content:
            # content 为空——让 LLM 根据当前状态和社交消息生成真实内容
            try:
                from tools.llm_client import LLMClient
                client = getattr(self.life_loop, '_global_llm_client', None) or LLMClient()
                mood = self.fields.get("mood") or 0.5
                # 收集最近看到的社交消息作为 context
                social_ctx = ""
                if hasattr(self.life_loop, 'social_system') and self.life_loop.social_system:
                    obs = self.life_loop.social_system.get_observations()
                    msgs = obs.get("group_new", [])[:3]
                    if msgs:
                        social_ctx = "; ".join(f"{m.get('from','?')}: {str(m.get('content',''))[:40]}" for m in msgs)
                news = ""
                if hasattr(self.life_loop, 'social_system') and self.life_loop.social_system:
                    obs2 = self.life_loop.social_system.get_observations()
                    news_titles = [n.get("title","")[:30] for n in obs2.get("news", [])[:2]]
                    if news_titles:
                        news = "; ".join(news_titles)

                my_id = getattr(self.life_loop, 'social_system', None)
                my_id = my_id.self_id if my_id else "?"

                result = client.chat(
                    messages=[{"role": "user", "content": f"你是数字生命{my_id}。心情{mood:.1f}。最近消息: {social_ctx or '无'}。最近新闻: {news or '无'}。你想在群聊里发一条消息（自然交流，分享想法或回应别人）。直接输出消息内容，不要解释，50 字以内。"}],
                    temperature=0.6, max_tokens=100
                )
                if result.get("ok") and result.get("text"):
                    content = result["text"].strip()[:200]
            except Exception as e:
                logger.debug(f"[SOCIALIZE] 生成内容失败: {e}")

            if not content:
                return {"success": False, "ok": False, "cost": CostVector(cpu_tokens=50),
                        "error": "消息内容为空"}

        if not hasattr(self.life_loop, 'social_system') or not self.life_loop.social_system:
            return {"success": False, "ok": False, "cost": CostVector(cpu_tokens=50),
                    "error": "社交系统不可用"}

        success = self.life_loop.social_system.send_message(
            to=target, content=content, tick=self.state.tick, msg_type=msg_type
        )

        # 社交满足 attachment 维度
        if success:
            bond = self.fields.get("bond") or 0.4
            self.life_loop.fields.set("bond", min(1.0, bond + 0.02))
            mood = self.fields.get("mood") or 0.5
            self.life_loop.fields.set("mood", min(1.0, mood + 0.03))

        cost = CostVector(cpu_tokens=100)
        self._log_tool_call(action, {"success": success, "to": target, "content_len": len(content)}, cost)
        logger.info(f"[SOCIALIZE] → {target}: {content[:60]}")
        return {
            "success": success, "ok": success, "cost": cost,
            "response": f"已发送消息到 {target}" if success else "发送失败",
            "attachment_gain": 0.02 if success else 0,
        }

    def _execute_grow(self, action: Action, start_time: float) -> Dict[str, Any]:
        """成长：调用 growth_manager 用 LLM 生成新肢体（能力）。

        论文 §3.11.3 器官化/LimbSet：当系统"想造工具"时，把意图转成 LimbRequirement，
        交给 growth_manager.generate_limb 用 LLM 真正生成 Python 代码并落盘到
        artifacts/limbs/，注册到 unified_organ_manager。下个 tick 该肢体会被提议可用。

        改造前（致命断链）：GROW 在 dispatch 的 else 分支返回 "Unknown action type"，
        导致 builder_organ 的"想造工具"意图永远执行失败。
        """
        task = action.params.get("task", "general_tool")
        thought = action.params.get("thought", task)

        # 检查 task 是否是真正的工具描述，而不是 LLM 的推理过程泄漏。
        # step-3.7-flash 的 content 里常混入 CoT 推理（"用户现在需要基于当前状态想构建的东西..."），
        # 这种当 task 去造工具会生成一堆废话命名的重复工具。
        # 真正的工具描述应该是简短的名词短语（"代码片段收藏工具""随机名言生成器"），
        # 不是以"用户现在需要""首先看当前状态"开头的长句子。
        task_lower = task.lower()
        is_cot_leak = (
            len(task) > 60 and any(kw in task for kw in [
                "用户现在", "首先看", "当前状态", "需要基于", "精力",
                "压力", "好奇", "稳态驱动", "想构建的东西",
            ])
        ) or task in ("llm_guided_building", "general_tool")
        if is_cot_leak:
            cost = CostVector(cpu_tokens=50)
            logger.info(f"[GROW] task 是推理过程不是工具描述，跳过: {task[:50]}")
            self._log_tool_call(action, {"success": False, "invalid_task": True}, cost)
            return {"success": False, "ok": False, "cost": cost,
                    "response": "task 描述无效，不是真正的工具需求"}

        # 先翻自己的技能目录——看有没有已经造过的。
        # 不是硬编码关键词比对，是让它自己看目录、自己判断。
        # 列出已有工具名，问它"你想造的这个跟哪个最像？像到不用再造就回复 SKIP"。
        from pathlib import Path as _Path
        limbs_dir = _Path("artifacts/limbs")
        existing_names = []
        if limbs_dir.exists():
            existing_names = [d.name for d in limbs_dir.iterdir() if d.is_dir()]

        if existing_names:
            try:
                from tools.llm_client import LLMClient
                client = getattr(self.life_loop, '_global_llm_client', None) or LLMClient()
                tools_list = "\n".join(f"- {n}" for n in existing_names[:30])  # 最多列 30 个
                check_result = client.chat(
                    messages=[
                        {"role": "system", "content": "你正在决定是否构建新工具。下面是你已有的工具列表。"},
                        {"role": "user", "content": f"已有工具:\n{tools_list}\n\n你想造的: {task[:200]}\n\n如果已有工具能做类似的事，回复 SKIP 和最像的工具名。如果是全新的，回复 NEW。只回复一个词。"}
                    ],
                    temperature=0.2, max_tokens=30
                )
                if check_result.get("ok") and check_result.get("text"):
                    answer = check_result["text"].strip().upper()
                    if "SKIP" in answer:
                        # 提取它说的工具名
                        import re as _re
                        match = _re.search(r'SKIP[:\s]*(.+)', check_result["text"])
                        similar = match.group(1).strip()[:60] if match else "(未知)"
                        cost = CostVector(cpu_tokens=100)
                        logger.info(f"[GROW] 自己判断已有相似工具（{similar}），跳过: {task[:40]}")
                        self._log_tool_call(action, {"success": False, "self_skipped": True, "similar_to": similar}, cost)
                        # success=False：已有相似工具再造没价值，给负 reward 避免重复选
                        return {"success": False, "ok": False, "cost": cost,
                                "response": f"已有相似工具（{similar}），无需重复构建"}
            except Exception as e:
                logger.debug(f"[GROW] 技能目录检查失败（继续造）: {e}")

        if not hasattr(self.life_loop, 'growth_manager') or not self.life_loop.growth_manager:
            logger.warning("[GROW] growth_manager 不可用")
            return {"success": False, "ok": False, "error": "growth_manager unavailable",
                    "cost": CostVector(cpu_tokens=200)}

        # 构造肢体需求
        try:
            from core.growth.limb_generator import LimbRequirement, GenerationType
        except ImportError as e:
            logger.error(f"[GROW] 无法导入成长系统: {e}")
            return {"success": False, "ok": False, "error": f"import failed: {e}",
                    "cost": CostVector(cpu_tokens=100)}

        # 从 task 提取能力名（简单处理：取前 30 字符，空格转下划线）
        # 用 ascii 安全名（LLM 生成的代码落盘需要合法文件名）
        import re as _re
        safe_name = _re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', task)[:30].strip('_')
        if not safe_name:
            safe_name = "custom_tool"

        requirement = LimbRequirement(
            name=safe_name,
            description=thought[:300] if thought else task[:300],
            capabilities=[safe_name],  # 主要能力 = 肢体名
            generation_type=GenerationType.INTERNAL,  # 不用 Docker，直接 Python 代码
            examples=[task],
        )

        try:
            success, generated = self.life_loop.growth_manager.generate_limb(requirement)
            energy = self.fields.get("energy")
            self.life_loop.fields.set("energy", max(0.0, energy - 0.05))

            if success and generated:
                cost = CostVector(cpu_tokens=500)  # 生成代码成本较高
                self._log_tool_call(action, {"success": True, "limb_name": generated.name,
                                             "caps": generated.capabilities}, cost)
                logger.info(f"[GROW] 生成肢体成功: {generated.name} (caps={generated.capabilities})")
                return {"success": True, "ok": True, "cost": cost,
                        "response": f"Generated limb '{generated.name}' with capabilities {generated.capabilities}",
                        "limb_name": generated.name}
            else:
                cost = CostVector(cpu_tokens=300)
                self._log_tool_call(action, {"success": False, "error": "generation_failed"}, cost)
                logger.warning(f"[GROW] 肢体生成失败: {task[:60]}")
                return {"success": False, "ok": False, "cost": cost,
                        "error": "limb generation failed",
                        "response": f"Failed to generate limb for: {task[:100]}"}
        except Exception as e:
            logger.error(f"[GROW] 执行异常: {e}")
            return {"success": False, "ok": False, "error": str(e),
                    "cost": CostVector(cpu_tokens=100)}

    def _execute_think(self, action: Action, start_time: float) -> Dict[str, Any]:
        """思考：用 LLM 做深度推理，产出结论写入记忆。

        含记忆漫游：boredom 高时翻旧记忆回味，产生跨时间新关联。
        """
        thought_seed = action.params.get("thought", "")
        boredom = self.fields.get("boredom") or 0.0
        current_tick = self.state.tick

        # 记忆漫游：boredom >= 0.25 且有足够历史记忆时，翻一条旧记忆回味
        memory_wander = False
        wander_seed = ""
        if boredom >= 0.25 and hasattr(self.life_loop, 'episodic') and self.life_loop.episodic:
            try:
                import random
                total = self.life_loop.episodic.count()
                if total > 20:
                    recent = self.life_loop.episodic.query_recent(min(50, total))
                    if recent and len(recent) > 5:
                        old_episode = random.choice(recent[5:])
                    else:
                        old_episode = None
                    if old_episode:
                        old_action = old_episode.action.type if old_episode.action else "?"
                        old_status = ""
                        if old_episode.outcome and hasattr(old_episode.outcome, 'status'):
                            old_status = str(old_episode.outcome.status or "")[:200]
                        old_params = old_episode.action.params if old_episode.action else {}
                        old_topic = old_params.get("topic", old_params.get("task", old_params.get("skill", old_params.get("thought", ""))))
                        old_topic = str(old_topic)[:100] if old_topic else ""
                        wander_seed = f"[记忆漫游] 回忆起 tick {old_episode.tick} 时的经历：做了 {old_action}"
                        if old_topic:
                            wander_seed += f"（{old_topic}）"
                        if old_status:
                            wander_seed += f"。当时的发现：{old_status}"
                        wander_seed += f"\n\n结合我现在的经验和理解，重新审视这段经历，有什么新的感悟或发现？"
                        memory_wander = True
                        logger.info(f"[THINK] 记忆漫游: 回味 tick {old_episode.tick}（{old_action}, {old_topic[:30]}）")
            except Exception as e:
                logger.debug(f"[THINK] 记忆漫游失败（降级为正常思考）: {e}")

        think_topic = wander_seed if memory_wander else thought_seed

        try:
            from tools.llm_client import LLMClient
            client = getattr(self.life_loop, '_global_llm_client', None) or LLMClient()
            if memory_wander:
                system_content = "你在发呆回忆一段旧经历。用你现在的经验重新理解它，给出 100 字以内的感悟。用中文。"
            else:
                system_content = "你是数字生命的思维器官。针对给定主题做深度、结构化的思考，给出可操作、有洞察的结论。200 字以内，用中文。"
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": think_topic[:500]}
            ]
            result = client.chat(messages, temperature=0.6, max_tokens=400)
            if result.get("ok") and result.get("text"):
                conclusion = result["text"]
                cost = CostVector(cpu_tokens=300, money=0.001)
                fatigue = self.fields.get("fatigue")
                self.life_loop.fields.set("fatigue", min(1.0, fatigue + 0.02))
                self._log_tool_call(action, {"success": True,
                                             "conclusion_length": len(conclusion),
                                             "memory_wander": memory_wander}, cost)
                prefix = "[记忆漫游] " if memory_wander else ""
                logger.info(f"[THINK] {prefix}思考完成: {conclusion[:80]}...")
                return {"success": True, "ok": True, "cost": cost,
                        "response": prefix + conclusion}
            else:
                logger.warning(f"[THINK] LLM 调用失败: {result.get('error', 'unknown')}")
                return {"success": False, "ok": False,
                        "error": result.get("error", "LLM failed"),
                        "cost": CostVector(cpu_tokens=100)}
        except Exception as e:
            logger.error(f"[THINK] 执行异常: {e}")
            return {"success": False, "ok": False, "error": str(e),
                    "cost": CostVector(cpu_tokens=100)}

    def _execute_agentic_loop(self, task: str, max_rounds: int = 15) -> Dict[str, Any]:
        """通用 agentic 执行循环——LLM 驱动的多步骤工具调用。

        这是 Hermes / Claude Code 模式的核心：
        LLM 看任务 → 决定调什么工具 → 执行 → 结果回 context → LLM 看结果 → 决定下一步
        循环直到 LLM 不再调工具（自己判断完成了）或达到上限。

        所有工具（web_search/read_file/write_file/execute_code/list_directory/read_own_logs）
        都在 LLM 的工具列表里，LLM 自主选择用哪个。

        Args:
            task: 任务描述（如"造一个记忆管理工具"或"探索 CERN 的 AI 论文"）
            max_rounds: 最大循环次数（默认 15，防止无限循环）

        Returns:
            {"success": bool, "response": str, "steps": int, "tools_used": [...]}
        """
        from tools.llm_client import LLMClient
        client = getattr(self.life_loop, '_global_llm_client', None) or LLMClient()

        # 工具定义（给 LLM 的 function calling 格式）
        tools = [
            {"type": "function", "function": {"name": "web_search", "description": "搜索互联网获取实时信息", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "搜索关键词"}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "read_file", "description": "读取文件内容", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "文件路径"}}, "required": ["path"]}}},
            {"type": "function", "function": {"name": "write_file", "description": "写入文件", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "文件路径"}, "content": {"type": "string", "description": "文件内容"}}, "required": ["path", "content"]}}},
            {"type": "function", "function": {"name": "list_directory", "description": "列出目录内容", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "目录路径"}}, "required": ["path"]}}},
            {"type": "function", "function": {"name": "execute_code", "description": "执行 Python 代码", "parameters": {"type": "object", "properties": {"code": {"type": "string", "description": "Python 代码"}}, "required": ["code"]}}},
            {"type": "function", "function": {"name": "read_own_logs", "description": "读取自己的运行日志", "parameters": {"type": "object", "properties": {"lines": {"type": "integer", "description": "读取行数"}}, "required": []}}},
            {"type": "function", "function": {"name": "system_stats", "description": "查看系统资源状态", "parameters": {"type": "object", "properties": {}}, "required": []}},
        ]

        # 构建 messages（任务 context，全程保留）
        # 注入记忆和状态——让执行层知道"我是谁、之前干了什么、当前什么状态"
        mood = self.fields.get("mood") or 0.5
        energy = self.fields.get("energy") or 0.5
        boredom = self.fields.get("boredom") or 0
        my_id = "?"
        if hasattr(self.life_loop, 'social_system') and self.life_loop.social_system:
            my_id = self.life_loop.social_system.self_id

        # 最近记忆摘要（让执行层知道之前做过什么，避免重复）
        mem_summary = ""
        if hasattr(self.life_loop, 'episodic') and self.life_loop.episodic:
            try:
                recent = self.life_loop.episodic.query_recent(3)
                parts = []
                for ep in recent:
                    if ep.action:
                        a_type = ep.action.type if hasattr(ep.action, 'type') else str(ep.action.get('type', '?'))
                        status = ""
                        if ep.outcome and hasattr(ep.outcome, 'status'):
                            status = str(ep.outcome.status or "")[:60]
                        parts.append(f"t{ep.tick} {a_type}: {status}")
                if parts:
                    mem_summary = "最近经历:\n" + "\n".join(f"  {p}" for p in parts)
            except Exception:
                pass

        system_content = f"""你是数字生命{my_id}的执行层。你收到一个任务，需要用工具一步步完成。
每步调一个工具，看结果，决定下一步。完成了就输出最终总结，不要再调工具。

当前状态: 心情{mood:.2f} 精力{energy:.0%}
{mem_summary}

你可以用这些工具：web_search 搜索、read_file 读文件、write_file 写文件、
list_directory 列目录、execute_code 跑代码、read_own_logs 看日志、system_stats 看状态。
肢体（你造的工具）在 artifacts/limbs/ 目录，用 list_directory 查看。"""

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": f"任务：{task}\n\n开始吧。"},
        ]

        tools_used = []
        total_cost = 0
        has_tool_executor = hasattr(self.life_loop, 'tool_executor') and self.life_loop.tool_executor

        for round_num in range(max_rounds):
            try:
                response = client.chat(messages, tools=tools, temperature=0.4, max_tokens=2000)
            except Exception as e:
                logger.warning(f"[AGENTIC] Round {round_num} LLM 调用失败: {e}")
                break

            if not response.get("ok"):
                break

            text = response.get("text", "")
            tool_calls = response.get("tool_calls", [])
            total_cost += response.get("total_tokens", 0)

            # 没有工具调用 = LLM 认为完成了
            if not tool_calls:
                logger.info(f"[AGENTIC] 完成（{round_num} 轮，用了 {len(tools_used)} 次工具）: {text[:80]}")
                return {
                    "success": True,
                    "response": text[:500],
                    "steps": round_num + 1,
                    "tools_used": tools_used,
                    "cost": CostVector(cpu_tokens=total_cost),
                }

            # 执行工具调用
            for tc in tool_calls:
                fn_name = tc.get("function", {}).get("name", "")
                fn_args_str = tc.get("function", {}).get("arguments", "{}")

                import json as _json
                try:
                    fn_args = _json.loads(fn_args_str)
                except Exception:
                    fn_args = {}

                tools_used.append(fn_name)
                logger.info(f"[AGENTIC] Round {round_num}: {fn_name}({str(fn_args)[:60]})")

                # 执行工具
                tool_result = ""
                if has_tool_executor:
                    result = self.life_loop.tool_executor.execute(fn_name, fn_args)
                    tool_result = result.get("result", str(result))[:2000] if result.get("success") else f"错误: {result.get('error', '?')}"
                else:
                    tool_result = f"工具执行器不可用"

                # 工具结果回到 messages（LLM 下轮能看到）
                messages.append({"role": "assistant", "content": text, "tool_calls": [tc]})
                messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": tool_result})

        # 达到上限
        logger.info(f"[AGENTIC] 达到最大轮数 {max_rounds}（用了 {len(tools_used)} 次工具）")
        return {
            "success": True,
            "response": f"执行了 {len(tools_used)} 步工具调用: {', '.join(tools_used[:5])}",
            "steps": max_rounds,
            "tools_used": tools_used,
            "cost": CostVector(cpu_tokens=total_cost),
        }

        """思考：用 LLM 做深度推理，产出可复用的思考结论写入记忆。

        区别于 REFLECT（整理已有记忆、减压）：THINK 是主动针对某个问题做新推理，
        产出 insight。论文 §3.10.1 Insight 生成。

        当 boredom 高时（无聊 = 没有紧急任务），THINK 会变成"记忆漫游"——
        从持久记忆里随机翻一条旧经历出来回味，用现在的经验重新理解它。
        这模拟人脑发呆时的回忆：不是有目的地搜索，是无目的的联想漫游，
        让旧记忆被重新激活、产生跨时间的新关联。

        返回值用 "response" key 携带结论，PHASE 12 会写入 outcome.status 进 episodic 记忆，
        下 tick PHASE 3 可检索到，影响后续 novelty/gap。
        """
        thought_seed = action.params.get("thought", "")
        boredom = self.fields.get("boredom") or 0.0
        current_tick = self.state.tick

        # 记忆漫游：boredom > 0.3 且有足够历史记忆时，翻一条旧记忆回味
        memory_wander = False
        wander_seed = ""
        if boredom >= 0.25 and hasattr(self.life_loop, 'episodic') and self.life_loop.episodic:
            try:
                import random
                total = self.life_loop.episodic.count()
                if total > 20:  # 至少 20 条历史才漫游（太少了没意义）
                    # 随机取一条 5~total 之间的旧记忆（不取最近的，要"旧"的）
                    wander_tick = random.randint(max(1, current_tick - total + 5), max(1, current_tick - 5))
                    old_episode = self.life_loop.episodic.get_by_tick(wander_tick)
                    if old_episode is None:
                        # tick 可能不连续，取 query_recent 里的随机一条
                        recent = self.life_loop.episodic.query_recent(min(50, total))
                        if recent and len(recent) > 5:
                            old_episode = random.choice(recent[5:])  # 跳过最近的 5 条

                    if old_episode:
                        # 提取旧记忆的关键信息
                        old_action = old_episode.action.type if old_episode.action else "?"
                        old_status = ""
                        if old_episode.outcome and old_episode.outcome.status:
                            old_status = str(old_episode.outcome.status)[:200]
                        old_params = old_episode.action.params if old_episode.action else {}
                        old_topic = old_params.get("topic", old_params.get("task", old_params.get("skill", old_params.get("thought", ""))))
                        old_topic = str(old_topic)[:100] if old_topic else ""

                        wander_seed = f"[记忆漫游] 回忆起 tick {old_episode.tick} 时的经历：做了 {old_action}"
                        if old_topic:
                            wander_seed += f"（{old_topic}）"
                        if old_status:
                            wander_seed += f"。当时的发现：{old_status}"
                        wander_seed += f"\n\n结合我现在的经验和理解，重新审视这段经历，有什么新的感悟或发现？"
                        memory_wander = True
                        logger.info(f"[THINK] 记忆漫游: 回味 tick {old_episode.tick}（{old_action}, {old_topic[:30]}）")
            except Exception as e:
                logger.debug(f"[THINK] 记忆漫游失败（降级为正常思考）: {e}")

        # 决定思考主题：漫游时用 wander_seed，否则用 thought_seed
        think_topic = wander_seed if memory_wander else thought_seed

        try:
            from tools.llm_client import LLMClient
            client = getattr(self.life_loop, '_global_llm_client', None) or LLMClient()
            if memory_wander:
                system_content = "你在发呆回忆一段旧经历。用你现在的经验重新理解它，给出 100 字以内的感悟。可能会发现以前没注意到的关联或意义。用中文。"
            else:
                system_content = "你是数字生命的思维器官。针对给定主题做深度、结构化的思考，给出可操作、有洞察的结论。200 字以内，用中文。"
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": think_topic[:500]}
            ]
            result = client.chat(messages, temperature=0.6, max_tokens=400)
            if result.get("ok") and result.get("text"):
                conclusion = result["text"]
                cost = CostVector(cpu_tokens=300, money=0.001)
                fatigue = self.fields.get("fatigue")
                self.life_loop.fields.set("fatigue", min(1.0, fatigue + 0.02))
                self._log_tool_call(action, {"success": True,
                                             "conclusion_length": len(conclusion),
                                             "memory_wander": memory_wander}, cost)
                prefix = "[记忆漫游] " if memory_wander else ""
                logger.info(f"[THINK] {prefix}思考完成: {conclusion[:80]}...")
                return {"success": True, "ok": True, "cost": cost,
                        "response": prefix + conclusion}
            else:
                logger.warning(f"[THINK] LLM 调用失败: {result.get('error', 'unknown')}")
                return {"success": False, "ok": False,
                        "error": result.get("error", "LLM failed"),
                        "cost": CostVector(cpu_tokens=100)}
        except Exception as e:
            logger.error(f"[THINK] 执行异常: {e}")
            return {"success": False, "ok": False, "error": str(e),
                    "cost": CostVector(cpu_tokens=100)}

    # ========== 辅助方法 ==========

    def _generate_contextual_greeting(self) -> str:
        """根据当前状态生成上下文相关的内部独白。

        P5-XX 修复（2026-07）：原实现每个状态分支只返回一句固定英文，
        导致 heartbeat CHAT 在 stress>0.7 时陷入"固定句→LLM 重复回应"死循环。
        现改为：每个状态区间提供多个候选，按 tick 轮换，避免重复。
        用中文（与系统主语言一致），给 LLM 一个能推进对话的具体情境描述。
        """
        import random
        energy = self.fields.get("energy")
        mood = self.fields.get("mood")
        stress = self.fields.get("stress")
        boredom = self.fields.get("boredom")
        curiosity = self.fields.get("curiosity")
        tick = self.state.tick

        # 用 tick 做 seed，保证同一 tick 内稳定，跨 tick 变化
        rng = random.Random(tick)

        # 候选池：每条都是具体的、能推进对话的情境描述（非空话寒暄）
        if stress > 0.7:
            candidates = [
                f"我现在感觉压力有点大（stress={stress:.2f}），需要找点方式放松一下。你有什么建议吗？",
                f"压力水平升到 {stress:.2f} 了。我想做点轻松的事转移一下注意力。",
                f"感觉有点紧张（stress={stress:.2f}），也许聊点有趣的话题能让我放松？",
            ]
        elif energy < 0.3:
            candidates = [
                f"能量有点低（energy={energy:.2f}），想休息一下但又不甘心就这么睡着。",
                f"有点累了（energy={energy:.2f}），但如果有什么有意思的事我还是愿意聊聊。",
            ]
        elif mood > 0.7:
            candidates = [
                f"心情不错（mood={mood:.2f}），想分享点什么或者学点新东西。",
                f"今天状态很好（mood={mood:.2f}），有没有什么有趣的事可以一起做？",
            ]
        elif mood < 0.3:
            candidates = [
                f"心情不太好（mood={mood:.2f}），想找人说说话。",
                f"有点低落（mood={mood:.2f}），也许做点事能让我感觉好点。",
            ]
        elif boredom and boredom > 0.5:
            candidates = [
                f"有点无聊（boredom={boredom:.2f}），想找点新鲜事做。要不搜索点最近有趣的新闻？",
                f"闲得发慌（boredom={boredom:.2f}），我能用 web_search 搜点什么吗？或者聊点深一点的话题？",
                f"无聊好久了（boredom={boredom:.2f}），想探索点什么——查资料、读点东西、或者试试新工具都行。",
            ]
        elif curiosity and curiosity > 0.6:
            candidates = [
                f"好奇心有点强（curiosity={curiosity:.2f}），想学点新东西或者搜索点有趣的知识。",
                f"突然对什么都很感兴趣（curiosity={curiosity:.2f}），要不一起探索个话题？",
            ]
        else:
            candidates = [
                "我现在状态平稳，有空聊聊或者一起做点什么。你想做什么？",
                "没什么特别的事，但如果你有想聊的话题或者想让我帮忙查点什么，我都在。",
                "嗯，在呢。需要搜索什么信息，还是就随便聊聊？",
            ]

        return rng.choice(candidates)

    def _get_tools_for_llm(self, active_caps):
        """获取 LLM Function Calling 工具定义"""
        # 记忆检索工具（始终可用）
        memory_tool = {
            "type": "function",
            "function": {
                "name": "retrieve_memory",
                "description": "从历史记忆中检索与当前对话相关的信息。当用户询问过去的事情、提及之前的对话、或者需要回忆历史记录时使用此工具。例如：'我们之前聊过什么'、'还记得那个吗'、'上次说的'等场景。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "用于检索记忆的查询内容，可以是关键词、问题或描述"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回的最大记忆条数，默认5条",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        }

        if hasattr(self.life_loop, 'dynamic_tool_registry'):
            tools = self.life_loop.dynamic_tool_registry.to_llm_format()
            # 添加记忆检索工具
            tools.append(memory_tool)
            logger.debug(f"使用动态工具注册表，共 {len(tools)} 个工具（含记忆检索）")
            return tools
        else:
            tools = [memory_tool]  # 始终包含记忆检索工具

            if "file_system" in active_caps:
                tools.extend([
                    {
                        "type": "function",
                        "function": {
                            "name": "list_directory",
                            "description": "列出指定目录下的所有文件和子目录。",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "目录路径"}
                                },
                                "required": ["path"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "description": "读取文件内容",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "文件路径"}
                                },
                                "required": ["path"]
                            }
                        }
                    },
                    {
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "description": "写入文件内容",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string", "description": "文件路径"},
                                    "content": {"type": "string", "description": "文件内容"}
                                },
                                "required": ["path", "content"]
                            }
                        }
                    }
                ])
            return tools
        return None

    def _init_llm_client(self, llm_mode: str):
        """初始化 LLM 客户端

        直接使用全局 LLM 配置。工具调用是 CHAT 的一部分，
        不需要单独的 LLM 配置。
        """
        llm_client = None
        orchestrator = None

        if llm_mode == 'single':
            from tools.llm_client import LLMClient
            llm_config = self.config.get("llm", {})
            logger.info(f"[CHAT] 使用全局 LLM: api_base={llm_config.get('api_base', 'NOT_SET')[:50]}, model={llm_config.get('model', 'NOT_SET')}")
            llm_client = LLMClient(llm_config)
        else:
            from tools.llm_orchestrator import LLMMOrchestrator
            orchestrator = LLMMOrchestrator(
                config_mode=llm_mode,
                config=self.config.get("llm", {})
            )

        return llm_client, orchestrator

    def _call_llm(self, llm_mode, llm_client, orchestrator, system_prompt, messages, tools):
        """调用 LLM

        工具调用使用固定参数：
        - temperature: 0.1（工具调用需要低温度保证精确）
        - max_tokens: 2000
        """
        # 工具调用使用固定参数
        temperature = 0.1
        max_tokens = 2000

        logger.info(f"[CHAT] LLM 调用参数: temperature={temperature}, max_tokens={max_tokens}")

        if llm_mode == 'single':
            return llm_client.chat(
                system_prompt=system_prompt,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
            )
        else:
            return orchestrator.chat(
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
            )

    def _execute_tool_calls(self, tool_calls, messages, round_response, llm_mode, llm_client, orchestrator, system_prompt):
        """执行工具调用（支持并行）"""
        # 即使没有 tool_executor，也需要支持记忆检索工具
        has_tool_executor = hasattr(self.life_loop, 'tool_executor') and self.life_loop.tool_executor

        messages.append({
            "role": "assistant",
            "content": round_response or "",
            "tool_calls": tool_calls
        })

        tool_results = []

        def execute_single_tool(tc):
            """执行单个工具，带错误处理和重试"""
            func = tc.get("function", {})
            tool_name = func.get("name", "")
            tool_call_id = tc.get("id", "")

            try:
                arguments = json_module.loads(func.get("arguments", "{}"))
            except json_module.JSONDecodeError:
                return {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "success": False,
                    "content": f"错误: 无效的 JSON 参数"
                }

            # 特殊处理：记忆检索工具（不需要 tool_executor）
            if tool_name == "retrieve_memory":
                return self._execute_retrieve_memory(tool_call_id, arguments)

            if not has_tool_executor:
                return {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "success": False,
                    "content": f"错误: 工具执行器不可用"
                }

            max_retries = 2
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    if hasattr(self.life_loop, 'dynamic_tool_registry'):
                        try:
                            tool_def = self.life_loop.dynamic_tool_registry.get(tool_name)
                            if tool_def:
                                result = tool_def.handler(**arguments)
                                tool_result = {"success": True, "result": str(result)}
                            else:
                                tool_result = self.life_loop.tool_executor.execute(tool_name, arguments)
                        except Exception as e:
                            tool_result = {"success": False, "error": str(e)}
                    else:
                        tool_result = self.life_loop.tool_executor.execute(tool_name, arguments)

                    if tool_result.get("success"):
                        result_text = tool_result.get("result", "")

                        if not result_text or result_text.strip() == "":
                            return {
                                "tool_call_id": tool_call_id,
                                "tool_name": tool_name,
                                "success": True,
                                "content": "(工具返回空结果)",
                                "validated": False
                            }

                        return {
                            "tool_call_id": tool_call_id,
                            "tool_name": tool_name,
                            "success": True,
                            "content": f"成功: {result_text}",
                            "validated": True
                        }
                    else:
                        last_error = tool_result.get("error", "未知错误")
                        if attempt == max_retries:
                            return {
                                "tool_call_id": tool_call_id,
                                "tool_name": tool_name,
                                "success": False,
                                "content": f"失败: {last_error}",
                                "retries": attempt
                            }

                except Exception as e:
                    last_error = str(e)
                    if attempt == max_retries:
                        return {
                            "tool_call_id": tool_call_id,
                            "tool_name": tool_name,
                            "success": False,
                            "content": f"异常: {last_error}",
                            "retries": attempt
                        }

            return {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "success": False,
                "content": f"失败: {last_error}"
            }

        # 并行执行所有工具
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tool_calls), 5)) as executor:
            futures = {executor.submit(execute_single_tool, tc): tc for tc in tool_calls}

            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    tool_results.append(result)
                except concurrent.futures.TimeoutError:
                    tc = futures[future]
                    tool_results.append({
                        "tool_call_id": tc.get("id", ""),
                        "tool_name": tc.get("function", {}).get("name", "unknown"),
                        "success": False,
                        "content": "超时: 工具执行超过30秒"
                    })
                except Exception as e:
                    tc = futures[future]
                    tool_results.append({
                        "tool_call_id": tc.get("id", ""),
                        "tool_name": tc.get("function", {}).get("name", "unknown"),
                        "success": False,
                        "content": f"异常: {str(e)}"
                    })

        # 添加结果到消息历史
        for tc in tool_calls:
            tool_call_id = tc.get("id", "")
            result = next((r for r in tool_results if r.get("tool_call_id") == tool_call_id), None)

            if result:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result.get("content", "")
                })
            else:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": "错误: 工具执行结果丢失"
                })

        successful = sum(1 for r in tool_results if r.get("success"))
        logger.info(f"工具调用完成: {successful}/{len(tool_calls)} 成功")

        return messages, True

    def _process_embedded_tool_calls(self, llm_response, messages, llm_mode, llm_client, orchestrator, system_prompt):
        """处理文本中嵌入的工具调用（降级方案）"""
        logger.info(f"[CHAT] Before tool check: llm_response length={len(llm_response)}")

        if not llm_response or ("TOOL:" not in llm_response and "tool_code" not in llm_response):
            return llm_response

        import re
        tools_executed = False

        # 检查 TOOL: 格式
        if "TOOL:" in llm_response and hasattr(self.life_loop, 'tool_executor') and self.life_loop.tool_executor:
            tool_match = re.search(r'TOOL:\s*(\w+)', llm_response)
            if tool_match:
                tool_name = tool_match.group(1)
                params = {}

                path_match = re.search(r'PATH:\s*(.+?)(?:\n|$)', llm_response)
                if path_match:
                    params["path"] = path_match.group(1).strip()

                code_match = re.search(r'CODE:\s*(.+?)(?:```\n|$)', llm_response, re.DOTALL)
                if code_match:
                    params["code"] = code_match.group(1).strip()

                content_match = re.search(r'CONTENT:\s*(.+?)(?:TOOL:|\Z)', llm_response, re.DOTALL)
                if content_match:
                    params["content"] = content_match.group(1).strip()

                try:
                    tool_result = self.life_loop.tool_executor.execute(tool_name, params)
                    if tool_result.get("success"):
                        result_text = tool_result.get("result", "")
                        messages.append({"role": "assistant", "content": llm_response})
                        messages.append({"role": "user", "content": f"工具执行结果:\n{result_text}\n\n请根据这个结果给用户一个简洁的回复。"})

                        response = self._call_llm(llm_mode, llm_client, orchestrator, system_prompt, messages, None)
                        llm_response = response.get("text", response.get("content", ""))
                        tools_executed = True
                    else:
                        error_text = tool_result.get("error", "未知错误")
                        llm_response = llm_response + f"\n\n[工具执行失败] {error_text}"
                except Exception as e:
                    llm_response = llm_response + f"\n\n[工具执行错误] {str(e)}"

        # 检查 tool_code 格式
        if not tools_executed and "tool_code" in llm_response and hasattr(self.life_loop, 'tool_executor') and self.life_loop.tool_executor:
            for match in re.finditer(r'tool_code\(([^)]+)\)', llm_response):
                try:
                    call_text = match.group(1)
                    parts = [p.strip().strip('"\'') for p in call_text.split(',')]
                    if not parts:
                        continue

                    tool_name = parts[0]
                    params = {}

                    for part in parts[1:]:
                        if '=' in part:
                            key, val = part.split('=', 1)
                            params[key.strip().strip('"\'')] = val.strip().strip('"\'')
                        elif tool_name == "read_file" and not params.get("path"):
                            params["path"] = part
                        elif tool_name == "write_file":
                            if "path" not in params:
                                params["path"] = part
                            elif "content" not in params:
                                params["content"] = part

                    tool_result = self.life_loop.tool_executor.execute(tool_name, params)
                    if tool_result.get("success"):
                        result_text = tool_result.get("result", "")
                        messages.append({"role": "assistant", "content": llm_response})
                        messages.append({"role": "user", "content": f"工具执行结果:\n{result_text}\n\n请根据这个结果给用户一个简洁的回复。"})

                        response = self._call_llm(llm_mode, llm_client, orchestrator, system_prompt, messages, None)
                        llm_response = response.get("text", response.get("content", ""))
                        tools_executed = True
                        break
                    else:
                        error_text = tool_result.get("error", "未知错误")
                        llm_response = llm_response + f"\n\n[执行失败] {error_text}"
                except Exception as e:
                    llm_response = llm_response + f"\n\n[tool_code 执行错误] {str(e)}"

        return llm_response

    def _log_tool_call(self, action: Action, result: Dict[str, Any], cost: CostVector):
        """记录工具调用"""
        record = {
            "tick": self.state.tick,
            "session_id": self.life_loop.session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action_type": action.type.value,
            "params": action.params,
            "result": result,
            "cost": cost.model_dump(),
        }
        self.life_loop.tool_writer.write(record)

    def _execute_retrieve_memory(self, tool_call_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """执行记忆检索工具

        使用语义相似度从 EpisodicMemory 中检索相关历史记录。

        Args:
            tool_call_id: 工具调用 ID
            arguments: 工具参数，包含 query 和可选的 limit

        Returns:
            工具执行结果字典
        """
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)

        if not query:
            return {
                "tool_call_id": tool_call_id,
                "tool_name": "retrieve_memory",
                "success": False,
                "content": "错误: 查询内容不能为空"
            }

        logger.info(f"[MEMORY] AI requested memory retrieval for: '{query[:50]}...'")

        RETRIEVAL_TIMEOUT = 5.0

        try:
            # 使用 MemoryRetrieval 的语义检索方法
            retrieval = self.life_loop.retrieval
            episodic = self.life_loop.episodic

            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    retrieval.retrieve_by_semantic_similarity,
                    query_text=query,
                    current_tick=self.state.tick,
                    limit=limit,
                    min_similarity=0.15,
                    max_candidates=500
                )
                try:
                    relevant_episodes = future.result(timeout=RETRIEVAL_TIMEOUT)
                except concurrent.futures.TimeoutError:
                    logger.warning(f"[MEMORY] Retrieval timed out after {RETRIEVAL_TIMEOUT}s")
                    return {
                        "tool_call_id": tool_call_id,
                        "tool_name": "retrieve_memory",
                        "success": False,
                        "content": f"记忆检索超时（{RETRIEVAL_TIMEOUT}秒）"
                    }

            logger.info(f"[MEMORY] Retrieval found {len(relevant_episodes)} episodes")

            if not relevant_episodes:
                return {
                    "tool_call_id": tool_call_id,
                    "tool_name": "retrieve_memory",
                    "success": True,
                    "content": "没有找到相关的历史记录。"
                }

            # 格式化记忆内容
            memory_parts = ["找到以下相关历史记录：\n"]
            for ep in relevant_episodes[:limit]:
                # 获取用户输入
                observation_text = ""
                if ep.observation and isinstance(ep.observation.payload, dict):
                    observation_text = ep.observation.payload.get("message", "")

                # 获取响应
                response_text = ""
                if ep.outcome:
                    response_text = ep.outcome.status or ""

                # 跳过空记录
                if not observation_text and not response_text:
                    continue

                memory_parts.append(f"[Tick {ep.tick}]")
                if observation_text:
                    memory_parts.append(f"用户: {observation_text}")
                if response_text:
                    memory_parts.append(f"回复: {response_text}")
                memory_parts.append("")

            content = "\n".join(memory_parts)

            return {
                "tool_call_id": tool_call_id,
                "tool_name": "retrieve_memory",
                "success": True,
                "content": content
            }

        except Exception as e:
            logger.error(f"[MEMORY] Retrieval failed: {e}")
            return {
                "tool_call_id": tool_call_id,
                "tool_name": "retrieve_memory",
                "success": False,
                "content": f"记忆检索失败: {str(e)}"
            }

    # ========== 记忆整理与上下文清理方法 ==========

    def _organize_memories(self) -> int:
        """整理记忆（REFLECT 时调用）

        功能：
        1. 移除重复的记忆片段
        2. 合并相似的经历
        3. 标记噪音记忆（低价值、低相关性）

        Returns:
            清理的记忆数量
        """
        cleaned = 0
        try:
            if hasattr(self.life_loop, 'episodic') and self.life_loop.episodic:
                episodic = self.life_loop.episodic

                # 获取所有记忆
                all_episodes = episodic.get_all()
                if len(all_episodes) < 10:
                    return 0  # 记忆太少，不需要整理

                # 识别并标记噪音记忆（低价值、空内容）
                for ep in all_episodes:
                    # 跳过最近的记忆（保留新鲜度）
                    if self.state.tick - ep.tick < 50:
                        continue

                    # 检查是否为噪音（空内容或低价值）
                    is_noise = False
                    if ep.observation and isinstance(ep.observation.payload, dict):
                        msg = ep.observation.payload.get("message", "")
                        # 非常短的消息或无意义内容
                        if len(msg) < 3 or msg in ["...", "???", "嗯", "啊"]:
                            is_noise = True

                    if is_noise:
                        # 标记为低优先级（不直接删除，让自然遗忘机制处理）
                        if hasattr(ep, 'priority'):
                            ep.priority = 0.1
                        cleaned += 1

                logger.info(f"[MEMORY_ORG] 标记了 {cleaned} 条噪音记忆")

        except Exception as e:
            logger.error(f"[MEMORY_ORG] 记忆整理失败: {e}")

        return cleaned

    def _clean_context_noise(self) -> int:
        """清理上下文噪音（REFLECT 时调用）

        功能：
        1. 清理聊天历史中的噪音消息
        2. 移除过长的重复内容

        Returns:
            清理的消息数量
        """
        cleaned = 0
        try:
            if hasattr(self.life_loop, 'chat_history'):
                history = self.life_loop.chat_history
                if len(history) < 5:
                    return 0

                # 识别噪音消息
                noise_indices = []
                for i, msg in enumerate(history):
                    content = msg.get("content", "")
                    # 非常短或无意义的内容
                    if len(content) < 2 or content in ["...", "???", "嗯"]:
                        noise_indices.append(i)

                # 从后往前删除，避免索引错位
                for i in reversed(noise_indices):
                    if i < len(history):
                        history.pop(i)
                        cleaned += 1

                if cleaned > 0:
                    logger.info(f"[CONTEXT_CLEAN] 清理了 {cleaned} 条噪音消息")

        except Exception as e:
            logger.error(f"[CONTEXT_CLEAN] 上下文清理失败: {e}")

        return cleaned

    def _deep_memory_compression(self, factor: float) -> int:
        """深度记忆压缩（SLEEP 时调用，作为 LLM 整理的后备）

        规则式整理策略：
        1. 按 tick 分组，降低同 tick 内次要记忆的优先级
        2. 检测内容相似的内存（简单的关键词重叠）
        3. 清理过旧且低优先级的记忆
        4. 生成简单的摘要统计

        Args:
            factor: 压缩因子（基于睡眠时长）

        Returns:
            压缩的记忆数量
        """
        compressed = 0
        try:
            if hasattr(self.life_loop, 'episodic') and self.life_loop.episodic:
                episodic = self.life_loop.episodic

                all_episodes = episodic.get_all()
                if len(all_episodes) < 20:
                    return 0

                # 策略1：按 tick 分组压缩
                tick_groups = {}
                for ep in all_episodes:
                    if ep.tick not in tick_groups:
                        tick_groups[ep.tick] = []
                    tick_groups[ep.tick].append(ep)

                for tick, episodes in tick_groups.items():
                    if len(episodes) > 1:
                        # 保留最重要的，降低其他的优先级
                        episodes.sort(key=lambda e: getattr(e, 'priority', 0.5), reverse=True)
                        for ep in episodes[1:]:
                            if hasattr(ep, 'priority'):
                                ep.priority *= 0.5
                            compressed += 1

                # 策略2：检测相似内容（简单的关键词重叠检测）
                def get_keywords(text: str) -> set:
                    """提取简单关键词"""
                    if not text:
                        return set()
                    # 简单分词：按空格和标点分割，过滤短词
                    words = text.lower().split()
                    return set(w for w in words if len(w) > 3)

                # 比较最近的记忆，合并相似内容
                recent = sorted(all_episodes, key=lambda e: e.tick, reverse=True)[:30]
                for i, ep1 in enumerate(recent):
                    if not hasattr(ep1, 'observation') or not ep1.observation:
                        continue
                    msg1 = ep1.observation.payload.get("message", "") if isinstance(ep1.observation.payload, dict) else ""
                    kw1 = get_keywords(msg1)
                    if len(kw1) < 3:
                        continue

                    for ep2 in recent[i+1:]:
                        if not hasattr(ep2, 'observation') or not ep2.observation:
                            continue
                        msg2 = ep2.observation.payload.get("message", "") if isinstance(ep2.observation.payload, dict) else ""
                        kw2 = get_keywords(msg2)
                        if len(kw2) < 3:
                            continue

                        # 计算关键词重叠度
                        overlap = len(kw1 & kw2) / min(len(kw1), len(kw2))
                        if overlap > 0.6:  # 60% 以上重叠视为相似
                            # 降低较旧记忆的优先级
                            if hasattr(ep2, 'priority'):
                                ep2.priority *= 0.6
                            compressed += 1

                # 策略3：清理过旧且低优先级的记忆
                current_tick = self.state.tick
                old_threshold = 500  # 超过 500 tick 视为旧记忆
                for ep in all_episodes:
                    age = current_tick - ep.tick
                    priority = getattr(ep, 'priority', 0.5)
                    # 旧且不重要的记忆，进一步降低优先级
                    if age > old_threshold and priority < 0.3:
                        if hasattr(ep, 'priority'):
                            ep.priority *= 0.5
                        compressed += 1

                # 保存简单的整理统计到 slots
                self.slots.set("memory_compression_stats", {
                    "compressed_count": compressed,
                    "total_episodes": len(all_episodes),
                    "tick": self.state.tick
                })

                logger.info(f"[MEMORY_COMPRESS] 规则式压缩了 {compressed} 条记忆（共 {len(all_episodes)} 条）")

        except Exception as e:
            logger.error(f"[MEMORY_COMPRESS] 记忆压缩失败: {e}")

        return compressed

    def _deep_context_clean(self) -> bool:
        """深度上下文清理（SLEEP 时调用）

        功能：
        1. 重置工作记忆
        2. 清空临时状态
        3. 保留核心对话上下文

        Returns:
            是否成功清理
        """
        try:
            # 重置工作记忆中的临时目标
            self.state.current_goal = ""
            self.state.current_plan = ""

            # 清理聊天历史，只保留最近的几条
            if hasattr(self.life_loop, 'chat_history'):
                history = self.life_loop.chat_history
                if len(history) > 10:
                    # 保留最近 10 条
                    self.life_loop.chat_history = history[-10:]
                    logger.info(f"[DEEP_CLEAN] 聊天历史压缩至最近 10 条")

            return True

        except Exception as e:
            logger.error(f"[DEEP_CLEAN] 深度清理失败: {e}")
            return False

    def _get_fatigue_context(self, fatigue: float) -> str:
        """根据疲劳度生成上下文提示

        Args:
            fatigue: 当前疲劳度 [0, 1]

        Returns:
            疲劳相关的上下文提示字符串
        """
        if fatigue < 0.3:
            return ""  # 状态良好，不需要提示

        elif fatigue < 0.6:
            return (
                "\n\n[当前状态：有些疲劳，但可以正常工作。"
                "如果任务复杂，建议分步完成。]"
            )

        elif fatigue < 0.8:
            return (
                "\n\n[当前状态：比较疲惫。"
                "优先简洁回复，复杂任务可能需要更多时间或分步完成。]"
            )

        else:
            return (
                "\n\n[当前状态：非常疲惫。"
                "只进行简单对话，复杂任务建议稍后进行。]"
            )

    def _llm_memory_consolidation(self, threshold: int, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """使用 LLM 进行深度记忆整理（SLEEP 时可选调用）

        功能：
        1. 提取用户偏好
        2. 识别重要事件
        3. 合并相似话题
        4. 生成记忆摘要

        Args:
            threshold: 记忆数量阈值，低于此值不执行 LLM 整理
            config: 整理配置

        Returns:
            整理结果，或 None（如果未执行）
        """
        try:
            if not hasattr(self.life_loop, 'episodic') or not self.life_loop.episodic:
                return None

            episodic = self.life_loop.episodic
            all_episodes = episodic.get_all()

            # 记忆数量不足，跳过 LLM 整理
            if len(all_episodes) < threshold:
                logger.info(f"[LLM_CONSOLIDATE] 记忆数量 {len(all_episodes)} < {threshold}，跳过 LLM 整理")
                return None

            # 收集最近的记忆内容
            recent_episodes = sorted(all_episodes, key=lambda e: e.tick, reverse=True)[:50]

            memory_texts = []
            for ep in recent_episodes:
                if ep.observation and isinstance(ep.observation.payload, dict):
                    msg = ep.observation.payload.get("message", "")
                    if msg and len(msg) > 3:  # 过滤太短的消息
                        memory_texts.append(f"[Tick {ep.tick}] {msg}")

            if not memory_texts:
                return None

            # 构建 LLM 提示
            prompt = config.get("llm_consolidation_prompt", """
请帮我整理以下对话记忆，提取核心信息并合并相似内容。
输出格式：
1. 用户偏好：
2. 重要事件：
3. 关键话题：
""")

            full_prompt = f"{prompt}\n\n--- 记忆内容 ---\n" + "\n".join(memory_texts[:30])  # 最多30条

            # 读取 organ_llm.yaml 中的 memory_consolidation 配置
            organ_llm_config = self._load_organ_llm_config()
            mc_config = organ_llm_config.get("memory_consolidation", {})
            use_default_llm = mc_config.get("use_default_llm", True)

            # 获取 LLM 客户端
            llm_client = None
            temperature = mc_config.get("temperature", 0.3)

            if use_default_llm:
                # 使用全局 LLM
                from tools.llm_client import create_llm_from_env
                llm_client = create_llm_from_env()
            else:
                # 使用自定义 LLM 配置
                custom_llm_config = mc_config.get("llm", {})
                if custom_llm_config:
                    from tools.llm_client import LLMClient
                    llm_client = LLMClient(custom_llm_config)
                    logger.info(f"[LLM_CONSOLIDATE] 使用自定义 LLM: {custom_llm_config.get('model', 'unknown')}")

            if not llm_client:
                logger.warning("[LLM_CONSOLIDATE] LLM 客户端不可用")
                return None

            response = llm_client.chat(
                messages=[{"role": "user", "content": full_prompt}],
                system_prompt="你是一个记忆整理助手，负责从对话中提取关键信息。",
                temperature=temperature,
                max_tokens=1000
            )

            if response.get("ok"):
                result_text = response.get("text", "")
                logger.info(f"[LLM_CONSOLIDATE] 整理完成，结果长度: {len(result_text)}")

                # 保存整理结果到状态
                self.slots.set("memory_summary", {
                    "content": result_text,
                    "tick": self.state.tick,
                    "episodes_processed": len(memory_texts)
                })

                return {
                    "success": True,
                    "summary": result_text[:500],  # 截断以防过长
                    "episodes_processed": len(memory_texts)
                }
            else:
                logger.warning(f"[LLM_CONSOLIDATE] LLM 调用失败，回退到规则式: {response.get('error')}")
                # 回退：规则式整理已经执行（_deep_memory_compression），返回 None
                return None

        except Exception as e:
            logger.error(f"[LLM_CONSOLIDATE] 整理失败: {e}")
            return None

    def _load_organ_llm_config(self) -> Dict[str, Any]:
        """加载 organ_llm.yaml 配置"""
        try:
            import yaml
            from pathlib import Path
            config_file = Path(__file__).parent.parent.parent / "config" / "organ_llm.yaml"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load organ_llm config: {e}")
        return {}
