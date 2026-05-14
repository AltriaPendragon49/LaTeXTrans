import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { BookOpenText, Loader2, Search, Share2, Upload, XCircle } from "lucide-react"

import { PageIntro } from "@/ui/page-intro/PageIntro"
import { Button } from "@/ui/button/Button"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { StatusBadge } from "@/ui/status-badge/StatusBadge"
import { Label } from "@/ui/primitives/label"
import {
  DataTable,
  DataTableBody,
  DataTableCell,
  DataTableHeader,
  DataTableHeaderCell,
  DataTableHeaderRow,
  DataTableRow,
} from "@/ui/data-table/DataTable"
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/ui/primitives/select"
import { EditorialTabs, EditorialTabsList, EditorialTabsTrigger } from "@/ui/tabs/EditorialTabs"
import { TabsContent } from "@/ui/primitives/tabs"

import type { TerminologyTerm } from "@/features/rag-terminology/types"
import {
  listMyTerms,
  listTerms,
  uploadTerminologyFile,
  shareTerm,
} from "@/features/rag-terminology/services/rag-terminology-api"

const PAGE_SIZE = 20

const STATUS_LABELS: Record<string, { tone: "muted" | "accent" | "info" | "success" | "warning" | "danger"; label: string }> = {
  pending_review: { tone: "warning", label: "Pending" },
  approved: { tone: "success", label: "Approved" },
  rejected: { tone: "danger", label: "Rejected" },
}

function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString)
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  } catch {
    return dateString
  }
}

const GRID_COLS_WITH_ACTIONS = "grid-cols-[1fr_1fr_120px_100px_120px_80px]"
const GRID_COLS_NO_ACTIONS = "grid-cols-[1fr_1fr_120px_100px_120px]"

function TermsTable({
  terms,
  loading,
  error,
  onRetry,
  emptyIcon,
  emptyMessage,
  onShare,
  shareLoadingId,
}: {
  terms: TerminologyTerm[]
  loading: boolean
  error: string | null
  onRetry: () => void
  emptyIcon?: React.ReactNode
  emptyMessage: string
  onShare?: (termId: string) => void
  shareLoadingId?: string | null
}) {
  const { t } = useTranslation()
  const showActions = !!onShare
  const gridCols = showActions ? GRID_COLS_WITH_ACTIONS : GRID_COLS_NO_ACTIONS

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-14 text-[color:var(--px-shell-muted)]">
        <Loader2 className="h-6 w-6 animate-spin" />
        <p className="mt-3 text-sm">{t("glossary.loading")}</p>
      </div>
    )
  }
  if (error) {
    return (
      <NoticeBanner
        tone="danger"
        icon={<XCircle className="h-4 w-4" />}
        description={error}
        action={<Button variant="ghost" size="sm" onClick={onRetry}>{t("common.actions.retry")}</Button>}
      />
    )
  }
  if (terms.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-14 text-[color:var(--px-shell-muted)]">
        {emptyIcon || <BookOpenText className="h-7 w-7" />}
        <p className="mt-3 text-sm">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <DataTable>
      <DataTableHeader>
        <DataTableHeaderRow className={gridCols}>
          <DataTableHeaderCell>{t("glossary.table.sourceTerm")}</DataTableHeaderCell>
          <DataTableHeaderCell>{t("glossary.table.targetTerm")}</DataTableHeaderCell>
          <DataTableHeaderCell>{t("glossary.table.domain")}</DataTableHeaderCell>
          <DataTableHeaderCell>{t("glossary.table.status")}</DataTableHeaderCell>
          <DataTableHeaderCell>{t("glossary.table.createdAt")}</DataTableHeaderCell>
          {showActions && <DataTableHeaderCell className="text-right">{t("glossary.table.actions")}</DataTableHeaderCell>}
        </DataTableHeaderRow>
      </DataTableHeader>
      <DataTableBody>
        {terms.map((term) => {
          const statusStyle = STATUS_LABELS[term.status] ?? { tone: "muted" as const, label: term.status }
          const isShareLoading = shareLoadingId === term.id
          return (
            <DataTableRow key={term.id} className={`${gridCols} items-center`}>
              <DataTableCell className="truncate font-medium text-[color:var(--px-shell-ink)]">{term.source_term}</DataTableCell>
              <DataTableCell className="truncate text-[color:var(--px-shell-muted)]">{term.target_term}</DataTableCell>
              <DataTableCell className="truncate text-sm text-[color:var(--px-shell-muted)]">{term.domain || "-"}</DataTableCell>
              <DataTableCell>
                <StatusBadge tone={statusStyle.tone} size="sm">{statusStyle.label}</StatusBadge>
              </DataTableCell>
              <DataTableCell className="text-xs text-[color:var(--px-shell-muted)]">{formatDate(term.created_at)}</DataTableCell>
              {showActions && (
                <DataTableCell className="text-right">
                  {term.source_type !== "system" && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onShare(term.id)}
                      disabled={isShareLoading}
                      title={t("glossary.share")}
                    >
                      {isShareLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Share2 className="h-3.5 w-3.5" />}
                    </Button>
                  )}
                </DataTableCell>
              )}
            </DataTableRow>
          )
        })}
      </DataTableBody>
    </DataTable>
  )
}

