import { beforeEach, describe, expect, it, vi } from "vitest"

const getMock = vi.fn()
const postMock = vi.fn()

vi.mock("@/lib/api", () => ({
  default: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}))

import {
  createCommunityPaperDownloadSession,
  getCommunityPapers,
} from "@/lib/community-api"

function transientAxiosError(message: string) {
  const error = new Error(message) as Error & {
    code?: string
    isAxiosError?: boolean
    response?: unknown
  }
  error.code = "ERR_NETWORK"
  error.isAxiosError = true
  error.response = undefined
  return error
}

describe("community api network retry", () => {
  beforeEach(() => {
    getMock.mockReset()
    postMock.mockReset()
  })

  it("retries the community feed request after a transient network error", async () => {
    getMock
      .mockRejectedValueOnce(transientAxiosError("socket closed"))
      .mockResolvedValueOnce({
        data: {
          items: [],
          total: 0,
          source_mode: "database",
        },
      })

    const result = await getCommunityPapers({ sort: "latest", limit: 3 })

    expect(getMock).toHaveBeenCalledTimes(2)
    expect(result.total).toBe(0)
  })

  it("retries download-session creation after a transient network error", async () => {
    postMock
      .mockRejectedValueOnce(transientAxiosError("connection closed"))
      .mockResolvedValueOnce({
        data: {
          paper_id: "paper-1",
          asset_id: "asset-1",
          download_url: "/api/papers/paper-1/download?token=abc",
          expires_at: "2026-04-12T10:17:04+00:00",
        },
      })

    const result = await createCommunityPaperDownloadSession("paper-1")

    expect(postMock).toHaveBeenCalledTimes(2)
    expect(result.asset_id).toBe("asset-1")
  })
})
