"""
Organ Differentiation: Dynamic Gene Expression System

Implements dynamic organ express/suppress based on:
- Stage (embryo/juvenile/adult/elder) - developmental maturity
- Mode (work/friend/sleep/reflect) - current activity context
- Signals (user_present, fatigue_high, stress_high, etc.) - state-driven
- Gene-level expression control with complex boolean conditions

References:
- 论文 3.10 器官系统+分化(differentiate)
- 代码大纲 core/differentiate.py
- 工作索引 10.7 differentiate: stage/mode/signal下express/suppress
"""

from typing import Dict, Any, Set, List, Tuple, Optional
from enum import Enum
import ast

from common.logger import get_logger

logger = get_logger(__name__)


class Stage(str, Enum):
    """Developmental stages"""
    EMBRYO = "embryo"      # Limited functionality, learning basics
    JUVENILE = "juvenile"  # Exploring and building skills
    ADULT = "adult"        # Full functionality
    ELDER = "elder"        # Wisdom, reflection, teaching


class Mode(str, Enum):
    """Activity modes"""
    WORK = "work"          # Task-focused, productive
    FRIEND = "friend"      # Social, bonding
    SLEEP = "sleep"        # Rest, consolidation
    REFLECT = "reflect"    # Introspection, learning
    PLAY = "play"          # Exploration, experimentation


