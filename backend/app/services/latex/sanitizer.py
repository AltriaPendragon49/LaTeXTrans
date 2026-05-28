"""
PDF 净化模块 —— 环境回退（图片净化器）
=============================================

提供对字节级损坏的 PDF 图片文件进行无损检测和修复的功能。
本模块专门为"翻译已发表论文"用例设计：源 PDF 是历史产物，无法在上游更改，
因此自动修复既安全又用户友好。

设计不变量
----------
* 原始文件永远不会被覆盖。
* 净化后的文件写入同目录下的 ``<原始文件名>.sanitized.pdf``。
* 所有修复操作都会被明确记录，没有任何静默操作。
* 如果未安装 Ghostscript，净化器会优雅降级（无操作）。

触发条件（调用方负责决定何时调用）
----------------------------------------------
* LaTeX 编译错误行包含：``pdf inclusion: reading image failed``
* 同时对同一文件 ``pdfinfo`` 报告语法错误。
"""

import re
import shutil
import subprocess
import sys
import logging
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# 已知会导致现代 CJK 引擎（XeLaTeX/LuaLaTeX）崩溃或降级的包。
# 这些通常是依赖 pdfTeX 专用原语的可访问性或 PDF 元数据包。
_CONFLICT_PACKAGES = {
    "axessibility": "与 XeLaTeX/LuaLaTeX 不兼容（使用 pdfTeX 原语）",
    "accsupp": "已知会导致 CJK 字符映射问题",
    "pdfcomment": "依赖 pdfTeX 专用特设命令",
}


def apply_precompile_sanitization(tex_content: str) -> Tuple[str, List[str]]:
    """第 0 阶段净化：编译前移除/注释掉不兼容的包。

    扫描 \\usepackage{...} 并与 _CONFLICT_PACKAGES 进行匹配。
    返回 (净化后的内容, 警告列表)。
    """
    warnings = []
    sanitized_lines = []

    # 匹配 \usepackage[options]{package1,package2...} 的正则表达式
    # 组 1: 可选参数 [..]
    # 组 2: 包列表
    pkg_pattern = re.compile(r"\\usepackage\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")

    for line in tex_content.splitlines():
        trimmed = line.strip()
        if not trimmed.startswith("\\usepackage"):
            sanitized_lines.append(line)
            continue

        match = pkg_pattern.search(line)
        if not match:
            sanitized_lines.append(line)
            continue

        packages = [p.strip() for p in match.group(1).split(",")]
        conflicts = [p for p in packages if p in _CONFLICT_PACKAGES]

        if conflicts:
            # 注释掉整行并添加原因说明
            reasons = "; ".join(set(_CONFLICT_PACKAGES[p] for p in conflicts))
            sanitized_line = f"% {line} % 净化处理: {reasons}"
            sanitized_lines.append(sanitized_line)
            msg = f"阶段 0 (预编译): 注释掉了不兼容的包 {conflicts}。原因: {reasons}"
            warnings.append(msg)
            logger.info(msg)
        else:
            sanitized_lines.append(line)

    return "\n".join(sanitized_lines), warnings


def _find_ghostscript() -> Optional[str]:
    """返回当前系统上可用的 Ghostscript 可执行文件名称。

    在 Windows 上，二进制文件通常是 ``gswin64c`` 或 ``gswin32c``；
    在 Linux/macOS 上，则是 ``gs``。
    如果未找到 Ghostscript 安装，返回 None。
    """
    candidates = ["gswin64c", "gswin32c", "gs"] if sys.platform == "win32" else ["gs"]
    for name in candidates:
        loc = shutil.which(name)
        if loc:
            return loc

    # Windows 特有：如果不在 PATH 中，回退到公共安装目录
    if sys.platform == "win32":
        roots = [Path("D:/apps"), Path("C:/Program Files"), Path("C:/Program Files (x86)")]
        for root in roots:
            if not root.exists():
                continue
            gs_root = root / "gs"
            if gs_root.exists() and gs_root.is_dir():
                # 查找最新版本文件夹，如 gs10.06.0
                versions = sorted(list(gs_root.glob("gs*")), reverse=True)
                for v in versions:
                    bin_dir = v / "bin"
                    if bin_dir.exists():
                        for name in ["gswin64c.exe", "gswin32c.exe"]:
                            gs_path = bin_dir / name
                            if gs_path.exists():
                                logger.info(f"通过路径回退找到 Ghostscript: {gs_path}")
                                return str(gs_path)
    return None


# 用于从 LaTeX 日志错误行中提取 "(file ...)" 的正则表达式
# 示例: ./sec/5_experiments.tex:58: error:  (file imgs/HOTA.pdf)
_PDF_INCLUSION_RE = re.compile(
    r'\(file\s+([^)]+\.pdf)\)',
    re.IGNORECASE,
)

