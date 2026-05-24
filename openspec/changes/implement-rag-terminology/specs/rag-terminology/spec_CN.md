# 规格：RAG 术语管理

## ADDED Requirements

### Requirement: 可选 RAG 术语模式
系统必须将 RAG 术语增强作为翻译工具中的显式可选能力提供，并且默认关闭。

#### Scenario: 默认翻译行为不变
- **WHEN** 翻译任务未开启 RAG 术语选项
- **THEN** 系统必须按现有默认翻译行为执行，不进行术语 RAG 检索或术语注入
- **AND** 系统不得改变默认 `origin_cli_parity` 行为。

#### Scenario: 用户开启 RAG 术语
- **WHEN** 用户在翻译工具中显式开启 RAG 术语
- **THEN** 系统必须对符合条件的翻译块执行术语检索
- **AND** 系统可以仅在本次开启的执行中将检索到的术语注入翻译提示词。

### Requirement: MySQL 术语审核存储
系统必须使用 MySQL 作为术语条目、审核状态、归属信息、来源元数据和向量同步元数据的事实来源。

#### Scenario: 术语进入审核存储
- **WHEN** 新术语对由上���、批量导入或自动抽取得到
- **THEN** 系统必须在 MySQL 中保存源术语、目标术语、语言对、领域、来源类型、状态、来源元数据、创建/审核元数据和时间戳。

#### Scenario: 不再依赖 Supabase
- **WHEN** RAG 术语服务启动或执行检索
- **THEN** 系统不得要求 Supabase 表、Supabase RPC 函数、Supabase RLS 策略或 Supabase 凭据。

#### Scenario: 来源元数据保留
- **WHEN** 术语从 CSV 导入或从 BibTeX 抽取得到
- **THEN** 系统必须在 JSON 字段中保留来源元数据（源文件、行号、引用键）
- **AND** 来源元数据须可通过术语管理 API 查看。

### Requirement: Milvus 已审核术语向量索引
当启用向量检索时，系统必须使用 Milvus 作为已审核术语 embedding 的向量检索索引。

#### Scenario: 已审核术语写入索引
- **WHEN** 管理员审核通过术语且 embedding 生成成功
- **THEN** 系统必须将术语 embedding 写入配置的 Milvus collection
- **AND** 更新 MySQL 中该术语的向量同步元数据。

#### Scenario: 待审核术语不参与向量检索
- **WHEN** 术语状态为 `pending_review` 或 `rejected`
- **THEN** 系统不得从 Milvus 向量检索中返回该术语。

### Requirement: 三阶段 RAG 流程
系统必须在提示词注入前执行查询转换、混合检索（BM25 + 向量）和 Cross-Encoder 重排这三个术语 RAG 阶段。

#### Scenario: 对开启的翻译块执行流程
- **WHEN** 某个 LaTeX 翻译块在开启 RAG 术语的情况下被翻译
- **THEN** 系统必须从该块提取纯文本或术语查询
- **AND** 通过 BM25 关键词路径和 Milvus 向量路径检索候选术语
- **AND** 使用 Cross-Encoder 模型对候选项重排后再选择注入术语。

### Requirement: BM25 关键词检索
系统必须使用 BM25 评分作为已审核术语的关键词检索路径。

#### Scenario: BM25 对查询评分
- **WHEN** 提交查询字符串进行术语检索
- **THEN** 系统必须基于已审核术语的源文本构建或刷新内存级 BM25 索引
- **AND** 使用 BM25 对每个已审核术语与查询进行评分
- **AND** 返回带有 BM25 得分的候选术语排名列表。

#### Scenario: BM25 索引在审核变更时刷新
- **WHEN** 术语被审核通过、拒绝、添加或移除
- **THEN** 系统必须在下次检索调用时或在可配置的间隔内刷新 BM25 索引。

#### Scenario: BM25 补充 MySQL 精确匹配
- **WHEN** BM25 检索和 MySQL 精确匹配同时执行
- **THEN** 系统必须按 MySQL 术语 id 合并并去重候选结果
- **AND** 对去重后的结果保留来自任一路径的较高得分。

