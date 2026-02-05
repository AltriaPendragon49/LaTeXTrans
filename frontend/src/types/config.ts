/**
 * Translation Configuration Types
 * 
 * Type definitions for advanced translation configuration.
 * All configuration options are optional - users can translate without configuring anything.
 */

/** Translation mode options - 只保留全文翻译和快速筛查 */
export type TranslationMode = 'full' | 'quick_scan'

/** LaTeX compile strategy options */
export type CompileStrategy = 'pdflatex' | 'xelatex' | 'lualatex' | 'auto'

/**
 * Advanced configuration options.
 * 
 * These options control translation behavior and API configuration.
 * All fields have sensible defaults.
 */
export interface AdvancedConfig {
    /** Translation mode: full document or quick_scan (abstract + conclusion only) */
    translation_mode: TranslationMode
    /** LaTeX compile strategy */
    compile_strategy: CompileStrategy
    /** Enable dual-model verification for quality */
    enable_verification: boolean
    /** Generate terminology reference table (CSV) */
    generate_terminology_table: boolean
    /** Translation LLM model name */
    translation_model: string
    /** Use author's API (default). When true, custom settings are ignored */
    use_author_api: boolean
    /** Custom API base URL (e.g., https://aicanapi.com) */
    custom_base_url?: string
    /** Custom API key */
    custom_api_key?: string
}

/**
 * Complete translation configuration including language settings.
 */
export interface TranslationConfig {
    /** Source language code */
    source_language: string
    /** Target language code */
    target_language: string
    /** Advanced configuration options */
    advanced_config: AdvancedConfig
}

/**
 * Default advanced configuration.
 * Users can start translating immediately without changing these.
 */
export const DEFAULT_ADVANCED_CONFIG: AdvancedConfig = {
    translation_mode: 'full',
    compile_strategy: 'auto',
    enable_verification: true,
    generate_terminology_table: true,  // 默认启用术语表生成
    translation_model: 'gpt-4.1-mini',
    use_author_api: true,
    custom_base_url: undefined,
    custom_api_key: undefined
}

/**
 * Default translation configuration.
 */
export const DEFAULT_CONFIG: TranslationConfig = {
    source_language: 'en',
    target_language: 'zh',
    advanced_config: { ...DEFAULT_ADVANCED_CONFIG }
}

/**
 * LaTeX validation result from upload.
 */
export interface LatexValidation {
    is_valid: boolean
    main_file?: string
    tex_files: string[]
    warnings: string[]
    errors: string[]
}
