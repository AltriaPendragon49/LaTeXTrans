import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { LanguageSelector } from "@/ui/language-selector/LanguageSelector"

const changeLanguage = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      language: "en",
      resolvedLanguage: "en",
      changeLanguage,
    },
  }),
}))

describe("LanguageSelector", () => {
  beforeEach(() => {
    changeLanguage.mockReset()
  })

  it("renders the current language label", () => {
    render(<LanguageSelector />)

    expect(screen.getByRole("combobox", { name: "common.choose_global_interface_language" })).toBeInTheDocument()
    expect(screen.getByText("English")).toBeInTheDocument()
  })

  it("changes the language when a new option is chosen", async () => {
    const user = userEvent.setup()

    render(<LanguageSelector />)

    await user.click(screen.getByRole("combobox", { name: "common.choose_global_interface_language" }))
    await user.click(screen.getByRole("option", { name: "中文" }))

    expect(changeLanguage).toHaveBeenCalledWith("zh")
  })
})
