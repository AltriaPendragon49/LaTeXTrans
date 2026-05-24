import { useCallback, useEffect, useState } from "react"
import type { DomainInfo, DomainsResponse } from "@/features/rag-terminology/types"
import { listDomains } from "@/features/rag-terminology/services/rag-terminology-api"

interface UseDomainsResult {
  domains: DomainInfo[]
  groups: Record<string, { label_zh: string; members: string[] }>
  isLoading: boolean
  error: string | null
  reload: () => void
}

/**
 * Custom hook to fetch available terminology domains from the API.
 * Results are cached in memory; call `reload` to force a refresh.
 */
export function useDomains(): UseDomainsResult {
  const [domains, setDomains] = useState<DomainInfo[]>([])
  const [groups, setGroups] = useState<Record<string, { label_zh: string; members: string[] }>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response: DomainsResponse = await listDomains()
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

  return { domains, groups, isLoading, error, reload: fetch }
}
