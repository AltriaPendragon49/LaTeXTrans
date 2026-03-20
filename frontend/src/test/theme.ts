import { vi } from "vitest"

export const setThemeMock = vi.fn()

export const themeState: {
  theme: "light" | "dark" | "system"
} = {
  theme: "dark",
}

export function resetThemeMock(theme: "light" | "dark" | "system" = "dark") {
  themeState.theme = theme
  setThemeMock.mockReset()
}
