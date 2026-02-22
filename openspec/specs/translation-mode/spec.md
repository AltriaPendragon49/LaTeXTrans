# translation-mode Specification

## Purpose
定义系统所支持的不同翻译模式的具体行为和技术规范。该规范目前主要覆盖了系统处理整篇论文全面翻译时的所有相关执行准则，其中包括确保所有章节标题、段落正文、图表说明和列表项都被有效且结构完整地进行翻译。同时明确了翻译流程在遇到 API 超时或 LaTeX 语法异常时的错误自动修复重试机制，以确保复杂科学文献和报告经过翻译后依然能够不损失信息并顺利无报错编译输出为最终的可读 PDF 格式文件。
## Requirements
### Requirement: Full document translation only
The system SHALL translate the entire document by default. All sections, captions, and environments are translated.

#### Scenario: User translates a document
- **WHEN** user submits a LaTeX document for translation
- **THEN** all sections are translated
- **AND** all captions and environments are translated
- **AND** output PDF is compiled successfully

### Requirement: Error retry mechanism
The system SHALL retry failed translation segments using the errors_report data.

#### Scenario: Translation errors trigger retry
- **WHEN** translation has validation errors
- **AND** errors_report is not empty
- **THEN** TranslatorAgent retranslates failed parts
- **AND** retry count is limited to MAX_RETRIES (3)

