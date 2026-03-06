"""Tool definitions for LLM function calling.

定义了系统可用的工具，用于 LLM 的 function calling 功能。
"""

from typing import List, Dict, Any, Optional


# 工具定义列表
AVAILABLE_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取文件内容。当用户要求查看、读取、检查文件时使用此工具。注意：必须使用完整的文件路径。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件的完整路径。Windows示例: C:\\Users\\Administrator\\Desktop\\file.txt 或 C:\\Users\\你的用户名\\Desktop\\文件名.txt"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "写入内容到文件。当用户要求保存、写入文件时使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "文件的完整路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的内容"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "列出目录中的文件和文件夹。当用户说'看桌面'、'列出文件'、'查看目录'时使用。注意：Windows桌面路径通常是 C:\\Users\\用户名\\Desktop，需要替换为实际用户名。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "目录的完整路径。Windows示例: C:\\Users\\Administrator\\Desktop 或 C:\\Users\\你的用户名\\Desktop"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "在网络上搜索信息。当用户询问最新信息、新闻、实时数据时使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询内容"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "执行 Python 代码并返回结果。当用户要求运行代码、计算、数据处理时使用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要执行的 Python 代码"
                    }
                },
                "required": ["code"]
            }
        }
    },
]


def get_available_tools() -> List[Dict[str, Any]]:
    """获取可用的工具定义列表。"""
    return AVAILABLE_TOOLS


def get_tool_names() -> List[str]:
    """获取所有工具名称。"""
    return [tool["function"]["name"] for tool in AVAILABLE_TOOLS]


def get_tool_definition(name: str) -> Optional[Dict[str, Any]]:
    """根据名称获取工具定义。"""
    for tool in AVAILABLE_TOOLS:
        if tool["function"]["name"] == name:
            return tool["function"]
    return None
