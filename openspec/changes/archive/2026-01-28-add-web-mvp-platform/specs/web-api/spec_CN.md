## 添加的要求

### 要求：翻译任务启动
系统应通过 REST API 接受翻译请求并在后台异步处理它们。

#### 场景：开始翻译上传的文件
- **何时** 用户发送`POST /translate/{task_id}`对于具有上传源文件的有效任务
- **然后** 系统将任务状态更新为“正在处理”，通过“CoordinatorAgent”触发后台翻译，并返回 HTTP 202 并显示消息“翻译已开始”

#### 场景：开始翻译 arXiv 源代码
- **何时** 用户发送`POST /translate/{task_id}`对于通过 arXiv 下载创建的任务
- **那么**系统识别出主要`.tex`文件、启动翻译并相应更新任务状态

#### 场景：无效任务的翻译请求
- **何时** 用户发送不存在的任务 ID 的翻译请求
- **然后** 系统返回 HTTP 404，并显示错误“找不到任务”

#### 场景：重复的翻译请求
- **何时** 用户发送已处于“处理”或“已完成”状态的任务的翻译请求
- **然后** 系统返回 HTTP 409，并显示错误“翻译已在进行中或已完成”

### 要求：任务状态跟踪
系统应维护并公开所有翻译任务的实时状态信息。

####场景：处理过程中查询任务状态
- **何时** 用户发送`GET /task/{task_id}`当翻译正在进行时
- **然后** 系统返回 JSON 并带有 `{status: "processing",progress: <0-100>, stage: <current_stage>, message: <description>}`

####场景：查询完成任务状态（完美编译）
- **何时** 用户发送`GET /task/{task_id}`成功完成翻译且编译错误为零
- **然后** 系统返回 `{status: "completed",progress: 100, stage: "done", output_path: <path_to_pdf>}`

####场景：查询完成任务状态（有警告）
- **何时** 用户发送`GET /task/{task_id}`生成 PDF 但带有编译警告的翻译
- **然后** 系统返回 `{status: "completed_with_warnings",progress: 100, stage: "done", output_path: <path_to_pdf>, warnings: <warning_summary>}`

####场景：查询失败编译任务状态
- **何时** 用户发送`GET /task/{task_id}`翻译成功但 PDF 编译失败
- **然后** 系统返回 `{status: "failed_compilation",progress: 100, stage: "compilation_failed", error: <combined_log_errors>, source_available: true}`

####场景：查询失败任务状态（翻译错误）
- **何时** 用户发送`GET /task/{task_id}`翻译失败（编译前）
- **然后** 系统返回 `{status: "failed", error: <error_message>, stage: <failed_stage>}``

####场景：查询不存在的任务
- **何时** 用户发送`GET /task/{task_id}`对于无效的任务 ID
- **然后** 系统返回 HTTP 404，并显示错误“找不到任务”

### 要求：翻译进度报告
系统应在翻译工作流程阶段报告精细的进度更新。

####场景：AST解析阶段进度
- **何时**`ParserAgent`正在提取LaTeX结构
- **THEN** 任务进度反映 0-25%，阶段“解析”和描述当前文件的消息

####场景：LLM翻译阶段进展
- **何时**`TranslatorAgent`正在翻译文本块
- **那么** 任务进度反映了 25-80%，阶段为“翻译”并且消息显示块 N/M

####场景：LaTeX编译阶段进度
- **何时**`GeneratorAgent`正在运行 xelatex
- **那么** 任务进度反映了 80-100%，阶段为“编译”并且消息显示编译通过

#### 场景：翻译期间出错
- **何时**任何代理遇到不可恢复的错误
- **然后** 任务状态更改为“失败”，错误字段已填充，进度在故障点冻结

### 要求：API 健康监控
系统应公开健康检查端点以验证后端准备情况。

#### 场景：健康检查成功
- **何时** 用户或监控工具发送“GET /health”
- **然后** 系统返回 HTTP 200 并显示 `{status: "ok", Latex: <true|false>, timestamp: <ISO8601>}`

#### 场景：LaTeX 不可用警告
- **何时** 健康检查检测到`xelatex`在系统 PATH 上不可用
- **那么** 回复包括`latex: false`和警告消息“未检测到 LaTeX 编译器”