# drag-drop-upload Specification

## Purpose
TBD - created by archiving change add-multi-user-support. Update Purpose after archive.
## Requirements
### Requirement: Drag and Drop Upload
前端 SHALL 支持用户通过拖拽方式上传本地 LaTeX 源文件夹。

#### Scenario: 拖拽文件夹到上传区域
- **WHEN** 用户将包含 LaTeX 源文件的文件夹拖拽到 Dashboard 上传区域
- **THEN** 系统显示文件夹预览信息（文件数量、主要 .tex 文件）
- **AND** 高亮显示上传区域

#### Scenario: 释放文件夹完成上传
- **WHEN** 用户释放拖拽的文件夹
- **THEN** 系统将文件夹内容打包上传到后端
- **AND** 显示上传进度
- **AND** 上传完成后自动触发翻译流程

#### Scenario: 拖拽单个 .tex 文件
- **WHEN** 用户拖拽单个 .tex 文件
- **THEN** 系统接受文件并上传
- **AND** 显示上传进度

#### Scenario: 拖拽多个文件
- **WHEN** 用户同时拖拽多个 .tex 文件或 .zip 压缩包
- **THEN** 系统接受文件并打包上传

### Requirement: Upload Zone UI
前端 SHALL 在 Dashboard 页面提供明显的拖拽上传区域。

#### Scenario: 显示拖拽区域
- **WHEN** 用户访问 Dashboard 页面
- **THEN** ArXiv ID 输入框下方显示拖拽上传区域
- **AND** 区域包含 "拖拽文件夹或 .tex 文件到此处" 提示

#### Scenario: 拖拽进入状态
- **WHEN** 用户拖拽文件进入上传区域
- **THEN** 上传区域边框变为高亮颜色
- **AND** 显示 "释放以上传" 提示

#### Scenario: 拖拽离开状态
- **WHEN** 用户拖拽文件离开上传区域
- **THEN** 上传区域恢复默认样式

### Requirement: Language Selection for Upload
上传本地文件时 SHALL 支持选择源语言和目标语言。

#### Scenario: 上传前选择语言
- **WHEN** 用户在上传区域准备上传文件
- **THEN** 系统使用 Dashboard 页面已选择的语言配置

#### Scenario: 使用默认语言
- **WHEN** 用户未显式选择语言就上传文件
- **THEN** 系统使用用户设置中的默认语言

