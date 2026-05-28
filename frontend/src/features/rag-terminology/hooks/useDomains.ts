import { useCallback, useEffect, useState } from "react"
import type { DomainInfo, DomainsResponse } from "@/features/rag-terminology/types"
import { listDomains } from "@/features/rag-terminology/services/rag-terminology-api"

/** 内存缓存：避免重复请求 */
let cachedDomains: DomainsResponse | null = null

/** useDomains 返回值接口 */
interface UseDomainsResult {
  domains: DomainInfo[]
  groups: Record<string, { label_zh: string; members: string[] }>
  isLoading: boolean
  error: string | null
  reload: () => void
}

/**
 * 获取可用术语领域的 Hook
 * 调用 GET /terminology/domains，结果缓存到内存中。
 * 使用 reload() 可强制刷新缓存
 */
export function useDomains(): UseDomainsResult {
  const [domains, setDomains] = useState<DomainInfo[]>(cachedDomains?.domains ?? [])
  const [groups, setGroups] = useState<Record<string, { label_zh: string; members: string[] }>>(cachedDomains?.groups ?? {})
  const [isLoading, setIsLoading] = useState(!cachedDomains)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async (force = false) => {
    if (!force && cachedDomains) {
      setDomains(cachedDomains.domains)
      setGroups(cachedDomains.groups)
      setIsLoading(false)
      return
    }
    setIsLoading(true)
    setError(null)
    try {
      const response: DomainsResponse = await listDomains()
      cachedDomains = response
      setDomains(response.domains)
      setGroups(response.groups)
    } catch {
      setError("Failed to load domains")
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch()
  }, [fetch])

  const reload = useCallback(() => fetch(true), [fetch])

  return { domains, groups, isLoading, error, reload }
}
