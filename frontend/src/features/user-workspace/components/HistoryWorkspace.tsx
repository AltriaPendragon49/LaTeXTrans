import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/ui/button/Button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/ui/primitives/collapsible'
import { Loader2, FileText, RefreshCw, Settings2, Languages, Wrench, Sparkles, CheckCircle2, XCircle, Trash2, Eye, AlertTriangle } from 'lucide-react'
import { toast } from 'sonner'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/ui/primitives/alert-dialog'
import { Checkbox } from '@/ui/primitives/checkbox'
import { deleteTask, deleteTasksBatch } from '@/lib/api'
import { API_BASE_URL } from '@/api-base'
import { useTranslation } from 'react-i18next'
import { useTranslationTask } from '@/features/translation-workflow/hooks/useTranslationTask'
import { useIsMobile } from '@/hooks/use-mobile'
import { getCompileStrategyLabel, getFormattingValueLabel, getTaskStatusLabel, getTranslationModeLabel } from '@/i18n/ui-text'
import { getAccessToken } from '@/lib/local-auth'
import { LoginPrompt } from '@/features/auth-shell/components/LoginPrompt'
import { PageIntro } from '@/ui/page-intro/PageIntro'
import { StatePanel } from '@/ui/state-panel/StatePanel'
import { NoticeBanner } from '@/ui/notice-banner/NoticeBanner'
import { InfoTile } from '@/ui/info-tile/InfoTile'
import { StatusBadge } from '@/ui/status-badge/StatusBadge'
import { LoadingState } from '@/ui/loading-state/LoadingState'
import { Pill } from '@/ui/pill/Pill'
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHeader,
  DataTableHeaderCell,
  DataTableHeaderRow,
  DataTableRow,
} from '@/ui/data-table/DataTable'

interface TaskHistoryItem {
  task_id: string
  source_type: string
  arxiv_id?: string
  translation_mode: string
  status: string
  progress: number
  created_at: string
  completed_at?: string
  source_language: string
  target_language: string
  compile_strategy: string
  translation_model?: string
  generate_glossary: boolean
  use_author_api: boolean
  formatting?: Record<string, unknown> | null
}

interface HistoryResponse {
  tasks: TaskHistoryItem[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

const statusTones: Record<string, "warning" | "info" | "success" | "danger"> = {
  pending: 'warning',
  processing: 'info',
  completed: 'success',
  completed_with_warnings: 'success',
  failed: 'danger',
  failed_compilation: 'danger',
  structure_invalid: 'danger',
}

const TERMINAL_FAIL_STATUSES = new Set(['failed', 'failed_compilation', 'structure_invalid'])

export function HistoryWorkspace() {
  const navigate = useNavigate()
  const { isAuthenticated, loading: authLoading, session } = useAuth()
  const { setTaskId, setArxivId } = useTranslationTask()
  const { t, i18n } = useTranslation()
  const isMobile = useIsMobile()

  const [tasks, setTasks] = useState<TaskHistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [total, setTotal] = useState(0)
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set())

  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [taskToDelete, setTaskToDelete] = useState<string | null>(null)

  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedTasks, setSelectedTasks] = useState<Set<string>>(new Set())
  const retryTimeoutRef = useRef<number | null>(null)

  const HISTORY_RETRY_DELAY_MS = 1000
  const MAX_HISTORY_RETRIES = 2

