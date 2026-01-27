import os
import re
from pathlib import Path

def generate_tree_structure(file_paths, root_dir):
    """构建目录树结构"""
    if not file_paths:
        return "（无文件）"
    tree = {}
    for path in file_paths:
        parts = path.relative_to(root_dir).parts
        current_level = tree
        for part in parts:
            if part not in current_level:
                current_level[part] = {}
            current_level = current_level[part]
    tree_lines = [f"📦 {root_dir.name}"]
    def _build_tree_string(node, prefix=""):
        keys = sorted(node.keys())
        count = len(keys)
        for i, key in enumerate(keys):
            is_last = (i == count - 1)
            connector = "└── " if is_last else "├── "
            tree_lines.append(f"{prefix}{connector}{key}")
            children = node[key]
            if children:
                extension = "    " if is_last else "│   "
                _build_tree_string(children, prefix + extension)
    _build_tree_string(tree)
    return "\n".join(tree_lines)

def clean_long_strings(content):
    """折叠超过 5 行的长字符串（如 Prompt）"""
    pattern = r'(\s*=\s*)(f?r?)("""|\'\'\')([\s\S]*?)(\3)'
    def replacer(match):
        equals = match.group(1)
        prefix = match.group(2)
        quote = match.group(3)
        inner_text = match.group(4)
        end_quote = match.group(5)
        lines_count = inner_text.count('\n')
        if lines_count > 5:
            summary = f"\n    ... [Prompt Content Hidden: {len(inner_text)} chars / {lines_count} lines] ...\n    "
            return f"{equals}{prefix}{quote}{summary}{end_quote}"
        return match.group(0)
    return re.sub(pattern, replacer, content)

def pack_py_files_to_md(output_filename="all_code.md"):
    root_dir = Path(__file__).resolve().parent
    current_script_name = Path(__file__).name
    
    # 【核心修改】：定义需要排除的文件名关键词
    exclude_keywords = ["backup", "test", "temp", "deprecated"]
    
    py_files = []
    # 遍历文件并应用过滤规则
    for f in root_dir.rglob("*.py"):
        # 1. 排除当前脚本
        if f.name == current_script_name:
            continue
        # 2. 排除 __init__.py
        if f.name == "__init__.py":
            continue
        # 3. 排除包含特定关键词的文件 (如 utils_backup.py)
        if any(keyword in f.name.lower() for keyword in exclude_keywords):
            continue
        # 4. 排除常见的虚拟环境或隐藏目录（虽然 rglob 默认不一定包含，但双重保险）
        if any(part.startswith('.') or part in ['venv', 'env'] for part in f.parts):
            continue
            
        py_files.append(f)
    
    if not py_files:
        print(f"未找到有效文件。")
        return

    output_path = root_dir / output_filename
    tree_structure = generate_tree_structure(py_files, root_dir)

    with open(output_path, "w", encoding="utf-8") as md_file:
        md_file.write(f"# 项目代码汇总: {root_dir.name}\n\n")
        md_file.write("> 说明：\n")
        md_file.write("> 1. 已忽略 `__init__.py` 及包含 `backup/test` 的文件。\n")
        md_file.write("> 2. 已自动折叠长 Prompt。\n\n")
        md_file.write("## 1. 项目文件结构\n\n")
        md_file.write("```text\n")
        md_file.write(tree_structure)
        md_file.write("\n```\n\n")
        md_file.write("---\n\n")
        md_file.write("## 2. 详细代码内容\n\n")

        for py_file in sorted(py_files):
            try:
                rel_path = py_file.relative_to(root_dir)
                raw_content = py_file.read_text(encoding="utf-8")
                final_content = clean_long_strings(raw_content)
                
                md_file.write(f"### 📄 {rel_path}\n\n")
                md_file.write("```python\n")
                md_file.write(final_content)
                md_file.write("\n```\n\n")
                md_file.write("---\n\n")
                print(f"已打包: {rel_path}")
            except Exception as e:
                print(f"处理 {py_file.name} 时出错: {e}")

    print(f"\n任务完成！文件已保存至: {output_path}")

if __name__ == "__main__":
    pack_py_files_to_md()