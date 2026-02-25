## ADDED Requirements

### Requirement: Preamble Formatting Injection
系统 SHALL 在翻译完成、PDF 编译之前，根据用户的排版配置对 LaTeX 导言区执行自动化注入和修改。

#### Scenario: 行距配置注入
- **WHEN** 用户配置 `formatting.line_spacing` 为一个数值（如 `1.5`）
- **THEN** 系统在 `\begin{document}` 前注入 `\usepackage{setspace}` 和 `\setstretch{1.5}`
- **AND** 若 `setspace` 已存在则仅修改行距数值

#### Scenario: 全局字号替换
- **WHEN** 用户配置 `formatting.font_size` 为一个数值（如 `12`）
- **THEN** 系统通过正则将 `\documentclass` 中的字号选项替换为 `12pt`
- **AND** 若原 `\documentclass` 无字号选项则追加

#### Scenario: 栏模式切换 - 双栏转单栏
- **WHEN** 用户配置 `formatting.column_mode = "single"`
- **THEN** 系统移除 `\documentclass` 中的 `twocolumn` 选项
- **AND** 在 `\begin{document}` 后注入 `\onecolumn`

#### Scenario: 栏模式切换 - 单栏转双栏
- **WHEN** 用户配置 `formatting.column_mode = "double"`
- **THEN** 系统在 `\documentclass` 选项中添加 `twocolumn`
- **AND** 在 `\begin{document}` 后注入 `\twocolumn`

#### Scenario: 页边距配置
- **WHEN** 用户配置 `formatting.margin` 为 `"narrow"` / `"normal"` / `"wide"`
- **THEN** 系统注入 `\usepackage[margin=X]{geometry}`
- **AND** 若 `geometry` 已存在则替换其 margin 参数

#### Scenario: 中文首行缩进
- **WHEN** 用户配置 `formatting.paragraph_indent = true`
- **THEN** 系统注入 `\setlength{\parindent}{2em}`

#### Scenario: CJK 字体覆盖
- **WHEN** 用户配置 `formatting.cjk_font = "songti"` 或 `"heiti"`
- **AND** 目标语言为中文 (zh/ch)
- **THEN** 系统注入对应的 `\setCJKmainfont{...}` 命令

#### Scenario: 参考文献格式替换
- **WHEN** 用户配置 `formatting.bib_style` 为非 null 值
- **THEN** 系统查找现有 `\bibliographystyle{...}` 并替换为指定格式
- **AND** 若不存在 `\bibliographystyle` 则不注入

#### Scenario: 引文标记风格配置
- **WHEN** 用户配置 `formatting.cite_style = "super"`
- **THEN** 系统注入 `\usepackage[numbers,sort&compress]{natbib}` 并定义上标引用宏

#### Scenario: 图表标题本地化
- **WHEN** 用户配置 `formatting.localize_captions = true`
- **AND** 目标语言为中文
- **THEN** 系统注入 `\renewcommand{\figurename}{图}` 和 `\renewcommand{\tablename}{表}`

#### Scenario: 默认不注入
- **WHEN** `formatting` 配置为 `null` 或所有字段均为 null
- **THEN** 系统不修改 LaTeX 导言区
- **AND** 翻译行为与升级前完全一致

#### Scenario: 宏包冲突检测
- **WHEN** 注入的宏包在原文档中已存在
- **THEN** 系统替换其参数而非重复添加

## MODIFIED Requirements

### Requirement: Language-Specific Font and Package Injection
The system SHALL dynamically configure LaTeX packages and fonts based on the selected target translation language to ensure accurate PDF rendering, 并在语言级注入完成后执行用户定义的排版配置注入。

#### Scenario: Chinese document compilation
- **WHEN** the target language is `zh` or `ch`
- **THEN** the system injects the `ctex` package with UTF-8 encoding
- **AND** comments out pdfLaTeX-specific primitive commands
- **AND** subsequently applies `FormattingConfig` if provided

#### Scenario: Japanese or Korean document compilation
- **WHEN** the target language is `ja` or `ko`
- **THEN** the system injects the `xeCJK` package and explicitly configures its fonts (`UnBatang` for Korean, `IPAexMincho` for Japanese) regardless of `xeCJK`'s prior presence in the document
- **AND** comments out pdfLaTeX-specific primitive commands
- **AND** subsequently applies `FormattingConfig` if provided

#### Scenario: Cyrillic document compilation
- **WHEN** the target language uses Cyrillic script (`ru`, `uk`, `bg`, `sr`, `mk`, `be`)
- **THEN** the system injects `fontspec` and configures it to use the `CMU Serif` font
- **AND** comments out conflicting pdfLaTeX-specific encoding packages (e.g., `fontenc[T1]`, `inputenc[utf8]`, `times`) and primitive commands
- **AND** subsequently applies `FormattingConfig` if provided

#### Scenario: Latin-extended document compilation
- **WHEN** the target language uses extended Latin script (`de`, `fr`, `es`, etc.)
- **THEN** the system preserves native pdfLaTeX encoding packages (`fontenc`, `inputenc`)
- **AND** exclusively comments out pdfLaTeX-specific primitive commands to safely allow `XeLaTeX` fallback compilation
- **AND** subsequently applies `FormattingConfig` if provided
