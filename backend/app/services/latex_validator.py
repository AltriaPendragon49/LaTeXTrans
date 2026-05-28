"""LaTeX 目录验证服务

验证上传目录是否为有效的 LaTeX 项目，检测主入口文件并提供警告/错误信息。
"""

import re
import logging
from pathlib import Path
from typing import Optional

from backend.app.models.config_models import LatexValidation

logger = logging.getLogger(__name__)


def validate_latex_directory(path: Path) -> LatexValidation:
    """验证目录是否为有效的 LaTeX 项目

    检测逻辑：
    1. 递归搜索 .tex 文件
    2. 按以下规则识别主入口文件：
       - 文件名匹配：main.tex, paper.tex, article.tex, document.tex
       - 内容包含 \\documentclass
    3. 返回包含警告和错误的验证结果

    参数:
        path: 待验证目录的路径

    返回:
        LatexValidation 验证结果对象
    """
    logger.info(f"Validating LaTeX directory: {path}")

    warnings = []
    errors = []
    main_file = None

    if not path.exists():
        return LatexValidation(
            is_valid=False,
            errors=["目录不存在"]
        )

    if not path.is_dir():
        return LatexValidation(
            is_valid=False,
            errors=["路径不是有效目录"]
        )

    # 查找所有 .tex 文件
    tex_files = list(path.rglob("*.tex"))
    tex_file_paths = [str(f.relative_to(path)) for f in tex_files]

    if not tex_files:
        return LatexValidation(
            is_valid=False,
            tex_files=[],
            errors=["压缩包中无 .tex 文件"]
        )

    logger.info(f"Found {len(tex_files)} .tex files")

    # 主文件检测的优先级名称
    priority_names = ["main.tex", "paper.tex", "article.tex", "document.tex"]

    # 按优先级名称查找主文件
    for priority_name in priority_names:
        for tex_file in tex_files:
            if tex_file.name.lower() == priority_name:
                main_file = str(tex_file.relative_to(path))
                logger.info(f"Found main file by name: {main_file}")
                break
        if main_file:
            break

    # 如果按名称未找到，则在文件内容中搜索 \documentclass
    if not main_file:
        candidates = []
        for tex_file in tex_files:
            try:
                content = tex_file.read_text(encoding='utf-8', errors='ignore')
                # 匹配 \documentclass 及其可选参数
                if re.search(r'\\documentclass(\[.*?\])?\{', content):
                    candidates.append(str(tex_file.relative_to(path)))
            except Exception as e:
                logger.warning(f"Error reading {tex_file}: {e}")

        if len(candidates) == 1:
            main_file = candidates[0]
            logger.info(f"Found main file by \\documentclass: {main_file}")
        elif len(candidates) > 1:
            # 多个候选文件，使用第一个并发出警告
            main_file = candidates[0]
            warnings.append(
                f"Multiple files contain \\documentclass: {', '.join(candidates)}. "
                f"Using {main_file} as main file."
            )
            logger.warning(f"Multiple main file candidates: {candidates}")

    # 仍未找到，使用第一个 .tex 文件
    if not main_file:
        main_file = str(tex_files[0].relative_to(path))
        warnings.append(
            f"Could not detect main entry file. Using first .tex file: {main_file}"
        )
        logger.warning(f"Using first .tex file as main: {main_file}")

    # 常见问题检查：.tex 文件过多（可能嵌套了子项目）
    if len(tex_files) > 50:
        warnings.append(
            f"Directory contains {len(tex_files)} .tex files. "
            "This might slow down translation."
        )

    # 检查是否缺少 .bib 文件（仅信息性，非错误）
    has_bib = any(path.rglob("*.bib"))
    if not has_bib:
        pass

    is_valid = len(errors) == 0

    logger.info(f"Validation result: valid={is_valid}, main_file={main_file}")

    return LatexValidation(
        is_valid=is_valid,
        main_file=main_file,
        tex_files=tex_file_paths,
        warnings=warnings,
        errors=errors
    )


def find_main_tex_file(path: Path) -> Optional[Path]:
    """在目录中查找主 .tex 文件的便捷函数

    参数:
        path: LaTeX 项目目录路径

    返回:
        主 .tex 文件的路径，未找到或无效时返回 None
    """
    validation = validate_latex_directory(path)
    if validation.is_valid and validation.main_file:
        return path / validation.main_file
    return None
