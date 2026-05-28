import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2, Search, XCircle } from "lucide-react"

import { Button } from "@/ui/button/Button"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { StatusBadge } from "@/ui/status-badge/StatusBadge"
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHeader,
  DataTableHeaderCell,
  DataTableHeaderRow,
  DataTableRow,
} from "@/ui/data-table/DataTable"

import type { MatchLogEntry } from "@/features/rag-terminology/types"
import { getMatchLogs } from "@/features/rag-terminology/services/rag-terminology-api"

/** 术语匹配日志组件 Props */
interface TerminologyMatchLogProps {
  /** 翻译任务 ID */
  taskId: string
  /** 可选的初始数据（用于 SSR 或预取场景） */
  initialData?: MatchLogEntry[]
}

/**
 * 术语匹配日志组件
 * 展示翻译任务中 RAG 术语检索的匹配日志，包括源术语、目标术语、
 * 所在 chunk 索引、检索来源、是否注入和重排序分数。
 * 调用 GET /terminology/tasks/{taskId}/matches
 */
export function TerminologyMatchLog({ taskId, initialData }: TerminologyMatchLogProps) {
  const { t } = useTranslation()
  const [logs, setLogs] = useState<MatchLogEntry[]>(initialData ?? [])
  const [isLoading, setIsLoading] = useState(!initialData)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (initialData) {
      return
    }

    let cancelled = false

    async function fetchLogs() {
      setIsLoading(true)
      setError(null)
      try {
        const data = await getMatchLogs(taskId)
        if (!cancelled) {
          setLogs(data)
        }
      } catch {
        if (!cancelled) {
          setError(t("ragTerminology.matchLog.error"))
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    fetchLogs()

    return () => {
      cancelled = true
    }
  }, [taskId, initialData, t])

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-14 text-[color:var(--px-shell-muted)]">
        <Loader2 className="h-6 w-6 animate-spin" />
        <p className="mt-3 text-sm">{t("ragTerminology.matchLog.loading")}</p>
      </div>
    )
  }

  if (error) {
    return (
      <NoticeBanner
        tone="danger"
        icon={<XCircle className="h-4 w-4" />}
        description={error}
        action={
          <Button variant="ghost" size="sm" onClick={() => window.location.reload()}>
            {t("common.actions.retry")}
          </Button>
        }
      />
    )
  }

  if (logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-14 text-[color:var(--px-shell-muted)]">
        <Search className="h-7 w-7" />
        <p className="mt-3 text-sm">{t("ragTerminology.matchLog.empty")}</p>
      </div>
    )
  }

  return (
    <DataTable>
      <DataTableHeader>
        <DataTableHeaderRow className="grid-cols-[1fr_1fr_80px_1fr_80px_80px]">
          <DataTableHeaderCell>
            {t("ragTerminology.matchLog.table.sourceTerm")}
          </DataTableHeaderCell>
          <DataTableHeaderCell>
            {t("ragTerminology.matchLog.table.targetTerm")}
          </DataTableHeaderCell>
          <DataTableHeaderCell>
            {t("ragTerminology.matchLog.table.chunkIndex")}
          </DataTableHeaderCell>
          <DataTableHeaderCell>
            {t("ragTerminology.matchLog.table.retrievalSource")}
          </DataTableHeaderCell>
          <DataTableHeaderCell className="text-center">
            {t("ragTerminology.matchLog.table.wasInjected")}
          </DataTableHeaderCell>
          <DataTableHeaderCell className="text-right">
            {t("ragTerminology.matchLog.table.rerankScore")}
          </DataTableHeaderCell>
        </DataTableHeaderRow>
      </DataTableHeader>

      <DataTableBody>
        {logs.map((entry) => (
          <DataTableRow
            key={entry.id}
            className="grid-cols-[1fr_1fr_80px_1fr_80px_80px] items-center"
          >
            <DataTableCell className="truncate font-medium text-[color:var(--px-shell-ink)]">
              {entry.source_term}
            </DataTableCell>
            <DataTableCell className="truncate text-[color:var(--px-shell-muted)]">
              {entry.target_term}
            </DataTableCell>
            <DataTableCell className="text-sm text-[color:var(--px-shell-muted)]">
              #{entry.chunk_index}
            </DataTableCell>
            <DataTableCell className="truncate text-sm text-[color:var(--px-shell-muted)]">
              {entry.retrieval_source}
            </DataTableCell>
            <DataTableCell className="flex justify-center">
              <StatusBadge
                tone={entry.was_injected ? "success" : "muted"}
                size="sm"
              >
                {entry.was_injected
                  ? t("ragTerminology.matchLog.injected")
                  : t("ragTerminology.matchLog.notInjected")}
              </StatusBadge>
            </DataTableCell>
            <DataTableCell className="text-right text-sm font-mono text-[color:var(--px-shell-muted)]">
              {entry.rerank_score != null ? entry.rerank_score.toFixed(3) : "-"}
            </DataTableCell>
          </DataTableRow>
        ))}
      </DataTableBody>
    </DataTable>
  )
}
