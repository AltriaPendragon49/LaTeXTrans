import { render, screen, waitFor, within } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

import i18n from "@/i18n"
import Layout from "@/layout"
import { resetThemeMock } from "@/test/theme"
import { setDesktopViewport, setMobileViewport } from "@/test/viewport"

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
    setDesktopViewport()
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
    expect(screen.getByRole("button", { name: "用户" })).toBeInTheDocument()

    await i18n.changeLanguage("en")

    await waitFor(() => {
      expect(screen.getAllByText("Community").length).toBeGreaterThan(0)
    })

    expect(screen.getByRole("button", { name: "User" })).toBeInTheDocument()
    expect(screen.getByText("layout-test-child")).toBeInTheDocument()
  })

  it("uses only the fixed four-item bottom navigation on narrow screens", async () => {
    await i18n.changeLanguage("en")
    setMobileViewport()

    const { container } = render(
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<div>mobile-layout-child</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.queryByTestId("mobile-shell-topbar")).not.toBeInTheDocument()
    expect(screen.getByTestId("mobile-bottom-nav")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Community" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Favorites" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Paper Tool" })).toBeInTheDocument()
    const accountLink = screen.getByRole("link", { name: "Settings & account" })
    expect(within(accountLink).getByRole("img", { name: "Settings & account" })).toBeInTheDocument()
    expect(container.querySelector("aside")).toBeNull()
  })
})
