#!/usr/bin/env python
"""迁移旧的 episodes 到新的持久化 session"""
import json
from pathlib import Path

def migrate_session(input_file: Path, new_session_id: str = "genesisx_persistent"):
    """将旧 session_id 的记录迁移到新的持久化 session"""
    lines = []
    migrated = 0

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                old_session = d.get('session_id', 'unknown')
                if old_session != new_session_id:
                    d['session_id'] = new_session_id
                    migrated += 1
                lines.append(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping invalid JSON line: {e}")
                continue

    # 写入新文件
    output_file = input_file.with_suffix('.jsonl.new')
    with open(output_file, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(line + '\n')

    print(f"Migrated {migrated} episodes to {new_session_id}")
    print(f"Output: {output_file}")

    return output_file

if __name__ == "__main__":
    web_run_dir = Path(__file__).parent / "artifacts" / "web_run"
    episodes_file = web_run_dir / "episodes.jsonl"

    if episodes_file.exists():
        migrate_session(episodes_file)
        print("\nTo apply the migration:")
        print("  1. Backup the original: cp episodes.jsonl episodes.jsonl.bak")
        print("  2. Replace: mv episodes.jsonl.new episodes.jsonl")
    else:
        print(f"File not found: {episodes_file}")
