import { describe, expect, it } from "vitest"

import { getApiBaseUrl } from "@/api-base"

describe("api base url resolution", () => {
  it("treats root-relative production api base as same-origin", () => {
    const previous = import.meta.env.VITE_API_BASE_URL

    import.meta.env.VITE_API_BASE_URL = "/"

    try {
      expect(getApiBaseUrl()).toBe("")
    } finally {
      import.meta.env.VITE_API_BASE_URL = previous
    }
  })
})
