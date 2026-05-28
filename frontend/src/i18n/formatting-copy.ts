/**
 * 格式化选项文案翻译工具
 * 将翻译模式、编译策略和排版格式化等枚举值转换为国际化文案
 */

type Translate = (key: string, options?: Record<string, unknown>) => string

/**
 * 获取翻译模式的国际化标签
 * @param translate - i18n 翻译函数
 * @param mode - 模式值（"full" / 其他）
 */
export function getTranslationModeLabel(translate: Translate, mode: string) {
  return mode === "full"
    ? translate("task.translationMode.full")
    : translate("task.translationMode.quickScan")
}

/**
 * 获取编译策略的国际化标签
 * @param translate - i18n 翻译函数
 * @param strategy - 策略值（auto / pdflatex / xelatex / lualatex）
 */
export function getCompileStrategyLabel(translate: Translate, strategy: string) {
  const strategyMap: Record<string, string> = {
    auto: translate("task.compileStrategy.auto"),
    pdflatex: "PDFLaTeX",
    xelatex: "XeLaTeX",
    lualatex: "LuaLaTeX",
  }

  return strategyMap[strategy] ?? strategy
}

/**
 * 获取排版格式化选项值的国际化标签
 * @param translate - i18n 翻译函数
 * @param type - 格式化类型（column_mode / margin / cjk_font / cite_style）
 * @param value - 值
 */
export function getFormattingValueLabel(
  translate: Translate,
  type: "column_mode" | "margin" | "cjk_font" | "cite_style",
  value: string,
) {
  const dictionary: Record<string, Record<string, string>> = {
    column_mode: {
      single: translate("formatting.column.single"),
      double: translate("formatting.column.double"),
    },
    margin: {
      narrow: translate("formatting.margin.narrowShort"),
      normal: translate("formatting.margin.standardShort"),
      wide: translate("formatting.margin.wideShort"),
    },
    cjk_font: {
      songti: translate("formatting.font.songti"),
      heiti: translate("formatting.font.heiti"),
    },
    cite_style: {
      numbers: translate("formatting.citationStyle.numericShort"),
      super: translate("formatting.citationStyle.superscript"),
      authoryear: translate("formatting.citationStyle.authorYearShort"),
    },
  }

  return dictionary[type][value] ?? value
}
