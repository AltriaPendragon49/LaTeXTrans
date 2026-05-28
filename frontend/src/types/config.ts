/**
 * 翻译配置类型定义
 *
 * 翻译高级配置选项的类型定义。
 * 所有配置项均为可选，用户无需任何配置即可开始翻译。
 */

/** 翻译模式选项 —— 全文翻译 / 快速筛查 */
export type TranslationMode = 'full' | 'quick_scan'

/** LaTeX 编译策略选项 */
export type CompileStrategy = 'pdflatex' | 'xelatex' | 'lualatex' | 'auto'

const viteEnv = (import.meta.env ?? {}) as Record<string, string | undefined>

/** 获取环境变量中的默认翻译模型名称 */
export const getDefaultTranslationModel = (): string => viteEnv.VITE_LLM_MODEL?.trim() || ''

/**
 * 排版格式化配置。
 * 所有字段默认为 undefined（保持原始 LaTeX 源码）。
 */
export interface FormattingConfig {
    /** 行间距倍数，如 1.5 */
    line_spacing?: number
    /** 字号（pt），如 12 */
    font_size?: number
    /** CJK 字体预设：'songti' | 'heiti' */
    cjk_font?: string
    /** 分栏模式：'single' | 'double' */
    column_mode?: string
    /** 页边距预设：'narrow' | 'normal' | 'wide' */
    margin?: string
    /** 启用 2 字符首行缩进（中文排版惯例） */
    paragraph_indent?: boolean
    /** 参考文献格式：'gbt7714-numerical' | 'gbt7714-author-year' | 'ieeetr' | 'apalike' */
    bib_style?: string
    /** 引用样式：'numbers' | 'super' | 'authoryear' */
    cite_style?: string
    /** 中文化图表标题（Figure/Table -> 图/表） */
    localize_captions?: boolean
}

/**
 * 高级翻译配置选项。
 *
 * 控制翻译行为和 API 配置。
 * 所有字段都有合理的默认值。
 */
export interface AdvancedConfig {
    /** 翻译模式：全文翻译或快速筛查（仅摘要+结论） */
    translation_mode: TranslationMode
    /** LaTeX 编译策略 */
    compile_strategy: CompileStrategy
    /** 生成术语参考表（CSV） */
    generate_terminology_table: boolean
    /** 翻译 LLM 模型名称 */
    translation_model: string
    /** 使用作者提供的 API（默认）。为 true 时忽略自定义配置 */
    use_author_api: boolean
    /** 自定义 API 基础 URL */
    custom_base_url?: string
    /** 自定义 API 密钥 */
    custom_api_key?: string
    /** 排版格式化配置（用于 LaTeX preamble 注入） */
    formatting?: FormattingConfig
    /** 任务完成或失败时发送邮件通知 */
    email_notification?: boolean
    /** 启用基于 RAG 的术语注入 */
    enable_rag_terminology?: boolean
    /** RAG 术语领域过滤 */
    rag_terminology_domain?: string
}

/**
 * 完整翻译配置，包含语言设置。
 */
export interface TranslationConfig {
    /** 源语言代码 */
    source_language: string
    /** 目标语言代码 */
    target_language: string
    /** 高级配置选项 */
    advanced_config: AdvancedConfig
}

/**
 * 默认高级配置。
 * 用户无需更改即可立即开始翻译。
 */
export const DEFAULT_ADVANCED_CONFIG: AdvancedConfig = {
    translation_mode: 'full',
    compile_strategy: 'auto',
    generate_terminology_table: true,
    translation_model: getDefaultTranslationModel(),
    use_author_api: true,
    custom_base_url: undefined,
    custom_api_key: undefined,
    email_notification: undefined,
    enable_rag_terminology: undefined,
}

/**
 * 默认翻译配置。
 */
export const DEFAULT_CONFIG: TranslationConfig = {
    source_language: 'en',
    target_language: 'zh',
    advanced_config: { ...DEFAULT_ADVANCED_CONFIG }
}

/**
 * 上传文件后返回的 LaTeX 验证结果。
 */
export interface LatexValidation {
    /** 是否为有效的 LaTeX 项目 */
    is_valid: boolean
    /** 主 tex 文件路径 */
    main_file?: string
    /** 所有 tex 文件列表 */
    tex_files: string[]
    /** 警告信息列表 */
    warnings: string[]
    /** 错误信息列表 */
    errors: string[]
}
