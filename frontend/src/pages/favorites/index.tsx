import { useEffect, useMemo, useState } from "react"
import {
  ArrowRight,
  Bookmark,
  Eye,
  FolderOpen,
  FolderPlus,
  Heart,
  LoaderCircle,
  Pencil,
  Trash2,
} from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link, useNavigate, useParams } from "react-router-dom"
import { toast } from "sonner"

import {
  createFavoriteFolder,
  deleteFavoriteFolder,
  getFavoriteFolderPapers,
  listFavoriteFolders,
  renameFavoriteFolder,
} from "@/features/community-paper/services/community-paper-api"
import type { CommunityPaper, FavoriteFolder } from "@/types/community"
import { Button } from "@/ui/button/Button"
import { PageIntro } from "@/ui/page-intro/PageIntro"

function extractActionErrorMessage(error: unknown): string | null {
  if (typeof error === "string") {
    return error
  }
  if (error instanceof Error) {
    return error.message
  }
  if (!error || typeof error !== "object") {
    return null
  }
  if ("response" in error) {
    const response = error.response
    if (
      response &&
      typeof response === "object" &&
      "data" in response &&
      response.data &&
      typeof response.data === "object" &&
      "detail" in response.data &&
      typeof response.data.detail === "string"
    ) {
      return response.data.detail
    }
  }
  if ("message" in error && typeof error.message === "string") {
    return error.message
  }
  return null
}

function formatAuthors(authors: unknown[], fallback: string) {
  if (!authors.length) {
    return fallback
  }

  return authors
    .slice(0, 3)
    .map((entry) => {
      if (typeof entry === "string") {
        return entry
      }
      if (entry && typeof entry === "object" && "name" in entry) {
        const name = (entry as { name?: unknown }).name
        return typeof name === "string" ? name : null
      }
      return null
    })
    .filter(Boolean)
    .join(", ")
}

