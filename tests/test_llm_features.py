"""测试工具调用 LLM 和记忆整理 LLM

运行方式:
    python tests/test_llm_features.py
"""

import sys
import io
from pathlib import Path

# 设置 UTF-8 编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    pass

import os
from common.logger import get_logger

logger = get_logger(__name__)


def test_organ_llm_config():
    """测试 organ_llm.yaml 配置加载"""
    import yaml

    config_path = project_root / "config" / "organ_llm.yaml"
    print("\n" + "=" * 60)
    print("测试 1: organ_llm.yaml 配置加载")
    print("=" * 60)

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    print(f"\n会话模式: {config.get('mode')}")

    # 工具调用配置
    tc = config.get("tool_calling", {})
    print(f"\n工具调用 LLM:")
    print(f"  - enabled: {tc.get('enabled')}")
    print(f"  - use_default_llm: {tc.get('use_default_llm')}")
    print(f"  - temperature: {tc.get('temperature')}")
    print(f"  - max_history: {tc.get('max_history')}")

    # 记忆整理配置
    mc = config.get("memory_consolidation", {})
    print(f"\n记忆整理 LLM:")
    print(f"  - enabled: {mc.get('enabled')}")
    print(f"  - use_default_llm: {mc.get('use_default_llm')}")
    print(f"  - temperature: {mc.get('temperature')}")
    print(f"  - threshold: {mc.get('threshold')}")

    return config


def test_llm_client():
    """测试 LLM 客户端是否可用"""
    print("\n" + "=" * 60)
    print("测试 2: LLM 客户端连接")
    print("=" * 60)

    api_base = os.getenv("LLM_API_BASE")
    api_key = os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    model = os.getenv("LLM_MODEL")

    print(f"\n环境变量:")
    print(f"  - LLM_API_BASE: {api_base[:30] + '...' if api_base else '未设置'}")
    print(f"  - LLM_API_KEY: {'已设置' if api_key else '未设置'}")
    print(f"  - LLM_MODEL: {model or '未设置'}")

    if not api_base or not api_key:
        print("\n[!] LLM 未配置，将使用模拟模式")
        return None

    try:
        from tools.llm_client import create_llm_from_env
        client = create_llm_from_env()

        print(f"\n[OK] LLM 客户端创建成功")
        print(f"  - API Base: {client.api_base}")
        print(f"  - Model: {client.model}")

        # 测试简单调用
        print(f"\n测试 LLM 调用...")
        response = client.chat(
            messages=[{"role": "user", "content": "请回复'测试成功'两个字"}],
            temperature=0.1,
            max_tokens=50
        )

        if response.get("ok"):
            text = response.get("text", "")
            print(f"[OK] LLM 响应: {text[:100]}")
            return client
        else:
            print(f"[FAIL] LLM 调用失败: {response.get('error')}")
            return None

    except Exception as e:
        print(f"[FAIL] LLM 客户端错误: {e}")
        return None


