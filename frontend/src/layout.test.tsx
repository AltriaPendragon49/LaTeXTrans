import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import i18n from "@/i18n"
import Layout from "@/layout"
import { resetThemeMock } from "@/test/theme"

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    loading: false,
    isSupabaseAvailable: false,
  }),
}))

describe("Layout language integration", () => {
  beforeEach(async () => {
    localStorage.clear()
    await i18n.changeLanguage("zh")
    resetThemeMock("dark")
  })

  it("updates shared layout text when the ui language changes", async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<Layout />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText(i18n.t("layout.guestMode"))).toBeInTheDocument()
    expect(screen.getByText(i18n.t("layout.menu"))).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: i18n.t("theme.toggle.switchToLight") }),
    ).toBeInTheDocument()

    const trigger = screen.getByRole("combobox", {
      name: i18n.t("common.choose_global_interface_language"),
    })
    trigger.focus()
    fireEvent.keyDown(trigger, { key: "ArrowDown" })

    const listbox = await screen.findByRole("listbox")
    await user.click(within(listbox).getByRole("option", { name: /English/i }))

    await waitFor(() => {
      expect(screen.getByText("Guest mode")).toBeInTheDocument()
    })

    expect(screen.getByText("Menu")).toBeInTheDocument()
    expect(screen.getByText("Community Feed")).toBeInTheDocument()
  })
})
