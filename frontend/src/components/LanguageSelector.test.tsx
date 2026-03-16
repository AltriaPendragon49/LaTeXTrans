import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it } from "vitest"

import i18n from "@/i18n"
import { UI_LANGUAGE_STORAGE_KEY } from "@/i18n/config"
import { LanguageSelector } from "@/components/LanguageSelector"

describe("LanguageSelector", () => {
  beforeEach(async () => {
    localStorage.clear()
    await i18n.changeLanguage("zh")
  })

  it("renders eight languages and persists the selection", async () => {
    const user = userEvent.setup()

    render(<LanguageSelector />)

    const trigger = screen.getByRole("combobox", { name: "选择全局界面语言" })
    trigger.focus()
    fireEvent.keyDown(trigger, { key: "ArrowDown" })

    const listbox = await screen.findByRole("listbox")
    expect(within(listbox).getAllByRole("option")).toHaveLength(8)

    await user.click(within(listbox).getByRole("option", { name: /English/i }))

    await waitFor(() => {
      expect(i18n.resolvedLanguage).toBe("en")
    })

    expect(localStorage.getItem(UI_LANGUAGE_STORAGE_KEY)).toBe("en")
  })
})
