"""社交系统 - 数字生命之间的交流 + 外部新闻感知。

设计原则：
- 每个生命可以看消息板（新闻 + 他人的消息 + 他人的状态）
- 每个生命可以选择发消息（群聊/私聊/不发）
- 完全自主——不强制回应，沉默也是一种选择
- 异步——各自在自己的 tick 里检查和回复

消息板结构：
  /shared/news/latest.json       ← 最新新闻
  /shared/channels/group.jsonl    ← 群聊
  /shared/channels/{A_B}.jsonl    ← 私聊
  /shared/profiles/{id}.json      ← 公开状态
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from common.logger import get_logger

logger = get_logger(__name__)

SHARED_DIR = Path("/home/genesisx/shared")


class SocialSystem:
    """社交系统 - 读写共享消息板。

    每个生命实例化时传入自己的 ID（如 "A"/"B"/"C"）。
    """

    def __init__(self, self_id: str):
        self.self_id = self_id
        self.shared_dir = SHARED_DIR
        self._last_read_positions: Dict[str, int] = {}  # 频道 -> 上次读到的行数

    def _ensure_dirs(self):
        """确保共享目录结构存在。"""
        for d in ["news", "channels", "profiles"]:
            (self.shared_dir / d).mkdir(parents=True, exist_ok=True)
        # 确保频道文件存在
        for ch in ["group"]:
            f = self.shared_dir / "channels" / f"{ch}.jsonl"
            if not f.exists():
                f.touch()

    def get_observations(self) -> Dict[str, Any]:
        """获取社交感知——新闻 + 频道新消息 + 他人的公开状态。

        返回一个 observation payload，供 life_loop 注入到 context。
        每次调用只返回"自上次以来"的新内容（增量读取）。
        """
        self._ensure_dirs()
        result = {
            "news": [],
            "group_new": [],
            "private_new": [],
            "others": [],
        }

        # 1. 最新新闻
        try:
            latest_file = self.shared_dir / "news" / "latest.json"
            if latest_file.exists():
                data = json.loads(latest_file.read_text(encoding="utf-8"))
                for item in data.get("items", []):
                    result["news"].append({
                        "title": item.get("title", ""),
                        "source": item.get("source", ""),
                        "summary": item.get("summary", "")[:100],
                    })
        except Exception as e:
            logger.debug(f"[SOCIAL] 读新闻失败: {e}")

        # 2. 群聊新消息
        group_new = self._read_new_messages("group")
        if group_new:
            result["group_new"] = group_new

        # 3. 私聊新消息（别人发给自己的）
        # 检查所有可能的私聊频道
        for other in ["A", "B", "C"]:
            if other == self.self_id:
                continue
            ch_name = "_".join(sorted([self.self_id, other]))
            private = self._read_new_messages(ch_name)
            if private:
                for msg in private:
                    if msg.get("from") != self.self_id:  # 只看别人发的
                        result["private_new"].append(msg)

        # 4. 他人的公开状态
        for other in ["A", "B", "C"]:
            if other == self.self_id:
                continue
            profile_file = self.shared_dir / "profiles" / f"{other}.json"
            try:
                if profile_file.exists():
                    profile = json.loads(profile_file.read_text(encoding="utf-8"))
                    result["others"].append({
                        "id": other,
                        "name": profile.get("name", other),
                        "mood": profile.get("mood", 0.5),
                        "interest": profile.get("current_interest", ""),
                        "last_active": profile.get("last_active_tick", 0),
                    })
            except Exception:
                pass

        return result

    def _read_new_messages(self, channel: str) -> List[Dict]:
        """读取频道中自上次以来的新消息（增量读取）。"""
        ch_file = self.shared_dir / "channels" / f"{channel}.jsonl"
        if not ch_file.exists():
            return []

        try:
            lines = ch_file.read_text(encoding="utf-8").strip().split("\n")
            lines = [l for l in lines if l.strip()]
            last_pos = self._last_read_positions.get(channel, 0)
            new_lines = lines[last_pos:]
            self._last_read_positions[channel] = len(lines)

            messages = []
            for line in new_lines:
                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError:
                    continue
            return messages
        except Exception as e:
            logger.debug(f"[SOCIAL] 读频道 {channel} 失败: {e}")
            return []

    def send_message(self, to: str, content: str, tick: int,
                     msg_type: str = "message") -> bool:
        """发消息到频道。

        Args:
            to: "group"（群聊）或 "B"/"C"（私聊）
            content: 消息内容
            tick: 当前 tick
            msg_type: message/question/share/reaction

        Returns:
            是否发送成功
        """
        self._ensure_dirs()

        # 确定频道文件
        if to == "group":
            ch_name = "group"
        else:
            ch_name = "_".join(sorted([self.self_id, to]))

        ch_file = self.shared_dir / "channels" / f"{ch_name}.jsonl"

        msg = {
            "from": self.self_id,
            "to": to,
            "tick": tick,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content": content[:500],  # 限制长度
            "type": msg_type,
        }

        try:
            with open(ch_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
            logger.info(f"[SOCIAL] {self.self_id} → {to}: {content[:60]}")
            return True
        except Exception as e:
            logger.warning(f"[SOCIAL] 发消息失败: {e}")
            return False

    def update_profile(self, mood: float, interest: str, tick: int,
                       name: str = None, extra: dict = None):
        """更新自己的公开状态（让别人能看到）。"""
        self._ensure_dirs()
        profile_file = self.shared_dir / "profiles" / f"{self.self_id}.json"

        profile = {
            "id": self.self_id,
            "name": name or self.self_id,
            "mood": round(mood, 2),
            "current_interest": interest[:100],
            "last_active_tick": tick,
            "last_active_time": datetime.now(timezone.utc).isoformat(),
        }
        if extra:
            profile.update(extra)

        try:
            profile_file.write_text(
                json.dumps(profile, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.debug(f"[SOCIAL] 更新 profile 失败: {e}")

    def has_social_content(self) -> bool:
        """快速检查是否有新的社交内容（用于决定是否注入 observation）。"""
        obs = self.get_observations()
        return bool(obs["news"] or obs["group_new"] or obs["private_new"])
