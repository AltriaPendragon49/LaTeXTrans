import { render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { AuthProvider, useAuth } from "@/contexts/AuthContext"

const fetchMock = vi.fn()

vi.stubGlobal("fetch", fetchMock)

function Consumer() {
  const { loading, isAuthenticated, user, session } = useAuth()

  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="user-id">{user?.id ?? ""}</span>
      <span data-testid="session-token">{session?.access_token ?? ""}</span>
    </div>
  )
}

function Wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>
}

describe("AuthProvider local auth bootstrap", () => {
  beforeEach(() => {
    fetchMock.mockReset()
    window.localStorage.clear()
  })

  it("hydrates the current user from a stored local access token", async () => {
    window.localStorage.setItem(
      "latextrans.localAuth.session",
      JSON.stringify({
        access_token: "stored-token",
        token_type: "Bearer",
        expires_in: 28800,
        user: {
          id: "usr_local_1",
          external_provider: "niutrans",
          external_user_id: "179017",
          roles: ["user"],
          display_name: "Local User",
        },
      }),
    )

    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        user: {
          id: "usr_local_1",
          external_provider: "niutrans",
          external_user_id: "179017",
          roles: ["user"],
          display_name: "Local User",
        },
      }),
    })

    render(<Consumer />, { wrapper: Wrapper })

    await waitFor(() => {
      expect(screen.getByTestId("loading")).toHaveTextContent("false")
    })

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/me"),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer stored-token",
        }),
      }),
    )
    expect(screen.getByTestId("authenticated")).toHaveTextContent("true")
    expect(screen.getByTestId("user-id")).toHaveTextContent("usr_local_1")
    expect(screen.getByTestId("session-token")).toHaveTextContent("stored-token")
  })
})
