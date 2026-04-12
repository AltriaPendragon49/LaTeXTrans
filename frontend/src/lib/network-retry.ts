import axios from "axios"

const RETRYABLE_AXIOS_CODES = new Set([
  "ECONNABORTED",
  "ECONNRESET",
  "ERR_NETWORK",
  "ETIMEDOUT",
])

const RETRYABLE_FETCH_MESSAGE_PATTERNS = [
  /failed to fetch/i,
  /networkerror/i,
  /connection closed/i,
  /connection reset/i,
  /empty response/i,
  /load failed/i,
]

function sleep(ms: number): Promise<void> {
  if (ms <= 0) {
    return Promise.resolve()
  }
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

export function isTransientNetworkError(error: unknown): boolean {
  if (axios.isAxiosError(error)) {
    if (error.response) {
      return false
    }
    return RETRYABLE_AXIOS_CODES.has(String(error.code || "").toUpperCase())
  }

  if (error instanceof TypeError) {
    return RETRYABLE_FETCH_MESSAGE_PATTERNS.some((pattern) => pattern.test(error.message))
  }

  if (error instanceof Error) {
    const code = String((error as Error & { code?: string }).code || "").toUpperCase()
    if (RETRYABLE_AXIOS_CODES.has(code)) {
      return true
    }
    return RETRYABLE_FETCH_MESSAGE_PATTERNS.some((pattern) => pattern.test(error.message))
  }

  return false
}

export async function retryOnTransientNetworkError<T>(
  operation: () => Promise<T>,
  options: {
    attempts?: number
    baseDelayMs?: number
  } = {},
): Promise<T> {
  const attempts = Math.max(1, options.attempts ?? 3)
  const baseDelayMs = Math.max(0, options.baseDelayMs ?? 200)

  let lastError: unknown
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await operation()
    } catch (error) {
      lastError = error
      if (attempt >= attempts || !isTransientNetworkError(error)) {
        throw error
      }
      await sleep(baseDelayMs * attempt)
    }
  }

  throw lastError instanceof Error ? lastError : new Error("Retry failed")
}
