import json
import os
from base64 import b64decode
from pathlib import Path

os.environ.setdefault("LLM_API_KEY", "dummy-key")
os.environ.setdefault("LLM_BASE_URL", "http://dummy")
os.environ.setdefault("LLM_MODEL", "gpt-4o")

from backend.app.services import paper_preview_service


def test_generate_preview_html_writes_semantic_reader_output(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "-1",
            "content": "\\documentclass{article}",
            "trans_content": "\\documentclass{article}",
        },
        {
            "section": "1",
            "content": "\\section{Introduction}\nFirst paragraph.\n\n<PLACEHOLDER_ENV_1>",
            "trans_content": "\\section{引言}\n第一段。\n\n<PLACEHOLDER_ENV_1>",
        },
        {
            "section": "1_1",
            "content": "\\subsection{Method}\nSecond paragraph with $E=mc^2$.",
            "trans_content": "\\subsection{方法}\n第二段包含 $E=mc^2$。",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "equation",
            "content": "\\begin{equation}a=b\\end{equation}",
            "trans_content": "\\begin{equation}a=b\\end{equation}",
        }
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert result["asset_type"] == "preview_html"
    assert "<h2" in html
    assert "引言" in html
    assert "<h3" in html
    assert "方法" in html
    assert "<p>第一段。</p>" in html
    assert "\\begin{equation}a=b\\end{equation}" in html
    assert "$E=mc^2$" in html


def test_generate_preview_html_strips_structural_latex_and_renders_figures_readably(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "0+1",
            "content": "\\begin{document}\\maketitle\\section{Introduction}\\label{sec:intro}\nBody.",
            "trans_content": "\\begin{document}\\maketitle\\section{引言}\\label{sec:intro}\n第一段正文，模型记为\\PPNeSF{}。",
        },
        {
            "section": "2",
            "content": "\\section{Case Studies}\n\\begin{figure*}[!t]\n<PLACEHOLDER_CAP_1>\n\\label{fig:demo}\n\\end{figure*}",
            "trans_content": "\\section{案例研究}\n\\clearpage\n\\begin{figure*}[!t]\n<PLACEHOLDER_CAP_1>\n\\label{fig:demo}\n\\end{figure*}",
        },
    ]
    captions = [
        {
            "placeholder": "<PLACEHOLDER_CAP_1>",
            "content": "\\caption{Figure caption.}",
            "trans_content": "\\caption{图像说明文字。}",
        }
    ]
    inputs = [
        {
            "command": "\\input{macros.tex}",
            "begin": "<PLACEHOLDER_macros.tex_begin>",
            "end": "<PLACEHOLDER_macros.tex_end>",
            "path": "macros.tex",
        }
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "captions_map.json").write_text(json.dumps(captions, ensure_ascii=False), encoding="utf-8")
    (output_dir / "inputs_map.json").write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "<h2>引言</h2>" in html
    assert "第一段正文，模型记为PPNeSF。" in html
    assert "\\begin{document}" not in html
    assert "\\maketitle" not in html
    assert "\\label{sec:intro}" not in html
    assert "\\clearpage" not in html
    assert "\\begin{figure" not in html
    assert "图表内容请查看 PDF 版本" in html
    assert "图像说明文字。" in html


