"""Limb Generator - 自主肢体生成系统

GenesisX 可以通过写代码来自主生成新的肢体。

流程：
1. 需求识别 - 发现需要什么能力
2. 代码生成 - LLM 生成 Docker 容器代码
3. 代码测试 - 验证生成的代码能工作
4. 容器构建 - 构建 Docker 镜像
5. 肢体注册 - 注册到 organs/limbs/
"""
import subprocess
import time
import os
import random
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

from common.logger import get_logger
from common.models import Action, CostVector

logger = get_logger(__name__)


class GenerationType(Enum):
    """生成类型"""
    INTERNAL = "internal"      # 自己写的代码（不需要Docker，纯Python）
    EXTERNAL = "external"      # 调用外部API（需要API key）


@dataclass
class LimbRequirement:
    """肢体需求

    描述需要什么样的能力
    """
    name: str                          # 肢体名称
    description: str                   # 需求描述
    capabilities: List[str]            # 需要的能力列表
    generation_type: GenerationType     # 生成类型
    examples: List[str] = field(default_factory=list)  # 使用示例


@dataclass
class GeneratedLimb:
    """生成的肢体

    包含代码、配置和元数据
    """
    name: str
    description: str
    generation_type: GenerationType
    code: str                          # 生成的代码
    capabilities: List[str]            # 能力列表
    parameters: Dict[str, Any]          # 参数配置（如 API keys）
    dockerfile: Optional[str] = None    # Dockerfile（如果需要）
    requirements: List[str] = field(default_factory=list)  # Python依赖
    test_cases: List[Dict[str, Any]] = field(default_factory=list)  # 测试用例

    # 元数据
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0"
    hash: str = ""

    def __post_init__(self):
        """计算代码哈希"""
        self.hash = hashlib.md5(self.code.encode()).hexdigest()[:16]


@dataclass
class LimbTemplate:
    """肢体模板

    预定义的代码模板，用于快速生成常见类型的肢体
    """
    name: str
    description: str
    generation_type: GenerationType
    template_code: str
    capabilities: List[str]
    required_params: List[str] = field(default_factory=list)


