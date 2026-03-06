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
        else:
            logger.warning(f"Unknown action type: {action.type}")
            return {"success": True, "cost": CostVector(cpu_tokens=50)}

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

        self.life_loop._sync_fields_to_global(
            energy=new_energy,
            fatigue=new_fatigue,
            stress=new_stress,
            boredom=new_boredom
        )

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
        """探索: 减少无聊，消耗能量"""
        boredom = self.fields.get("boredom")
        energy = self.fields.get("energy")
        new_boredom = max(0.0, boredom - 0.15)
        new_energy = max(0.0, energy - 0.02)
        self.life_loop._sync_fields_to_global(boredom=new_boredom, energy=new_energy)
        cost = CostVector(cpu_tokens=200)
        self._log_tool_call(action, {"success": True}, cost)
        return {"success": True, "cost": cost}

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

        # 执行记忆整理
        memory_cleaned = self._organize_memories()

        # 执行上下文清理
        context_cleaned = self._clean_context_noise()

        self.life_loop._sync_fields_to_global(stress=new_stress, fatigue=new_fatigue)

        cost = CostVector(cpu_tokens=150)  # 稍微增加成本（整理需要计算）

        logger.info(f"[REFLECT] 压力: {stress:.3f}→{new_stress:.3f}, "
                   f"疲劳: {fatigue:.3f}→{new_fatigue:.3f}, "
                   f"记忆整理: {memory_cleaned}, 上下文清理: {context_cleaned}")

        return {
            "success": True,
            "cost": cost,
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

                        # 保存非空响应（累积）
                        if round_response and round_response.strip():
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
                bond = self.fields.get("bond")
                trust = self.fields.get("trust")
                boredom = self.fields.get("boredom")
                new_bond = min(1.0, bond + 0.01)
                new_trust = min(1.0, trust + 0.005)
                new_boredom = max(0.0, boredom - 0.05)
                self.life_loop._sync_fields_to_global(bond=new_bond, trust=new_trust, boredom=new_boredom, fatigue=new_fatigue)

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
        """学习技能: 消耗能量，增长胜任力"""
        energy = self.fields.get("energy")
        fatigue = self.fields.get("fatigue")
        new_energy = max(0.0, energy - 0.03)
        new_fatigue = min(1.0, fatigue + 0.02)
        self.life_loop._sync_fields_to_global(energy=new_energy, fatigue=new_fatigue)
        cost = CostVector(cpu_tokens=150)
        self._log_tool_call(action, {"success": True}, cost)
        return {"success": True, "cost": cost}

    def _execute_use_tool(self, action: Action, start_time: float) -> Dict[str, Any]:
        """使用工具: 通过 ToolRegistry 查找工具并执行"""
        tool_id = action.params.get("tool_id", "")
        tool_spec = self.tool_registry.get(tool_id)

        if tool_spec is None:
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
            self.life_loop._sync_fields_to_global(energy=new_energy)

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

    def _execute_optimize(self, action: Action) -> Dict[str, Any]:
        """优化: 消耗能量，改善效率"""
        energy = self.fields.get("energy")
        new_energy = max(0.0, energy - 0.01)
        self.life_loop._sync_fields_to_global(energy=new_energy)
        cost = CostVector(cpu_tokens=100)
        self._log_tool_call(action, {"success": True}, cost)
        return {"success": True, "cost": cost}

    # ========== 辅助方法 ==========

    def _generate_contextual_greeting(self) -> str:
        """根据当前状态生成上下文相关的问候语"""
        energy = self.fields.get("energy")
        mood = self.fields.get("mood")
        stress = self.fields.get("stress")

        if stress > 0.7:
            return "I'm feeling a bit stressed right now."
        elif energy < 0.3:
            return "I'm running low on energy."
        elif mood > 0.7:
            return "I'm in good spirits today!"
        elif mood < 0.3:
            return "I've been better, but I'm managing."
        else:
            return "Hello! How can I help you today?"

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
