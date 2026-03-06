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

        # 使用 LLM 自主生成
        logger.info(f"使用 LLM 自主生成: {requirement.name}")
        limb = self._generate_from_llm(requirement)

        if not limb:
            logger.warning(f"LLM 生成失败: {requirement.name}")
            return False, None

        # 测试肢体
        if not self._test_limb(limb):
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
4. 每个方法都要有文档字符串
5. 包含错误处理
6. 如果需要外部依赖，在代码注释中说明
7. 不要使用 markdown 代码块标记

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
                return self.llm_client.generate(prompt, system_prompt, temperature=0.3)

            elif hasattr(self.llm_client, 'chat'):
                # 聊天接口
                return self.llm_client.chat(prompt, system_prompt)

            elif hasattr(self.llm_client, 'complete'):
                # 补全接口
                return self.llm_client.complete(prompt, system=system_prompt)

            elif callable(self.llm_client):
                # 可调用对象
                return self.llm_client(prompt, system_prompt)

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
            f.write(json.dumps(record) + "\n")

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

