import { describe, expect, it } from "vitest"

import {
  getApiBaseUrl,
  getPaperPreviewApiBaseUrl,
  isTranslatedHtmlReaderEnabled,
} from "@/api-base"

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

  it("falls back to the hosted backend during browser-based local development when api base env is missing", () => {
    const previous = import.meta.env.VITE_API_BASE_URL

    import.meta.env.VITE_API_BASE_URL = ""

    try {
      expect(getApiBaseUrl()).toBe("https://api.latextrans.online")
    } finally {
      import.meta.env.VITE_API_BASE_URL = previous
    }
  })

  it("uses the dedicated paper preview api base when configured", () => {
    const previousPreviewBase = import.meta.env.VITE_PAPER_PREVIEW_API_BASE_URL

    import.meta.env.VITE_PAPER_PREVIEW_API_BASE_URL = "https://api.latextrans.online/"

    try {
      expect(getPaperPreviewApiBaseUrl()).toBe("https://api.latextrans.online")
    } finally {
      import.meta.env.VITE_PAPER_PREVIEW_API_BASE_URL = previousPreviewBase
    }
  })

  it("falls back to the main api base when no preview base is configured", () => {
    const previousApiBase = import.meta.env.VITE_API_BASE_URL
    const previousPreviewBase = import.meta.env.VITE_PAPER_PREVIEW_API_BASE_URL

    import.meta.env.VITE_API_BASE_URL = "/"
    import.meta.env.VITE_PAPER_PREVIEW_API_BASE_URL = ""

    try {
      expect(getPaperPreviewApiBaseUrl()).toBe("")
    } finally {
      import.meta.env.VITE_API_BASE_URL = previousApiBase
      import.meta.env.VITE_PAPER_PREVIEW_API_BASE_URL = previousPreviewBase
    }
  })

  it("allows disabling the translated html reader from env", () => {
    const previous = import.meta.env.VITE_ENABLE_TRANSLATED_HTML_READER

    import.meta.env.VITE_ENABLE_TRANSLATED_HTML_READER = "false"

    try {
      expect(isTranslatedHtmlReaderEnabled()).toBe(false)
    } finally {
      import.meta.env.VITE_ENABLE_TRANSLATED_HTML_READER = previous
    }
  })
})
