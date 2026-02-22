## Context

LaTexTrans 目前的 `add_cjk_package()` 函数已实现"在 `\documentclass` 后注入宏包"的成熟模式。新的排版配置注入将完全复用这一 **锚点定位 + 正则替换/插入** 的技术模式。使用 TexLive 2025，所有宏包（包括 `gbt7714`、中文字体等）均已可用。

### 关键集成要求
排版配置必须**完全复用现有的配置系统链路**：
1. **系统设置存储**：保存到 `user_settings` 表，通过 `GET/PUT /api/settings` 读写
2. **翻译时覆盖**：前端 Advanced Settings 中可覆盖系统默认值
3. **配置签名**：纳入 `config_hash` 以支持 output reuse
4. **历史快照**：`FormattingConfig` 嵌套在 `AdvancedConfig` 中，自动随 `advanced_config` JSONB 字段写入 `translation_tasks` 表

## Goals / Non-Goals

### Goals
- 用户可配置：行距（自定义数值）、字号（自定义数值）、字体、单双栏互转、页边距、首行缩进、参考文献格式、引文风格、标题本地化
- 配置默认值全部为"保持原样"，不影响现有行为
- 完全复用现有的 settings → advanced_config → agent_config → config_hash → 历史快照 链路

### Non-Goals
- 不实现完整模板替换（如套用学校学位论文 `.cls` 模板），属于 Phase 2
- 不修改翻译正文内容，仅修改导言区宏包和配置指令

## Decisions

### Decision 1: FormattingConfig 嵌套在 AdvancedConfig 中

**选择**：`AdvancedConfig.formatting: Optional[FormattingConfig] = None`

**理由**：
- 自动享有 `advanced_config` 的全部已有能力：配置传递、DB 快照、config_hash
- `None` 默认值确保完全向后兼容

### Decision 2: 行距和字号使用自定义数值输入

**选择**：`line_spacing` 和 `font_size` 字段为 `Optional[float]`，前端使用"启用按钮 + 数字输入框"交互。

**理由**：用户反馈要求灵活输入而非预设选项。例如 `line_spacing=1.5`、`font_size=12`。

### Decision 3: 栏模式支持双向切换

**选择**：`column_mode` 支持 `"single"` 和 `"double"`，而非仅"强制单栏"。

**理由**：用户明确要求双向切换能力。

### Decision 4: 注入时机

**选择**：`GeneratorAgent` 编译前，`add_cjk_package()` 之后执行 `apply_formatting_config()`。**（针对中文字体配置，通过新增的 `_inject_after_cjk_package` 准确定位到 `\usepackage{ctex}` 或 `xeCJK` 之后进行注入，以解决 `\setCJKmainfont` 不能在宏包加载前执行导致字体变纯文本的 Bug。）**

### Decision 5: 配置持久化与加载链路

与现有配置完全一致，外加针对 `translation_tasks` 历史记录表的针对性优化：

```
用户设置页 (Settings)
  → PUT /api/settings { default_formatting: {...} }
  → Supabase user_settings 表

Dashboard 初始化
  → GET /api/settings → 读取 default_formatting
  → 填充 FormattingPanel 初始值

翻译提交
  → TranslateRequest.advanced_config.formatting = 当前面板状态
  → run_translation() → agent_config → GeneratorAgent
  → apply_formatting_config() 注入到 .tex
  → advanced_config JSONB 整体保存
  → 同时独立提取 formatting 保存至 translation_tasks 新增的 formatting JSONB 列中，以便对外提供强类型的历史快照查询
  → formatting 纳入 config_hash (output reuse)
```

## FormattingConfig 字段设计

```python
class FormattingConfig(BaseModel):
    # 行距: None=保持, 数值如 1.5, 2.0
    line_spacing: Optional[float] = None
    
    # 全局字号: None=保持, 数值如 10, 11, 12(单位pt)
    font_size: Optional[float] = None
    
    # 中文字体: None=保持, "songti", "heiti"
    cjk_font: Optional[str] = None
    
    # 栏模式: None=保持, "single", "double"
    column_mode: Optional[str] = None
    
    # 页边距: None=保持, "narrow", "normal", "wide"
    margin: Optional[str] = None
    
    # 首行缩进: None=保持, True=启用2em缩进
    paragraph_indent: Optional[bool] = None
    
    # 参考文献格式: None=保持, "gbt7714-numerical", "gbt7714-author-year", "ieeetr", "apalike"
    bib_style: Optional[str] = None
    
    # 引文标记风格: None=保持, "numbers", "super", "authoryear"
    cite_style: Optional[str] = None
    
    # 图表标题本地化: None=保持, True=启用
    localize_captions: Optional[bool] = None
```

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 注入的宏包与原文档冲突 | 注入前检查是否已存在相同宏包，存在则替换参数 |
| `\documentclass` 字号替换正则不匹配特殊格式 | 对常见 class 做充分测试 |
| 中文字体在 Docker 中不可用 | TexLive 2025 自带 Fandol 字体作为回退 |
