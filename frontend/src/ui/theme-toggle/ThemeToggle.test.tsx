import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { ThemeToggle } from "@/ui/theme-toggle/ThemeToggle"

const setTheme = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("next-themes", () => ({
  useTheme: () => ({
    theme: "light",
    setTheme,
  }),
}))

describe("ThemeToggle", () => {
  it("renders the light mode label", () => {
    render(<ThemeToggle />)

    expect(screen.getByRole("button", { name: "theme.toggle.switchToDark" })).toHaveTextContent("theme.mode.light")
  })

  it("switches to dark mode when clicked", async () => {
    const user = userEvent.setup()

    render(<ThemeToggle />)

    await user.click(screen.getByRole("button", { name: "theme.toggle.switchToDark" }))

    expect(setTheme).toHaveBeenCalledWith("dark")
  })
})