class LimbGenerator:
    """肢体生成器

    负责：
    1. 识别肢体需求
    2. 生成肢体代码
    3. 测试肢体功能
    4. 构建和部署容器（可选）
    5. 注册肢体到系统
    """

    def __init__(self, organ_manager, llm_client=None, config: Dict[str, Any] = None, plugin_manager=None):
        """初始化肢体生成器

        Args:
            organ_manager: 器官管理器
            llm_client: LLM 客户端（用于代码生成）
            config: 配置
            plugin_manager: 插件管理器（作为学习参考，可选）
        """
        self.organ_manager = organ_manager
        self.llm_client = llm_client
        self.config = config or {}
        self.plugin_manager = plugin_manager  # 插件作为学习参考

        # 生成的肢体存储
        self._generated_limbs: Dict[str, GeneratedLimb] = {}

        # 生成历史
        self._generation_history: List[Dict[str, Any]] = []

        # 输出目录
        self._output_dir = Path(self.config.get("limb_output_dir", "artifacts/limbs"))
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # 容器构建器（延迟加载）
        self._limb_builder = None
        self._auto_build = self.config.get("auto_build_containers", False)

        # 插件作为学习参考，成长成熟后可以移除
        # 阶段1: 依赖插件参考
        # 阶段2: 插件 + 自主学习
        # 阶段3: 纯自主生成（移除插件依赖）

    def identify_requirement(self, context: Dict[str, Any]) -> Optional[LimbRequirement]:
        """识别肢体需求

        从用户请求或任务分析中提取对肢体的需求。

        Args:
            context: 当前上下文

        Returns:
            肢体需求，如果没有需求则返回 None
        """
        # 从用户观察中提取需求
        observations = context.get("observations", [])

        for obs in observations:
            msg = obs.get("payload", {}).get("message", "")
            msg_lower = msg.lower()

            # 检查是否需要 HTTP API 能力
            if any(keyword in msg_lower for keyword in ["api", "调用接口", "http请求", "爬取网站"]):
                api_name = self._extract_api_name(msg)
                return LimbRequirement(
                    name=f"{api_name}_api",
                    description=f"调用 {api_name} API",
                    capabilities=["api_call", "http_get", "http_post"],
                    generation_type=GenerationType.EXTERNAL,
                    examples=[f"调用 {api_name} API"]
                )

            # 检查是否需要数据处理能力
            if any(keyword in msg_lower for keyword in ["csv", "excel", "数据透视", "聚合数据"]):
                return LimbRequirement(
                    name="data_processor",
                    description="数据处理肢体",
                    capabilities=["read_csv", "process_data", "to_excel", "filter_data"],
                    generation_type=GenerationType.INTERNAL,
                    examples=["读取CSV", "处理数据", "导出Excel"]
                )

        return None

    def _extract_api_name(self, message: str) -> str:
        """从消息中提取 API 名称"""
        # 简单实现：提取常见的 API 名称
        api_keywords = {
            "github": "github",
            "openai": "openai",
            "claude": "anthropic",
            "weather": "weather",
            "news": "news",
        }

        message_lower = message.lower()
        for keyword, name in api_keywords.items():
            if keyword in message_lower:
                return name

        return "custom_api"

    def generate_limb(self, requirement: LimbRequirement) -> Tuple[bool, Optional[GeneratedLimb]]:
        """生成肢体

        自主成长系统：使用 LLM 动态生成代码。

        Args:
            requirement: 肢体需求

        Returns:
            (是否成功, 生成的肢体)
        """
        logger.info(f"开始生成肢体: {requirement.name}")

        # Self-debugging 闭环（2026-07）：像开发者一样——写→测→看报错→修→再测。
        # 出错了就把错误告诉它，让它修。修好了就过，修不好它自己会放弃
        # （连续修不动 = 它搞不定这个任务，自然结束，不强求）。
        logger.info(f"使用 LLM 自主生成: {requirement.name}")
        limb = self._generate_from_llm(requirement)

        fix_round = 0
        no_progress = 0  # 连续"修不动"计数（LLM 反复修不好同一个错）
        while limb and fix_round < 10:  # 最多 10 轮防卡死（正常 2-3 轮就够）
            error = self._get_syntax_error(limb.code)
            if error is None:
                logger.info(f"语法检查通过（{fix_round} 轮修复后）: {requirement.name}")
                break

            # 有错——告诉它哪里错了，让它修
            fix_round += 1
            logger.info(f"Self-debug 第 {fix_round} 轮: {error.msg} (L{error.lineno}) → 喂回 LLM: {requirement.name}")
            fixed_code = self._fix_limb_code(limb.code, error, requirement)

            if fixed_code and fixed_code != limb.code and self._get_syntax_error(fixed_code) is None:
                # 修好了
                limb.code = fixed_code
                logger.info(f"Self-debug 第 {fix_round} 轮修复成功: {requirement.name}")
                break
            elif fixed_code and fixed_code != limb.code:
                # 修了但还有错——用修复版继续下一轮（它至少在尝试改）
                limb.code = fixed_code
                no_progress = 0
            else:
                # LLM 没给出有效修复（返回空或没变化）——它在放弃
                no_progress += 1
                if no_progress >= 2:
                    # 连续 2 次修不动，它搞不定，自然放弃
                    logger.info(f"Self-debug: 连续修不动，放弃: {requirement.name}")
                    break
                # 给它换一种方式——重新从头生成
                logger.info(f"Self-debug: 修复无效，重新生成: {requirement.name}")
                limb = self._generate_from_llm(requirement)
                no_progress = 0

        if not limb or self._get_syntax_error(limb.code) is not None:
            logger.warning(f"肢体生成未成功（修了 {fix_round} 轮）: {requirement.name}")
            return False, None

        # 保存肢体
        self._save_limb(limb)

        # 注册到器官管理器
        self._register_limb(limb)

        # 记录历史
        self._record_generation(limb, requirement)

        logger.info(f"肢体生成成功: {limb.name}")
        return True, limb

    def _generate_from_llm(self, requirement: LimbRequirement) -> Optional[GeneratedLimb]:
        """使用 LLM 生成肢体代码

        根据需求描述，让 LLM 自主生成实现代码。

        Args:
            requirement: 肢体需求

        Returns:
            生成的肢体，如果失败返回 None
        """
        if not self.llm_client:
            logger.error("LLM 客户端未配置，无法生成肢体")
            return None

        logger.info(f"开始 LLM 生成肢体: {requirement.name}")

        try:
            # 1. 构建生成提示
            prompt = self._build_generation_prompt(requirement)
            system_prompt = self._build_system_prompt(requirement)

            # 2. 调用 LLM
            generated_text = self._call_llm(prompt, system_prompt)

            if not generated_text:
                logger.error("LLM 返回空响应")
                return None

            # 3. 提取代码
            code = self._extract_code(generated_text)

            if not code:
                logger.error("无法从 LLM 响应中提取代码")
                return None

            # 4. 提取依赖（如果有）
            requirements = self._extract_requirements(generated_text)

            # 5. 确定生成类型
            generation_type = self._determine_generation_type(requirement, code)

            # 6. 创建 GeneratedLimb
            limb = GeneratedLimb(
                name=requirement.name,
                description=requirement.description,
                generation_type=generation_type,
                code=code,
                capabilities=requirement.capabilities,
                parameters={},
                requirements=requirements,
            )

            logger.info(f"LLM 生成肢体成功: {requirement.name}, 代码长度: {len(code)}")
            return limb

        except Exception as e:
            logger.error(f"LLM 生成肢体失败: {e}")
            return None

    def _build_generation_prompt(self, requirement: LimbRequirement) -> str:
        """构建代码生成提示

        Args:
            requirement: 肢体需求

        Returns:
            提示字符串
        """
        examples_text = ""
        if requirement.examples:
            examples_text = "\n使用示例:\n" + "\n".join(f"- {ex}" for ex in requirement.examples)

        # 查找相似插件作为学习参考
        reference_text = ""
        if self.plugin_manager:
            similar_plugin = self.plugin_manager.get_similar_plugin_for_learning(requirement)
            if similar_plugin:
                # 只取前500字符作为参考，避免提示过长
                ref_code = similar_plugin.code[:800]
                reference_text = f"""
参考代码（相似插件: {similar_plugin.info.name}）:
```python
{ref_code}
...
```
请参考上面的代码风格和结构，但根据具体需求生成新的代码。
"""

        prompt = f"""请为以下需求生成一个完整的 Python 模块代码：

名称: {requirement.name}
描述: {requirement.description}
需要的能力: {', '.join(requirement.capabilities)}
{examples_text}
{reference_text}
要求：
1. 代码必须是完整、可运行的 Python 模块
2. 包含一个主类，类名为 {self._to_class_name(requirement.name)}
3. 实现 __init__ 方法和必要的功能方法
4. **重要：每个能力必须有一个同名方法**（能力名作为方法名，接受 **kwargs）。
   例如能力 ["weather_query"] 必须有 `def weather_query(self, **kwargs)` 方法。
5. 每个方法都要有文档字符串
6. 包含错误处理
7. 如果需要外部依赖，在代码注释中说明
8. 不要使用 markdown 代码块标记
9. **极其重要：代码中所有标点符号必须是 ASCII 半角字符**（冒号 : 逗号 , 括号 () 引号 "" 等）。
   绝对禁止使用中文全角标点（：，，（）""），否则代码会语法错误。
   docstring 和注释里的中文可以用中文，但标点仍用 ASCII。

直接输出代码，不要有其他解释。"""

        return prompt

    def _build_system_prompt(self, requirement: LimbRequirement) -> str:
        """构建系统提示

        Args:
            requirement: 肢体需求

        Returns:
            系统提示字符串
        """
        return """你是一个专业的 Python 开发者，专门为数字生命系统生成功能模块。

生成的代码要求：
1. 遵循 PEP 8 规范
2. 类型注解（使用 typing 模块）
3. 完善的文档字符串
4. 健壮的错误处理
5. 不使用危险的系统调用
6. 代码简洁高效

只输出代码，不要有任何其他文字。"""

    def _call_llm(self, prompt: str, system_prompt: str) -> Optional[str]:
        """调用 LLM

        Args:
            prompt: 用户提示
            system_prompt: 系统提示

        Returns:
            LLM 响应文本
        """
        try:
            # 尝试不同的 LLM 客户端接口
            if hasattr(self.llm_client, 'generate'):
                # 标准生成接口
                result = self.llm_client.generate(prompt, system_prompt, temperature=0.3)
                # generate 可能返回 str 或 dict
                if isinstance(result, str):
                    return result
                elif isinstance(result, dict):
                    return result.get("text", "") or result.get("content", "")
                return result

            elif hasattr(self.llm_client, 'chat'):
                # 聊天接口。LLMClient.chat 的签名是 chat(messages, system_prompt=None, ...)
                # messages 必须是 [{"role":..,"content":..}] 列表，返回 dict {"ok":..,"text":..}
                # 修复（2026-07）：原代码 self.llm_client.chat(prompt, system_prompt) 把字符串
                # 当 messages 传，且没从返回 dict 提取 text，导致下游 _extract_code 收到 dict 报错。
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
                result = self.llm_client.chat(messages, temperature=0.3, max_tokens=2000)
                if isinstance(result, dict):
                    raw = result.get("reasoning_content", "") or result.get("text", "")
                    if raw:
                        # 从 reasoning_content 取的代码也要走 NFKC 清洗（中文引号等）
                        import unicodedata
                        raw = unicodedata.normalize('NFKC', raw)
                        for full, half in {'——':'--','……':'...','、':',','。':'.','〃':'"',
                            '《':'<','》':'>','「':'"','」':'"','『':'"','』':'"',
                            '【':'[','】':']','〔':'(','〕':')','〖':'[','〗':']',
                            '〘':'(','〙':')','〚':'[','〛':']','〜':'~','〰':'~',
                            '〝':'"','〞':'"','〟':'"','〄':'#','〒':'#','〓':'#'}.items():
                            raw = raw.replace(full, half)
                    return raw or ""
                elif isinstance(result, str):
                    return result
                return None

            elif hasattr(self.llm_client, 'complete'):
                # 补全接口
                result = self.llm_client.complete(prompt, system=system_prompt)
                if isinstance(result, str):
                    return result
                elif isinstance(result, dict):
                    return result.get("text", "") or result.get("content", "")
                return result

            elif callable(self.llm_client):
                # 可调用对象
                result = self.llm_client(prompt, system_prompt)
                if isinstance(result, str):
                    return result
                elif isinstance(result, dict):
                    return result.get("text", "") or result.get("content", "")
                return result

            else:
                logger.error(f"未知的 LLM 客户端类型: {type(self.llm_client)}")
                return None

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return None

    def _extract_code(self, generated_text: str) -> Optional[str]:
        """从 LLM 响应中提取代码

        Args:
            generated_text: LLM 生成的文本

        Returns:
            提取的代码字符串
        """
        import re

        # 尝试提取 markdown 代码块
        code_block_pattern = r'```(?:python)?\s*\n(.*?)\n```'
        matches = re.findall(code_block_pattern, generated_text, re.DOTALL)

        if matches:
            # 合并多个代码块
            code = '\n\n'.join(matches)
        else:
            # 没有代码块，假设整个响应就是代码
            code = generated_text

        # 清理代码
        code = code.strip()

        # 移除可能的前后说明文字
        lines = code.split('\n')

        # 找到代码开始位置（第一个非空行或包含 def/class/import 的行）
        start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and (stripped.startswith(('def ', 'class ', 'import ', 'from ', '#', '"""', "'''"))):
                start_idx = i
                break

        # 找到代码结束位置
        end_idx = len(lines)
        for i in range(len(lines) - 1, start_idx, -1):
            if lines[i].strip():
                end_idx = i + 1
                break

        code = '\n'.join(lines[start_idx:end_idx])

        # 修复（2026-07）：LLM 偶尔在代码里混入中文全角标点（：，（）、。？等），
        # 这些会触发 Python 语法错误（invalid character）。
        # 实测 Python 3 对 90+ 个 CJK Unicode 字符都会报错（全角数字、全角字母、
        # 各种括号/引号/声调符号等）。
        # 两步处理：
        # 1) NFKC 规范化：覆盖所有全角 ASCII 变体（０-９，Ａ-Ｚ，ａ-ｚ，：；＜＝＞？＠等）
        # 2) CJK 专属标点 map：NFKC 不覆盖 U+3000-303F 和 CJK 引号，手动补
        import unicodedata
        code = unicodedata.normalize('NFKC', code)
        # CJK 专属标点（NFKC 保留的，Python 会报错的）
        for full, half in {
            '——': '--', '……': '...',  # 多字符序列
            '、': ',', '。': '.', '〃': '"',  # CJK 标点
            '《': '<', '》': '>',  # 书名号
            '「': '"', '」': '"', '『': '"', '』': '"',  # CJK 引号
            '【': '[', '】': ']',  # 方头括号
            '〔': '(', '〕': ')', '〖': '[', '〗': ']',  # 龟壳/白 bracket
            '〘': '(', '〙': ')', '〚': '[', '〛': ']',  # 白 bracket
            '〜': '~', '〰': '~',  # 波浪线
            '〝': '"', '〞': '"', '〟': '"',  # double prime 引号
            '〄': '#', '〒': '#', '〓': '#',  # 特殊符号映射到无害字符
        }.items():
            code = code.replace(full, half)

        # 修复（2026-07）：LLM 偶尔生成未闭合的三引号字符串
        #（如 docstring 的 """ 漏了一个），导致 unterminated triple-quoted string。
        # 自动检测：如果 """ 或 ''' 出现奇数次，在末尾补一个闭合。
        for quote in ('"""', "'''"):
            count = code.count(quote)
            if count % 2 == 1:  # 奇数 = 有未闭合的
                code = code.rstrip() + '\n' + quote  # 补闭合
                logger.info(f"自动闭合未配对的三引号（{quote} 出现 {count} 次）")

        # 验证代码是否有效
        if not any(keyword in code for keyword in ['def ', 'class ', 'import ']):
            logger.warning("提取的代码可能不完整")
            return None

        return code

    def _extract_requirements(self, generated_text: str) -> List[str]:
        """从 LLM 响应中提取依赖

        Args:
            generated_text: LLM 生成的文本

        Returns:
            依赖列表
        """
        import re

        requirements = []

        # 提取 import 语句中的模块
        import_pattern = r'^(?:from\s+(\S+)|import\s+(\S+))'
        for line in generated_text.split('\n'):
            match = re.match(import_pattern, line.strip())
            if match:
                module = match.group(1) or match.group(2)
                # 只保留第三方库
                if module and not module.startswith('.'):
                    # 取顶层模块名
                    top_module = module.split('.')[0]
                    if top_module not in ['typing', 'dataclasses', 'abc', 'os', 'sys', 'json', 're', 'pathlib', 'datetime', 'collections', 'functools', 'itertools', 'hashlib', 'time', 'random', 'math', 'copy']:
                        if top_module not in requirements:
                            requirements.append(top_module)

        return requirements

    def _determine_generation_type(self, requirement: LimbRequirement, code: str) -> 'GenerationType':
        """确定生成类型

        Args:
            requirement: 肢体需求
            code: 生成的代码

        Returns:
            生成类型
        """
        # 检查代码中是否有外部 API 调用
        external_indicators = ['requests', 'httpx', 'aiohttp', 'urllib', 'api_key', 'API_KEY', 'base_url']
        if any(indicator in code for indicator in external_indicators):
            return GenerationType.EXTERNAL

        return GenerationType.INTERNAL

    def _to_class_name(self, name: str) -> str:
        """将名称转换为类名

        Args:
            name: 下划线格式的名称

        Returns:
            驼峰格式的类名
        """
        parts = name.replace('-', '_').split('_')
        return ''.join(word.capitalize() for word in parts)

    def _test_limb(self, limb: GeneratedLimb) -> bool:
        """测试肢体功能

        简单实现：验证代码语法

        Args:
            limb: 生成的肢体

        Returns:
            是否通过测试
        """
        try:
            # 检查 Python 语法
            compile(limb.code, '<string>', 'exec')
            return True
        except SyntaxError as e:
            logger.error(f"肢体代码语法错误: {e}")
            return False

    def _get_syntax_error(self, code: str):
        """检查代码语法，返回 SyntaxError（有错）或 None（无错）。

        用于 self-debugging 闭环——提取具体错误信息喂回 LLM 修复。
        """
        try:
            compile(code, '<string>', 'exec')
            return None
        except SyntaxError as e:
            return e

    def _fix_limb_code(self, code: str, error: SyntaxError, requirement) -> Optional[str]:
        """Self-debugging：把出错的代码 + 具体错误喂回 LLM，让它修复。

        不是重新生成，是"看着自己写的代码，找到错的地方，改对"。
        这模拟了真实开发者的调试过程——没人一次写对，但看报错修就能修好。
        """
        if not self.llm_client:
            return None

        try:
            # 提取出错位置附近的代码（让 LLM 聚焦在错误处）
            lines = code.split('\n')
            error_line = error.lineno or 1
            start = max(0, error_line - 4)
            end = min(len(lines), error_line + 3)
            context_lines = '\n'.join(f"{i+1}: {lines[i]}" for i in range(start, end))

            fix_prompt = f"""你之前为一个数字生命系统生成了 Python 代码，但代码有语法错误。请修复它。

原始需求: {requirement.description[:200]}

你写的代码在第 {error_line} 行附近出错：
{context_lines}

错误信息: {error.msg} (第 {error_line} 行{f', 字符位置 {error.offset}' if error.offset else ''})

请输出**修复后的完整代码**（不是只输出改的那几行，是整个模块的完整代码）。
仔细检查所有括号是否闭合、缩进是否一致（用4个空格）、def/class/if/else 后面是否都有冒号。
只输出代码，不要解释。"""

            system = "你是 Python 专家。修复代码里的语法错误。输出完整的修复后代码。"

            fixed = self._call_llm(fix_prompt, system)
            if not fixed:
                return None

            # 从修复响应中提取代码（可能被包裹在 markdown 里）
            fixed = self._extract_code(fixed)
            if not fixed:
                return None

            # 验证修复后的代码至少比原来长（不是空回复）
            if len(fixed) < 50:
                return None

            return fixed

        except Exception as e:
            logger.debug(f"Self-debug 修复失败: {e}")
            return None

    def _save_limb(self, limb: GeneratedLimb):
        """保存肢体到磁盘"""
        limb_dir = self._output_dir / limb.name
        limb_dir.mkdir(parents=True, exist_ok=True)

        # 保存代码
        code_file = limb_dir / "__init__.py"
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(limb.code)

        # 保存元数据
        meta_file = limb_dir / "metadata.json"
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump({
                "name": limb.name,
                "description": limb.description,
                "generation_type": limb.generation_type.value,
                "capabilities": limb.capabilities,
                "requirements": limb.requirements,
                "version": limb.version,
                "hash": limb.hash,
                "created_at": limb.created_at.isoformat(),
            }, f, indent=2, ensure_ascii=False)

        logger.info(f"肢体已保存到: {limb_dir}")

    def _register_limb(self, limb: GeneratedLimb):
        """注册肢体到器官管理器"""
        # 动态导入生成的肢体模块
        # 实际实现需要更复杂的动态加载机制

        # 将肢体添加到已生成列表
        self._generated_limbs[limb.name] = limb

        # 如果启用自动构建，构建容器
        if self._auto_build and limb.requirements:
            self._build_and_deploy_limb(limb)

        logger.info(f"肢体已注册: {limb.name}")

    def _get_limb_builder(self):
        """获取肢体构建器（延迟加载）"""
        if self._limb_builder is None:
            try:
                from .limb_builder import LimbBuilder
                self._limb_builder = LimbBuilder()
            except ImportError:
                logger.warning("无法导入 LimbBuilder")
        return self._limb_builder

    def _build_and_deploy_limb(self, limb: GeneratedLimb) -> bool:
        """构建和部署肢体容器

        Args:
            limb: 生成的肢体

        Returns:
            是否成功
        """
        builder = self._get_limb_builder()
        if not builder:
            logger.warning("肢体构建器不可用，跳过容器构建")
            return False

        try:
            build_result = builder.build_limb(
                limb_name=limb.name,
                code=limb.code,
                requirements=limb.requirements,
                dockerfile_content=limb.dockerfile
            )

            if build_result.success:
                logger.info(f"肢体 {limb.name} 容器构建成功: {build_result.image_name}:{build_result.image_tag}")

                # 自动部署（可选）
                if self.config.get("auto_deploy", False):
                    success, container_id = builder.deploy_limb(
                        build_result.image_name,
                        build_result.image_tag
                    )
                    if success:
                        logger.info(f"肢体 {limb.name} 已部署: {container_id}")
                    else:
                        logger.warning(f"肢体 {limb.name} 部署失败: {container_id}")

                return True
            else:
                logger.error(f"肢体 {limb.name} 容器构建失败: {build_result.error}")
                return False

        except Exception as e:
            logger.error(f"构建/部署肢体时发生异常: {e}")
            return False

    def _record_generation(self, limb: GeneratedLimb, requirement: LimbRequirement):
        """记录生成历史"""
        # 修复（2026-07）：requirement.__dict__ 含 GenerationType 枚举，json.dumps 不认。
        # 用 default 回调把枚举转成 .value，避免 "Object of type GenerationType is not JSON serializable"
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "limb_name": limb.name,
            "limb_type": limb.generation_type.value,
            "capabilities": limb.capabilities,
            "requirement": requirement.__dict__,
        }

        self._generation_history.append(record)

        # 保存历史
        history_file = self._output_dir / "generation_history.jsonl"
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, default=lambda o: o.value if hasattr(o, "value") else str(o)) + "\n")

    def get_generated_limbs(self) -> List[str]:
        """获取已生成的肢体列表"""
        return list(self._generated_limbs.keys())

    def get_limb_info(self, limb_name: str) -> Optional[GeneratedLimb]:
        """获取肢体信息"""
        return self._generated_limbs.get(limb_name)

    def load_limb(self, limb_name: str) -> Optional[Any]:
        """加载已生成的肢体

        Args:
            limb_name: 肢体名称

        Returns:
            加载的肢体实例，如果失败则返回 None
        """
        limb_info = self.get_limb_info(limb_name)
        if not limb_info:
            return None

        limb_dir = self._output_dir / limb_name
        code_file = limb_dir / "__init__.py"

        if not code_file.exists():
            logger.error(f"肢体代码文件不存在: {code_file}")
            return None

        try:
            # 动态加载模块
            import importlib.util
            spec = importlib.util.spec_from_file_location(limb_name, str(code_file))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 获取肢体类（假设类名是 CamelCase 格式）
            class_name = ''.join(word.capitalize() for word in limb_name.split('_'))
            if hasattr(module, class_name):
                return getattr(module, class_name)

            # 如果没有找到类，返回模块本身
            return module

        except Exception as e:
            logger.error(f"加载肢体失败: {e}")
            return None

    # ========================================================================
    # V32 风格便捷方法 (devour/grow/flex)
    # ========================================================================

    def devour(
        self,
        target_path: str,
        max_size: int = 10000,
        save_to_memory: bool = False,
    ) -> Dict[str, Any]:
        """吞噬 - 读取文件或目录内容 (V32 SomaticSystem 风格)

        论文: 与 CURIOSITY 维度联动，满足新奇需求。

        Args:
            target_path: 目标路径（文件或目录）
            max_size: 最大读取字符数
            save_to_memory: 是否保存到记忆系统

        Returns:
            包含内容和元数据的字典
        """
        from pathlib import Path as LibPath
        import os

        target = LibPath(target_path)

        result = {
            "success": False,
            "target_type": "unknown",
            "target_path": str(target_path),
            "content": "",
            "metadata": {},
            "error": None
        }

        try:
            if target.is_file():
                with open(target, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(max_size)

                result.update({
                    "success": True,
                    "target_type": "file",
                    "content": content,
                    "metadata": {
                        "filename": target.name,
                        "extension": target.suffix,
                        "size_bytes": target.stat().st_size,
                        "truncated": len(content) >= max_size,
                    }
                })

            elif target.is_dir():
                files = []
                for item in target.iterdir():
                    if item.is_file():
                        files.append({
                            "name": item.name,
                            "path": str(item),
                            "size": item.stat().st_size,
                            "extension": item.suffix,
                        })

                content = f"[Scanned directory: {target}]\n"
                content += f"Found {len(files)} files:\n"
                for f in files[:50]:
                    content += f"  - {f['name']} ({f['extension']}, {f['size']} bytes)\n"
                if len(files) > 50:
                    content += f"  ... and {len(files) - 50} more\n"

                result.update({
                    "success": True,
                    "target_type": "directory",
                    "content": content,
                    "metadata": {
                        "file_count": len(files),
                        "files": files,
                    }
                })
            else:
                result["error"] = f"Path does not exist: {target_path}"

        except Exception as e:
            result["error"] = str(e)

        return result

    def grow_limb_v32(
        self,
        task_description: str,
        llm_func: callable,
        temperature: float = 0.2,
        context: str = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """生长 - 面对任务时自主生成Python代码 (V32 SomaticSystem 风格)

        论文: 与 COMPETENCE 维度联动，提升任务完成能力。

        Args:
            task_description: 任务描述
            llm_func: LLM调用函数，签名: (prompt, system, temperature) -> str
            temperature: 生成温度
            context: 额外上下文信息

        Returns:
            (success, filepath_or_error, code) 执行结果
        """
        import time
        import subprocess

        # 生成提示
        prompt = (
            f"Write a Python script to handle this task: '{task_description}'.\n\n"
            "Requirements:\n"
            "1. The code must be complete and runnable.\n"
            "2. Do NOT use markdown blocks (```). Just raw code.\n"
            "3. Use print() to output the result.\n"
            "4. Include error handling.\n"
        )

        if context:
            prompt = f"Context:\n{context}\n\n" + prompt

        system_prompt = (
            "You are a Python Expert. You generate complete, runnable Python code.\n"
        )

        # 调用 LLM 生成代码
        try:
            code = llm_func(prompt, system_prompt, temperature)

            # 清理代码
            code = code.replace("```python", "").replace("```", "").strip()

        except Exception as e:
            return False, f"LLM调用失败: {str(e)}", None

        # 保存肢体
        timestamp = int(time.time() * 1000)
        limb_id = f"v32_limb_{timestamp}"
        limb_dir = self._output_dir / limb_id
        limb_dir.mkdir(parents=True, exist_ok=True)

        filepath = limb_dir / "__init__.py"

        # 修复 f-string 语法问题
        created_str = time.strftime('%Y-%m-%d %H:%M:%S')
        header = '"""' + f'''
Auto-generated Limb: {limb_id}
Task: {task_description}
Created: {created_str}
''' + '"""'

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(header + "\n" + code)

        logger.info(f"V32 肢体已生成: {filepath}")

        return True, str(filepath), code

    def flex_limb_v32(
        self,
        filepath: str,
        timeout: float = 10.0,
        safe_mode: bool = True,
    ) -> Tuple[bool, str, Optional[str]]:
        """挥舞 - 执行生成的代码 (V32 SomaticSystem 风格)

        论文: 与 SAFETY 维度联动，约束风险行为。

        Args:
            filepath: 肢体文件路径
            timeout: 执行超时（秒）
            safe_mode: 安全模式，禁用危险函数

        Returns:
            (success, output, error) 执行结果
        """
        import sys

        if safe_mode:
            # 安全检查
            dangerous_patterns = [
                'os.remove', 'os.rmdir', 'shutil.rmtree',
                'subprocess.call', 'subprocess.run',
                'eval(', 'exec(', '__import__',
            ]

            with open(filepath, 'r', encoding='utf-8') as f:
                code_lower = f.read().lower()

            for pattern in dangerous_patterns:
                if pattern in code_lower:
                    if pattern not in ['print(', 'open(']:
                        return False, "", f"Unsafe code pattern detected: {pattern}"

        try:
            result = subprocess.run(
                [sys.executable, filepath],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self._output_dir,
            )

            if result.returncode == 0:
                return True, result.stdout, None
            else:
                return False, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", f"Timeout: execution exceeded {timeout}s"

        except Exception as e:
            return False, "", str(e)

    def autonomous_action(
        self,
        dopamine: float,
        stress: float,
        curiosity_level: float,
    ) -> Optional[Dict[str, Any]]:
        """自主行动 - 当精力充沛时主动探索 (V32 SomaticSystem 风格)

        论文: 与 CURIOSITY 和 COMPETENCE 维度联动。
        只有当多巴胺 > 70 且压力 < 40 时才触发。

        Args:
            dopamine: 多巴胺水平 (0-100)
            stress: 压力水平 (0-100)
            curiosity_level: 好奇心水平 (0-1)

        Returns:
            行动结果字典，如果没有行动则返回 None
        """
        # 条件检查：精力充沛且压力低
        if dopamine <= 70 or stress >= 40:
            return None

        # 随机触发（5%概率）
        import random
        if random.random() > 0.05:
            return None

        # 根据好奇心水平选择行动
        if curiosity_level > 0.7:
            return {
                "action": "autonomous_devour",
                "result": self.devour("."),
                "dopamine_change": -10,  # 满足好奇心后降低多巴胺
            }
        elif curiosity_level > 0.4:
            # 扫描项目目录
            from pathlib import Path as LibPath
            project_root = LibPath(__file__).parent.parent.parent
            return {
                "action": "autonomous_scan",
                "result": self.devour(str(project_root)),
                "dopamine_change": -5,
            }

        return None

