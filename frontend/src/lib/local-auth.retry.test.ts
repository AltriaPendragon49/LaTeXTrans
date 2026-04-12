import { beforeEach, describe, expect, it, vi } from "vitest"

import { clearStoredSession, getStoredSession, signInWithPassword } from "@/lib/local-auth"

const fetchMock = vi.fn()

vi.stubGlobal("fetch", fetchMock)

describe("local auth network retry", () => {
  beforeEach(() => {
    fetchMock.mockReset()
    window.localStorage.clear()
  })

  it("retries sign-in once after a transient network failure", async () => {
    fetchMock
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          access_token: "token-1",
          token_type: "Bearer",
          expires_in: 28800,
          user: {
            id: "usr_local_1",
            external_provider: "niutrans",
            external_user_id: "179017",
            roles: ["admin"],
          },
        }),
      })

    const result = await signInWithPassword("1593120349@qq.com", "secret")

    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(result.error).toBeNull()
    expect(result.session?.access_token).toBe("token-1")
    expect(getStoredSession()?.access_token).toBe("token-1")

    clearStoredSession()
  })
})