### Requirement: Cross-Encoder 重排
系统必须使用 Cross-Encoder 模型对合并后的检索候选项进行重排，然后再进行术语注入。

#### Scenario: Cross-Encoder 对候选术语评分
- **WHEN** 合并后的关键词和向量候选项可用
- **THEN** 系统必须使用 Cross-Encoder 模型对每个 (块文本, 候选源术语) 对进行评分
- **AND** 按 Cross-Encoder 相关性得分选择 Top-N 术语。

#### Scenario: Cross-Encoder 不可用
- **WHEN** 配置的 Cross-Encoder 模型失败、不可用或未配置
- **THEN** 系统必须回退到 BM25 和向量相似度得分合并，结合优先级排序
- **AND** 继续翻译，不得使任务失败。

### Requirement: 多源知识库摄入
系统必须从多个外部来源摄入术语候选：CSV 批量导入、BibTeX 引用解析和翻译后自动抽取。

#### Scenario: CSV 术语导入
- **WHEN** 用户上传包含 source_term、target_term 和语言对的 CSV 文件
- **THEN** 系统必须验证行格式，检测 (source_term, target_term, 语言对) 的重复项
- **AND** 将有效行以 `source_type=imported` 和 `status=pending_review` 写入 MySQL
- **AND** 拒绝无效行并返回描述性错误。

#### Scenario: 基于 BibTeX 引用的术语抽取
- **WHEN** 用户上传包含引用条目的 BibTeX 文件
- **THEN** 系统必须解析引用键和条目元数据
- **AND** 使用 LLM 从引用上下文中建议源-目标术语候选
- **AND** 以 `source_type=auto_extracted` 和链接到引用的来源元数据存储候选。

#### Scenario: 翻译后自动抽取
- **WHEN** 开启 RAG 的翻译块完成且术语抽取发现源-目标术语对
- **THEN** 系统必须将这些术语对以 `pending_review` 状态写入 MySQL，并链接到翻译任务。

### Requirement: 术语优先级和冲突处理
当同一源短语存在多个冲突的已审核术语时，系统必须优先使用用户/导入术语而不是系统术语。

#### Scenario: 用户术语和系统术语冲突
- **WHEN** 同一语言对下，已审核的用户/导入术语与已审核系统术语具有相同源短语
- **THEN** 系统必须在该用户开启 RAG 的翻译中优先使用用户/导入术语。

### Requirement: 个人术语库工作区
系统必须为已认证用户提供一个专门的个人术语库工作区，用于管理自己的术语条目。

#### Scenario: 用户打开个人术语库工作区
- **WHEN** 已认证用户从工具中心打开 `/workspace/glossary`
- **THEN** 工作区必须只显示该用户自己的术语条目，位于 `My Terms` 选项卡中
- **AND** 还必须提供只读的 `Official Library` 视图，用于浏览已通过审核的系统术语。

#### Scenario: 个人术语保持用户归属
- **WHEN** 用户在个人术语库工作区上传 CSV 或 BibTeX 术语
- **THEN** 系统必须将这些行存储为带有 `owner_user_id` 的用户术语
- **AND** 只能通过该用户自己的个人术语 API 列出这些条目。

#### Scenario: 个人术语可分享审核
- **WHEN** 用户将自己的一条个人术语分享给管理员审核
- **THEN** 系统必须创建一个单独的待审核副本供管理员审核
- **AND** 原始个人术语必须继续保留在该用户的术语库中可见。

### Requirement: 术语注入
系统必须选择有界的 Top-N 术语，并且只在开启 RAG 的翻译执行中以紧凑 `<Glossary>` 块注入。

#### Scenario: 相关术语被注入
- **WHEN** Cross-Encoder 重排成功
- **THEN** 系统必须选择配置的 Top-N 相关术语
- **AND** 将它们以有界 `<Glossary>` 块加入翻译提示词。

