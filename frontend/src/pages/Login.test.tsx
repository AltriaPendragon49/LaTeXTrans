import { render, screen } from "@testing-library/react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import LoginPage from "@/pages/Login"

const useAuthMock = vi.fn()

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => useAuthMock(),
}))

describe("LoginPage", () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await i18n.changeLanguage("en")
  })

  it("shows the backend auth error instead of flattening it into a generic failure message", () => {
    useAuthMock.mockReturnValue({
      signIn: vi.fn(),
      error: "NiuTrans did not accept these credentials.",
      clearError: vi.fn(),
      loading: false,
    })

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText("NiuTrans did not accept these credentials.")).toBeInTheDocument()
    expect(screen.queryByText("Unable to complete authentication. Please try again.")).not.toBeInTheDocument()
  })
})
