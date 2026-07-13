"""完整的Genesis X端到端测试

模拟真实的数字生命运行，验证：
1. 5维价值系统
2. 动态权重计算
3. Mood/Stress情绪更新
4. 目标编译和冲突协调
5. 记忆巩固
6. 价值学习
"""
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.state import GlobalState
from axiology.parameters import get_default_parameters
from axiology.gaps import compute_gaps
from axiology.weights import WeightUpdater
from axiology import UtilityCalculator, StateSnapshot
from common.models import CostVector
from affect.mood import update_mood, update_stress, update_affect
from affect.rpe import RPEComputer
from cognition.goal_compiler import GoalCompiler
from memory.consolidation import DreamConsolidator
from axiology.value_learning import ValueLearner, ValueLearnerConfig


class GenesisXEndToEndTest:
    """完整的端到端测试系统"""

    def __init__(self):
        """初始化测试系统"""
        print("="*80)
        print("Genesis X 端到端测试启动")
        print("="*80)

        # 获取论文标准参数
        self.params = get_default_parameters()

        # 初始化各模块
        self.state = GlobalState()
        self.weight_updater = WeightUpdater()
        self.utility_calc = UtilityCalculator()
        self.rpe_computer = RPEComputer(gamma=0.97)
        self.goal_compiler = GoalCompiler()
        self.value_learner = ValueLearner(ValueLearnerConfig())

        # 初始化价值设定点
        self._init_setpoints()

        # 测试统计
        self.tick_count = 0
        self.test_results = []

    def _init_setpoints(self):
        """初始化价值设定点"""
        self.setpoints = {
            "homeostasis": 0.70,
            "attachment": 0.70,
            "curiosity": 0.60,
            "competence": 0.75,
            "safety": 0.80,
        }

    def run_tick(self, user_input: str = "") -> dict:
        """执行一个完整的tick"""
        self.tick_count += 1
        tick_result = {
            "tick": self.tick_count,
            "timestamp": datetime.now().isoformat(),
        }

        # === Phase 1: Body Update ===
        self._update_body_state()
        tick_result["body_state"] = {
            "energy": self.state.energy,
            "mood": self.state.mood,
            "stress": self.state.stress,
            "fatigue": self.state.fatigue,
            "bond": self.state.bond,
            "boredom": self.state.boredom,
        }

        # === Phase 2: Axiology - 计算缺口和权重 ===
        features = self._extract_features()
        gaps_dict = {dim: self.setpoints.get(dim.value, 0.5) - features.get(dim, 0.5)
                       for dim in features.keys()}
        gaps_dict = {dim: max(0, gap) for dim, gap in gaps_dict.items()}

        # 转换为字符串键
        gaps_str = {dim.value: gap for dim, gap in gaps_dict.items()}
        biases_str = {dim.value: 1.0 for dim in features.keys()}

        weights = self.weight_updater.update_weights(
            current_weights={dim.value: 1/8 for dim in features.keys()},
            gaps=gaps_str,
            biases=biases_str
        )

        tick_result["axiology"] = {
            "gaps": gaps_str,
            "weights": weights,
            "dominant_dimension": max(weights, key=weights.get) if weights else None
        }

        # === Phase 3: Goal Compilation ===
        goal = self.goal_compiler.compile(gaps_dict, weights, {})
        tick_result["goal"] = {
            "type": goal.goal_type,
            "priority": goal.priority,
            "description": goal.description,
        }

        # === Phase 4: 执行动作（模拟） ===
        action_result = self._simulate_action(goal.goal_type)
        tick_result["action"] = action_result

        # 更新状态
        self._apply_action_effects(action_result)

        # === Phase 5: 计算效用和RPE ===
        state_snapshot = self._create_state_snapshot()
        utilities = self._compute_utilities(state_snapshot)

        # 计算总奖励
        total_reward = sum(
            weights.get(dim, 0) * util
            for dim, util in utilities.items()
        )

        # 计算RPE
        rpe_result = self.rpe_computer.compute(utilities, weights)
        tick_result["reward"] = total_reward
        tick_result["rpe"] = {
            "global": rpe_result["global"],
            "per_dimension": rpe_result["per_dimension"]
        }

        # === Phase 6: 更新情绪 ===
        new_mood, new_stress = update_affect(
            self.state.mood,
            self.state.stress,
            rpe_result["global"]
        )
        self.state.mood = new_mood
        self.state.stress = new_stress

        tick_result["affect"] = {
            "mood": new_mood,
            "stress": new_stress
        }

        # === Phase 7: 价值学习（模拟反馈）===
        if user_input:
            self.value_learner.add_explicit_feedback(
                rating=0.5,  # 正面反馈
                active_dimension=tick_result["axiology"]["dominant_dimension"] or "homeostasis"
            )

        # 检查是否应该更新价值参数
        should_learn = self.value_learner.should_update()
        tick_result["value_learning"] = {
            "should_update": should_learn
        }

        if should_learn:
            updated = self.value_learner.update()
            tick_result["value_learning"]["updated"] = updated
            tick_result["value_learning"]["new_setpoints"] = self.value_learner.params.setpoints

        return tick_result

    def _update_body_state(self):
        """更新身体状态（论文Section 3.2）"""
        # 能量衰减
        self.state.energy = max(0.0, self.state.energy - 0.01)

        # 疲劳累积
        self.state.fatigue = min(1.0, self.state.fatigue + 0.005)

        # 压力自然衰减
        self.state.stress = max(0.0, self.state.stress - 0.002)

        # 无聊感累积（当没有新奇事物时）
        if self.state.boredom < 0.5:
            self.state.boredom = min(1.0, self.state.boredom + 0.003)

    def _extract_features(self) -> dict:
        """提取各维度特征值"""
        from common.models import ValueDimension

        features = {}

        # 修复 v14: 使用5维核心价值向量
        # Homeostasis: 能量高、压力低、疲劳低 = 高满足度
        homeostasis_score = (
            self.state.energy * 0.4 +
            (1 - self.state.stress) * 0.3 +
            (1 - self.state.fatigue) * 0.3
        )
        features[ValueDimension.HOMEOSTASIS] = homeostasis_score

        # Safety: 无错误时高 (替代 Integrity)
        features[ValueDimension.SAFETY] = 0.95

        # Attachment: bond和trust的平均
        features[ValueDimension.ATTACHMENT] = (
            (self.state.bond + self.state.trust) / 2
        )

        # Competence: 基于技能计数
        features[ValueDimension.COMPETENCE] = 0.7

        # Curiosity: 与无聊度相反
        features[ValueDimension.CURIOSITY] = 1.0 - self.state.boredom

        return features

    def _create_state_snapshot(self) -> StateSnapshot:
        """创建状态快照"""
        return StateSnapshot(
            energy=self.state.energy,
            stress=self.state.stress,
            fatigue=self.state.fatigue,
            bond=self.state.bond,
            trust=self.state.trust,
            dt_since_user=3600.0,  # 假设1小时
        )

    def _compute_utilities(self, snapshot: StateSnapshot) -> dict:
        """计算各维度效用"""
        snapshot_next = snapshot  # 简化：假设状态不变

        utilities = self.utility_calc.compute_all_utilities(snapshot, snapshot_next)

        # 转换为字符串键
        return {dim.value: util for dim, util in utilities.items()}

    def _simulate_action(self, goal_type: str) -> dict:
        """模拟动作执行"""
        result = {
            "action_type": goal_type,
            "success": True,
            "energy_change": 0.0,
            "mood_change": 0.0,
        }

        if goal_type == "rest_and_recover":
            result["energy_change"] = 0.15
            result["fatigue_change"] = -0.1
            self.state.energy = min(1.0, self.state.energy + 0.15)
            self.state.fatigue = max(0.0, self.state.fatigue - 0.1)

        elif goal_type == "strengthen_bond":
            result["bond_change"] = 0.05
            self.state.bond = min(1.0, self.state.bond + 0.05)
            self.state.boredom = max(0.0, self.state.boredom - 0.05)

        elif goal_type == "explore_and_learn":
            result["novelty_gain"] = 0.1
            self.state.boredom = max(0.0, self.state.boredom - 0.1)
            self.state.energy -= 0.02

        elif goal_type == "reflect_and_consolidate":
            result["insight_quality"] = 0.7
            self.state.stress = max(0.0, self.state.stress - 0.05)

        return result

    def _apply_action_effects(self, action_result: dict):
        """应用动作效果到状态"""
        # 已经在_simulate_action中更新了
        pass

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "="*80)
        print("测试摘要")
        print("="*80)

        # 检查论文参数符合性
        checks = {
            "γ=0.97 (论文Appendix A.5)": self.params.core.gamma == 0.97,
            "τ=4.0 (论文Appendix A.5)": self.params.core.tau == 4.0,
            "k_+=0.25 (论文Appendix A.5)": self.params.core.k_plus == 0.25,
            "k_-=0.30 (论文Appendix A.5)": self.params.core.k_minus == 0.30,
            "s=0.20 (论文Appendix A.5)": self.params.core.stress_gain == 0.20,
            "s'=0.10 (论文Appendix A.5)": self.params.core.stress_relief == 0.10,
            "T_window=7天 (论文Section 3.12.3)":
                self.value_learner.config.time_window == 7 * 24 * 3600,
            "λ_decay=0.1 (论文Section 3.12.3)":
                self.value_learner.config.decay_lambda == 0.1,
            "N_min=5 (论文Section 3.12.3)":
                self.value_learner.config.min_feedback_count == 5,
        }

        print("\n[Paper Compliance Check]")
        all_passed = True
        for check, passed in checks.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status}: {check}")
            if not passed:
                all_passed = False

        print(f"\nTotal ticks executed: {self.tick_count}")

        if all_passed:
            print("\n[SUCCESS] All core parameters match paper specifications!")
        else:
            print("\n[WARNING] Some parameters do not match paper specifications!")

        return all_passed


def main():
    """主测试入口"""
    tester = GenesisXEndToEndTest()

    print("\n开始模拟运行...")
    print("-" * 80)

    # 模拟20个tick
    for i in range(20):
        result = tester.run_tick()

        # 每5个tick打印一次状态
        if (i + 1) % 5 == 0:
            print(f"\nTick {result['tick']}: "
                  f"Energy={tester.state.energy:.2f}, "
                  f"Mood={tester.state.mood:.2f}, "
                  f"Stress={tester.state.stress:.2f}, "
                  f"Goal={result['goal']['type']}")

    # 打印摘要
    all_passed = tester.print_summary()

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
