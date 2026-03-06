#!/usr/bin/env python3
"""GXBS Runner - Run Genesis X Benchmark Suite

运行 GXBS 基准测试套件的脚本

用法:
    python -m benchmarks.run_gxbs              # 运行所有测试
    python -m benchmarks.run_gxbs --suite memory  # 运行指定套件
    python -m benchmarks.run_gxbs --report markdown  # 生成报告
"""

import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from benchmarks.gxbs_runner import GXBSSuite, create_gxbs_runner
from benchmarks.memory_benchmark import create_memory_benchmark
from benchmarks.emotion_benchmark import create_emotion_benchmark
from benchmarks.personality_benchmark import create_personality_benchmark
from benchmarks.multi_model_benchmark import create_multi_model_benchmark

from common.logger import get_logger

logger = get_logger(__name__)


def setup_suites(runner):
    """设置所有测试套件"""
    # 记忆基准测试套件
    memory_suite = GXBSSuite("memory", "Memory retrieval and associative activation benchmarks")
    for benchmark in create_memory_benchmark():
        memory_suite.register(benchmark)
    runner.register_suite(memory_suite)

    # 情绪基准测试套件
    emotion_suite = GXBSSuite("emotion", "Emotion decay and Proust effect benchmarks")
    for benchmark in create_emotion_benchmark():
        emotion_suite.register(benchmark)
    runner.register_suite(emotion_suite)

    # 人格调制基准测试套件
    personality_suite = GXBSSuite("personality", "Personality modulation effectiveness benchmarks")
    for benchmark in create_personality_benchmark():
        personality_suite.register(benchmark)
    runner.register_suite(personality_suite)

    # 多模型基准测试套件
    multi_model_suite = GXBSSuite("multi_model", "Model switching and coordination benchmarks")
    for benchmark in create_multi_model_benchmark():
        multi_model_suite.register(benchmark)
    runner.register_suite(multi_model_suite)


def main():
    parser = argparse.ArgumentParser(description="Genesis X Benchmark Suite (GXBS)")
    parser.add_argument(
        "--suite",
        choices=["memory", "emotion", "personality", "multi_model", "all"],
        default="all",
        help="Benchmark suite to run"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory for results"
    )
    parser.add_argument(
        "--report",
        choices=["text", "markdown", "json"],
        default="text",
        help="Report format"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save results to file"
    )

    args = parser.parse_args()

    # 创建运行器
    runner = create_gxbs_runner(output_dir=args.output)
    setup_suites(runner)

    # 运行测试
    logger.info(f"Running GXBS benchmark suite: {args.suite}")

    if args.suite == "all":
        results = runner.run_all()
    else:
        results = {args.suite: runner.run_suite(args.suite)}

    # 保存结果
    if args.save:
        output_path = runner.save_results(results)
        logger.info(f"Results saved to {output_path}")

    # 生成报告
    report = runner.generate_report(results, output_format=args.report)
    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

    # 返回退出码
    all_passed = all(
        all(r.overall_passed for r in suite.values())
        for suite in results.values()
    )

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
