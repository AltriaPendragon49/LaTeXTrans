import { render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { AuthProvider, useAuth } from "@/contexts/AuthContext"

const fetchMock = vi.fn()

vi.stubGlobal("fetch", fetchMock)

function Consumer() {
  const { loading, isAuthenticated, user, session, quotaSnapshot } = useAuth()

  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="user-id">{user?.id ?? ""}</span>
      <span data-testid="session-token">{session?.access_token ?? ""}</span>
      <span data-testid="latex-quota">
        {quotaSnapshot
          ? `${quotaSnapshot.latex_translation.remaining}/${quotaSnapshot.latex_translation.limit}`
          : ""}
      </span>
      <span data-testid="pdf-direct-quota">
        {quotaSnapshot?.pdf_direct.unused_integral ?? ""}
      </span>
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
        quota_snapshot: {
          latex_translation: {
            limit: 3,
            used: 1,
            remaining: 2,
            quota_date: "2026-05-07",
            reset_timezone: "Asia/Shanghai",
          },
          pdf_direct: {
            unused_integral: 60,
            source: "niutrans",
            status: "available",
            fetched_at: "2026-05-07T00:00:00Z",
          },
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
    expect(screen.getByTestId("latex-quota")).toHaveTextContent("2/3")
    expect(screen.getByTestId("pdf-direct-quota")).toHaveTextContent("60")

    const storedSession = JSON.parse(window.localStorage.getItem("latextrans.localAuth.session") ?? "{}")
    expect(storedSession.quota_snapshot?.latex_translation?.remaining).toBe(2)
    expect(storedSession.quota_snapshot?.pdf_direct?.unused_integral).toBe(60)
  })
})
