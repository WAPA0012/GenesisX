"""内在生命线程（Inner Life Thread，2026-08）——解决不连续性问题。

真实思维是连续的、不请自来的（默认模式网络、闯入式回忆、白日梦）。
本线程让联想网络在 tick 之间持续运转：

- 每 30s 做一次激活扩散（零 LLM，纯图计算）
- 情绪调制扩散方向（开心时偏向正面记忆 = 普鲁斯特效应）
- 激活达到阈值 → 生成"闯入式想法"注入下一 tick 感知
- Hebbian 强化：被一起激活的边在无意识中已经在加强

意识（tick 决策）只是无意识冰山的尖端。
"""
import random
import threading
from typing import Any, Dict, List, Optional

from common.logger import get_logger

logger = get_logger(__name__)


class InnerLifeThread(threading.Thread):
    """后台联想网络线程——生命的无意识层。"""

    def __init__(self, life_loop, interval_s: float = 30.0):
        super().__init__(daemon=True, name="inner_life")
        self.life_loop = life_loop
        self.interval = interval_s
        self._stop_event = threading.Event()
        self.intrusive_thoughts: List[str] = []
        self.stats = {
            "spreading_cycles": 0,
            "intrusive_thoughts": 0,
            "hebbian_edges": 0,
        }

    def stop(self):
        self._stop_event.set()

    def run(self):
        logger.info(f"[INNER-LIFE] 内在生命线程启动（每 {self.interval:.0f}s 激活扩散）")
        while not self._stop_event.wait(self.interval):
            try:
                self._cycle()
            except Exception as e:
                logger.debug(f"[INNER-LIFE] 周期失败: {e}")

    def _get_network(self):
        """安全获取联想网络。"""
        ep = getattr(self.life_loop, "episodic", None) if self.life_loop else None
        if ep is None:
            return None
        assoc = getattr(ep, "_associative_memory", None)
        if assoc is None:
            return None
        return getattr(assoc, "network", None)

    def _cycle(self):
        self.stats["spreading_cycles"] += 1
        net = self._get_network()
        if net is None:
            return

        nodes = list(net._nodes.values())
        if len(nodes) < 10:
            return

        mood = self.life_loop.fields.get("mood") if self.life_loop else 0.5
        stress = self.life_loop.fields.get("stress") if self.life_loop else 0.2

        # 1. 选种子：随机（自发噪声）+ 情绪匹配（普鲁斯特效应）
        seed_ids = self._select_seeds(nodes, mood)
        if not seed_ids:
            return

        # 2. 激活扩散
        try:
            activation = net.propagate_activation(
                seed_ids=seed_ids,
                max_steps=3,
                activation_threshold=0.2,
            )
        except Exception:
            return
        if not activation:
            return

        # 3. Hebbian 强化（无意识学习）
        self._hebbian(net, activation)

        # 4. 概率性浮现闯入式想法
        self._maybe_surface(net, activation, stress)

    def _select_seeds(self, nodes, mood: float) -> List[str]:
        seeds = []
        try:
            # 随机 2-3 个（念头不请自来）
            n = random.randint(2, 3)
            picks = random.sample(nodes, min(n, len(nodes)))
            seeds = [p.id for p in picks]
            # 普鲁斯特：mood 高时偏向正面记忆
            if mood > 0.6 and len(nodes) > 50:
                positive = [nd for nd in nodes if nd.mood_context > 0.6]
                if positive:
                    seeds.append(random.choice(positive).id)
        except Exception:
            pass
        return seeds[:5]

    def _hebbian(self, net, activation: Dict[str, float]):
        """对高激活节点对做 Hebbian 强化。"""
        try:
            top = sorted(activation.items(), key=lambda kv: -kv[1])[:6]
            for i in range(len(top) - 1):
                src_id = top[i][0]
                tgt_id = top[i + 1][0]
                if src_id != tgt_id:
                    net.reinforce_association(src_id, tgt_id)
                    self.stats["hebbian_edges"] += 1
        except Exception:
            pass

    def _maybe_surface(self, net, activation: Dict[str, float], stress: float):
        """概率性产生闯入式想法。"""
        if len(self.intrusive_thoughts) >= 3:
            return
        threshold = 0.15 if stress > 0.5 else 0.08
        if random.random() > threshold:
            return
        try:
            best_id = max(activation, key=activation.get)
            node = net.get_node(best_id)
            if node is None or not node.text or len(node.text) < 5:
                return
            intrusion = f"（突然想起）{node.text[:120]}"
            self.intrusive_thoughts.append(intrusion)
            self.stats["intrusive_thoughts"] += 1
            logger.info(f"[INNER-LIFE] 闯入式想法 #{self.stats['intrusive_thoughts']}: "
                        f"{node.text[:60]}")
        except Exception:
            pass

    def consume_intrusions(self) -> List[str]:
        out = list(self.intrusive_thoughts)
        self.intrusive_thoughts.clear()
        return out