def test_generate_preview_html_renders_lists_tables_and_embeds_image_figures(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    source_dir = tmp_path / "source"
    (source_dir / "figures").mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    png_bytes = b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+X2ioAAAAASUVORK5CYII="
    )
    (source_dir / "figures" / "demo.png").write_bytes(png_bytes)

    sections = [
        {
            "section": "1",
            "content": "\\section{Reader}\nIntro\n<PLACEHOLDER_ENV_1>\n<PLACEHOLDER_ENV_2>\n<PLACEHOLDER_ENV_3>\n\\bibliography{refs}",
            "trans_content": "\\section{富渲染阅读}\n导语段落。\n<PLACEHOLDER_ENV_1>\n<PLACEHOLDER_ENV_2>\n<PLACEHOLDER_ENV_3>\n\\bibliography{refs}",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "itemize",
            "content": "\\begin{itemize}\\item First bullet\\item Second bullet\\end{itemize}",
            "trans_content": "\\begin{itemize}\\item 第一条要点\\item 第二条要点\\end{itemize}",
        },
        {
            "placeholder": "<PLACEHOLDER_ENV_2>",
            "env_name": "table",
            "content": "\\begin{table}\\caption{Results}\\begin{tabular}{cc}A&B\\\\1&2\\\\\\end{tabular}\\end{table}",
            "trans_content": "\\begin{table}\\caption{结果对比}\\begin{tabular}{cc}方法&得分\\\\基线&81\\\\本文&93\\\\\\end{tabular}\\end{table}",
        },
        {
            "placeholder": "<PLACEHOLDER_ENV_3>",
            "env_name": "figure",
            "content": "\\begin{figure}\\includegraphics{figures/demo.png}\\caption{Demo}\\end{figure}",
            "trans_content": "\\begin{figure}\\includegraphics{figures/demo.png}\\caption{示意图}\\end{figure}",
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir, source_dirs=[source_dir])
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "<ul" in html
    assert "<li>第一条要点</li>" in html
    assert "<table" in html
    assert "<th>方法</th>" in html
    assert "<td>本文</td>" in html
    assert "data:image/png;base64," in html
    assert "示意图" in html
    assert "\\begin{itemize}" not in html
    assert "\\bibliography{refs}" not in html


def test_generate_preview_html_emits_anchorable_math_blocks_instead_of_pre(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "2",
            "content": "\\section{Math}\n<PLACEHOLDER_ENV_1>\n<PLACEHOLDER_ENV_2>\nBody paragraph.",
            "trans_content": "\\section{数学}\n<PLACEHOLDER_ENV_1>\n<PLACEHOLDER_ENV_2>\n正文段落。",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "equation",
            "content": "\\begin{equation}a=b\\end{equation}",
            "trans_content": "\\begin{equation}a=b\\end{equation}",
        },
        {
            "placeholder": "<PLACEHOLDER_ENV_2>",
            "env_name": "algorithm",
            "content": "\\begin{algorithm}Step 1\\\\Step 2\\end{algorithm}",
            "trans_content": "\\begin{algorithm}Step 1\\\\Step 2\\end{algorithm}",
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert 'data-section-id="section-2"' in html
    assert 'data-block-id="section-2-block-0"' in html
    assert 'data-block-id="section-2-block-1"' in html
    assert 'data-block-kind="math"' in html
    assert 'data-block-kind="algorithm"' in html
    assert "<pre class=\"paper-preview__latex\">" not in html
    assert "<pre class=\"paper-preview__latex paper-preview__algorithm\">" not in html
    assert "\\begin{equation}a=b\\end{equation}" in html


def test_generate_preview_html_renders_pdf_figures_inline_when_rasterizer_succeeds(tmp_path: Path, monkeypatch):
    output_dir = tmp_path / "task-output"
    source_dir = tmp_path / "source"
    (source_dir / "figures").mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "figures" / "demo.pdf").write_bytes(b"%PDF-1.4\n%mock\n")

    sections = [
        {
            "section": "3",
            "content": "\\section{Figures}\n<PLACEHOLDER_ENV_1>",
            "trans_content": "\\section{图示}\n<PLACEHOLDER_ENV_1>",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "figure",
            "content": "\\begin{figure}\\includegraphics{figures/demo.pdf}\\caption{PDF figure}\\end{figure}",
            "trans_content": "\\begin{figure}\\includegraphics{figures/demo.pdf}\\caption{PDF 图示}\\end{figure}",
        },
    ]

    monkeypatch.setattr(
        paper_preview_service,
        "_inline_pdf_data_uri",
        lambda _path: "data:image/png;base64,ZmFrZS1wZGY=",
    )

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir, source_dirs=[source_dir])
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "data:image/png;base64,ZmFrZS1wZGY=" in html
    assert "PDF 图示" in html
    assert "图表内容请查看 PDF 版本" not in html


