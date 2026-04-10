import { render, screen, waitFor } from "@testing-library/react"
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
    isAuthAvailable: false,
  }),
}))

describe("Layout language integration", () => {
  beforeEach(async () => {
    localStorage.clear()
    await i18n.changeLanguage("zh")
    resetThemeMock("dark")
  })

  it("updates shared layout text when the ui language changes", async () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<div>layout-test-child</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getAllByText("社区").length).toBeGreaterThan(0)
    expect(screen.getByText("登录")).toBeInTheDocument()

    await i18n.changeLanguage("en")

    await waitFor(() => {
      expect(screen.getAllByText("Community").length).toBeGreaterThan(0)
    })

    expect(screen.getByText("Sign in")).toBeInTheDocument()
    expect(screen.getByText("layout-test-child")).toBeInTheDocument()
  })
})
