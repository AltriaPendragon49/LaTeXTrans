import os
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


def pack_md_files_to_md(output_filename="all_docs_combined.md"):
    root_dir = Path(__file__).resolve().parent
    current_script_name = Path(__file__).name
    
    # 定义需要排除的文件名关键词
    exclude_keywords = ["backup", "test", "temp", "deprecated"]
    
    md_files = []
    # 遍历文件并应用过滤规则，改为匹配 *.md
    for f in root_dir.rglob("*.md"):
        # 1. 排除生成的汇总文件本身，防止无限套娃
        if f.name == output_filename:
            continue
        # 2. 排除当前脚本（以防脚本本身被命名为.md）
        if f.name == current_script_name:
            continue
        # 3. 排除包含特定关键词的文件 
        if any(keyword in f.name.lower() for keyword in exclude_keywords):
            continue
        # 4. 排除常见的隐藏目录或不需要的目录 (增加了 node_modules 等)
        if any(part.startswith('.') or part in ['venv', 'env', 'node_modules'] for part in f.parts):
            continue
            
        md_files.append(f)
    
    if not md_files:
        print(f"未找到有效的 .md 文件。")
        return

    output_path = root_dir / output_filename
    tree_structure = generate_tree_structure(md_files, root_dir)

    with open(output_path, "w", encoding="utf-8") as out_file:
        out_file.write(f"# 项目文档汇总: {root_dir.name}\n\n")
        out_file.write("> 说明：\n")
        out_file.write(f"> 1. 已忽略汇总文件自身 `{output_filename}` 及包含 `backup/test` 等关键词的文件。\n")
        out_file.write("> 2. 为避免 Markdown 语法冲突，源码使用了 4 个反引号进行代码块包裹。\n\n")
        out_file.write("## 1. 文档文件结构\n\n")
        out_file.write("```text\n")
        out_file.write(tree_structure)
        out_file.write("\n```\n\n")
        out_file.write("---\n\n")
        out_file.write("## 2. 详细文档内容\n\n")

        for md_file in sorted(md_files):
            try:
                rel_path = md_file.relative_to(root_dir)
                raw_content = md_file.read_text(encoding="utf-8")
                
                out_file.write(f"### 📄 {rel_path}\n\n")
                # 使用 4 个反引号，防止内部原本的 3 反引号代码块打断格式
                out_file.write("````markdown\n")
                out_file.write(raw_content)
                # 确保末尾有换行，防止反引号拼接错误
                if not raw_content.endswith("\n"):
                    out_file.write("\n")
                out_file.write("````\n\n")
                out_file.write("---\n\n")
                print(f"已打包: {rel_path}")
            except Exception as e:
                print(f"处理 {md_file.name} 时出错: {e}")

    print(f"\n任务完成！文件已保存至: {output_path}")

if __name__ == "__main__":
    pack_md_files_to_md()