# folder-upload Specification Delta

## Purpose
支持用户拖拽本地 LaTeX 工程目录或压缩包进行翻译。

## ADDED Requirements

### Requirement: Drag and Drop Upload Zone
前端 SHALL 在新建翻译页面提供拖拽上传区域。

#### Scenario: 显示拖拽区域
- **WHEN** 用户访问新建翻译页面
- **THEN** 页面显示明显的拖拽区域
- **AND** 区域包含 "拖拽 LaTeX 文件夹或 ZIP 文件到此处" 提示

#### Scenario: 拖拽文件进入
- **WHEN** 用户将文件拖拽进入上传区域
- **THEN** 区域边框变为高亮颜色
- **AND** 显示 "释放以上传" 提示

#### Scenario: 拖拽文件离开
- **WHEN** 用户将文件拖拽离开上传区域
- **THEN** 区域恢复默认样式

#### Scenario: 释放文件
- **WHEN** 用户在上传区域释放拖拽的文件
- **THEN** 系统显示文件信息预览
- **AND** 显示文件/文件夹名称、文件数量
- **AND** 显示是否检测到 .tex 文件

### Requirement: Folder Upload Support
后端 SHALL 支持接收 LaTeX 工程目录上传，并支持多种压缩格式。

#### Scenario: 上传 ZIP 文件
- **WHEN** 用户上传 ZIP 压缩的 LaTeX 工程
- **THEN** 后端使用 zipfile 解压到临时目录
- **AND** 对解压后的目录进行校验

#### Scenario: 上传 TAR.GZ 文件
- **WHEN** 用户上传 .tar.gz 或 .tgz 格式的 LaTeX 工程
- **THEN** 后端使用 tarfile 解压到临时目录
- **AND** 对解压后的目录进行校验

#### Scenario: 上传 RAR 文件
- **WHEN** 用户上传 .rar 格式的 LaTeX 工程
- **THEN** 后端使用 rarfile 库解压到临时目录
- **AND** 对解压后的目录进行校验
- **IF** 服务器未安装 unrar 或 rarfile
- **THEN** 返回错误 "RAR 格式不受支持，请使用 ZIP 或 TAR.GZ"

#### Scenario: 上传多个文件
- **WHEN** 用户一次性拖拽多个文件
- **THEN** 后端将文件保存到同一任务目录
- **AND** 进行统一校验

### Requirement: LaTeX Directory Validation
后端 SHALL 在创建翻译任务前校验 LaTeX 目录。

#### Scenario: 检测 .tex 文件
- **WHEN** 后端接收到上传的目录
- **THEN** 系统检测目录中是否存在 .tex 文件
- **IF** 不存在 .tex 文件
- **THEN** 返回错误 "未检测到 LaTeX 文件"

#### Scenario: 检测主入口文件
- **WHEN** 目录包含 .tex 文件
- **THEN** 系统检测主入口文件
- **AND** 优先识别 main.tex 或包含 `\documentclass` 的文件
- **IF** 未找到明确主入口
- **THEN** 使用第一个 .tex 文件并返回警告

#### Scenario: 校验通过
- **WHEN** 目录校验通过
- **THEN** 返回校验结果（主入口文件路径、.tex 文件列表）
- **AND** 允许创建翻译任务

### Requirement: Unified Source Type
任务记录 SHALL 区分不同的翻译输入源类型。

#### Scenario: 标记目录上传来源
- **WHEN** 用户通过拖拽上传创建任务
- **THEN** 任务记录 source_type = "folder_upload"
- **AND** 记录包含校验结果信息

#### Scenario: 保持与其他来源兼容
- **WHEN** 任务通过 folder_upload 创建
- **THEN** 后续翻译流程与 arxiv/upload 类型一致
- **AND** 使用相同的翻译 pipeline

### Requirement: Upload Does Not Auto-Trigger Translation
拖拽上传 SHALL NOT 自动触发翻译，需用户确认。

#### Scenario: 拖拽后等待确认
- **WHEN** 用户完成拖拽上传
- **THEN** 系统仅显示文件预览
- **AND** 用户可调整高级配置
- **AND** 点击 "开始翻译" 后才创建任务

## Cross-References
- 关联: file-management (文件上传 API)
- 关联: advanced-config (配置选项)
- 关联: web-ui (Dashboard 页面)