def test_generate_preview_html_normalizes_inline_command_examples_in_prose(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "4",
            "content": "\\section{Iteration}\nBody.",
            "trans_content": (
                "\\section{翻译-验证迭代机制}\n"
                "命令``\\texttt{\\textbackslash textbf\\{\\}}''可能被遗漏，或``"
                "\\begin{CJK}{UTF8}{gbsn}\\texttt{\\textbackslash 左}\\end{CJK}''被误译。"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "<code>\\textbf{}</code>" in html
    assert "<code>\\左</code>" in html
    assert "\\begin{CJK}" not in html
    assert "\\end{CJK}" not in html


def test_generate_preview_html_strips_spaced_citations_from_prose(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "4",
            "content": "\\section{Iteration}\nBody.",
            "trans_content": (
                "\\section{翻译-验证迭代机制}\n"
                "这可能导致个别句子的漏译或误译 \\cite {wang2025deltaonlinedocumentleveltranslation}。"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "\\cite" not in html
    assert "wang2025deltaonlinedocumentleveltranslation" not in html


def test_generate_preview_html_renders_subsection_command_blocks_readably(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "4_1",
            "content": "\\section{Deployment}\nBody.",
            "trans_content": (
                "\\section{系统部署与使用}\n"
                "\\subsection{命令行工具}\n"
                "LaTeXTrans 支持通过命令行界面进行本地部署。\n"
                "\\begin{center}\n"
                "\\ttfamily\\small LaTeXTrans --arxiv xxxx.xxxxx\n"
                "\\end{center}\n"
                "翻译完成后，系统将同时生成翻译后的 PDF 文件。\n"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "系统部署与使用" in html
    assert "<h4 class=\"paper-preview__subheading\">命令行工具</h4>" in html
    assert "LaTeXTrans --arxiv xxxx.xxxxx" in html
    assert "paper-preview__command-block" in html
    assert "\\subsection" not in html
    assert "\\begin{center}" not in html
    assert "\\ttfamily" not in html


def test_generate_preview_html_normalizes_complex_latex_tables(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "5",
            "content": "\\section{Results}\n<PLACEHOLDER_ENV_1>",
            "trans_content": "\\section{实验结果}\n<PLACEHOLDER_ENV_1>",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "table",
            "content": (
                "\\begin{table}[!t]\n"
                "\\centering\n"
                "\\resizebox{\\linewidth}{!}{\\begin{tabular}{lc*{8}{>{\\centering\\arraybackslash}p{0.05\\textwidth}}}\n"
                "[1.1pt]\n"
                "\\multirow{2}{*}{System} & \\multirow{2}{*}{Total (70)} & Mathematics (20) & Computer Science (50)\\\\\n"
                "\\cmidrule(l){3-4} \\cmidrule(l){5-6}\n"
                "A & B & A & B\\\\\n"
                "LaTeXTrans & 67 & 14 & 3 & 45 & 1\\\\\n"
                "gpt-academic & 69 & 9 & 6 & 40 & 7\\\\\n"
                "[1.1pt]\n"
                "\\end{tabular}}\n"
                "\\caption{格式保留的人工评估（英译中）。A：完美保留；B：轻微格式错误；C：严重格式损坏。}\n"
                "\\end{table}"
            ),
            "trans_content": (
                "\\begin{table}[!t]\n"
                "\\centering\n"
                "\\resizebox{\\linewidth}{!}{\\begin{tabular}{lc*{8}{>{\\centering\\arraybackslash}p{0.05\\textwidth}}}\n"
                "[1.1pt]\n"
                "\\multirow{2}{*}{System} & \\multirow{2}{*}{Total (70)} & Mathematics (20) & Computer Science (50)\\\\\n"
                "\\cmidrule(l){3-4} \\cmidrule(l){5-6}\n"
                "A & B & A & B\\\\\n"
                "LaTeXTrans & 67 & 14 & 3 & 45 & 1\\\\\n"
                "gpt-academic & 69 & 9 & 6 & 40 & 7\\\\\n"
                "[1.1pt]\n"
                "\\end{tabular}}\n"
                "\\caption{格式保留的人工评估（英译中）。A：完美保留；B：轻微格式错误；C：严重格式损坏。}\n"
                "\\end{table}"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "paper-preview__table" in html
    assert "LaTeXTrans" in html
    assert "gpt-academic" in html
    assert "[1.1pt]" not in html
    assert "\\multirow" not in html
    assert "\\resizebox" not in html


def test_generate_preview_html_linkifies_publication_urls(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "6",
            "content": "\\section{Links}\nBody.",
            "trans_content": (
                "\\section{公开资源}\n"
                "源代码[<https://github.com/NiuTrans/LaTeXTrans>]、"
                "在线演示平台[<https://latextrans.online>]及"
                "演示视频[<https://youtu.be/-ODRUTE-VU8>]均已公开。"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert 'href="https://github.com/NiuTrans/LaTeXTrans"' in html
    assert 'href="https://latextrans.online"' in html
    assert 'href="https://youtu.be/-ODRUTE-VU8"' in html
    assert 'target="_blank"' in html


def test_generate_preview_html_prefers_clean_display_math_environment(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "7",
            "content": "\\section{Loss}\n<PLACEHOLDER_ENV_1>",
            "trans_content": "\\section{损失函数}\n<PLACEHOLDER_ENV_1>",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "align",
            "content": (
                "LNCE=...\\begin{align}\n"
                "L_{NCE} = -\\frac{1}{2N} \\sum_{i=1}^N \\log \\left( \\frac{\\exp{\\left(F^{3D}_{u_i} F^{2D}_{u_i}/\\tau \\right)}^2}{A} \\right).\n"
                "\\end{align}LNCE..."
            ),
            "trans_content": (
                "LNCE=−12N∑i=1Nlog⁡(...).\\begin{align}\n"
                "L_{NCE} = -\\frac{1}{2N} \\sum_{i=1}^N \\log \\left( \\frac{\\exp{\\left(F^{3D}_{u_i} F^{2D}_{u_i}/\\tau \\right)}^2}{A} \\right) \\enspace.\n"
                "\\label{eq:Lnce}\n"
                "\\end{align}LNCE​=−2N1​i=1∑N​log(...)."
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "paper-preview__math-block" in html
    assert "\\begin{align}" in html
    assert "\\end{align}" in html
    assert "\\label{eq:Lnce}" not in html
    assert "LNCE=−12N" not in html
    assert "LNCE​=−2N1" not in html


def test_generate_preview_html_renders_paragraph_commands_as_subheadings(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "8",
            "content": "\\section{Details}\nBody.",
            "trans_content": (
                "\\section{细节}\n"
                "\\paragraph{数据集.} 我们使用三个公开基准。\n\n"
                "\\PARR{PPNeSF} 采用 ZipNeRF 架构作为背景神经隐式场。"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "<h4 class=\"paper-preview__subheading\">数据集.</h4>" in html
    assert "<h4 class=\"paper-preview__subheading\">PPNeSF</h4>" in html
    assert "\\paragraph{" not in html
    assert "\\PARR{" not in html


def test_generate_preview_html_renders_nested_subheadings_without_leaking_raw_commands(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "11",
            "content": "\\section{Experiment}\nBody.",
            "trans_content": (
                "\\section{实验}\n"
                "\\subsection{实验设置}\n"
                "\\paragraph{数据集.} 我们构建了一个包含 100 篇论文的数据集。"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "<h4 class=\"paper-preview__subheading\">实验设置</h4>" in html
    assert "<h4 class=\"paper-preview__subheading\">数据集.</h4>" in html
    assert "\\paragraph{" not in html


def test_generate_preview_html_removes_duplicate_plaintext_formula_after_math_block(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "12",
            "content": "\\section{Math}\n<PLACEHOLDER_ENV_1>\nBody.",
            "trans_content": (
                "\\section{公式}\n"
                "沿光线采样后，像素颜色计算如下：\n\n"
                "<PLACEHOLDER_ENV_1>\n\n"
                "C^ = i=1∑n T_i α_i c_i.\n\n"
                "其中 $T_i$ 表示累积透射率。"
            ),
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "align",
            "content": "\\begin{align}\\hat{C} = \\sum_{i=1}^n T_i \\alpha_i c_i.\\end{align}",
            "trans_content": "\\begin{align}\\hat{C} = \\sum_{i=1}^n T_i \\alpha_i c_i.\\end{align}",
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "paper-preview__math-block" in html
    assert "C^ = i=1∑n T_i α_i c_i." not in html
    assert "其中 $T_i$ 表示累积透射率。" in html


def test_generate_preview_html_strips_malformed_inline_math_from_captions(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    source_dir = output_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    image_path = source_dir / "segmentation.png"
    image_path.write_bytes(
        b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a6fQAAAAASUVORK5CYII=")
    )

    sections = [
        {
            "section": "13",
            "content": "\\section{Figure}\n<PLACEHOLDER_ENV_1>",
            "trans_content": "\\section{图示}\n<PLACEHOLDER_ENV_1>",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "figure",
            "content": (
                "\\begin{figure}\n"
                "\\includegraphics{segmentation.png}\n"
                "\\caption{从左至右依次为：原始图像、渲染深度图、基于图像的粗分割 $s_c^{2D}\n"
                "\\end{figure}"
            ),
            "trans_content": (
                "\\begin{figure}\n"
                "\\includegraphics{segmentation.png}\n"
                "\\caption{从左至右依次为：原始图像、渲染深度图、基于图像的粗分割 $s_c^{2D}\n"
                "\\end{figure}"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir, source_dirs=[source_dir])
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "从左至右依次为：原始图像、渲染深度图、基于图像的粗分割" in html
    assert "$s_c^{2D" not in html


def test_generate_preview_html_normalizes_dashline_sideways_and_textsubscript_markup_in_tables(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "9",
            "content": "\\section{Table}\n<PLACEHOLDER_ENV_1>",
            "trans_content": "\\section{结果表}\n<PLACEHOLDER_ENV_1>",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "table",
            "content": (
                "\\begin{table}\n"
                "\\begin{tabular}{lcc}\n"
                "\\multirow{2}*{\\begin{sideways}7S\\end{sideways}} & Qwen-3-14b & 73.48\\\\\n"
                "\\hdashline\n"
                "LaTeXTrans \\textsubscript{DeepSeek-V3} & \\bd{73.59} & 8.92\\\\\n"
                "LaTeXTrans \\textsubscript{GPT-4o} & \\underline{74.47} & 8.93\\\\\n"
                "\\end{tabular}\n"
                "\\end{table}"
            ),
            "trans_content": (
                "\\begin{table}\n"
                "\\begin{tabular}{lcc}\n"
                "\\multirow{2}*{\\begin{sideways}7S\\end{sideways}} & Qwen-3-14b & 73.48\\\\\n"
                "\\hdashline\n"
                "LaTeXTrans \\textsubscript{DeepSeek-V3} & \\bd{73.59} & 8.92\\\\\n"
                "LaTeXTrans \\textsubscript{GPT-4o} & \\underline{74.47} & 8.93\\\\\n"
                "\\end{tabular}\n"
                "\\end{table}"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "Qwen-3-14b" in html
    assert "<sub>DeepSeek-V3</sub>" in html
    assert "<sub>GPT-4o</sub>" in html
    assert "7S" in html
    assert "\\hdashline" not in html
    assert "\\begin{sideways}" not in html
    assert "\\textsubscript" not in html


def test_generate_preview_html_renders_algorithm_blocks_as_structured_steps(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "10",
            "content": "\\section{Algorithm}\n<PLACEHOLDER_ENV_1>",
            "trans_content": "\\section{算法}\n<PLACEHOLDER_ENV_1>",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "algorithm*",
            "content": (
                "\\begin{algorithm*}\n"
                "\\caption{描述 PPNeSF 训练过程的伪算法。}\n"
                "\\SetAlgoLined\n"
                "\\KwData{Set of posed training images with associated depth}\n"
                "Randomly initialize the coarse and fine prototypes.\\\\\n"
                "\\For{iteration in range(N\\_iterations)}{\n"
                "Sample a random image $I$ \\\\\n"
                "Compute feature contrastive loss $L_{NCE}$ \\\\\n"
                "}\n"
                "\\end{algorithm*}"
            ),
            "trans_content": (
                "\\begin{algorithm*}\n"
                "\\caption{描述 PPNeSF 训练过程的伪算法。}\n"
                "\\SetAlgoLined\n"
                "\\KwData{Set of posed training images with associated depth}\n"
                "Randomly initialize the coarse and fine prototypes.\\\\\n"
                "\\For{iteration in range(N\\_iterations)}{\n"
                "Sample a random image $I$ \\\\\n"
                "Compute feature contrastive loss $L_{NCE}$ \\\\\n"
                "}\n"
                "\\end{algorithm*}"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "paper-preview__algorithm" in html
    assert "paper-preview__algorithm-steps" in html
    assert "描述 PPNeSF 训练过程的伪算法。" in html
    assert "Data:" in html
    assert "For iteration in range" in html
    assert "\\KwData" not in html
    assert "\\SetAlgoLined" not in html
    assert "\\For{" not in html


def test_generate_preview_html_normalizes_metric_arrows_and_caption_command_residue(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "11",
            "content": "\\section{Results}\n<PLACEHOLDER_ENV_1>\n<PLACEHOLDER_ENV_2>",
            "trans_content": "\\section{结果}\n<PLACEHOLDER_ENV_1>\n<PLACEHOLDER_ENV_2>",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "table",
            "content": (
                "\\begin{table}\n"
                "\\begin{tabular}{lc}\n"
                "LPIPS($\\uparrow$)/ FID ($\\uparrow$) / Captions similarity ($\\downarrow$) & Value\\\\\n"
                "PPNeSF & 0.60/313/0.64\\\\\n"
                "\\end{tabular}\n"
                "\\end{table}"
            ),
            "trans_content": (
                "\\begin{table}\n"
                "\\begin{tabular}{lc}\n"
                "LPIPS($\\uparrow$)/ FID ($\\uparrow$) / Captions similarity ($\\downarrow$) & Value\\\\\n"
                "PPNeSF & 0.60/313/0.64\\\\\n"
                "\\end{tabular}\n"
                "\\end{table}"
            ),
        },
        {
            "placeholder": "<PLACEHOLDER_ENV_2>",
            "env_name": "figure",
            "content": (
                "\\begin{figure}\n"
                "\\caption{我们通过感知指标和LLaVa \\\\cite{liu2024visual}\n"
                "\\textbf{PPNeSF}}\n"
                "\\end{figure}"
            ),
            "trans_content": (
                "\\begin{figure}\n"
                "\\caption{我们通过感知指标和LLaVa \\\\cite{liu2024visual}\n"
                "\\textbf{PPNeSF}}\n"
                "\\end{figure}"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "LPIPS(↑)/ FID (↑) / Captions similarity (↓)" in html
    assert "\\uparrow" not in html
    assert "\\downarrow" not in html
    assert "\\cite{" not in html
    assert "\\textbf{" not in html
    assert "PPNeSF" in html


def test_generate_preview_html_renders_mixed_prose_and_display_math_without_latex_fallback(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "12",
            "content": (
                "\\subsubsection{Optimization}\n"
                "最终，我们获得像素级分配$v=\\argmax_k(Q)$。\n"
                "$$\\textstyle{\n"
                "p^{2D}_{k} = \\mu p^{2D}_{k} + (1-\\mu) ( \\beta \\frac{1}{|A(k)|} \\sum_{i\\in A(k)} F^{2D}_i }$$\n"
                "$$\\textstyle{+ (1 - \\beta) \\frac{1}{|A(k)|} \\sum_{i\\in A(k)} F^{3D}_i) } \\enspace , $$\n"
                "其中$\\beta$在训练过程中从0线性增至0.5。"
            ),
            "trans_content": (
                "\\subsubsection{优化}\n"
                "最终，我们获得像素级分配$v=\\argmax_k(Q)$。\n"
                "$$\\textstyle{\n"
                "p^{2D}_{k} = \\mu p^{2D}_{k} + (1-\\mu) ( \\beta \\frac{1}{|A(k)|} \\sum_{i\\in A(k)} F^{2D}_i }$$\n"
                "$$\\textstyle{+ (1 - \\beta) \\frac{1}{|A(k)|} \\sum_{i\\in A(k)} F^{3D}_i) } \\enspace , $$\n"
                "其中$\\beta$在训练过程中从0线性增至0.5。"
            ),
        },
        {
            "section": "12_1",
            "content": (
                "\\PAR{PPNeSF}\n"
                "六个结果特征根据高斯与网格单元的匹配程度重新加权$w_{j,l}$，并平均\n"
                "$$\\textstyle{f_l = \\mean_j(w_{j,l} trilerp(x_j;V_l) \\enspace ,}$$\n"
                "（$trilerp$表示三线性插值操作）。"
            ),
            "trans_content": (
                "\\PAR{PPNeSF}\n"
                "六个结果特征根据高斯与网格单元的匹配程度重新加权$w_{j,l}$，并平均\n"
                "$$\\textstyle{f_l = \\mean_j(w_{j,l} trilerp(x_j;V_l) \\enspace ,}$$\n"
                "（$trilerp$表示三线性插值操作）。"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "paper-preview__math-block" in html
    assert "最终，我们获得像素级分配" in html
    assert "其中$\\beta$在训练过程中从0线性增至0.5。" in html
    assert "\\argmax_k(Q)" in html
    assert "\\operatorname{mean}_{j}" in html
    assert "paper-preview__latex" not in html


def test_generate_preview_html_cleans_nested_figure_caption_and_bibliography_helpers(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "13",
            "content": "<PLACEHOLDER_ENV_1>\n<PLACEHOLDER_ENV_2>",
            "trans_content": "<PLACEHOLDER_ENV_1>\n<PLACEHOLDER_ENV_2>",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "figure",
            "content": "\\begin{figure}\\caption{\\textbf{\\PPNeSF{} 架构示意图。} 给定输入图像。}\\end{figure}",
            "trans_content": "\\begin{figure}\\caption{\\textbf{\\PPNeSF{} 架构示意图。} 给定输入图像。}\\end{figure}",
        },
        {
            "placeholder": "<PLACEHOLDER_ENV_2>",
            "env_name": "thebibliography",
            "content": (
                "\\begin{thebibliography}{1}\n"
                "\\bibitem{tensorrf}\n"
                "Anpei Chen, Zexiang Xu, Andreas Geiger, Jingyi Yu, and Hao Su.\n"
                "\\newblock {TensoRF: Tensorial Radiance Fields}.\n"
                "\\newblock In \\emph{{ECCV}}, 2022{\\natexlab{a}}.\n"
                "\\end{thebibliography}"
            ),
            "trans_content": (
                "\\begin{thebibliography}{1}\n"
                "\\bibitem{tensorrf}\n"
                "Anpei Chen, Zexiang Xu, Andreas Geiger, Jingyi Yu, and Hao Su.\n"
                "\\newblock {TensoRF: Tensorial Radiance Fields}.\n"
                "\\newblock In \\emph{{ECCV}}, 2022{\\natexlab{a}}.\n"
                "\\end{thebibliography}"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "PPNeSF 架构示意图。" in html
    assert "\\textbf{" not in html
    assert "\\newblock" not in html
    assert "\\natexlab" not in html
    assert "TensoRF: Tensorial Radiance Fields" in html
    assert "In ECCV, 2022a." in html


def test_generate_preview_html_keeps_inline_math_prose_as_reader_paragraphs_and_balances_subheading_titles(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "14",
            "content": (
                "\\section{Architecture}\n"
                "\\PARR{PPNeSF geometric field \\GF{}}\n"
                "This multi-sampling and weighting combination reduces spatial aliasing.\n"
                "The rendered segmentation stays readable as $s^{3D} = \\sum_{i=1}^n T_i \\alpha_i s_i^{3D}$.\n"
            ),
            "trans_content": (
                "\\section{Architecture}\n"
                "\\PARR{PPNeSF geometric field \\GF{}}\n"
                "This multi-sampling and weighting combination reduces spatial aliasing.\n"
                "The rendered segmentation stays readable as $s^{3D} = \\sum_{i=1}^n T_i \\alpha_i s_i^{3D}$.\n"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "<h4 class=\"paper-preview__subheading\">PPNeSF geometric field GF</h4>" in html
    assert "This multi-sampling and weighting combination reduces spatial aliasing." in html
    assert "The rendered segmentation stays readable as $s^{3D} = \\sum_{i=1}^n T_i \\alpha_i s_i^{3D}$." in html
    assert "paper-preview__latex" not in html


def test_generate_preview_html_normalizes_display_math_operator_macros(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "15",
            "content": (
                "\\section{Uncertainty}\n"
                "$$\\textstyle{\n"
                "s^{2D}(k|u_i) = \\softmax(\\mean_t(\\{l_i^{2D} + u_i *\\epsilon_t\\}_1^{N_S}))} \\enspace ,$$\n"
            ),
            "trans_content": (
                "\\section{Uncertainty}\n"
                "$$\\textstyle{\n"
                "s^{2D}(k|u_i) = \\softmax(\\mean_t(\\{l_i^{2D} + u_i *\\epsilon_t\\}_1^{N_S}))} \\enspace ,$$\n"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "\\operatorname{softmax}" in html
    assert "\\operatorname{mean}_{t}" in html
    assert "\\softmax" not in html
    assert "\\mean_t" not in html


def test_generate_preview_html_links_internal_cross_references_and_reference_entries(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "1",
            "content": "\\section{Intro}\\label{sec:intro}\nSee \\cref{fig:arch,sec:intro} and \\cite{tensorrf}.",
            "trans_content": "\\section{引言}\\label{sec:intro}\nSee \\cref{fig:arch,sec:intro} and \\cite{tensorrf}.",
        },
        {
            "section": "2",
            "content": "<PLACEHOLDER_ENV_1>\n<PLACEHOLDER_ENV_2>",
            "trans_content": "<PLACEHOLDER_ENV_1>\n<PLACEHOLDER_ENV_2>",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "figure",
            "content": "\\begin{figure}\\label{fig:arch}\\caption{System overview.}\\end{figure}",
            "trans_content": "\\begin{figure}\\label{fig:arch}\\caption{System overview.}\\end{figure}",
        },
        {
            "placeholder": "<PLACEHOLDER_ENV_2>",
            "env_name": "thebibliography",
            "content": (
                "\\begin{thebibliography}{1}\n"
                "\\bibitem{tensorrf}\n"
                "Anpei Chen, Zexiang Xu, Andreas Geiger, Jingyi Yu, and Hao Su.\n"
                "\\newblock {TensoRF: Tensorial Radiance Fields}.\n"
                "\\newblock In \\emph{{ECCV}}, 2022{\\natexlab{a}}.\n"
                "\\end{thebibliography}"
            ),
            "trans_content": (
                "\\begin{thebibliography}{1}\n"
                "\\bibitem{tensorrf}\n"
                "Anpei Chen, Zexiang Xu, Andreas Geiger, Jingyi Yu, and Hao Su.\n"
                "\\newblock {TensoRF: Tensorial Radiance Fields}.\n"
                "\\newblock In \\emph{{ECCV}}, 2022{\\natexlab{a}}.\n"
                "\\end{thebibliography}"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert 'href="#label-fig-arch"' in html
    assert 'href="#section-1"' in html
    assert 'href="#reference-tensorrf"' in html
    assert 'id="reference-tensorrf"' in html
    assert "\\cref{" not in html
    assert "\\cite{" not in html


def test_generate_preview_html_appends_external_reference_search_links(tmp_path: Path):
    output_dir = tmp_path / "task-output"
    output_dir.mkdir(parents=True, exist_ok=True)

    sections = [
        {
            "section": "1",
            "content": "<PLACEHOLDER_ENV_1>",
            "trans_content": "<PLACEHOLDER_ENV_1>",
        },
    ]
    envs = [
        {
            "placeholder": "<PLACEHOLDER_ENV_1>",
            "env_name": "thebibliography",
            "content": (
                "\\begin{thebibliography}{1}\n"
                "\\bibitem{tensorrf}\n"
                "Anpei Chen, Zexiang Xu, Andreas Geiger, Jingyi Yu, and Hao Su.\n"
                "\\newblock {TensoRF: Tensorial Radiance Fields}.\n"
                "\\newblock In \\emph{{ECCV}}, 2022{\\natexlab{a}}.\n"
                "\\end{thebibliography}"
            ),
            "trans_content": (
                "\\begin{thebibliography}{1}\n"
                "\\bibitem{tensorrf}\n"
                "Anpei Chen, Zexiang Xu, Andreas Geiger, Jingyi Yu, and Hao Su.\n"
                "\\newblock {TensoRF: Tensorial Radiance Fields}.\n"
                "\\newblock In \\emph{{ECCV}}, 2022{\\natexlab{a}}.\n"
                "\\end{thebibliography}"
            ),
        },
    ]

    (output_dir / "sections_map.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")
    (output_dir / "envs_map.json").write_text(json.dumps(envs, ensure_ascii=False), encoding="utf-8")

    result = paper_preview_service.generate_preview_html(output_dir)
    html = Path(result["file_path"]).read_text(encoding="utf-8")

    assert "https://scholar.google.com/scholar?q=" in html
    assert "paper-preview__reference-link" in html
