import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import i18n from "@/i18n"
import Layout from "@/layout"

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

    expect(screen.getByText("访客模式")).toBeInTheDocument()
    expect(screen.getByText("菜单")).toBeInTheDocument()

    const trigger = screen.getByRole("combobox", { name: "选择全局界面语言" })
    trigger.focus()
    fireEvent.keyDown(trigger, { key: "ArrowDown" })

    const listbox = await screen.findByRole("listbox")
    await user.click(within(listbox).getByRole("option", { name: /English/i }))

    await waitFor(() => {
      expect(screen.getByText("Guest mode")).toBeInTheDocument()
    })

    expect(screen.getByText("Menu")).toBeInTheDocument()
    expect(screen.getByText("LaTeX Translation Platform")).toBeInTheDocument()
  })
})