  const clearScheduledRetry = useCallback(() => {
    if (retryTimeoutRef.current !== null) {
      window.clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
  }, [])

  const toggleExpand = (taskId: string, event: React.MouseEvent) => {
    event.stopPropagation()
    setExpandedTasks((prev) => {
      const next = new Set(prev)
      if (next.has(taskId)) {
        next.delete(taskId)
      } else {
        next.add(taskId)
      }
      return next
    })
  }

  const fetchHistory = useCallback(async (pageNum: number, append = false, attempt = 0) => {
    clearScheduledRetry()
    setLoading(true)
    if (attempt === 0) {
      setError(null)
    }

    try {
      const token = session?.access_token ?? await getAccessToken()
      if (!token) {
        if (attempt < MAX_HISTORY_RETRIES) {
          retryTimeoutRef.current = window.setTimeout(() => {
            void fetchHistory(pageNum, append, attempt + 1)
          }, HISTORY_RETRY_DELAY_MS)
          return
        }
        throw new Error(t('history.failed_to_load_history'))
      }

      const response = await fetch(`${API_BASE_URL}/api/history?page=${pageNum}&page_size=10`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        if ((response.status >= 500 || response.status === 401) && attempt < MAX_HISTORY_RETRIES) {
          retryTimeoutRef.current = window.setTimeout(() => {
            void fetchHistory(pageNum, append, attempt + 1)
          }, HISTORY_RETRY_DELAY_MS)
          return
        }
        throw new Error(t('history.failed_to_load_history'))
      }

      const data: HistoryResponse = await response.json()

      if (append) {
        setTasks((prev) => [...prev, ...data.tasks])
      } else {
        setTasks(data.tasks)
      }
      setHasMore(data.has_more)
      setTotal(data.total)
      setPage(pageNum)
    } catch (err) {
      if (attempt < MAX_HISTORY_RETRIES) {
        retryTimeoutRef.current = window.setTimeout(() => {
          void fetchHistory(pageNum, append, attempt + 1)
        }, HISTORY_RETRY_DELAY_MS)
        return
      }
      setError(err instanceof Error ? err.message : t('history.failed_to_load_history'))
    } finally {
      if (retryTimeoutRef.current === null) {
        setLoading(false)
      }
    }
  }, [clearScheduledRetry, session?.access_token, t])

  const loadMore = () => {
    if (!loading && hasMore) {
      void fetchHistory(page + 1, true)
    }
  }

  useEffect(() => {
    if (isAuthenticated) {
      void fetchHistory(1)
    }
    return clearScheduledRetry
  }, [clearScheduledRetry, fetchHistory, isAuthenticated])

  const handleDeleteClick = (taskId: string, event: React.MouseEvent) => {
    event.stopPropagation()
    setTaskToDelete(taskId)
    setDeleteDialogOpen(true)
  }

  const confirmDelete = async () => {
    if (!taskToDelete) return

    const deletingId = taskToDelete
    setDeleteDialogOpen(false)
    setTaskToDelete(null)

    const toastId = toast.loading(t('history.deleting_task'))

    try {
      await deleteTask(deletingId)
      setTasks((prev) => prev.filter((task) => task.task_id !== deletingId))
      setTotal((prev) => prev - 1)
      setSelectedTasks((prev) => {
        const next = new Set(prev)
        next.delete(deletingId)
        return next
      })
      toast.success(t('history.task_deleted'), { id: toastId })
    } catch {
      toast.error(t('history.delete_failed_please_try_again'), { id: toastId })
    }
  }

  const handleBatchDelete = async () => {
    if (selectedTasks.size === 0) return

    const deletingIds = Array.from(selectedTasks)
    const count = deletingIds.length

    setSelectedTasks(new Set())
    setSelectionMode(false)

    const toastId = toast.loading(t('history.deleting_tasks', { count }))

    try {
      const result = await deleteTasksBatch(deletingIds)
      const successCount = result.results.filter((item) => item.success).length
      const successIds = new Set(result.results.filter((item) => item.success).map((item) => item.task_id))

      if (successCount > 0) {
        setTasks((prev) => prev.filter((task) => !successIds.has(task.task_id)))
        setTotal((prev) => prev - successCount)
      }

      if (successCount === count) {
        toast.success(t('history.successfully_deleted_tasks', { count: successCount }), { id: toastId })
      } else if (successCount > 0) {
        toast.warning(t('history.deleted_tasks_some_failed_please_try_again', { successCount, count }), { id: toastId })
      } else {
        toast.error(t('history.delete_failed_0_please_try_again', { count }), { id: toastId })
      }
    } catch {
      toast.error(t('history.batch_delete_failed_please_try_again'), { id: toastId })
    }
  }

  const toggleSelection = (taskId: string) => {
    setSelectedTasks((prev) => {
      const next = new Set(prev)
      if (next.has(taskId)) {
        next.delete(taskId)
      } else {
        next.add(taskId)
      }
      return next
    })
  }

  const selectAll = () => {
    if (selectedTasks.size === tasks.length) {
      setSelectedTasks(new Set())
    } else {
      setSelectedTasks(new Set(tasks.map((task) => task.task_id)))
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const locale = i18n.resolvedLanguage === 'zh' ? 'zh-CN' : i18n.resolvedLanguage
    return date.toLocaleString(locale, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const handleTaskClick = (task: TaskHistoryItem) => {
    setTaskId(task.task_id)
    if (task.arxiv_id) {
      setArxivId(task.arxiv_id)
    }

    if (task.status === 'completed' || task.status === 'completed_with_warnings') {
      navigate('/preview')
    } else if (TERMINAL_FAIL_STATUSES.has(task.status)) {
      navigate(`/processing?taskId=${task.task_id}`)
    } else {
      navigate(`/processing?taskId=${task.task_id}`)
    }
  }

  if (authLoading) {
    return (
      <div className="flex min-h-[40vh] flex-col items-center justify-center">
        <LoadingState label={t('common.status.loading')} />
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-2xl space-y-6 py-12 animate-in fade-in duration-500">
        <LoginPrompt
          messageKey="history.sign_in_to_view_translation_history"
          descriptionKey="history.sign_in_to_view_and_manage_all_translation_task_records"
          actionLabelKey="common.go_to_sign_in"
        />
      </div>
    )
  }

  return (
    <div className="mx-auto w-full max-w-[1400px] px-6 py-6 md:px-8 md:py-8 lg:px-10 lg:py-10">
      <div className="space-y-6 animate-in fade-in duration-500">
        <PageIntro
          title={t('history.history')}
        description={t('history.total_translation_tasks', { count: total })}
        actions={selectionMode ? (
          <>
            <Button variant="outline" size="sm" onClick={selectAll} className="rounded-full shadow-sm">
              {selectedTasks.size === tasks.length ? t('history.clear_selection') : t('history.select_all')}
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={handleBatchDelete}
              disabled={selectedTasks.size === 0}
              className="min-w-[90px] rounded-full shadow-sm"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              {t('history.delete_selected', { count: selectedTasks.size })}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSelectionMode(false)
                setSelectedTasks(new Set())
              }}
              className="rounded-full"
            >
              {t('common.actions.cancel')}
            </Button>
          </>
        ) : (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectionMode(true)}
              disabled={tasks.length === 0}
              className="rounded-full shadow-sm"
            >
              {t('history.select')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void fetchHistory(1)}
              disabled={loading}
              className="rounded-full shadow-sm"
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              {t('history.refresh')}
            </Button>
          </>
        )}
      />

      {error ? (
        <NoticeBanner
          tone="danger"
          icon={<AlertTriangle className="h-4 w-4" />}
          title={t('history.failed_to_load_history')}
          description={error}
        />
      ) : null}

      <DataTable
        data-testid="history-records"
        data-layout={isMobile ? 'cards' : 'table'}
        className="!bg-transparent !border-none !shadow-none p-0"
      >
        <DataTableHeader className="hidden md:block !bg-transparent !border-b !border-[color:var(--px-shell-line)]">
          <DataTableHeaderRow className="grid-cols-12">
            <DataTableHeaderCell className="col-span-1" />
            <DataTableHeaderCell className="col-span-4">{t('history.table.document')}</DataTableHeaderCell>
            <DataTableHeaderCell className="col-span-3">{t('history.table.timestampMode')}</DataTableHeaderCell>
            <DataTableHeaderCell className="col-span-2">{t('task.status')}</DataTableHeaderCell>
            <DataTableHeaderCell className="col-span-2 text-right">{t('history.table.actions')}</DataTableHeaderCell>
          </DataTableHeaderRow>
        </DataTableHeader>

        <DataTableBody>
          {loading && tasks.length === 0 ? (
            <LoadingState className="m-6 py-10" layout="panel" label={t('common.status.loading')} />
          ) : null}
          {tasks.length === 0 && !loading ? (
            <StatePanel
              className="m-6 py-10 shadow-none"
              icon={<FileText className="h-7 w-7" />}
              title={t('history.no_translation_history_yet')}
              description={t('history.sign_in_to_view_and_manage_all_translation_task_records')}
            />
          ) : (
            tasks.map((task) => (
              <Collapsible
                key={task.task_id}
                open={expandedTasks.has(task.task_id)}
                onOpenChange={() => { }}
                className="group transition-colors hover:bg-[color:var(--px-shell-panel-strong)]/70"
              >
                <DataTableRow className={`flex flex-col items-start gap-4 p-4 md:grid md:grid-cols-12 md:items-center sm:px-6 sm:py-5 border-b border-[color:var(--px-shell-line)]/50 transition-colors hover:bg-[color:var(--px-shell-panel-strong)] group-data-[state=open]:bg-[color:var(--px-shell-panel-strong)] ${isMobile ? 'rounded-[24px] border bg-[color:var(--px-shell-panel)] shadow-[0_18px_38px_-34px_rgba(15,23,42,0.22)]' : 'rounded-2xl md:rounded-none'}`}>
                  <DataTableCell className="pt-1 md:col-span-1 md:pt-0">
                    {selectionMode ? (
                      <Checkbox
                        checked={selectedTasks.has(task.task_id)}
                        onCheckedChange={() => toggleSelection(task.task_id)}
                        aria-label={t('history.select_task', { task: task.arxiv_id || task.task_id.slice(0, 8) })}
                      />
                    ) : (
                      <FileText className="h-5 w-5 text-[color:var(--px-shell-accent)] opacity-80" />
                    )}
                  </DataTableCell>

                  <DataTableCell
                    className="md:col-span-4 flex min-w-0 self-stretch items-center cursor-pointer"
                    onClick={() => !selectionMode && handleTaskClick(task)}
                  >
                    <div className="min-w-0">
                      <div className="truncate text-sm font-bold text-[color:var(--px-shell-ink)]">
                        {task.arxiv_id || task.task_id.slice(0, 8)}
                      </div>
                      <div className="truncate text-[10px] text-[color:var(--px-shell-muted)]">
                        {task.source_type === 'upload' ? t('history.source.localProject') : t('history.source.arxiv')}
                      </div>
                    </div>
                  </DataTableCell>

                  <DataTableCell className="md:col-span-3 flex flex-col text-sm text-[color:var(--px-shell-muted)] md:block">
                    <span className="md:block">{formatDate(task.created_at)}</span>
                    <span className="text-[11px] text-[color:var(--px-shell-muted)] md:mt-0.5">
                      {getTranslationModeLabel(t, task.translation_mode)}
                    </span>
                  </DataTableCell>

                  <DataTableCell className="md:col-span-2">
                    <StatusBadge tone={statusTones[task.status] || 'danger'}>
                      {getTaskStatusLabel(t, task.status)}
                    </StatusBadge>
                  </DataTableCell>

                  <DataTableCell className="md:col-span-2 flex w-full items-center justify-end gap-1 md:w-auto">
                    {!selectionMode ? (
                      <>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 rounded-lg p-0 text-[color:var(--px-shell-muted)] transition-all hover:bg-[color:var(--px-shell-accent-soft)] hover:text-[color:var(--px-shell-accent)]"
                          onClick={(event) => {
                            event.stopPropagation()
                            handleTaskClick(task)
                          }}
                          title={t('common.actions.view')}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 rounded-lg p-0 text-[color:var(--px-shell-muted)] transition-all hover:bg-[color:var(--px-shell-danger-soft)] hover:text-[color:var(--px-shell-danger)]"
                          onClick={(event) => handleDeleteClick(task.task_id, event)}
                          title={t('history.delete_task')}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                        <CollapsibleTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 rounded-lg p-0 text-[color:var(--px-shell-muted)] transition-all hover:bg-[color:var(--px-shell-panel-strong)]"
                            onClick={(event) => toggleExpand(task.task_id, event)}
                            title={t('history.expand_configuration_details')}
                          >
                            <Settings2 className="h-4 w-4" />
                          </Button>
                        </CollapsibleTrigger>
                      </>
                    ) : null}
                  </DataTableCell>
                </DataTableRow>

                <CollapsibleContent className="mt-4 animate-in fade-in slide-in-from-top-2 duration-200 md:mt-2">
                  <div className="space-y-3 border-t border-[color:var(--px-shell-line)] pt-4 md:ml-12 lg:ml-[11.1%]">
                    <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-[color:var(--px-shell-muted)]">
                      <Settings2 className="h-3 w-3" />
                      {t('history.translation_configuration')}
                    </div>

                    <div className="grid grid-cols-1 gap-3 pb-2 text-sm md:grid-cols-2">
                      <InfoTile
                        icon={<Languages className="h-4 w-4" />}
                        title={t('history.language')}
                        value={`${task.source_language} → ${task.target_language}`}
                      />

                      <InfoTile
                        icon={<Wrench className="h-4 w-4" />}
                        title={t('history.compile_strategy')}
                        value={getCompileStrategyLabel(t, task.compile_strategy)}
                        valueClassName="capitalize"
                      />

                      {task.translation_model ? (
                        <div className="md:col-span-2 mt-2">
                          <InfoTile
                            icon={<Sparkles className="h-4 w-4" />}
                            title={t('history.translation_model')}
                            value={task.translation_model}
                            valueClassName="font-mono text-xs"
                          />
                        </div>
                      ) : null}

                      <div className="md:col-span-2 mt-1 flex flex-wrap gap-2">
                        <Pill className="px-3 py-1.5 text-[11px] font-bold normal-case tracking-normal">
                          {task.generate_glossary ? (
                            <CheckCircle2 className="h-3.5 w-3.5 text-[color:var(--px-shell-success)]" />
                          ) : (
                            <XCircle className="h-3.5 w-3.5 text-[color:var(--px-shell-muted)]" />
                          )}
                          <span className="text-[11px] font-bold text-[color:var(--px-shell-ink)]">{t('common.generate_glossary')}</span>
                        </Pill>

                        <Pill className="px-3 py-1.5 text-[11px] font-bold normal-case tracking-normal">
                          {task.use_author_api ? (
                            <CheckCircle2 className="h-3.5 w-3.5 text-[color:var(--px-shell-success)]" />
                          ) : (
                            <XCircle className="h-3.5 w-3.5 text-[color:var(--px-shell-muted)]" />
                          )}
                          <span className="text-[11px] font-bold text-[color:var(--px-shell-ink)]">{t('history.use_author_api')}</span>
                        </Pill>
                      </div>

                      {task.formatting && Object.keys(task.formatting).length > 0 ? (
                        <div className="md:col-span-2 mt-3 rounded-2xl bg-[color:var(--px-shell-panel-strong)]/30 px-5 py-4">
                          <div className="mb-3 text-[10px] font-bold uppercase tracking-widest text-[color:var(--px-shell-muted)]">
                            {t('history.formatting_settings')}
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {task.formatting.line_spacing != null ? (
                              <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                {t('history.line_spacing', { value: String(task.formatting.line_spacing) })}
                              </Pill>
                            ) : null}
                            {task.formatting.font_size != null ? (
                              <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                {t('history.font_size_pt', { value: String(task.formatting.font_size) })}
                              </Pill>
                            ) : null}
                            {task.formatting.column_mode != null ? (
                              <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                {getFormattingValueLabel(t, 'column_mode', String(task.formatting.column_mode))}
                              </Pill>
                            ) : null}
                            {task.formatting.margin != null ? (
                              <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                {t('history.margins', { value: getFormattingValueLabel(t, 'margin', String(task.formatting.margin)) })}
                              </Pill>
                            ) : null}
                            {task.formatting.cjk_font != null ? (
                              <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                {t('history.font', { value: getFormattingValueLabel(t, 'cjk_font', String(task.formatting.cjk_font)) })}
                              </Pill>
                            ) : null}
                            {task.formatting.paragraph_indent === true ? (
                              <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                {t('formatting.firstLineIndent')}
                              </Pill>
                            ) : null}
                            {task.formatting.localize_captions === true ? (
                              <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                {t('history.localize_figures_tables')}
                              </Pill>
                            ) : null}
                            {task.formatting.bib_style != null ? (
                              <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                {t('history.bibliography', { value: String(task.formatting.bib_style) })}
                              </Pill>
                            ) : null}
                            {task.formatting.cite_style != null ? (
                              <Pill tone="accent" className="rounded-md px-2.5 py-1 text-[11px] font-bold normal-case tracking-normal">
                                {t('history.citation', { value: getFormattingValueLabel(t, 'cite_style', String(task.formatting.cite_style)) })}
                              </Pill>
                            ) : null}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            ))
          )}
        </DataTableBody>
      </DataTable>

      {hasMore ? (
        <div className="flex justify-center pt-2">
          <Button variant="outline" onClick={loadMore} disabled={loading} className="rounded-full shadow-sm">
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('common.status.loading')}
              </>
            ) : (
              t('common.actions.loadMore')
            )}
          </Button>
        </div>
      ) : null}

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('history.dialog.confirmDeleteTitle')}</AlertDialogTitle>
            <AlertDialogDescription className="text-sm">
              {t('history.this_action_deletes_all_data_for_this_task_source_files_translated_results_glossary_and_cannot_be_undone_continue')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="mt-4 gap-2 sm:gap-0">
            <AlertDialogCancel>{t('common.actions.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} variant="destructive">
              {t('common.actions.confirmDelete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  </div>
  )
}
