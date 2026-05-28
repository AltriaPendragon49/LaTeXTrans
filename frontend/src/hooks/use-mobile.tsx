/**
 * useIsMobile — 响应式移动端检测 Hook
 * 监听窗口宽度变化，返回当前是否为移动端（宽度 < 768px）
 */
import * as React from "react"

const MOBILE_BREAKPOINT = 768

/**
 * 判断当前视口是否为移动端尺寸
 * @returns 当前宽度 < 768px 返回 true
 */
export function useIsMobile() {
  const [isMobile, setIsMobile] = React.useState(() =>
    typeof window === "undefined" ? false : window.innerWidth < MOBILE_BREAKPOINT,
  )

  React.useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`)
    const onChange = () => {
      setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    }
    mql.addEventListener("change", onChange)
    setIsMobile(window.innerWidth < MOBILE_BREAKPOINT)
    return () => mql.removeEventListener("change", onChange)
  }, [])

  return isMobile
}
