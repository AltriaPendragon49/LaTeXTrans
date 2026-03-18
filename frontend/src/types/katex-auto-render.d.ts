declare module "katex/contrib/auto-render" {
  interface DelimiterConfig {
    left: string
    right: string
    display: boolean
  }

  interface AutoRenderOptions {
    delimiters?: DelimiterConfig[]
    throwOnError?: boolean
  }

  export default function renderMathInElement(
    element: Element,
    options?: AutoRenderOptions,
  ): void
}
