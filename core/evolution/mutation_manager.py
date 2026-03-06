"""Mutation Manager - 变异管理器

负责进化系统中的变异提案生成和应用。

核心功能：
- 生成变异提案（基于进化需求）
- 应用变异到克隆体
- 验证变异的有效性
- 回滚变异（如果需要）

变异类型（按风险级别排序）：
1. PARAMETER_TUNE: 参数微调（低风险）
2. PROMPT_OPTIMIZE: 提示词优化（低风险）
3. CONFIG_CHANGE: 配置变更（低风险）
4. REFACTOR_SMALL: 小型重构（中等风险）
5. MODULE_ADD: 添加模块（中等风险）
6. MODULE_REMOVE: 移除模块（中等风险）
7. REFACTOR_LARGE: 大型重构（高风险）
8. ARCHITECTURE_CHANGE: 架构变更（高风险）
9. CORE_MODIFY: 核心修改（极高风险）

注意：此模块默认关闭，因为还不够成熟。
"""

import time
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path

from common.logger import get_logger
from .models import MutationType, EvolutionProposal, CloneInstance, EVOLUTION_ENABLED

logger = get_logger(__name__)


class MutationManager:
    """变异管理器

    负责：
    1. 根据进化需求生成变异提案
    2. 将变异应用到克隆体
    3. 验证变异的有效性
    4. 管理变异历史

    使用方式：
        manager = MutationManager()
        proposal = manager.generate_proposal(need, context)
        success = manager.apply_mutation(clone, proposal)
    """

    # 变异类型的风险等级
    RISK_LEVELS = {
        MutationType.PARAMETER_TUNE: 0.1,
        MutationType.PROMPT_OPTIMIZE: 0.2,
        MutationType.CONFIG_CHANGE: 0.2,
        MutationType.MODULE_ADD: 0.4,
        MutationType.MODULE_REMOVE: 0.5,
        MutationType.REFACTOR_SMALL: 0.4,
        MutationType.REFACTOR_LARGE: 0.7,
        MutationType.ARCHITECTURE_CHANGE: 0.8,
        MutationType.CORE_MODIFY: 0.9,
    }

    def __init__(self, llm_client=None, config: Dict[str, Any] = None):
        """初始化变异管理器

        Args:
            llm_client: LLM客户端（用于生成变异提案）
            config: 配置
        """
        self.llm_client = llm_client
        self.config = config or {}

        # 最大允许风险等级
        self.max_risk_level = self.config.get("max_risk_level", 0.5)

        # 变异历史
        self._mutation_history: List[Dict[str, Any]] = []

        logger.info("MutationManager initialized")

    def generate_proposal(
        self,
        evolution_need: str,
        context: Dict[str, Any],
        mutation_type: MutationType = None
    ) -> Optional[EvolutionProposal]:
        """生成变异提案

        根据进化需求，生成具体的变异提案。

        Args:
            evolution_need: 进化需求描述
            context: 当前上下文
            mutation_type: 指定变异类型（可选）

        Returns:
            EvolutionProposal 或 None
        """
        logger.info(f"Generating mutation proposal for: {evolution_need}")

        # 如果没有指定变异类型，根据需求自动选择
        if mutation_type is None:
            mutation_type = self._select_mutation_type(evolution_need, context)

        # 检查风险等级
        risk_level = self.RISK_LEVELS.get(mutation_type, 0.5)
        if risk_level > self.max_risk_level:
            logger.warning(
                f"Mutation type {mutation_type.value} risk level ({risk_level}) "
                f"exceeds max allowed ({self.max_risk_level})"
            )
            # 降级到更安全的变异类型
            mutation_type = MutationType.PARAMETER_TUNE
            risk_level = self.RISK_LEVELS[mutation_type]

        # 生成提案（使用 LLM 或模板）
        if self.llm_client:
            proposal = self._generate_with_llm(evolution_need, context, mutation_type, risk_level)
        else:
            proposal = self._generate_from_template(evolution_need, context, mutation_type, risk_level)

        if proposal:
            logger.info(f"Generated proposal: {proposal.description}")
            self._mutation_history.append({
                "timestamp": time.time(),
                "need": evolution_need,
                "proposal": proposal.to_dict() if hasattr(proposal, 'to_dict') else str(proposal),
            })

        return proposal

    def _select_mutation_type(self, need: str, context: Dict[str, Any]) -> MutationType:
        """根据需求选择变异类型

        Args:
            need: 进化需求
            context: 上下文

        Returns:
            选择的变异类型
        """
        need_lower = need.lower()

        # 关键词匹配
        if any(kw in need_lower for kw in ["参数", "parameter", "调整", "tune"]):
            return MutationType.PARAMETER_TUNE
        elif any(kw in need_lower for kw in ["提示词", "prompt", "优化"]):
            return MutationType.PROMPT_OPTIMIZE
        elif any(kw in need_lower for kw in ["配置", "config", "设置"]):
            return MutationType.CONFIG_CHANGE
        elif any(kw in need_lower for kw in ["添加", "add", "新增", "模块"]):
            return MutationType.MODULE_ADD
        elif any(kw in need_lower for kw in ["删除", "remove", "移除"]):
            return MutationType.MODULE_REMOVE
        elif any(kw in need_lower for kw in ["重构", "refactor"]):
            return MutationType.REFACTOR_SMALL
        elif any(kw in need_lower for kw in ["架构", "architecture", "核心"]):
            return MutationType.ARCHITECTURE_CHANGE
        else:
            # 默认使用参数微调
            return MutationType.PARAMETER_TUNE

    def _generate_with_llm(
        self,
        need: str,
        context: Dict[str, Any],
        mutation_type: MutationType,
        risk_level: float
    ) -> Optional[EvolutionProposal]:
        """使用 LLM 生成变异提案

        Args:
            need: 进化需求
            context: 上下文
            mutation_type: 变异类型
            risk_level: 风险等级

        Returns:
            EvolutionProposal 或 None
        """
        try:
            prompt = f"""作为进化系统，请根据以下需求生成变异提案：

需求：{need}

变异类型：{mutation_type.value}

请提供：
1. 具体变更描述
2. 需要修改的文件列表
3. 预期收益
4. 风险评估

以 JSON 格式返回。"""

            # 调用 LLM
            if hasattr(self.llm_client, 'generate'):
                response = self.llm_client.generate(prompt)
            elif hasattr(self.llm_client, 'chat'):
                response = self.llm_client.chat(prompt)
            else:
                logger.warning("LLM client does not have generate or chat method")
                return None

            # 解析响应（简化处理）
            # TODO: 实现 JSON 解析
            return EvolutionProposal(
                mutation_type=mutation_type,
                description=f"LLM 生成的变异: {need[:50]}",
                target_files=[],
                changes={},
                expected_benefit="待评估",
                risk_level=risk_level,
            )

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return None

    def _generate_from_template(
        self,
        need: str,
        context: Dict[str, Any],
        mutation_type: MutationType,
        risk_level: float
    ) -> EvolutionProposal:
        """从模板生成变异提案

        Args:
            need: 进化需求
            context: 上下文
            mutation_type: 变异类型
            risk_level: 风险等级

        Returns:
            EvolutionProposal
        """
        # 简化的模板生成
        return EvolutionProposal(
            mutation_type=mutation_type,
            description=f"模板变异: {need[:100]}",
            target_files=[],
            changes={},
            expected_benefit=f"满足需求: {need[:50]}",
            risk_level=risk_level,
        )

    def apply_mutation(self, clone: CloneInstance, proposal: EvolutionProposal) -> bool:
        """应用变异到克隆体

        Args:
            clone: 克隆体实例
            proposal: 变异提案

        Returns:
            是否成功
        """
        logger.info(f"Applying mutation to clone {clone.clone_id}")
        logger.info(f"  Mutation type: {proposal.mutation_type.value}")
        logger.info(f"  Description: {proposal.description}")

        if not proposal.changes:
            logger.warning("No changes in proposal, nothing to apply")
            return True  # 空变更视为成功

        try:
            applied_count = 0
            for file_path, new_content in proposal.changes.items():
                target_file = clone.clone_path / file_path

                # 确保父目录存在
                target_file.parent.mkdir(parents=True, exist_ok=True)

                # 写入新内容
                target_file.write_text(new_content, encoding="utf-8")
                applied_count += 1
                logger.debug(f"Applied change to: {file_path}")

            logger.info(f"Applied {applied_count} changes to clone")
            return True

        except Exception as e:
            logger.error(f"Failed to apply mutation: {e}")
            return False

    def validate_mutation(self, clone: CloneInstance, proposal: EvolutionProposal) -> bool:
        """验证变异是否有效

        检查变异后的克隆体是否仍然可以正常工作。

        Args:
            clone: 克隆体实例
            proposal: 变异提案

        Returns:
            是否有效
        """
        logger.info(f"Validating mutation on clone {clone.clone_id}")

        # 检查目标文件是否存在
        for file_path in proposal.target_files:
            target_file = clone.clone_path / file_path
            if not target_file.exists():
                logger.warning(f"Target file not found: {file_path}")
                # 不一定是错误，可能是新文件

        # 检查语法（对 Python 文件）
        for file_path in proposal.target_files:
            if file_path.endswith(".py"):
                target_file = clone.clone_path / file_path
                if target_file.exists():
                    if not self._check_python_syntax(target_file):
                        logger.error(f"Syntax error in: {file_path}")
                        return False

        logger.info("Mutation validation passed")
        return True

    def _check_python_syntax(self, file_path: Path) -> bool:
        """检查 Python 文件语法

        Args:
            file_path: 文件路径

        Returns:
            语法是否正确
        """
        try:
            import py_compile
            py_compile.compile(str(file_path), doraise=True)
            return True
        except py_compile.PyCompileError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return False

    def get_mutation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取变异历史

        Args:
            limit: 最大返回数量

        Returns:
            变异历史列表
        """
        return self._mutation_history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "total_mutations": len(self._mutation_history),
            "max_risk_level": self.max_risk_level,
        }
