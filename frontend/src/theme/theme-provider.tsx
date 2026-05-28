import { ThemeProvider as NextThemesProvider, type ThemeProviderProps } from "next-themes"

/** 主题提供者组件：封装 next-themes ThemeProvider，固定为 class 策略、light 默认主题，使用自定义 localStorage key */
export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="light"
      enableSystem={false}
      disableTransitionOnChange
      storageKey="latextrans-ui-theme-v2"
      {...props}
    >
      {children}
    </NextThemesProvider>
  )
}
