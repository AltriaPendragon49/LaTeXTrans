## 修改要求

### 要求：LaTeX 解析和翻译
系统应将 LaTeX 源文件解析为抽象语法树（AST），在保留结构的同时翻译提取的文本内容，并重建有效的 LaTeX 输出。

#### 场景：CLI 翻译工作流程（现有）
- **何时** 用户运行 `python main.py --arxiv 2508.18791`
- **然后**系统下载源代码，使用解析LaTeX`pylatexenc`, translates text chunks via LLM, reconstructs `.tex`文件，并编译 PDF`outputs/`目录

#### 场景：Web API 翻译工作流程（新）
- **何时** 后端调用`CoordinatorAgent.workflow_latextrans()`来自 FastAPI 后台任务
- **然后**系统执行相同的解析→翻译→编译管道，通过回调更新任务进度，并将输出写入`data/outputs/{task_id}/`

####场景：进度回调集成（新）
- **何时**`ParserAgent`, `TranslatorAgent`, or `GeneratorAgent`完成一个处理步骤
- **然后** 每个代理调用`on_progress(stage, percentage, message)`回调更新`TaskManager`状态

#### 场景：无 Streamlit 操作（新）
- **何时** 任何代理在没有 Streamlit 上下文（Web 环境）的情况下运行
- **那么**系统使用Python`logging`用于输出的模块，不调用 `st.progress()`、`st.text()` 或 `st.spinner()`

#### 场景：错误传播到 Web 层（新）
- **何时** 由于 LaTeX 解析错误、LLM 超时或编译错误而导致翻译失败
- **然后** 代理引发带有描述性消息的异常，该异常由后台任务处理程序捕获并存储在`TaskManager`错误字段

### 要求：arXiv 源码下载
给定有效的论文 ID，系统应从 arXiv.org 下载 LaTeX 源代码。

#### 场景：CLI arXiv 下载（现有）
- **何时** 用户提供`--arxiv`CLI 的参数
- **然后**`batch_download_arxiv_tex()`下载`.tar.gz`来源至`tex source/`目录

#### 场景：Web API arXiv 下载（新）
- **何时** 后端接收`POST /arxiv`使用 arXiv ID 进行请求
- **然后** 改编`batch_download_arxiv_tex()`将源下载到`data/uploads/{task_id}/`并将任务 ID 返回给调用者

####场景：arXiv元数据提取（现有）
- **何时** 从 arXiv 下载
- **然后**系统通过以下方式提取论文类别（例如“cs.AI”）`get_arxiv_category()`用于潜在术语选择（MVP 中未使用，第 2 阶段使用）

### 要求：具有智能回退功能的 LaTeX 编译
系统应使用具有自动引擎回退和基于错误的输出选择的多阶段编译策略将翻译后的 LaTeX 文件编译为 PDF。

#### 场景：主要 pdflatex 编译尝试
- **何时**`GeneratorAgent.execute()`被翻译后调用`.tex`文件
- **那么**系统首先尝试使用`pdflatex`通过`subprocess`, captures the `.log`文件，并记录退出代码和错误计数

#### 场景：在 pdflatex 失败时回退到 xelatex
- **何时** pdflatex 编译失败（非零退出代码）
- **那么**系统会自动尝试使用以下命令进行编译`xelatex`通过`subprocess`, captures the `.log`文件，并记录退出代码和错误计数

####场景：完美编译（零错误）
- **何时** pdflatex 或 xelatex 生成的 PDF 中的错误为零`.log`文件
- **然后** 系统立即返回该 PDF 作为最终输出，并将任务状态标记为“已完成”

#### 场景：单次成功编译但有错误
- **何时** pdflatex 生成 PDF（退出代码 0），但`.log`文件包含错误
- **然后** 系统尝试 xelatex 编译，比较错误计数，并选择错误较少的 PDF

#### 场景：从不完美的编译中选择最佳输出
- **何时** pdflatex 和 xelatex 都生成 PDF，但两者都有错误`.log`文件
- **然后** 系统比较错误计数并选择错误较少的 PDF，将任务状态标记为“completed_with_warnings”

#### 场景：部分输出偏好
- **当**一个编译器生成 PDF（即使有错误）而另一个编译器无法生成任何输出时
- **那么** 无论错误计数如何，系统都会返回可用的 PDF

#### 场景：编译完全失败并保留源代码
- **何时** pdflatex 和 xelatex 均无法生成任何 PDF 输出
- **那么**系统保留翻译后的内容`.tex`源文件，将任务状态标记为“failed_compilation”，存储来自两者的组合错误详细信息`.log`任务错误字段中的文件，并使源文件可供通过下载`/download/{task_id}/source`终点

####场景：错误日志解析进行比较
-**何时**解析`.log`计算错误的文件
- **然后** 系统对与 LaTeX 错误模式匹配的行进行计数（例如，`!LaTeX Error`、`!未定义的控制序列`、`!Missing`）

#### 场景：MiKTeX 自动安装要求（现有约束）
- **何时**编译遇到缺少 LaTeX 包的情况
- **然后** 系统依赖 MiKTeX 的“即时安装”功能来自动下载 pdflatex 和 xelatex 的软件包（需要在主机上配置 MiKTeX 以获得 MVP；Docker 隔离推迟到第 3 阶段）