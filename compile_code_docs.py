"""Code documentation generator for Genesis X.

Generates comprehensive API documentation from source code.
Usage:
    python compile_code_docs.py
"""

import os
import ast
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import json


class DocGenerator:
    """Generate documentation from Python source code."""

    def __init__(self, project_root: Path):
        """Initialize documentation generator.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = project_root
        self.docs_output = project_root / "docs" / "api"

    def generate_all(self) -> Dict[str, Any]:
        """Generate documentation for all Python modules.

        Returns:
            Dictionary with module documentation
        """
        docs = {}

        # 发现所有 Python 模块
        for module_path in self._find_modules():
            try:
                module_docs = self._generate_module_docs(module_path)
                if module_docs:
                    module_name = self._get_module_name(module_path)
                    docs[module_name] = module_docs
            except Exception as e:
                print(f"[Warning] Failed to generate docs for {module_path}: {e}")

        return docs

    def _find_modules(self) -> List[Path]:
        """Find all Python modules in the project.

        Returns:
            List of module paths
        """
        modules = []

        # 核心模块
        core_dirs = [
            "core", "axiology", "affect", "memory", "cognition",
            "organs", "perception", "metabolism", "safety",
            "tools", "persistence", "common", "interface"
        ]

        for dir_name in core_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                modules.extend(dir_path.glob("*.py"))
                # 子模块
                for submodule in dir_path.rglob("*.py"):
                    if "__pycache__" not in str(submodule):
                        modules.append(submodule)

        return sorted(set(modules))

    def _get_module_name(self, module_path: Path) -> str:
        """Get module name from file path.

        Args:
            module_path: Path to module file

        Returns:
            Module name (e.g., "core.life_loop")
        """
        rel_path = module_path.relative_to(self.project_root)
        parts = list(rel_path.parts[:-1]) + [rel_path.stem]
        return ".".join(p for p in parts if p != "__init__")

    def _generate_module_docs(self, module_path: Path) -> Optional[Dict[str, Any]]:
        """Generate documentation for a single module.

        Args:
            module_path: Path to module file

        Returns:
            Module documentation dictionary
        """
        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                source = f.read()
        except Exception as e:
            return None

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return None

        module_doc = {
            "path": str(module_path),
            "docstring": ast.get_docstring(tree) or "",
            "classes": {},
            "functions": {},
            "imports": []
        }

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                class_doc = self._generate_class_docs(node)
                module_doc["classes"][node.name] = class_doc
            elif isinstance(node, ast.FunctionDef):
                func_doc = self._generate_function_docs(node)
                module_doc["functions"][node.name] = func_doc
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module_doc["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        module_doc["imports"].append(f"{node.module}.{alias.name}")

        return module_doc

    def _generate_class_docs(self, node: ast.ClassDef) -> Dict[str, Any]:
        """Generate documentation for a class.

        Args:
            node: AST ClassDef node

        Returns:
            Class documentation dictionary
        """
        class_doc = {
            "docstring": ast.get_docstring(node) or "",
            "methods": {},
            "attributes": []
        }

        # 提取基类
        if node.bases:
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(ast.unparse(base))
            class_doc["bases"] = bases

        # 提取方法和属性
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method_doc = self._generate_function_docs(item)
                class_doc["methods"][item.name] = method_doc
            elif isinstance(item, ast.AnnAssign):
                # 类属性注解
                if isinstance(item.target, ast.Name):
                    attr_name = item.target.id
                    class_doc["attributes"].append({
                        "name": attr_name,
                        "annotation": ast.unparse(item.annotation) if item.annotation else None
                    })

        return class_doc

    def _generate_function_docs(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """Generate documentation for a function.

        Args:
            node: AST FunctionDef node

        Returns:
            Function documentation dictionary
        """
        func_doc = {
            "docstring": ast.get_docstring(node) or "",
            "args": [],
            "returns": None,
            "decorators": []
        }

        # 提取装饰器
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                func_doc["decorators"].append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                func_doc["decorators"].append(ast.unparse(decorator))

        # 提取参数
        for arg in node.args.args:
            arg_info = {"name": arg.arg}
            if arg.annotation:
                arg_info["annotation"] = ast.unparse(arg.annotation)
            func_doc["args"].append(arg_info)

        # 提取返回类型
        if node.returns:
            func_doc["returns"] = ast.unparse(node.returns)

        return func_doc

    def save_markdown(self, docs: Dict[str, Any], output_path: Optional[Path] = None):
        """Save documentation as Markdown files.

        Args:
            docs: Documentation dictionary
            output_path: Output directory (defaults to docs/api)
        """
        output_path = output_path or self.docs_output
        output_path.mkdir(parents=True, exist_ok=True)

        # 生成总索引
        index_content = "# Genesis X API 文档\n\n"
        index_content += f"生成时间: {datetime.now(timezone.utc).isoformat()}\n\n"
        index_content += "## 模块索引\n\n"

        for module_name, module_doc in sorted(docs.items()):
            module_file = output_path / f"{module_name.replace('.', '_')}.md"

            # 生成模块文档
            module_content = f"# {module_name}\n\n"
            module_content += f"**路径**: `{module_doc['path']}`\n\n"

            if module_doc['docstring']:
                module_content += f"## 模块说明\n\n{module_doc['docstring']}\n\n"

            # 类
            if module_doc['classes']:
                module_content += "## 类\n\n"
                for class_name, class_doc in module_doc['classes'].items():
                    module_content += f"### {class_name}\n\n"
                    if class_doc['docstring']:
                        module_content += f"{class_doc['docstring']}\n\n"
                    if class_doc.get('bases'):
                        module_content += f"**基类**: {', '.join(class_doc['bases'])}\n\n"
                    if class_doc['methods']:
                        module_content += "#### 方法\n\n"
                        for method_name, method_doc in class_doc['methods'].items():
                            module_content += f"##### {method_name}\n\n"
                            module_content += self._format_function_doc(method_doc)

            # 函数
            if module_doc['functions']:
                module_content += "## 函数\n\n"
                for func_name, func_doc in module_doc['functions'].items():
                    module_content += f"### {func_name}\n\n"
                    module_content += self._format_function_doc(func_doc)

            # 写入文件
            with open(module_file, 'w', encoding='utf-8') as f:
                f.write(module_content)

            # 添加到索引
            index_content += f"- [{module_name}]({module_file.name})\n"

        # 写入索引
        index_file = output_path / "README.md"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_content)

    def _format_function_doc(self, func_doc: Dict[str, Any]) -> str:
        """Format function documentation as Markdown.

        Args:
            func_doc: Function documentation dictionary

        Returns:
            Markdown formatted string
        """
        content = ""

        if func_doc['docstring']:
            content += f"{func_doc['docstring']}\n\n"

        # 签名
        args_str = ", ".join([
            f"{arg['name']}" + (f": {arg['annotation']}" if arg.get('annotation') else "")
            for arg in func_doc['args']
        ])
        returns_str = f" -> {func_doc['returns']}" if func_doc['returns'] else ""

        content += f"**签名**: `({args_str}){returns_str}`\n\n"

        return content

    def save_json(self, docs: Dict[str, Any], output_path: Optional[Path] = None):
        """Save documentation as JSON file.

        Args:
            docs: Documentation dictionary
            output_path: Output file path
        """
        output_path = output_path or (self.docs_output / "docs.json")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(docs, f, indent=2, ensure_ascii=False, default=str)


def main():
    """Main entry point."""
    project_root = Path(__file__).parent

    print("=" * 60)
    print("Genesis X 代码文档生成器")
    print("=" * 60)
    print()

    generator = DocGenerator(project_root)

    print("正在扫描 Python 模块...")
    docs = generator.generate_all()

    print(f"找到 {len(docs)} 个模块")
    print()

    print("正在生成 Markdown 文档...")
    generator.save_markdown(docs)

    print("正在生成 JSON 文档...")
    generator.save_json(docs)

    print()
    print("=" * 60)
    print("文档生成完成!")
    print(f"输出目录: {generator.docs_output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
