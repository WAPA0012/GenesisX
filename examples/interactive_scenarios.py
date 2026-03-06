"""
Genesis X 交互测试脚本

模拟不同场景下的系统行为，展示数字生命的"生命力"。
"""

import json
import time
from pathlib import Path


def test_scenario_scenario(name: str, description: str, initial_state: dict, ticks: int):
    """运行一个测试场景"""
    print(f"\n{'='*70}")
    print(f"  场景: {name}")
    print(f"{'='*70}")
    print(f"描述: {description}")
    print(f"Tick数: {ticks}")
    print()

    # 运行系统
    import subprocess
    cmd = f"cd GenesisX && python run.py --ticks {ticks}"

    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        cwd="C:/Users/Administrator/Desktop/项目开发/2数字生命/0开发"
    )

    # 分析结果
    lines = result.stdout.split('\n')
    for line in lines:
        if "Tick" in line or "Energy=" in line:
            print(line)

    # 分析最新的运行
    artifacts = Path("C:/Users/Administrator/Desktop/项目开发/2数字生命/0开发/GenesisX/artifacts")
    runs = sorted(artifacts.glob("run_*"), reverse=True)

    if runs:
        import sys
        sys.path.insert(0, str(artifacts.parent))

        # 运行分析
        exec(open("analyze_run.py").read(), {"__name__": "__main__"})


def main():
    """主函数"""
    print("="*70)
    print("  Genesis X 交互测试套件")
    print("  测试数字生命在不同场景下的行为表现")
    print("="*70)

    scenarios = [
        {
            "name": "社交模式测试",
            "description": "观察系统在friend模式下如何维护关系",
            "mode": "friend",
            "ticks": 50
        },
        {
            "name": "工作模式测试",
            "description": "观察系统在work模式下如何处理任务",
            "mode": "work",
            "ticks": 50
        },
        {
            "name": "长期运行测试",
            "description": "观察系统在100个tick中的状态变化",
            "mode": "friend",
            "ticks": 100
        }
    ]

    print("\n可用场景:")
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print(f"   {scenario['description']}")

    print("\n0. 退出")

    choice = input("\n选择场景 (0-3): ").strip()

    if choice == "0":
        print("退出测试")
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(scenarios):
            scenario = scenarios[idx]

            # 运行测试
            import subprocess
            cmd = f"cd \"C:\\Users\\Administrator\\Desktop\\项目开发\\2数字生命\\0开发\\GenesisX\" && python run.py --ticks {scenario['ticks']} --mode {scenario['mode']}"

            print(f"\n运行场景: {scenario['name']}")
            print(f"{'='*70}")

            result = subprocess.run(cmd, shell=True)

            # 分析结果
            print(f"\n{'='*70}")
            print("场景完成，正在分析结果...")
            print(f"{'='*70}")

            import sys
            import os
            os.chdir("C:/Users/Administrator/Desktop/项目开发/2数字生命/0开发/GenesisX")

            from analyze_run import analyze_run

            # 找到最新的运行
            artifacts = Path("artifacts")
            runs = sorted(artifacts.glob("run_*"), reverse=True)

            if runs:
                analyze_run(str(runs[0]))
        else:
            print("无效选择")
    except ValueError:
        print("无效输入")
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main()
