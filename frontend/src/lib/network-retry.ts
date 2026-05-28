/**
 * 网络请求重试工具
 * 检测瞬态网络错误（如 ECONNRESET、网络中断），对失败操作自动重试
 */
import axios from "axios"

/** Axios 可重试错误码集合 */
const RETRYABLE_AXIOS_CODES = new Set([
  "ECONNABORTED",
  "ECONNRESET",
  "ERR_NETWORK",
  "ETIMEDOUT",
])

/** fetch API 可重试错误消息模式 */
const RETRYABLE_FETCH_MESSAGE_PATTERNS = [
  /failed to fetch/i,
  /networkerror/i,
  /connection closed/i,
  /connection reset/i,
  /empty response/i,
  /load failed/i,
]

/**
 * 异步延迟函数
 * @param ms - 延迟毫秒数
 */
function sleep(ms: number): Promise<void> {
  if (ms <= 0) {
    return Promise.resolve()
  }
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

/**
 * 判断错误是否为可重试的瞬态网络错误
 * @param error - 捕获的错误对象
 * @returns 是否为瞬态网络错误
 */
export function isTransientNetworkError(error: unknown): boolean {
  if (axios.isAxiosError(error)) {
    // 有响应的 Axios 错误不是网络问题，不重试
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

/**
 * 在瞬态网络错误时自动重试的包装函数
 * @param operation - 需要重试的异步操作
 * @param options - 重试配置（attempts: 最大尝试次数; baseDelayMs: 基础延迟毫秒）
 * @returns 操作成功时的返回结果
 * @throws 所有重试均失败时抛出最后捕获的错误
 */
export async function retryOnTransientNetworkError<T>(
  operation: () => Promise<T>,
  options: {
    /** 最大尝试次数，默认 3 */
    attempts?: number
    /** 基础延迟（毫秒），默认 200，每次重试乘以尝试次数 */
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
      // 递增延迟：第 N 次重试等待 baseDelayMs * N 毫秒
      await sleep(baseDelayMs * attempt)
    }
  }

  throw lastError instanceof Error ? lastError : new Error("Retry failed")
}
