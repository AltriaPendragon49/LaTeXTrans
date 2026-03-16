type Translate = (key: string, options?: Record<string, unknown>) => string

export function getTranslationModeLabel(translate: Translate, mode: string) {
  return mode === "full"
    ? translate("task.translationMode.full")
    : translate("task.translationMode.quickScan")
}

export function getCompileStrategyLabel(translate: Translate, strategy: string) {
  const strategyMap: Record<string, string> = {
    auto: translate("task.compileStrategy.auto"),
    pdflatex: "PDFLaTeX",
    xelatex: "XeLaTeX",
    lualatex: "LuaLaTeX",
  }

  return strategyMap[strategy] ?? strategy
}

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