# 用于匹配特定 PDF 词干的 LaTeX \includegraphics 路径模式
_INCLUDEGRAPHICS_RE = re.compile(
    r'(\\includegraphics(?:\[[^\]]*\])?\{)([^}]*?)(\})',
)


def extract_failed_pdf_paths(error_lines: List[str], tex_dir: Path) -> List[Path]:
    """解析编译后的 LaTeX 错误行，返回触发 PDF 包含失败的 PDF 文件绝对路径。

    匹配 ``reading image failed`` 或 ``pdf inclusion`` 作为触发短语。
    这可以处理 LaTeX 将错误文本拆分到多行日志中的情况
    （``parse_log_errors`` 中的续行合并应该将它们连接起来，
    但我们对部分匹配也保持弹性）。

    仅返回磁盘上实际存在的路径。
    """
    _TRIGGER_PHRASES = ["reading image failed", "pdf inclusion"]
    failed: List[Path] = []

    for line in error_lines:
        line_lower = line.lower()
        if not any(phrase in line_lower for phrase in _TRIGGER_PHRASES):
            continue
        match = _PDF_INCLUSION_RE.search(line)
        if match:
            rel = match.group(1).strip()
            candidate = (tex_dir / rel).resolve()
            if candidate.exists() and candidate not in failed:
                failed.append(candidate)

    return failed


def check_pdf_syntax_error(pdf_path: Path) -> bool:
    """使用 ``pdfinfo`` 检查 PDF 是否具有字节级语法错误。

    如果检测到语法错误或非法字符，返回 True。
    如果文件正常，返回 False。

    Raises:
        RuntimeError: 当 pdfinfo 不可用或无法执行时。
    """
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        combined = result.stdout + result.stderr
        return "Syntax Error" in combined or "Illegal character" in combined
    except FileNotFoundError:
        raise RuntimeError("pdfinfo 是必需的但未安装")
    except Exception as exc:
        raise RuntimeError(f"pdfinfo 检查失败 {pdf_path.name}: {exc}") from exc


def sanitize_pdf(pdf_path: Path) -> Optional[Path]:
    """使用 Ghostscript 将损坏的 PDF 蒸馏为干净的结构副本。

    原始文件永远不会被修改。净化后的副本写入同目录下的
    ``<词干>.sanitized.pdf``。

    成功时返回净化后 PDF 的路径，失败时返回 None。
    """
    sanitized_path = pdf_path.with_name(pdf_path.stem + ".sanitized.pdf")

    # 如果输出已存在则警告（幂等：我们将覆盖它）
    existed = sanitized_path.exists()

    gs_bin = _find_ghostscript()
    if gs_bin is None:
        logger.warning(
            "未找到 Ghostscript（尝试了 gs/gswin64c/gswin32c）；"
            "无法净化 %s。安装 Ghostscript 以启用自动 PDF 修复。",
            pdf_path.name,
        )
        return None

    try:
        proc = subprocess.run(
            [
                gs_bin,
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                "-dNOPAUSE",
                "-dBATCH",
                "-dQUIET",
                f"-sOutputFile={sanitized_path}",
                str(pdf_path),
            ],
            capture_output=True,
            check=True,
            timeout=60,
        )
        if sanitized_path.exists() and sanitized_path.stat().st_size > 0:
            action = "覆盖了" if existed else "创建了"
            logger.warning(
                "图片净化器: 检测到图形文件 '%s' 在字节级存在结构损坏。"
                " %s净化后的实例 '%s' 用于编译。"
                " 原始文件已保留。（使用 %s）",
                pdf_path.name,
                action,
                sanitized_path.name,
                gs_bin,
            )
            print(
                f"\n  图片净化器\n"
                f"   源 PDF:    {pdf_path}\n"
                f"   状态:       检测到字节级语法错误\n"
                f"   净化到:  {sanitized_path}\n"
                f"   原始文件: 已保留（未修改）\n"
            )
            return sanitized_path
        else:
            logger.error("Ghostscript 为 %s 生成了空/缺失的输出", pdf_path.name)
            return None

    except FileNotFoundError:
        logger.warning(
            "未找到 Ghostscript（%s）；无法净化 %s。"
            "安装 Ghostscript 以启用自动 PDF 修复。",
            gs_bin, pdf_path.name,
        )
        return None
    except subprocess.CalledProcessError as exc:
        logger.error("Ghostscript 对 %s 处理失败: %s", pdf_path.name, exc)
        if sanitized_path.exists():
            sanitized_path.unlink(missing_ok=True)
        return None
    except subprocess.TimeoutExpired:
        logger.error("Ghostscript 对 %s 处理超时", pdf_path.name)
        sanitized_path.unlink(missing_ok=True)
        return None
    except Exception as exc:
        logger.error("净化器对 %s 出现意外错误: %s", pdf_path.name, exc)
        return None


