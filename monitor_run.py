"""GenesisX 监控运行脚本 - 跑 30 tick 输出关键指标"""
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))

from common.config import load_config
from core.life_loop import LifeLoop

cfg = load_config(Path('config'))
ll = LifeLoop(config=cfg, run_dir=Path('artifacts/monitor_run_003'))

print('='*60, flush=True)
print('GenesisX 30-tick monitor', flush=True)
print('='*60, flush=True)

action_log = []
prev_mood = ll.fields.get('mood')

for i in range(1, 31):
    try:
        ll.tick(i)
    except Exception as e:
        print(f'FATAL tick {i}: {e}', flush=True)
        import traceback; traceback.print_exc()
        break

    recent = ll.episodic.query_recent(1)
    at = 'UNK'
    if recent and recent[0].action:
        at = recent[0].action.type.value if hasattr(recent[0].action.type, 'value') else str(recent[0].action.type)
    action_log.append(at)

    if i % 5 == 0 or i == 1:
        vals = {x: ll.fields.get(x) for x in ['mood','stress','energy','boredom','fatigue','bond']}
        arrow = '+' if vals['mood'] > prev_mood else '-' if vals['mood'] < prev_mood else '='
        print(f"t{i:3d} mood={vals['mood']:.3f}{arrow} str={vals['stress']:.3f} eng={vals['energy']:.3f} "
              f"bor={vals['boredom']:.3f} fat={vals['fatigue']:.3f} bond={vals['bond']:.3f} "
              f"act={at} ep={ll.episodic.count()}", flush=True)
        prev_mood = vals['mood']

print(flush=True)
print('=== FINAL ===', flush=True)
for n in ['energy','mood','stress','fatigue','bond','trust','boredom']:
    print(f'  {n}: {ll.fields.get(n):.4f}', flush=True)
print(f'actions: {dict(Counter(action_log))}', flush=True)
print(f'episodes: {ll.episodic.count()} schemas: {ll.schema.count()} skills: {ll.skill.count()}', flush=True)
print(f'mind.plan_history: {len(ll.organs["mind"].plan_history)}', flush=True)
print(f'immune.trust: {dict(ll.organs["immune"].action_trust_scores)}', flush=True)
print(f'caretaker.stress_history: {len(ll.organs["caretaker"].stress_history)}', flush=True)
ll.shutdown()
print('DONE', flush=True)
