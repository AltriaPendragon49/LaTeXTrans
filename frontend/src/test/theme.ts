import { vi } from "vitest"

export const setThemeMock = vi.fn()

export const themeState: {
  theme: "light" | "dark" | "system"
} = {
  theme: "light",
}

export function resetThemeMock(theme: "light" | "dark" | "system" = "light") {
  themeState.theme = theme
  setThemeMock.mockReset()
}
