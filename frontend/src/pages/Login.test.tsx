import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import i18n from "@/i18n"
import LoginPage from "@/pages/login"

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

  it("submits a phone number identifier without blocking on email-only validation", async () => {
    const signIn = vi.fn().mockResolvedValue({ error: null })
    const clearError = vi.fn()
    const user = userEvent.setup()

    useAuthMock.mockReturnValue({
      signIn,
      error: null,
      clearError,
      loading: false,
    })

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText("Email or phone number"), "15043413070")
    await user.type(screen.getByLabelText("Password"), "secret")
    await user.click(screen.getByRole("button", { name: "Sign in" }))

    expect(clearError).toHaveBeenCalled()
    expect(signIn).toHaveBeenCalledWith("15043413070", "secret")
    expect(screen.queryByText("Enter a valid email address")).not.toBeInTheDocument()
  })
})