export function GlossaryWorkspace() {
  const { t } = useTranslation()

  const [activeTab, setActiveTab] = useState("my")

  // My terms
  const [myTerms, setMyTerms] = useState<TerminologyTerm[]>([])
  const [myTotal, setMyTotal] = useState(0)
  const [myPage, setMyPage] = useState(1)
  const [isLoadingMy, setIsLoadingMy] = useState(false)
  const [myLoadError, setMyLoadError] = useState<string | null>(null)
  const [myStatusFilter, setMyStatusFilter] = useState("")

  // Official terms
  const [officialTerms, setOfficialTerms] = useState<TerminologyTerm[]>([])
  const [officialTotal, setOfficialTotal] = useState(0)
  const [officialPage, setOfficialPage] = useState(1)
  const [isLoadingOfficial, setIsLoadingOfficial] = useState(false)
  const [officialLoadError, setOfficialLoadError] = useState<string | null>(null)

  // Upload
  const [isUploading, setIsUploading] = useState(false)
  const [isDragActive, setIsDragActive] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // Share
  const [shareLoadingId, setShareLoadingId] = useState<string | null>(null)

  const myTotalPages = Math.max(1, Math.ceil(myTotal / PAGE_SIZE))
  const officialTotalPages = Math.max(1, Math.ceil(officialTotal / PAGE_SIZE))

  // ---- Load my terms ----
  const loadMyTerms = useCallback(async () => {
    setIsLoadingMy(true)
    setMyLoadError(null)
    try {
      const params: Record<string, string | number> = { page: myPage, page_size: PAGE_SIZE }
      if (myStatusFilter) params.status = myStatusFilter
      const response = await listMyTerms(params)
      setMyTerms(response.terms)
      setMyTotal(response.total)
    } catch {
      setMyLoadError(t("glossary.loadError"))
    } finally {
      setIsLoadingMy(false)
    }
  }, [myPage, myStatusFilter, t])

  useEffect(() => {
    if (activeTab === "my") loadMyTerms()
  }, [loadMyTerms, activeTab])

  // ---- Load official terms ----
  const loadOfficialTerms = useCallback(async () => {
    setIsLoadingOfficial(true)
    setOfficialLoadError(null)
    try {
      const response = await listTerms({ page: officialPage, page_size: PAGE_SIZE, status: "approved", source_type: "system" })
      setOfficialTerms(response.terms)
      setOfficialTotal(response.total)
    } catch {
      setOfficialLoadError(t("glossary.loadError"))
    } finally {
      setIsLoadingOfficial(false)
    }
  }, [officialPage, t])

  useEffect(() => {
    if (activeTab === "official") loadOfficialTerms()
  }, [loadOfficialTerms, activeTab])

  // ---- Upload ----
  function handleDrag(event: React.DragEvent) {
    event.preventDefault()
    event.stopPropagation()
    if (event.type === "dragenter" || event.type === "dragover") {
      setIsDragActive(true)
    } else if (event.type === "dragleave") {
      setIsDragActive(false)
    }
  }

  async function handleUploadFile(file: File) {
    const validExtensions = [".csv", ".bib"]
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase()
    if (!validExtensions.includes(ext)) {
      toast.error(t("glossary.supportedFormats"))
      return
    }
    setIsUploading(true)
    try {
      const result = await uploadTerminologyFile(file)
      toast.success(t("glossary.uploadSuccess", { accepted: result.accepted, rejected: result.rejected }))
      loadMyTerms()
    } catch {
      toast.error(t("glossary.uploadError"))
    } finally {
      setIsUploading(false)
    }
  }

  function handleDrop(event: React.DragEvent) {
    event.preventDefault()
    event.stopPropagation()
    setIsDragActive(false)
    const file = event.dataTransfer.files[0]
    if (file) handleUploadFile(file)
  }

  function handleFileSelect(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (file) handleUploadFile(file)
    event.target.value = ""
  }

  // ---- Share ----
  async function handleShare(termId: string) {
    setShareLoadingId(termId)
    try {
      const result = await shareTerm(termId)
      toast.success(t("glossary.shareSuccess"))
      loadMyTerms()
    } catch {
      toast.error(t("glossary.shareError"))
    } finally {
      setShareLoadingId(null)
    }
  }

  // ---- Render upload area ----
  function renderUploadArea() {
    return (
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-[24px] border-2 border-dashed p-8 transition-colors ${
          isDragActive
            ? "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)]"
            : "border-[color:var(--px-shell-line)] hover:border-[color:var(--px-shell-accent)]/30 hover:bg-[color:var(--px-shell-panel-strong)]"
        }`}
      >
        <input ref={inputRef} type="file" accept=".csv,.bib" className="hidden" onChange={handleFileSelect} />
        {isUploading ? (
          <>
            <Loader2 className="h-8 w-8 animate-spin text-[color:var(--px-shell-accent)]" />
            <p className="mt-3 text-sm font-medium text-[color:var(--px-shell-ink)]">{t("glossary.uploading")}</p>
          </>
        ) : (
          <>
            <Upload className="h-8 w-8 text-[color:var(--px-shell-muted)]" />
            <p className="mt-3 text-sm font-medium text-[color:var(--px-shell-ink)]">{t("glossary.uploadPrompt")}</p>
            <p className="mt-1 text-xs text-[color:var(--px-shell-muted)]">{t("glossary.supportedFormats")}</p>
          </>
        )}
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 py-2">
      <PageIntro
        title={t("glossary.glossary_management")}
        description={t("glossary.description")}
      />

      <PanelShell className="space-y-6 p-4 sm:p-6">
        <EditorialTabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <div className="flex justify-start">
            <EditorialTabsList className="gap-1">
              <EditorialTabsTrigger value="my">
                {t("glossary.myTerms")}
              </EditorialTabsTrigger>
              <EditorialTabsTrigger value="official">
                {t("glossary.officialLibrary")}
              </EditorialTabsTrigger>
            </EditorialTabsList>
          </div>

          <TabsContent value="my" className="mt-0 space-y-6">
            {/* Upload area */}
            {renderUploadArea()}

            {/* Status filter */}
            <div className="flex items-center gap-3">
              <Label className="text-sm whitespace-nowrap">{t("glossary.filterStatus")}</Label>
              <Select value={myStatusFilter} onValueChange={(v) => { setMyStatusFilter(v); setMyPage(1) }}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder={t("glossary.all")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">{t("glossary.all")}</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="pending_review">Pending</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <TermsTable
              terms={myTerms}
              loading={isLoadingMy}
              error={myLoadError}
              onRetry={loadMyTerms}
              emptyMessage={t("glossary.empty")}
              onShare={handleShare}
              shareLoadingId={shareLoadingId}
            />

            {myTotalPages > 1 && (
              <div className="flex items-center justify-between pt-2">
                <p className="text-xs text-[color:var(--px-shell-muted)]">
                  {t("glossary.pageInfo", { current: myPage, total: myTotalPages })}
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setMyPage((p) => Math.max(1, p - 1))} disabled={myPage <= 1}>
                    {t("glossary.previous")}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setMyPage((p) => Math.min(myTotalPages, p + 1))} disabled={myPage >= myTotalPages}>
                    {t("glossary.next")}
                  </Button>
                </div>
              </div>
            )}
          </TabsContent>

          <TabsContent value="official" className="mt-0 space-y-4">
            <TermsTable
              terms={officialTerms}
              loading={isLoadingOfficial}
              error={officialLoadError}
              onRetry={loadOfficialTerms}
              emptyMessage={t("glossary.officialEmpty")}
            />

            {officialTotalPages > 1 && (
              <div className="flex items-center justify-between pt-2">
                <p className="text-xs text-[color:var(--px-shell-muted)]">
                  {t("glossary.pageInfo", { current: officialPage, total: officialTotalPages })}
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setOfficialPage((p) => Math.max(1, p - 1))} disabled={officialPage <= 1}>
                    {t("glossary.previous")}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => setOfficialPage((p) => Math.min(officialTotalPages, p + 1))} disabled={officialPage >= officialTotalPages}>
                    {t("glossary.next")}
                  </Button>
                </div>
              </div>
            )}
          </TabsContent>
        </EditorialTabs>
      </PanelShell>
    </div>
  )
}
