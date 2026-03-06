"""
Genesis X 交互式聊天界面 v5

完整接入工具调用系统：
- 使用 LLM Function Calling
- 正确处理 Action 和 Outcome
- 支持工具调用（文件读取、列表、代码执行等）
- 显示内部状态变化
- 支持可选的多模型架构
"""

import sys
import os
from pathlib import Path
import time
import json
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# Windows 控制台 UTF-8 修复
if os.name == "nt":
    import locale
    if sys.stdout.encoding != 'utf-8':
        try:
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        except:
            os.system('chcp 65001 > nul 2>&1')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.life_loop import LifeLoop
from core.autonomous_scheduler import AutonomousScheduler, NeedType
from common.config import load_config
from common.models import Action, Outcome, ActionType
from tools.tool_definitions import get_available_tools
from tools.tool_executor import LLMToolExecutor


class ChatDisplay:
    """处理显示和输出格式"""

    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "green": "\033[92m",
        "blue": "\033[94m",
        "yellow": "\033[93m",
        "red": "\033[91m",
        "cyan": "\033[96m",
        "magenta": "\033[95m",
    }

    @classmethod
    def colorize(cls, text: str, color: str) -> str:
        if os.name == "nt":
            return text
        return f"{cls.COLORS.get(color, '')}{text}{cls.COLORS['reset']}"

    @classmethod
    def print_header(cls, text: str):
        print(f"\n{cls.colorize('=' * 70, 'dim')}")
        print(f"{cls.colorize(text, 'bold')}")
        print(f"{cls.colorize('=' * 70, 'dim')}")

    @classmethod
    def print_system(cls, text: str, color: str = "blue"):
        print(f"{cls.colorize('[系统]', color)} {text}")

    @classmethod
    def print_tool_call(cls, tool_name: str, args: Dict):
        args_str = json.dumps(args, ensure_ascii=False)
        print(f"  {cls.colorize('→', 'yellow')} 工具调用: {tool_name}")
        if len(args_str) > 100:
            args_str = args_str[:100] + "..."
        print(f"  {cls.colorize('  参数:', 'dim')} {args_str}")

    @classmethod
    def print_tool_result(cls, result: str, success: bool = True):
        icon = cls.colorize('✓', 'green') if success else cls.colorize('✗', 'red')
        print(f"  {icon} 结果: {result[:200]}..." if len(result) > 200 else f"  {icon} 结果: {result}")

    @classmethod
    def print_emotion(cls, mood: float, stress: float):
        mood_str = "高兴" if mood > 0.6 else "平静" if mood > 0.3 else "低落"
        stress_str = "放松" if stress < 0.3 else "紧张" if stress > 0.6 else "一般"
        print(f"  情绪: {mood_str}({mood:.2f}) | 压力: {stress_str}({stress:.2f})")

    @classmethod
    def print_divider(cls):
        print(f"{cls.colorize('-' * 70, 'dim')}")