export default function FavoritesPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { folderId } = useParams<{ folderId?: string }>()
  const [folders, setFolders] = useState<FavoriteFolder[]>([])
  const [foldersLoading, setFoldersLoading] = useState(true)
  const [folderListError, setFolderListError] = useState<string | null>(null)
  const [activeFolder, setActiveFolder] = useState<FavoriteFolder | null>(null)
  const [folderPapers, setFolderPapers] = useState<CommunityPaper[]>([])
  const [folderPapersTotal, setFolderPapersTotal] = useState(0)
  const [folderPapersLoading, setFolderPapersLoading] = useState(false)
  const [folderPapersError, setFolderPapersError] = useState<string | null>(null)
  const [newFolderName, setNewFolderName] = useState("")
  const [creatingFolder, setCreatingFolder] = useState(false)
  const [mutatingFolderId, setMutatingFolderId] = useState<string | null>(null)

  const selectedFolder = useMemo(
    () => folders.find((folder) => folder.id === folderId) ?? activeFolder,
    [activeFolder, folderId, folders],
  )
  const canCreateFolder = folders.length < 9

  useEffect(() => {
    let cancelled = false

    const loadFolders = async () => {
      try {
        setFoldersLoading(true)
        setFolderListError(null)
        const response = await listFavoriteFolders()
        if (cancelled) {
          return
        }
        setFolders(response.items)
      } catch (error) {
        if (cancelled) {
          return
        }
        setFolderListError(
          extractActionErrorMessage(error) ?? t("community.favorites.page.loadFoldersFailed"),
        )
      } finally {
        if (!cancelled) {
          setFoldersLoading(false)
        }
      }
    }

    void loadFolders()

    return () => {
      cancelled = true
    }
  }, [t])

  useEffect(() => {
    if (!folderId) {
      setActiveFolder(null)
      setFolderPapers([])
      setFolderPapersTotal(0)
      setFolderPapersError(null)
      setFolderPapersLoading(false)
      return
    }

    let cancelled = false

    const loadFolderPapers = async () => {
      try {
        setFolderPapersLoading(true)
        setFolderPapersError(null)
        const response = await getFavoriteFolderPapers(folderId)
        if (cancelled) {
          return
        }
        setActiveFolder(response.folder)
        setFolderPapers(response.items)
        setFolderPapersTotal(response.total)
      } catch (error) {
        if (cancelled) {
          return
        }
        setFolderPapersError(
          extractActionErrorMessage(error) ?? t("community.favorites.page.loadFolderDetailFailed"),
        )
        setFolderPapers([])
        setFolderPapersTotal(0)
      } finally {
        if (!cancelled) {
          setFolderPapersLoading(false)
        }
      }
    }

    void loadFolderPapers()

    return () => {
      cancelled = true
    }
  }, [folderId, t])

  async function handleCreateFolder() {
    const normalizedName = newFolderName.trim()
    if (!normalizedName || creatingFolder || !canCreateFolder) {
      return
    }

    try {
      setCreatingFolder(true)
      const response = await createFavoriteFolder(normalizedName)
      const nextFolder = response.folder
      setFolders((current) => [nextFolder, ...current])
      setNewFolderName("")
      toast.success(t("community.favorites.toast.folderCreated"))
      navigate(`/favorites/${nextFolder.id}`)
    } catch (error) {
      const message =
        extractActionErrorMessage(error) ?? t("community.favorites.toast.folderCreateFailed")
      toast.error(message)
    } finally {
      setCreatingFolder(false)
    }
  }

  async function handleRenameFolder(folder: FavoriteFolder) {
    const nextName = window.prompt(
      t("community.favorites.page.renamePrompt"),
      folder.name,
    )?.trim()
    if (!nextName || nextName === folder.name) {
      return
    }

    try {
      setMutatingFolderId(folder.id)
      const response = await renameFavoriteFolder(folder.id, nextName)
      setFolders((current) =>
        current.map((entry) => (entry.id === folder.id ? response.folder : entry)),
      )
      setActiveFolder((current) => (current?.id === folder.id ? response.folder : current))
      toast.success(t("community.favorites.toast.folderRenamed"))
    } catch (error) {
      toast.error(
        extractActionErrorMessage(error) ?? t("community.favorites.toast.folderRenameFailed"),
      )
    } finally {
      setMutatingFolderId(null)
    }
  }

  async function handleDeleteFolder(folder: FavoriteFolder) {
    const confirmed = window.confirm(
      t("community.favorites.page.deleteConfirm", { name: folder.name }),
    )
    if (!confirmed) {
      return
    }

    try {
      setMutatingFolderId(folder.id)
      await deleteFavoriteFolder(folder.id)
      setFolders((current) => current.filter((entry) => entry.id !== folder.id))
      if (folder.id === folderId) {
        navigate("/favorites", { replace: true })
      }
      toast.success(t("community.favorites.toast.folderDeleted"))
    } catch (error) {
      toast.error(
        extractActionErrorMessage(error) ?? t("community.favorites.toast.folderDeleteFailed"),
      )
    } finally {
      setMutatingFolderId(null)
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-6 md:px-8">
      <div className="space-y-8 animate-in fade-in duration-500">
        <PageIntro
          eyebrow={t("community.nav.favorites")}
          title={t("community.favorites.page.title")}
          description={t("community.favorites.page.description")}
          icon={<Bookmark className="h-5 w-5" />}
        />

        <div className="grid gap-8 xl:grid-cols-[minmax(18rem,22rem)_minmax(0,1fr)] items-start">
          <section className="space-y-5">
            <div className="space-y-1">
              <h2 className="text-base font-semibold text-[color:var(--px-shell-ink)]">
                {t("community.favorites.page.foldersTitle")}
              </h2>
              <p className="text-sm text-[color:var(--px-shell-muted)]">
                {t("community.favorites.page.folderLimit", { count: folders.length, max: 9 })}
              </p>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={newFolderName}
                onChange={(event) => setNewFolderName(event.target.value)}
                placeholder={t("community.favorites.create.placeholder")}
                aria-label={t("community.favorites.create.placeholder")}
                className="min-h-11 flex-1 rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-3 text-sm text-[color:var(--px-shell-ink)] outline-none transition-colors focus:border-[color:var(--px-shell-accent)]"
              />
              <Button
                type="button"
                size="sm"
                disabled={!newFolderName.trim() || creatingFolder || !canCreateFolder}
                onClick={() => void handleCreateFolder()}
                className="rounded-2xl px-4 normal-case tracking-normal"
              >
                {creatingFolder ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <FolderPlus className="h-4 w-4" />
                )}
                {t("community.favorites.create.action")}
              </Button>
            </div>

            {!canCreateFolder ? (
              <p className="text-xs font-medium text-[color:var(--px-shell-muted)]">
                {t("community.favorites.page.limitReached")}
              </p>
            ) : null}

            {folderListError ? (
              <div className="rounded-2xl border border-dashed border-[color:var(--px-shell-danger)]/30 bg-[color:var(--px-shell-danger-soft)] px-4 py-3 text-sm text-[color:var(--px-shell-danger)]">
                {folderListError}
              </div>
            ) : null}

            <div className="space-y-2">
              {foldersLoading ? (
                <div className="flex min-h-32 items-center justify-center text-[color:var(--px-shell-muted)]">
                  <LoaderCircle className="h-5 w-5 animate-spin" />
                </div>
              ) : null}

              {!foldersLoading && folders.length === 0 ? (
                <div className="rounded-[22px] border border-dashed border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-4 py-6 text-center">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-accent)]">
                    <FolderOpen className="h-5 w-5" />
                  </div>
                  <p className="mt-3 text-sm font-semibold text-[color:var(--px-shell-ink)]">
                    {t("community.favorites.page.emptyFoldersTitle")}
                  </p>
                  <p className="mt-1 text-sm leading-6 text-[color:var(--px-shell-muted)]">
                    {t("community.favorites.page.emptyFoldersDescription")}
                  </p>
                </div>
              ) : null}

              {!foldersLoading
                ? folders.map((folder) => {
                    const selected = folder.id === folderId
                    const mutating = mutatingFolderId === folder.id

                    return (
                      <div
                        key={folder.id}
                        className={`rounded-[22px] border p-3 transition-colors ${
                          selected
                            ? "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)]"
                            : "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)]"
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <Link
                            to={`/favorites/${folder.id}`}
                            className="min-w-0 flex-1 rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/25"
                          >
                            <div className="flex items-center gap-2">
                              <FolderOpen className="h-4 w-4 text-[color:var(--px-shell-accent)]" />
                              <p className="truncate text-sm font-semibold text-[color:var(--px-shell-ink)]">
                                {folder.name}
                              </p>
                            </div>
                            <p className="mt-2 text-xs text-[color:var(--px-shell-muted)]">
                              {t("community.favorites.folder.paperCount", { count: folder.paper_count })}
                            </p>
                          </Link>

                          <div className="flex items-center gap-1">
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              disabled={mutating}
                              onClick={() => void handleRenameFolder(folder)}
                              aria-label={t("community.favorites.page.renameAction", { name: folder.name })}
                              className="h-8 w-8 rounded-xl"
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              disabled={mutating}
                              onClick={() => void handleDeleteFolder(folder)}
                              aria-label={t("community.favorites.page.deleteAction", { name: folder.name })}
                              className="h-8 w-8 rounded-xl text-[color:var(--px-shell-danger)] hover:bg-[color:var(--px-shell-danger-soft)]"
                            >
                              {mutating ? (
                                <LoaderCircle className="h-4 w-4 animate-spin" />
                              ) : (
                                <Trash2 className="h-4 w-4" />
                              )}
                            </Button>
                          </div>
                        </div>
                      </div>
                    )
                  })
                : null}
            </div>
          </section>

          <section className="space-y-5">
            {selectedFolder ? (
              <div className="space-y-6">
                <div className="flex flex-wrap items-end justify-between gap-4 pb-4 border-b border-[color:var(--px-shell-line)]/50">
                  <div className="space-y-1">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--px-shell-muted)]">
                      {t("community.favorites.page.folderDetailEyebrow")}
                    </p>
                    <h2 className="text-lg font-semibold text-[color:var(--px-shell-ink)]">
                      {selectedFolder.name}
                    </h2>
                    <p className="text-sm text-[color:var(--px-shell-muted)]">
                      {t("community.favorites.page.folderPaperTotal", { count: folderPapersTotal })}
                    </p>
                  </div>
                </div>

                {folderPapersLoading ? (
                  <div className="flex min-h-48 items-center justify-center text-[color:var(--px-shell-muted)]">
                    <LoaderCircle className="h-5 w-5 animate-spin" />
                  </div>
                ) : null}

                {folderPapersError ? (
                  <div className="rounded-2xl border border-dashed border-[color:var(--px-shell-danger)]/30 bg-[color:var(--px-shell-danger-soft)] px-4 py-3 text-sm text-[color:var(--px-shell-danger)]">
                    {folderPapersError}
                  </div>
                ) : null}

                {!folderPapersLoading && !folderPapersError && folderPapers.length === 0 ? (
                  <div className="rounded-[22px] border border-dashed border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-4 py-8 text-center">
                    <p className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
                      {t("community.favorites.page.emptyFolderPapersTitle")}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-[color:var(--px-shell-muted)]">
                      {t("community.favorites.page.emptyFolderPapersDescription")}
                    </p>
                  </div>
                ) : null}

                {!folderPapersLoading && !folderPapersError && folderPapers.length > 0 ? (
                  <div className="grid gap-3">
                    {folderPapers.map((paper) => (
                      <Link
                        key={paper.id}
                        to={`/paper/${paper.id}`}
                        className="group rounded-[22px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-4 py-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-[color:var(--px-shell-accent)]/28 hover:shadow-[0_18px_38px_-30px_rgba(15,23,42,0.35)]"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 space-y-2">
                            <h3 className="line-clamp-2 text-base font-semibold text-[color:var(--px-shell-ink)]">
                              {paper.title}
                            </h3>
                            <p className="text-sm text-[color:var(--px-shell-muted)]">
                              {formatAuthors(paper.authors, t("community.card.authorsUnavailable"))}
                            </p>
                            <p className="line-clamp-2 text-sm leading-6 text-[color:var(--px-shell-muted)]">
                              {paper.abstract_translated ||
                                paper.abstract_raw ||
                                t("community.card.abstractPlaceholder")}
                            </p>
                          </div>
                          <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-[color:var(--px-shell-muted)] transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-[color:var(--px-shell-accent)]" />
                        </div>

                        <div className="mt-4 flex flex-wrap gap-4 text-xs text-[color:var(--px-shell-muted)]">
                          <span className="flex items-center gap-1.5">
                            <Eye className="h-4 w-4" />
                            {paper.view_count ?? 0}
                          </span>
                          <span className="flex items-center gap-1.5">
                            <Heart className="h-4 w-4" />
                            {paper.like_count ?? 0}
                          </span>
                          <span className="flex items-center gap-1.5">
                            <Bookmark className="h-4 w-4" />
                            {paper.favorite_count ?? 0}
                          </span>
                        </div>
                      </Link>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="flex min-h-[22rem] flex-col items-center justify-center rounded-[22px] border border-dashed border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-6 text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-[20px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-accent)]">
                  <FolderOpen className="h-6 w-6" />
                </div>
                <p className="mt-4 text-base font-semibold text-[color:var(--px-shell-ink)]">
                  {t("community.favorites.page.selectFolderTitle")}
                </p>
                <p className="mt-2 max-w-md text-sm leading-6 text-[color:var(--px-shell-muted)]">
                  {t("community.favorites.page.selectFolderDescription")}
                </p>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
