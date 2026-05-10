import fs from "node:fs"
import path from "node:path"

import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

import i18n from "@/i18n"
import { AppSidebar } from "@/layout/AppSidebar"

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: false,
    user: null,
  }),
}))

describe("brand surfaces", () => {
  it("uses the PaperX favicon and document title in index.html", () => {
    const indexPath = path.resolve(import.meta.dirname, "../index.html")
    const html = fs.readFileSync(indexPath, "utf8")

    expect(html).toContain('href="./paperx-mark.svg"')
    expect(html).toContain("<title>PaperX</title>")
  })

  it("shows the PaperX brand in the shared sidebar", async () => {
    await i18n.changeLanguage("en")

    render(
      <MemoryRouter initialEntries={["/"]}>
        <AppSidebar />
      </MemoryRouter>,
    )

    expect(screen.getByRole("button", { name: "PaperX" })).toBeInTheDocument()
    expect(screen.getByRole("img", { name: "PaperX" })).toBeInTheDocument()
    expect(screen.queryByText(/Powered By Niutrans/i)).not.toBeInTheDocument()
  })
})
