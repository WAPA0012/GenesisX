"""Salience computation for memory prioritization.

论文 Section 3.10.4:
Sal = a_δ|δ| + a_u(1-Prog) + a_n*Novelty

默认权重 (Appendix A.7):
- a_δ = 1.0 (RPE magnitude)
- a_u = 0.5 (unmet goals)
- a_n = 0.3 (novelty)

v15 修复: 使用5维核心价值向量 (HOMEOSTASIS, ATTACHMENT, CURIOSITY, COMPETENCE, SAFETY)
- 使用 competence 维度作为任务未完成度的代理
- 使用 curiosity 维度作为新颖性的代理
"""
import math
from common.models import EpisodeRecord

# 论文v15: 5维核心价值向量
VALID_DIMENSIONS = {"homeostasis", "attachment", "curiosity", "competence", "safety"}


def compute_salience(
    episode: EpisodeRecord,
    a_delta: float = 1.0,    # 论文默认: RPE权重
    a_unmet: float = 0.5,    # 论文默认: 未完成目标权重
    a_novelty: float = 0.3,  # 论文默认: 新颖性权重
    kappa_sal: float = 3.0,  # 论文默认: 显著性温度
) -> float:
    """Compute salience score for an episode.

    论文公式 Section 3.10.4:
    Sal = a_δ|δ| + a_u(1-Prog) + a_n*Novelty

    v15修复: 使用5维价值系统的维度作为代理：
    - competence gap: 任务完成度代理（competence与任务成功相关）
    - curiosity gap: 新颖性代理（curiosity与探索和发现相关）

    Args:
        episode: Episode to score
        a_delta: Weight for RPE magnitude (论文a_δ)
        a_unmet: Weight for unmet goal progress (论文a_u)
        a_novelty: Weight for novelty (论文a_n)
        kappa_sal: Salience temperature (论文κ_sal)

    Returns:
        Salience score ∈ [0,1]
    """
    # RPE magnitude component (论文: a_δ|δ|)
    rpe_score = min(1.0, abs(episode.delta))

    # Unmet goal component (论文: a_u(1-Prog))
    # 如果有目标但未完成，增加显著性
    unmet_score = 0.0
    if episode.current_goal:
        # v15修复: 使用 competence 维度作为任务未完成度的代理
        # competence 与任务成功、技能成长相关，其 gap 反映了未完成程度
        # 同时考虑所有维度的最大 gap 作为备选
        competence_gap = episode.gaps.get("competence", 0.0)
        if competence_gap > 0:
            unmet_score = competence_gap
        else:
            # 如果 competence gap 为0，使用所有有效维度的最大 gap
            valid_gaps = [g for k, g in episode.gaps.items() if k in VALID_DIMENSIONS]
            unmet_score = max(valid_gaps) if valid_gaps else 0.0

    # Novelty component (论文: a_n*Novelty)
    # 使用 curiosity 维度的 gap 作为新颖性代理
    # curiosity 与新奇探索、信息增益相关
    novelty_score = episode.gaps.get("curiosity", 0.0)

    # 论文公式: Sal = a_δ|δ| + a_u(1-Prog) + a_n*Novelty
    raw_salience = (
        a_delta * rpe_score +
        a_unmet * unmet_score +
        a_novelty * novelty_score
    )

    # 论文: 使用温度参数κ_sal进行缩放 (softmax-style scaling)
    salience = 1.0 / (1.0 + math.exp(-kappa_sal * (raw_salience - 0.5)))

    # 归一化到[0,1]
    return min(1.0, max(0.0, salience))
