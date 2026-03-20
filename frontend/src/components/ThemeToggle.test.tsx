import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it } from "vitest"

import i18n from "@/i18n"
import { resetThemeMock, setThemeMock } from "@/test/theme"
import { ThemeToggle } from "@/components/ThemeToggle"

describe("ThemeToggle", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en")
    resetThemeMock("dark")
  })

  it("switches from dark mode into day mode", async () => {
    const user = userEvent.setup()

    render(<ThemeToggle />)

    await user.click(screen.getByRole("button", { name: "Switch to day mode" }))

    expect(setThemeMock).toHaveBeenCalledWith("light")
  })

  it("switches from day mode into dark mode", async () => {
    const user = userEvent.setup()
    resetThemeMock("light")

    render(<ThemeToggle />)

    await user.click(screen.getByRole("button", { name: "Switch to dark mode" }))

    expect(setThemeMock).toHaveBeenCalledWith("dark")
  })
})
