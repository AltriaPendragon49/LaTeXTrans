import type { ReactNode } from "react"
import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { Outlet } from "react-router-dom"

import i18n from "@/i18n"
import App from "@/App"

vi.mock("@/contexts/AuthContext", () => ({
  AuthProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

vi.mock("@/pages/CommunityFeed", () => ({
  default: () => <div>Community feed page</div>,
}))

vi.mock("@/pages/Dashboard", () => ({
  default: () => <div>Dashboard page</div>,
}))

vi.mock("@/pages/PaperDetail", () => ({
  default: () => <div>Paper detail page</div>,
}))

vi.mock("@/pages/Processing", () => ({
  default: () => <div>Processing page</div>,
}))

vi.mock("@/pages/Comparisons", () => ({
  default: () => <div>Comparisons page</div>,
}))

vi.mock("@/pages/Login", () => ({
  default: () => <div>Login page</div>,
}))

vi.mock("@/pages/History", () => ({
  default: () => <div>History page</div>,
}))

vi.mock("@/pages/Settings", () => ({
  default: () => <div>Settings page</div>,
}))

vi.mock("@/pages/Profile", () => ({
  default: () => <div>Profile page</div>,
}))

vi.mock("@/layout", () => ({
  default: () => (
    <div>
      <span>Layout shell</span>
      <Outlet />
    </div>
  ),
}))

describe("App community routing", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en")
  })

  it("routes the homepage to the community feed", async () => {
    window.history.pushState({}, "", "/")

    render(<App />)

    expect(await screen.findByText("Community feed page")).toBeInTheDocument()
  })

  it("keeps the translation workspace on /translate", async () => {
    window.history.pushState({}, "", "/translate")

    render(<App />)

    expect(await screen.findByText("Dashboard page")).toBeInTheDocument()
  })
})
