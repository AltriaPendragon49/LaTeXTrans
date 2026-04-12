import { beforeEach, describe, expect, it, vi } from "vitest"

import { onRequest } from "./[[path]]"

const fetchMock = vi.fn()

vi.stubGlobal("fetch", fetchMock)

describe("pages api proxy", () => {
  beforeEach(() => {
    fetchMock.mockReset()
  })

  it("forwards api requests to the configured origin", async () => {
    fetchMock.mockResolvedValueOnce(new Response("ok", { status: 200 }))

    const response = await onRequest({
      env: {},
      request: new Request("https://latextrans.niutrans.com/api/health?full=1"),
    } as never)

    expect(fetchMock).toHaveBeenCalledTimes(1)

    const proxiedRequest = fetchMock.mock.calls[0]?.[0] as Request
    expect(proxiedRequest.url).toBe("https://allocation-fighting-allowed-workshops.trycloudflare.com/api/health?full=1")
    expect(response.status).toBe(200)
  })
})