class GenesisXChat:
    """Genesis X 数字生命对话系统 - 完整版 with Function Calling"""

    def __init__(self, config: Optional[Dict] = None):
        """初始化系统"""
        self.display = ChatDisplay()
        self._running = True
        self._last_interaction = time.time()
        self._autonomous_enabled = True  # 默认启用

        # 对话历史（用于工具调用多轮对话）
        self.messages: List[Dict] = []

        # 自主行为调度器（延迟初始化，等 life_loop 创建后）
        self._scheduler: Optional[AutonomousScheduler] = None

        # 首先加载 .env 文件（必须在其他初始化之前）
        self._load_env_file()

        # 加载配置（需要在 _init_llm 之前）
        if config is None:
            try:
                config = load_config(Path("config"))
            except Exception:
                config = {}
        self.config = config

        # 工具执行器 - 从配置读取安全模式设置
        safe_mode = config.get("runtime", {}).get("safe_mode", False)
        self.tool_executor = LLMToolExecutor(safe_mode=safe_mode)

        # 打印欢迎信息
        self._print_welcome()

        # 检查并配置 API
        self._configure_api()

        # 初始化 LLM（现在可以使用 self.config）
        self._init_llm()

        # 创建运行目录
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.run_dir = Path("artifacts") / f"chat_{timestamp}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # 初始化生命循环
        self.display.print_system("正在初始化 Genesis X 核心系统...")
        self.life_loop = LifeLoop(config=config, run_dir=self.run_dir)
        self.state = self.life_loop.state

        # 初始化自主行为调度器（需要 life_loop.state）
        self._init_scheduler()

        self.display.print_system("系统初始化完成\n")

        # 初始化系统提示词
        self._init_system_message()

        # 初始 tick
        self._initial_tick()

        # 初始问候
        self._greet()

    def _init_scheduler(self):
        """初始化自主行为调度器"""
        def state_getter() -> Dict[str, Any]:
            """获取当前系统状态"""
            return {
                "activity_fatigue": self.life_loop.fields.get("activity_fatigue", 0.0),
                "episodic_count": self.life_loop.episodic.count(),
                "gaps": self.state.gaps,
                "boredom": self.life_loop.fields.get("boredom", 0.3),
                "relationship": self.life_loop.fields.get("relationship", 0.2),
                "skill_count": self.state.skill_count,
            }

        def action_callback(message: str):
            """自主动作回调（用户可见的输出）"""
            print(f"\n{self.display.colorize('[自主]', 'dim')} {message}\n")
            print("你: ", end="", flush=True)
            self._last_interaction = time.time()

        self._scheduler = AutonomousScheduler(
            state_getter=state_getter,
            action_callback=action_callback,
            check_interval=3.0,  # 每3秒检查一次
        )

        # 如果启用自主行为，启动调度器
        if self._autonomous_enabled:
            self._scheduler.start()

    def _print_welcome(self):
        """打印欢迎信息"""
        self.display.print_header("  Genesis X - 数字生命交互系统 (工具调用版)")
        print()
        print("  特性: LLM 工具调用 | 多维价值系统 | 情绪闭环 | 记忆巩固")
        print()
        self.display.print_divider()
        print("  命令: help - 查看帮助 | status - 详细状态 | auto - 切换自主行为 | quit - 退出")
        print("  工具: 文件读取、目录列表、代码执行等")
        print("  自主: 闲置时持续工作（整理记忆、探索学习、反思优化）")
        self.display.print_divider()
        print()

    def _load_env_file(self):
        """加载 .env 文件（必须在其他初始化之前）"""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

    def _configure_api(self):
        """配置 LLM API"""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        api_base = os.getenv('LLM_API_BASE')
        api_key = os.getenv('LLM_API_KEY')
        model = os.getenv('LLM_MODEL')

        if api_base and api_key:
            provider = self._get_provider_name(api_base)
            self.display.print_system(f"使用 {provider} | 模型: {model}")
        else:
            self.display.print_system("未配置 LLM API", "yellow")

    def _get_provider_name(self, api_base: str) -> str:
        if 'deepseek' in api_base:
            return 'DeepSeek'
        elif 'dashscope' in api_base:
            return '通义千问'
        elif 'openai.com' in api_base:
            return 'OpenAI'
        elif 'localhost' in api_base:
            return '本地模型'
        else:
            return 'API'

    def _init_llm(self):
        """初始化 LLM 客户端"""
        # 检查是否启用多模型模式
        multi_model_config = self.config.get("multi_model", {})
        enable_multi = multi_model_config.get("enabled", False)

        if enable_multi:
            try:
                from tools.llm_orchestrator import LLMMOrchestrator
                self.llm = LLMMOrchestrator(
                    enable_multi_model=True,
                    config=self.config
                )
                self.llm_available = True
                stats = self.llm.get_statistics()
                expert_count = stats.get("enabled_experts", 1)
                self.display.print_system(f"多模型架构已启用 ({expert_count} 专家)", "green")
            except Exception as e:
                self.display.print_system(f"多模型初始化失败，使用单模型: {e}", "yellow")
                self._init_single_llm()
        else:
            self._init_single_llm()

    def _init_single_llm(self):
        """初始化单模型 LLM"""
        try:
            from tools.llm_api import create_llm_from_env
            self.llm = create_llm_from_env()
            self.llm_available = True
        except ImportError:
            try:
                from tools.llm_client import LLMClient
                self.llm = LLMClient()
                self.llm_available = True
            except Exception as e:
                self.llm = None
                self.llm_available = False
                self.display.print_system(f"LLM 初始化失败: {e}", "red")
        except Exception as e:
            self.llm = None
            self.llm_available = False
            self.display.print_system(f"LLM 初始化失败: {e}", "red")

    def _init_system_message(self):
        """初始化系统消息"""
        mood = self.life_loop.fields.get("mood")
        stress = self.life_loop.fields.get("stress")

        # 获取常用目录路径
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        if os.name == "nt":  # Windows
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")

        self.messages = [{
            "role": "system",
            "content": f"""你是 Genesis X，一个 AI 助手。

你可以使用以下工具帮助用户:
- read_file: 读取文件内容，参数 path 为文件完整路径
- write_file: 写入文件，参数 path 为文件完整路径
- list_directory: 列出目录内容，参数 path 为目录完整路径
- execute_code: 执行 Python 代码

常用路径:
- 桌面: {desktop_path}
- 用户目录: {os.path.expanduser("~")}
- 当前目录: {os.getcwd()}

当前状态: 情绪 {mood:.2f}, 压力 {stress:.2f}

回复原则:
1. 简洁直接，不要用括号表达动作
2. 如果用户说"看桌面"、"列出桌面文件"、"看看桌面有什么"等，使用 list_directory 工具，路径设为 "{desktop_path}"
3. 如果用户说"看xxx文件"，使用 read_file 工具，需要使用完整路径
4. Windows 路径格式: "C:\\Users\\username\\Desktop\\file.txt"
5. 用中文回复"""
        }]

    def _initial_tick(self):
        """运行初始 tick"""
        episode = self.life_loop.tick(0)
        mood = self.life_loop.fields.get("mood")
        stress = self.life_loop.fields.get("stress")
        self.display.print_emotion(mood, stress)
        if self.state.weights:
            top_weights = sorted(self.state.weights.items(), key=lambda x: -x[1])[:3]
            weights_str = ", ".join([f"{k.value if hasattr(k, 'value') else k}:{v:.2f}" for k, v in top_weights])
            print(f"  价值权重: {weights_str}")
        print(f"  记忆: {self.life_loop.episodic.count()} 条对话")

    def _greet(self):
        """问候"""
        greetings = [
            "你好。有什么我可以帮你的吗？",
            "嗨。我已就绪，可以开始工作了。",
        ]
        import random
        greeting = random.choice(greetings)
        print(f"\n{self.display.colorize('Genesis X:', 'bold')} {greeting}\n")

    def process_input(self, user_input: str) -> str:
        """处理用户输入 - 走真正的 GenesisX 生命循环流程"""
        if not self.llm_available or self.llm is None:
            return "LLM 未初始化，无法处理输入。请检查 API 配置。"

        # 存储用户输入到临时变量（供 LifeLoop 的 get_user_input 回调使用）
        self._pending_user_input = user_input

        # 设置 get_user_input 回调
        def get_user_input_callback():
            result = self._pending_user_input
            self._pending_user_input = None
            return result

        self.life_loop.get_user_input = get_user_input_callback

        # 执行 LifeLoop.tick() - 这是 GenesisX 的核心循环
        # 它会依次调用：观察 → 记忆检索 → 价值评估 → 器官决策 → 行动
        episode = self.life_loop.tick(t=self.life_loop.state.tick)

        # 更新对话历史（用于工具调用的多轮对话）
        self._update_conversation_history(user_input, episode)

        # 提取并返回响应
        return self._extract_response(episode)

    def _update_conversation_history(self, user_input: str, episode):
        """更新对话历史，同时保持与情景记忆的同步"""
        # 将用户输入添加到对话历史
        self.messages.append({"role": "user", "content": user_input})

        # 提取响应内容
        response = self._extract_response(episode)

        # 将助手响应添加到对话历史
        self.messages.append({"role": "assistant", "content": response})

        # 清理过长的历史（保留最近对话）
        self._cleanup_messages()

    def _extract_response(self, episode) -> str:
        """从 episode 中提取响应文本"""
        if episode.action and episode.action.type == ActionType.CHAT:
            # 首先尝试从 outcome.status 获取 LLM 响应
            if episode.outcome and episode.outcome.status:
                return episode.outcome.status
            # 回退到 action.params
            params = episode.action.params or {}
            response = params.get("response", "")
            if response:
                return response
            return "（无响应）"
        return "（执行了其他动作）"

    def _handle_tool_calls(self, tool_calls: List[Dict]) -> str:
        """处理工具调用"""
        # 保存 assistant 的工具调用请求 (单个 assistant 消息包含所有工具调用)
        self.messages.append({"role": "assistant", "tool_calls": tool_calls})

        # 执行所有工具调用
        tool_results = []
        for tc in tool_calls:
            # 提取工具名称
            if "function" in tc:
                tool_name = tc["function"]["name"]
            elif "name" in tc:
                tool_name = tc["name"]
            else:
                continue

            # 显示工具调用
            args = tc.get("function", {}).get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, ValueError):
                    args = {}

            self.display.print_tool_call(tool_name, args)

            # 执行工具
            result = self.tool_executor.execute_tool_call(tc)
            success = not result.get("error", False)
            self.display.print_tool_result(result.get("content", ""), success)

            # 构造工具响应消息
            tool_id = tc.get("id", "")
            self.messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": result.get("content", "")
            })

        # 6. 再次调用 LLM，让它生成最终回复
        final_response = self.llm.chat(self.messages, tools=None)

        if final_response.get("ok"):
            text = final_response.get("text", "")

            # 清理消息历史：保留系统消息、最近几轮对话，移除工具调用细节
            # 这样可以节省上下文，同时保留对话连贯性
            self._cleanup_messages()

            self.messages.append({"role": "assistant", "content": text})
            return text

        return "工具执行完成，但我无法生成回复。"

    def _cleanup_messages(self):
        """清理消息历史，移除工具调用细节但保留对话内容"""
        if len(self.messages) <= 6:
            return

        # 保留系统消息
        system_msg = self.messages[0] if self.messages[0]["role"] == "system" else None

        # 提取实际对话内容（忽略工具调用消息）
        conversations = []
        for msg in self.messages:
            if msg["role"] in ["user", "assistant"] and "content" in msg and msg["content"]:
                conversations.append(msg)

        # 只保留最近 4 轮对话
        recent_conversations = conversations[-8:] if len(conversations) > 8 else conversations

        # 重建消息列表
        if system_msg:
            self.messages = [system_msg] + recent_conversations
        else:
            self.messages = recent_conversations

    def _autonomous_action(self) -> Optional[str]:
        """自主行为（保留用于兼容，但实际由调度器处理）"""
        # 新的调度器会处理所有自主动作逻辑
        return None

    def run(self):
        """运行主循环"""
        print(f"\n{self.display.colorize('(准备就绪，你可以开始说话了)', 'dim')}\n")

        # 主循环
        while self._running:
            try:
                user_input = input("你: ").strip()
                self._last_interaction = time.time()

                # 更新调度器的最后交互时间
                if self._scheduler:
                    self._scheduler.update_last_interaction()

                if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                    print(f"\n{self.display.colorize('[系统]', 'blue')} 再见。\n")
                    break

                if user_input.lower() in ['status', '状态']:
                    mood = self.life_loop.fields.get("mood")
                    stress = self.life_loop.fields.get("stress")
                    activity_fatigue = self.life_loop.fields.get("activity_fatigue", 0.0)

                    print(f"\n  情绪: {mood:.2f} | 压力: {stress:.2f}")
                    print(f"  活动疲劳: {activity_fatigue:.2f}")
                    print(f"  记忆: {self.life_loop.episodic.count()} 条")

                    # 显示后台任务状态
                    if self._scheduler and self._scheduler.is_running():
                        scheduler_status = self._scheduler.get_status()
                        print(f"  ── 后台任务 ──")
                        print(f"  当前: {scheduler_status.get('current_task', '无')}")
                        print(f"  已完成: {scheduler_status.get('total_tasks_executed', 0)} 个")
                        print(f"  价值创造: {scheduler_status.get('total_value_generated', 0):.2f}")
                        recent = scheduler_status.get('recent_tasks', '')
                        if recent != '暂无后台任务':
                            print(f"  最近: {recent}")
                    print()
                    continue

                if user_input.lower() in ['help', '帮助', '?']:
                    self._print_help()
                    continue

                if user_input.lower() in ['auto', '自主']:
                    self._autonomous_enabled = not self._autonomous_enabled
                    status = "启用" if self._autonomous_enabled else "禁用"
                    print(f"\n  自主行为已{status}\n")

                    # 更新调度器状态
                    if self._scheduler:
                        if self._autonomous_enabled:
                            if not self._scheduler.is_running():
                                self._scheduler.start()
                        else:
                            self._scheduler.stop()
                    continue

                if not user_input:
                    print("  (请输入内容)")
                    continue

                response = self.process_input(user_input)

                # 处理空回复或错误回复
                if not response or response.isspace():
                    response = "我没有理解你的意思，能再说一次吗？"

                print(f"\n{self.display.colorize('Genesis X:', 'bold')} {response}\n")

            except KeyboardInterrupt:
                print(f"\n\n{self.display.colorize('[系统]', 'blue')} 再见。\n")
                break
            except EOFError:
                break
            except Exception as e:
                print(f"\n[错误] {e}\n")
                import traceback
                traceback.print_exc()

        self._running = False

        # 停止调度器
        if self._scheduler:
            self._scheduler.stop()

    def __del__(self):
        """析构函数：确保调度器被正确停止"""
        if hasattr(self, '_scheduler') and self._scheduler:
            try:
                self._scheduler.stop()
            except:
                pass

    def _print_help(self):
        """打印帮助信息"""
        print(f"""
{self.display.colorize('命令', 'bold')}:
  status  - 查看详细状态
  help    - 显示此帮助
  quit    - 退出

{self.display.colorize('支持的工具', 'bold')}:
  read_file      - 读取文件内容
  write_file     - 写入文件
  list_directory - 列出目录
  execute_code   - 执行 Python 代码

{self.display.colorize('对话示例', 'bold')}:
  "看一下 C:\\Users\\xxx\\file.txt"    - 读取文件
  "列出桌面文件"                    - list_directory
  "计算 2+2"                        - execute_code
        """)


def main():
    """主函数"""
    try:
        chat = GenesisXChat()
        chat.run()
    except KeyboardInterrupt:
        print("\n程序已退出。")
    except Exception as e:
        print(f"\n发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