def test_memory_consolidation():
    """测试记忆整理功能"""
    print("\n" + "=" * 60)
    print("测试 3: 记忆整理功能")
    print("=" * 60)

    from common.config import load_config

    config_path = project_root / "config"
    config = load_config(config_path)

    try:
        from core.life_loop import LifeLoop

        # 创建临时运行目录
        run_dir = project_root / "artifacts" / "test_llm_features"
        run_dir.mkdir(parents=True, exist_ok=True)

        life_loop = LifeLoop(config=config, run_dir=run_dir)

        # 添加一些测试记忆
        print("\n添加测试记忆...")
        from common.models import Observation, EpisodeRecord

        base_tick = life_loop.state.tick
        # 添加超过阈值的记忆（阈值=30）
        for i in range(35):
            obs = Observation(
                type="chat",
                payload={"message": f"测试消息 {i+1}: 用户问了关于天气、美食、旅行、电影的话题"},
                tick=base_tick + i
            )
            ep = EpisodeRecord(
                tick=base_tick + i,
                session_id="test_session",
                observation=obs
            )
            life_loop.episodic.append(ep)

        print(f"添加了 35 条测试记忆（超过阈值 30）")

        # 检查配置
        from core.handlers.action_executor import ActionExecutor
        executor = ActionExecutor(life_loop)

        organ_config = executor._load_organ_llm_config()
        mc_config = organ_config.get("memory_consolidation", {})

        print(f"\n记忆整理配置:")
        print(f"  - enabled: {mc_config.get('enabled')}")
        print(f"  - threshold: {mc_config.get('threshold')}")

        # 测试规则式压缩
        print(f"\n测试规则式压缩...")
        compressed = executor._deep_memory_compression(1.0)
        print(f"  - 压缩了 {compressed} 条记忆")

        # 测试 LLM 整理（如果 LLM 可用）
        if mc_config.get("enabled"):
            print(f"\n测试 LLM 记忆整理...")
            llm_result = executor._llm_memory_consolidation(
                mc_config.get("threshold", 30),
                mc_config
            )
            if llm_result:
                print(f"  [OK] LLM 整理成功")
                print(f"    - 处理的记忆数: {llm_result.get('episodes_processed', 0)}")
                summary = llm_result.get("content", "")
                if summary:
                    print(f"    - 摘要: {summary[:200]}...")
            else:
                print(f"  [SKIP] LLM 整理未执行（记忆不足或 LLM 不可用）")

        life_loop.shutdown()
        print("\n[OK] 记忆整理测试完成")
        return True

    except Exception as e:
        print(f"[FAIL] 记忆整理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sleep_behavior():
    """测试 SLEEP 行为的完整流程"""
    print("\n" + "=" * 60)
    print("测试 4: SLEEP 行为（包含记忆整理）")
    print("=" * 60)

    from common.config import load_config
    from common.models import Action, ActionType

    config_path = project_root / "config"
    config = load_config(config_path)

    try:
        from core.life_loop import LifeLoop

        run_dir = project_root / "artifacts" / "test_llm_features"
        run_dir.mkdir(parents=True, exist_ok=True)

        life_loop = LifeLoop(config=config, run_dir=run_dir)

        # 添加一些疲劳
        life_loop.state.fatigue = 0.5
        life_loop.state.stress = 0.3

        print(f"\nSLEEP 前状态:")
        print(f"  - fatigue: {life_loop.state.fatigue:.2f}")
        print(f"  - stress: {life_loop.state.stress:.2f}")

        # 执行 SLEEP
        from core.handlers.action_executor import ActionExecutor
        executor = ActionExecutor(life_loop)

        sleep_action = Action(type=ActionType.SLEEP, params={"duration": 5})
        result = executor.execute(sleep_action)

        print(f"\nSLEEP 后状态:")
        print(f"  - fatigue: {life_loop.state.fatigue:.2f}")
        print(f"  - stress: {life_loop.state.stress:.2f}")

        print(f"\nSLEEP 结果:")
        print(f"  - success: {result.get('success')}")
        print(f"  - memory_compressed: {result.get('memory_compressed')}")
        print(f"  - llm_consolidation: {result.get('llm_consolidation') is not None}")
        print(f"  - used_fallback: {result.get('used_fallback')}")
        print(f"  - context_reset: {result.get('context_reset')}")

        life_loop.shutdown()
        print("\n[OK] SLEEP 行为测试完成")
        return True

    except Exception as e:
        print(f"[FAIL] SLEEP 行为测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("Genesis X - 工具调用 & 记忆整理 LLM 测试")
    print("=" * 60)

    # 测试配置加载
    config = test_organ_llm_config()

    # 测试 LLM 客户端
    llm_client = test_llm_client()

    # 测试记忆整理
    test_memory_consolidation()

    # 测试 SLEEP 行为
    test_sleep_behavior()

    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
