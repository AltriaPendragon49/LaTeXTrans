## ADDED Requirements

### Requirement: Formatting Configuration Panel
前端 SHALL 在 Advanced Settings 面板中提供"排版与文献设置"折叠区，允许用户配置翻译后 PDF 的排版格式。

#### Scenario: 展开排版配置面板
- **WHEN** 用户在 Advanced Settings 中点击"排版与文献设置"折叠项
- **THEN** 系统显示排版配置表单，包含以下选项组：
  - 版面设置：行距、字号、栏模式、页边距
  - 中文排版：字体、首行缩进（仅中文目标语言时显示）
  - 文献引用：参考文献格式、引文标记风格
  - 其他：图表标题本地化

#### Scenario: 行距和字号使用启用按钮与数字输入
- **WHEN** 用户查看行距或字号配置项
- **THEN** 显示为一个启用/禁用按钮
- **AND** 启用后出现数字输入框，用户填入纯数字（如行距 `1.5`，字号 `12`）
- **AND** 禁用时恢复为"保持原样"

#### Scenario: 栏模式支持双向切换
- **WHEN** 用户查看栏模式配置项
- **THEN** 显示下拉选项：保持原样 / 单栏 / 双栏

#### Scenario: 配置默认为"保持原样"
- **WHEN** 用户首次打开排版配置面板
- **THEN** 所有选项默认值为"保持原样"
- **AND** 若用户系统设置中有 `default_formatting` 则使用其值填充

#### Scenario: 目标语言联动显示
- **WHEN** 用户选择的目标语言为中文 (zh/ch)
- **THEN** 显示"中文字体"和"首行缩进"选项
- **AND** "图表标题本地化"选项可用

#### Scenario: 排版配置随翻译请求提交
- **WHEN** 用户修改排版配置并点击翻译按钮
- **THEN** 排版配置序列化为 `advanced_config.formatting` JSON 字段
- **AND** 随翻译请求一同提交到后端 API

#### Scenario: 排版配置在批量翻译中共享
- **WHEN** 用户切换到 Batch Tab
- **THEN** 排版配置面板仍然可见且配置对批量任务统一生效