def patch_tex_includegraphics(tex_content: str, original: Path, sanitized: Path) -> Tuple[str, int]:
    """在 TeX 源代码字符串中将 ``\\includegraphics{...original.pdf...}``
    替换为净化后的文件名。

    返回 (打补丁后的内容, 替换次数)。
    """
    orig_stem = original.stem
    san_name  = sanitized.name
    orig_name = original.name
    count = 0

    def _replace(m: re.Match) -> str:
        nonlocal count
        prefix, inner, suffix = m.group(1), m.group(2), m.group(3)
        # 如果内部路径以原始文件名结尾（带或不带目录前缀）则匹配
        inner_stripped = inner.replace("\\", "/")
        if inner_stripped.endswith("/" + orig_name) or inner_stripped == orig_name:
            # 仅替换文件名部分，保留目录前缀
            dir_part = inner_stripped[: -(len(orig_name))]
            count += 1
            return prefix + dir_part.replace("/", "/") + san_name + suffix
        return m.group(0)

    patched = _INCLUDEGRAPHICS_RE.sub(_replace, tex_content)
    return patched, count


def try_sanitize_images_in_errors(
    error_lines: List[str],
    tex_dir: Path,
    already_sanitized: Optional[set] = None,
) -> Tuple[List[Path], bool, set]:
    """净化损坏的 PDF 并递归修补所有 .tex 文件。

    Args:
        error_lines: 从 LaTeX 编译日志中扫描图片错误的行。
        tex_dir: LaTeX 项目的根目录。
        already_sanitized: 在之前迭代轮次中已经修复过的 PDF 路径集合。
            此集合中的文件将被跳过 —— 每个 PDF 最多蒸馏一次。

    Returns:
        (新净化列表, 是否有新净化, 新净化集合)
        newly_sanitized_list —— 本轮产生的净化输出路径。
        any_newly_sanitized —— 如果至少有一个新 PDF 被修复则为 True。
        newly_sanitized_set —— 本轮修复的原始 PDF 路径集合
                              （将合并到调用方的累加器中）。
    """
    if already_sanitized is None:
        already_sanitized = set()

    failed_pdfs = extract_failed_pdf_paths(error_lines, tex_dir)
    if not failed_pdfs:
        return [], False, set()

    # 仅处理在之前轮次中尚未被净化的 PDF。
    new_failed_pdfs = [p for p in failed_pdfs if p not in already_sanitized]
    if not new_failed_pdfs:
        logger.info(
            "阶段 3: 所有 %d 个检测到的损坏 PDF 在之前轮次中已被净化；短路退出。",
            len(failed_pdfs),
        )
        return [], False, set()

    sanitized_list: List[Path] = []
    newly_sanitized_originals: set = set()

    # 识别哪些新 PDF 需要修补
    pdf_to_sanitized = {}
    for pdf_path in new_failed_pdfs:
        if not check_pdf_syntax_error(pdf_path):
            logger.info(
                "PDF %s 触发了读取失败但 pdfinfo 报告无语法错误；跳过净化器。",
                pdf_path.name,
            )
            continue

        san = sanitize_pdf(pdf_path)
        if san:
            pdf_to_sanitized[pdf_path] = san
            sanitized_list.append(san)
            newly_sanitized_originals.add(pdf_path)

    if not sanitized_list:
        return [], False, set()

    # 递归查找并修补项目中所有 .tex 文件
    tex_files = list(tex_dir.rglob("*.tex"))
    logger.info("阶段 3: 扫描 %d 个 .tex 文件以进行图片引用修补...", len(tex_files))

    for tex_file in tex_files:
        try:
            content = tex_file.read_text(encoding="utf-8", errors="replace")
            original_content = content
            total_patches = 0

            for pdf_path, san_path in pdf_to_sanitized.items():
                content, count = patch_tex_includegraphics(content, pdf_path, san_path)
                total_patches += count

            if total_patches > 0 and content != original_content:
                tex_file.write_text(content, encoding="utf-8")
                logger.info("阶段 3: 在 %s 中修补了 %d 个引用", total_patches, tex_file.relative_to(tex_dir))
        except Exception as e:
            logger.warning("阶段 3: 修补 %s 失败: %s", tex_file, e)

    return sanitized_list, len(sanitized_list) > 0, newly_sanitized_originals