class Gene:
    """
    Gene: Expression rule for an organ.

    A gene defines when an organ should be expressed or suppressed.
    """

    def __init__(
        self,
        organ_name: str,
        express_conditions: List[str],
        suppress_conditions: List[str],
        priority: int = 5
    ):
        """
        Initialize gene.

        Args:
            organ_name: Name of organ this gene controls
            express_conditions: List of conditions that activate expression
            suppress_conditions: List of conditions that suppress (override)
            priority: Execution priority (lower = higher priority)
        """
        self.organ_name = organ_name
        self.express_conditions = express_conditions
        self.suppress_conditions = suppress_conditions
        self.priority = priority

    def should_express(self, context: Dict[str, Any]) -> bool:
        """
        Check if organ should be expressed.

        Args:
            context: Evaluation context with stage/mode/signals

        Returns:
            True if should express
        """
        # Check suppress first (suppress overrides express)
        for condition in self.suppress_conditions:
            if self._evaluate_condition(condition, context):
                return False

        # Check express conditions (any must match)
        if not self.express_conditions:
            return True  # Default express if no conditions

        for condition in self.express_conditions:
            if self._evaluate_condition(condition, context):
                return True

        return False

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate boolean condition expression.

        Supports:
        - Variable checks: stage == adult, mode == work
        - Comparisons: stress > 0.7, fatigue < 0.3
        - Boolean operators: and, or, not
        - Signal checks: signal.user_present, signal.fatigue_high

        Args:
            condition: Condition string
            context: Evaluation context

        Returns:
            True if condition evaluates to true
        """
        # Security: Limit condition length to prevent DoS
        MAX_CONDITION_LENGTH = 200
        if len(condition) > MAX_CONDITION_LENGTH:
            logger.warning(f"Condition too long ({len(condition)} > {MAX_CONDITION_LENGTH}), rejecting")
            return False

        # Build evaluation environment with actual variable values
        eval_env = {}

        # Add stage and mode
        eval_env["stage"] = context.get("stage", "adult")
        eval_env["mode"] = context.get("mode", "work")

        # Add state variables directly to eval environment
        state = context.get("state", {})
        for key, value in state.items():
            eval_env[key] = value

        # Add signal variables as boolean values
        signals = context.get("signals", {})
        for signal_name, signal_value in signals.items():
            eval_env[f"signal_{signal_name}"] = bool(signal_value)

        # Also add signal dict for dot notation access
        eval_env["signal"] = {k: bool(v) for k, v in signals.items()}

        # Add constants
        eval_env["True"] = True
        eval_env["False"] = False

        # Parse and evaluate the condition
        try:
            # Parse the original condition (not modified)
            tree = ast.parse(condition, mode='eval')

            # Security checks: Only allow specific node types
            allowed_nodes = (
                ast.Expression,
                ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare,
                ast.Name, ast.Constant,
                ast.And, ast.Or, ast.Not,
                ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
                ast.Attribute,
                # Context nodes (required for variable access)
                ast.Load,
            )

            for node in ast.walk(tree):
                # Disallow dangerous operations
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    logger.warning(f"Dangerous AST node type detected in condition: {type(node).__name__}")
                    return False

                # Check node type is in allowed list
                node_type = type(node)
                # Get the actual node type name for comparison
                type_name = node_type.__name__
                # Compare against allowed node type names
                if not isinstance(node, allowed_nodes):
                    logger.warning(f"Disallowed AST node type: {type_name}")
                    return False

                # For Name nodes, check if identifier is in eval_env
                if isinstance(node, ast.Name):
                    if node.id not in eval_env:
                        logger.debug(f"Unknown identifier in condition: {node.id}")
                        return False

                # Handle Attribute nodes (e.g., signal.user_present, signal.fatigue_high)
                # 修复: 正确处理 signal.xxx 属性访问
                if isinstance(node, ast.Attribute):
                    # Block double-underscore attribute access (sandbox escape prevention)
                    if node.attr.startswith("__"):
                        logger.warning(f"Blocked dunder attribute access: {node.attr}")
                        return False

                    # Check if this is a valid signal attribute access
                    # e.g., signal.user_present -> node.value is ast.Name(id='signal'), node.attr is 'user_present'
                    if isinstance(node.value, ast.Name):
                        if node.value.id == "signal":
                            # signal.xxx access is allowed if 'signal' exists in eval_env
                            if "signal" not in eval_env:
                                logger.debug("Signal dict not available in eval environment")
                                return False
                            # The attribute will be resolved at runtime via eval_env["signal"][attr]
                            # No need to pre-validate the attribute name
                        elif node.value.id not in eval_env:
                            # Other attribute access on unknown variables
                            logger.debug(f"Unknown variable for attribute access: {node.value.id}")
                            return False

                # Limit nesting depth
                if hasattr(node, 'lineno') and hasattr(tree, 'body'):
                    nesting_depth = self._get_nesting_depth(node)
                    if nesting_depth > 5:
                        logger.warning(f"Expression nesting too deep: {nesting_depth}")
                        return False

            # 修复 H16: 使用 compile + eval 替代直接 eval，增加安全层
            # AST 验证已通过，现在使用编译后的代码对象执行
            compiled = compile(tree, filename="<gene_condition>", mode="eval")
            result = eval(compiled, {"__builtins__": {}}, eval_env)
            return bool(result)

        except Exception as e:
            # If evaluation fails, return False
            logger.debug(f"Condition evaluation failed: {condition} -> {e}")
            return False

    def _get_nesting_depth(self, node, depth=0) -> int:
        """Get maximum nesting depth of AST node.

        Args:
            node: AST node
            depth: Current depth

        Returns:
            Maximum nesting depth
        """
        if isinstance(node, ast.Call):
            child_depths = [self._get_nesting_depth(arg, depth + 1) for arg in node.args]
            child_depths.extend([self._get_nesting_depth(kw.value, depth + 1) for kw in node.keywords])
            return max(child_depths) if child_depths else depth
        elif isinstance(node, (ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare)):
            if hasattr(node, 'left'):
                left_depth = self._get_nesting_depth(node.left, depth + 1)
            else:
                left_depth = depth
            if hasattr(node, 'right'):
                right_depth = self._get_nesting_depth(node.right, depth + 1)
            else:
                right_depth = depth
            # Handle Compare.comparators (list of right-hand operands)
            if hasattr(node, 'comparators'):
                comp_depths = [self._get_nesting_depth(c, depth + 1) for c in node.comparators]
                right_depth = max([right_depth] + comp_depths)
            if hasattr(node, 'values'):
                value_depths = [self._get_nesting_depth(v, depth + 1) for v in node.values]
                all_depths = [left_depth, right_depth] + value_depths
                return max(all_depths) if all_depths else depth
            return max(left_depth, right_depth)
        return depth


class Genome:
    """
    Genome: Collection of genes defining organ expression patterns.

    The genome encodes the developmental program and adaptive rules.
    """

    def __init__(self):
        """Initialize with default gene set"""
        self.genes: List[Gene] = []
        self._load_default_genes()

    def _load_default_genes(self):
        """Load default gene expression rules"""

        # Caretaker: Always active (highest priority)
        self.genes.append(Gene(
            organ_name="caretaker",
            express_conditions=["True"],  # Always express
            suppress_conditions=[],        # Never suppress
            priority=0
        ))

        # Immune: Always active (safety critical)
        self.genes.append(Gene(
            organ_name="immune",
            express_conditions=["True"],
            suppress_conditions=[],
            priority=1
        ))

        # Mind: Main reasoning, active in most contexts
        self.genes.append(Gene(
            organ_name="mind",
            express_conditions=[
                'stage == "juvenile" or stage == "adult" or stage == "elder"',
                'mode == "work" or mode == "friend" or mode == "reflect"',
            ],
            suppress_conditions=[
                'mode == "sleep"',
                'fatigue > 0.9',
            ],
            priority=2
        ))

        # Scout: Exploration, suppressed under high stress
        self.genes.append(Gene(
            organ_name="scout",
            express_conditions=[
                'stage == "juvenile" or stage == "adult"',
                'stress < 0.7',
                'mode == "work" or mode == "play"',
            ],
            suppress_conditions=[
                'stage == "embryo"',
                'stress > 0.8',
                'mode == "sleep"',
                'fatigue > 0.8',
            ],
            priority=3
        ))

        # Builder: Project execution, not during sleep
        self.genes.append(Gene(
            organ_name="builder",
            express_conditions=[
                'stage == "adult" or stage == "elder"',
                'mode == "work"',
                'energy > 0.3',
            ],
            suppress_conditions=[
                'stage == "embryo"',
                'mode == "sleep"',
                'fatigue > 0.85',
                'stress > 0.9',
            ],
            priority=4
        ))

        # Archivist: Memory consolidation, active during rest/reflection
        self.genes.append(Gene(
            organ_name="archivist",
            express_conditions=[
                'stage == "adult" or stage == "elder"',
                'mode == "sleep" or mode == "reflect"',
                'fatigue > 0.6',
            ],
            suppress_conditions=[
                'stage == "embryo"',
                'mode == "work" and signal.user_present',
            ],
            priority=5
        ))

    def add_gene(self, gene: Gene):
        """Add custom gene"""
        self.genes.append(gene)

    def get_genes_for_organ(self, organ_name: str) -> List[Gene]:
        """Get all genes controlling an organ"""
        return [g for g in self.genes if g.organ_name == organ_name]

    def differentiate(self, context: Dict[str, Any]) -> Set[str]:
        """
        Differentiate: determine which organs to express.

        Args:
            context: Context with stage/mode/state/signals

        Returns:
            Set of organ names to express
        """
        expressed = set()

        # Group genes by organ
        organ_genes = {}
        for gene in self.genes:
            if gene.organ_name not in organ_genes:
                organ_genes[gene.organ_name] = []
            organ_genes[gene.organ_name].append(gene)

        # Evaluate each organ
        for organ_name, genes in organ_genes.items():
            # If ANY gene says to express, organ is expressed
            should_express = False
            for gene in genes:
                if gene.should_express(context):
                    should_express = True
                    break

            if should_express:
                expressed.add(organ_name)

        return expressed

    def get_organ_priority(self, organ_name: str) -> int:
        """Get execution priority for organ"""
        genes = self.get_genes_for_organ(organ_name)
        if genes:
            return min(g.priority for g in genes)
        return 99


class Differentiator:
    """
    Differentiator: Main differentiation controller.

    Manages genome, evaluates context, and determines organ expression.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.genome = Genome()

        # Load custom genes from config if provided
        if "custom_genes" in config:
            self._load_custom_genes(config["custom_genes"])

    def _load_custom_genes(self, custom_genes: List[Dict[str, Any]]):
        """Load custom genes from configuration"""
        for gene_config in custom_genes:
            gene = Gene(
                organ_name=gene_config["organ"],
                express_conditions=gene_config.get("express", []),
                suppress_conditions=gene_config.get("suppress", []),
                priority=gene_config.get("priority", 5)
            )
            self.genome.add_gene(gene)

    def select_organs(
        self,
        stage: str,
        mode: str,
        state: Dict[str, Any],
        signals: Dict[str, float]
    ) -> Tuple[Set[str], Dict[str, int]]:
        """
        Select which organs to express.

        Args:
            stage: Developmental stage
            mode: Activity mode
            state: Current state (stress, fatigue, energy, etc.)
            signals: Signal bus values

        Returns:
            (expressed_organs, priorities) tuple
        """
        # Build evaluation context
        context = {
            "stage": stage,
            "mode": mode,
            "state": state,
            "signals": self._process_signals(signals),
            **state  # Include state variables at top level
        }

        # Differentiate
        expressed = self.genome.differentiate(context)

        # Get priorities
        priorities = {
            organ: self.genome.get_organ_priority(organ)
            for organ in expressed
        }

        return expressed, priorities

    def _process_signals(self, signals: Dict[str, float]) -> Dict[str, bool]:
        """
        Convert signal values to boolean flags.

        Args:
            signals: Signal values [0, 1]

        Returns:
            Dict of boolean signal flags
        """
        signal_flags = {}

        # Convert continuous signals to boolean
        for name, value in signals.items():
            # Define thresholds for common signals
            threshold = 0.5

            # Special thresholds
            if "high" in name.lower():
                threshold = 0.7
            elif "low" in name.lower():
                threshold = 0.3
            elif "present" in name.lower():
                threshold = 0.5

            signal_flags[name] = value >= threshold

        return signal_flags

    def can_organ_override(self, organ_name: str) -> bool:
        """
        Check if organ can override/veto actions.

        Only Caretaker and Immune can veto.
        """
        return organ_name in {"caretaker", "immune"}

    def get_stage_config(self, stage: str) -> Dict[str, Any]:
        """
        Get configuration for a developmental stage.

        Args:
            stage: Stage name (string or Stage enum)

        Returns:
            Stage configuration
        """
        # Convert string to Stage enum for lookup
        if isinstance(stage, str):
            try:
                stage = Stage(stage)
            except ValueError:
                stage = Stage.ADULT  # Fallback to adult

        stage_configs = {
            Stage.EMBRYO: {
                "max_tools": 2,
                "max_planning_depth": 1,
                "learning_rate": 0.1,
                "exploration_rate": 0.3,
                "description": "Learning basics, limited functionality"
            },
            Stage.JUVENILE: {
                "max_tools": 5,
                "max_planning_depth": 2,
                "learning_rate": 0.05,
                "exploration_rate": 0.2,
                "description": "Exploring and building skills"
            },
            Stage.ADULT: {
                "max_tools": 10,
                "max_planning_depth": 3,
                "learning_rate": 0.01,
                "exploration_rate": 0.1,
                "description": "Full functionality"
            },
            Stage.ELDER: {
                "max_tools": 10,
                "max_planning_depth": 5,
                "learning_rate": 0.001,
                "exploration_rate": 0.05,
                "description": "Wisdom, reflection, teaching"
            },
        }

        return stage_configs.get(stage, stage_configs[Stage.ADULT])

    def advance_stage(self, current_stage: str, ticks_elapsed: int) -> Optional[str]:
        """
        Determine if stage should advance.

        Args:
            current_stage: Current stage (string or Stage enum)
            ticks_elapsed: Total ticks elapsed

        Returns:
            New stage value if advancement occurs, None otherwise
        """
        # Convert string to Stage enum for lookup
        if isinstance(current_stage, str):
            try:
                current_stage = Stage(current_stage)
            except ValueError:
                return None

        # Stage advancement thresholds (in ticks)
        advancement = {
            Stage.EMBRYO: (100, Stage.JUVENILE),
            Stage.JUVENILE: (500, Stage.ADULT),
            Stage.ADULT: (5000, Stage.ELDER),
        }

        if current_stage in advancement:
            threshold, next_stage = advancement[current_stage]
            if ticks_elapsed >= threshold:
                return next_stage

        return None