#### Scenario: 重排不可用
- **WHEN** Cross-Encoder 重排器失败或不可用
- **THEN** 系统必须回退到 BM25 与向量得分合并并应用优先级排序
- **AND** 继续翻译，不得使任务失败。

### Requirement: 术语自动抽取和管理员审核
系统必须将所有摄入来源（CSV、BibTeX、自动抽取）的候选术语提交到同一个管理员审核工作流。

#### Scenario: 候选术语进入待审核
- **WHEN** 候选术语从任何摄入源进入系统
- **THEN** 系统必须以 `status=pending_review` 写入 MySQL
- **AND** 该术语在审核通过前不得参与检索。

#### Scenario: 管理员审核通过候选术语
- **WHEN** 管理员审核通过待审核术语
- **THEN** 系统必须将其标记为 `approved`
- **AND** 刷新该术语源语言的 BM25 索引
- **AND** 尝试生成 embedding 并写入 Milvus。

#### Scenario: 管理员拒绝候选术语
- **WHEN** 管理员拒绝待审核术语
- **THEN** 系统必须将其标记为 `rejected`
- **AND** 将其排除在 BM25 关键词检索和 Milvus 向量检索之外。

### Requirement: 术语管理 API
系统必须提供术语列表、CSV/BibTeX 上传、待审核列表、审核通过、拒绝和任务命中术语查看 API。

#### Scenario: 管理员审核需要授权
- **WHEN** 非管理员用户调用管理员审核接口
- **THEN** 系统必须以授权错误拒绝请求。

#### Scenario: CSV 和 BibTeX 上传端点
- **WHEN** 用户以 CSV 或 BibTeX 文件调用上传端点
- **THEN** 系统必须验证文件大小（可配置上限）、内容类型和格式
- **AND** 返回包含接受和拒绝行数的处理结果。

#### Scenario: 可查看命中术语
- **WHEN** 开启 RAG 的翻译任务记录了命中或注入术语
- **THEN** 系统应向有权限的客户端暴露这些术语，用于 UI 展示和评估。

### Requirement: 优雅降级
RAG 术语流程必须在失败时优雅降级，不阻塞翻译。

#### Scenario: 检索依赖失败
- **WHEN** 某个翻译块的查询转换、BM25 索引构建、embedding、Milvus 检索、MySQL 检索或 Cross-Encoder 重排失败
- **THEN** 系统必须继续翻译该块，但不注入 RAG 术语
- **AND** 记录警告或诊断事件。

### Requirement: 评估可观测性
系统必须记录足够的命中术语证据，用于毕业设计中对 baseline 与 RAG 翻译结果进行对比评估。

#### Scenario: RAG 运行记录证据
- **WHEN** 任务开启 RAG 术语运行
- **THEN** 系统必须记录被选中的术语 id、源术语、目标术语、检索来源（BM25/向量/两者）以及是否被注入
- **AND** 该记录必须可用于术语一致性评估。

### Requirement: BLEU/ROUGE 评估
系统必须提供评估脚本，计算 baseline（无 RAG）和 RAG 翻译输出的 BLEU 和 ROUGE 得分。

#### Scenario: 评估脚本对比配对输出
- **WHEN** 评估脚本对同一篇源论文的 baseline 和 RAG 翻译结果运行
- **THEN** 系统必须计算句子级和文档级的 BLEU 和 ROUGE 得分
- **AND** 报告每个指标的差值（RAG - baseline）。

#### Scenario: 术语一致性度量
- **WHEN** 评估脚本对配对输出运行
- **THEN** 系统必须计算术语一致性得分：预定义关键术语在输出中所有出现位置翻译一致的比例
- **AND** 报告每个术语的一致率和总体一致率。

### Requirement: 评估产物
系统必须导出适用于毕业设计论文报告的评估产物。

#### Scenario: 生成评估报告
- **WHEN** 评估在测试数据集上完成
- **THEN** 系统必须生成包含 BLEU、ROUGE 和术语一致性得分的结构化报告（JSON 或 CSV）
- **AND** 包含 RAG 运行的命中术语日志以支持定性分析。