# 模块级缓存的 Differentiator 实例，避免每次调用都创建新实例
# 修复: 之前每次调用便利函数都创建新 Differentiator({})，浪费性能且忽略自定义基因
_cached_differentiator: Optional[Differentiator] = None


def _get_differentiator() -> Differentiator:
    """获取或创建缓存的 Differentiator 实例"""
    global _cached_differentiator
    if _cached_differentiator is None:
        _cached_differentiator = Differentiator({})
    return _cached_differentiator


# Convenience functions for backward compatibility
def select_organs(
    genome: Dict[str, Any],
    state: Dict[str, Any],
    ctx: Dict[str, Any]
) -> Set[str]:
    """
    Legacy compatibility function.

    Args:
        genome: Personality DNA (may contain stage/mode)
        state: Current state (field snapshot with energy/mood/stress etc.)
        ctx: Tick context (may contain signals, observations)

    Returns:
        Set of organ names to express
    """
    differentiator = _get_differentiator()

    # state is field_snapshot (energy/mood/stress etc.), so get stage/mode from genome or ctx
    stage = genome.get("stage", ctx.get("stage", "adult"))
    mode = genome.get("mode", ctx.get("mode", "work"))
    signals = ctx.get("signals", {})

    expressed, _ = differentiator.select_organs(stage, mode, state, signals)

    return expressed


def get_organ_priority(organ_name: str) -> int:
    """Legacy compatibility function"""
    return _get_differentiator().genome.get_organ_priority(organ_name)


def can_organ_override(organ_name: str, action: Dict[str, Any]) -> bool:
    """Legacy compatibility function"""
    return _get_differentiator().can_organ_override(organ_name)
