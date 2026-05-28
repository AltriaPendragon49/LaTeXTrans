import { useEffect, useMemo, useState } from "react"
import { Bookmark, Check, FolderPlus, LoaderCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"

import { useAuth } from "@/contexts/AuthContext"
import {
  createFavoriteFolder,
  getPaperFavoriteFolders,
  updatePaperFavoriteFolders,
} from "@/features/community-paper/services/community-paper-api"
import type {
  FavoriteFolder,
  PaperFavoriteFolderUpdateResponse,
  ViewerState,
} from "@/types/community"
import { Button } from "@/ui/button/Button"
import { Popover, PopoverContent, PopoverTrigger } from "@/ui/primitives/popover"

/** 收藏选择器 Props */
interface FavoritePickerProps {
  /** 论文 ID */
  paperId: string
  /** 收藏数 */
  favoriteCount?: number
  /** 查看者状态（是否已收藏等） */
  viewerState?: ViewerState | null
  /** 展示样式：卡片模式或图标模式 */
  variant?: "card" | "icon"
  className?: string
  /** 收藏状态变更回调 */
  onFavoriteStateChange?: (payload: PaperFavoriteFolderUpdateResponse) => void
}

/** 将字符串数组转为 Set，用于比较选择差异 */
function buildSet(values: string[]) {
  return new Set(values.map((value) => value.trim()).filter(Boolean))
}

/** 比较两个选择列表是否相同 */
function sameSelection(left: string[], right: string[]) {
  const leftSet = buildSet(left)
  const rightSet = buildSet(right)
  if (leftSet.size !== rightSet.size) {
    return false
  }
  for (const value of leftSet) {
    if (!rightSet.has(value)) {
      return false
    }
  }
  return true
}

/** 计算文件夹在选择变更后的论文数量 */
function nextFolderCount(folder: FavoriteFolder, fromSelected: boolean, toSelected: boolean) {
  if (fromSelected === toSelected) {
    return folder.paper_count
  }
  if (toSelected) {
    return folder.paper_count + 1
  }
  return Math.max(0, folder.paper_count - 1)
}

/**
 * 收藏选择器组件
 * 通过 Popover 展示收藏夹列表，支持多选切换、新建收藏夹、确认保存。
 * 调用 GET /api/papers/{paperId}/favorite-folders 获取文件夹列表，
 * 调用 POST /api/papers/{paperId}/favorite-folders 更新收藏状态
 */
export function FavoritePicker({
  paperId,
  favoriteCount = 0,
  viewerState,
  variant = "card",
  className = "",
  onFavoriteStateChange,
}: FavoritePickerProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [creating, setCreating] = useState(false)
  const [folders, setFolders] = useState<FavoriteFolder[]>([])
  const [selectedFolderIds, setSelectedFolderIds] = useState<string[]>([])
  const [initialSelectedFolderIds, setInitialSelectedFolderIds] = useState<string[]>([])
  const [newFolderName, setNewFolderName] = useState("")
  const [panelError, setPanelError] = useState<string | null>(null)

  const favorited = Boolean(viewerState?.favorited)
  const favoriteFolderCount = Number(viewerState?.favorite_folder_count ?? 0)
  const hasChanges = useMemo(
    () => !sameSelection(selectedFolderIds, initialSelectedFolderIds),
    [initialSelectedFolderIds, selectedFolderIds],
  )

  // 打开时加载收藏夹列表
  useEffect(() => {
    if (!open || !isAuthenticated) {
      return
    }

    let isCancelled = false

    const loadPickerState = async () => {
      try {
        setLoading(true)
        setPanelError(null)
        const response = await getPaperFavoriteFolders(paperId)
        if (isCancelled) {
          return
        }
        setFolders(response.items)
        setSelectedFolderIds(response.selected_folder_ids)
        setInitialSelectedFolderIds(response.selected_folder_ids)
      } catch (error) {
        if (isCancelled) {
          return
        }
        const message = error instanceof Error ? error.message : t("community.favorites.toast.loadFailed")
        setPanelError(message)
      } finally {
        if (!isCancelled) {
          setLoading(false)
        }
      }
    }

    void loadPickerState()

    return () => {
      isCancelled = true
    }
  }, [isAuthenticated, open, paperId, t])

  /** 处理打开/关闭，未登录用户重定向到登录页 */
  function handleOpenChange(nextOpen: boolean) {
    if (nextOpen && !isAuthenticated) {
      toast.error(t("auth.loginRequiredForThisFeature"))
      navigate("/login")
      return
    }
    setOpen(nextOpen)
  }

  /** 切换文件夹选中状态 */
  function toggleFolder(folderId: string) {
    setSelectedFolderIds((current) =>
      current.includes(folderId)
        ? current.filter((value) => value !== folderId)
        : [...current, folderId],
    )
  }

  /** 创建新收藏夹 */
  async function handleCreateFolder() {
    const normalizedName = newFolderName.trim()
    if (!normalizedName || creating) {
      return
    }

    try {
      setCreating(true)
      setPanelError(null)
      const response = await createFavoriteFolder(normalizedName)
      const nextFolder = response.folder
      setFolders((current) => [nextFolder, ...current])
      setSelectedFolderIds((current) => (current.includes(nextFolder.id) ? current : [...current, nextFolder.id]))
      setNewFolderName("")
      toast.success(t("community.favorites.toast.folderCreated"))
    } catch (error) {
      const message = error instanceof Error ? error.message : t("community.favorites.toast.folderCreateFailed")
      setPanelError(message)
      toast.error(message)
    } finally {
      setCreating(false)
    }
  }

  /** 确认保存收藏夹选择 */
  async function handleConfirm() {
    if (!hasChanges || saving) {
      return
    }

    try {
      setSaving(true)
      setPanelError(null)
      const response = await updatePaperFavoriteFolders(paperId, selectedFolderIds)
      setFolders((current) =>
        current.map((folder) => ({
          ...folder,
          paper_count: nextFolderCount(
            folder,
            initialSelectedFolderIds.includes(folder.id),
            response.selected_folder_ids.includes(folder.id),
          ),
        })),
      )
      setSelectedFolderIds(response.selected_folder_ids)
      setInitialSelectedFolderIds(response.selected_folder_ids)
      onFavoriteStateChange?.(response)
      toast.success(
        response.favorited
          ? t("community.favorites.toast.saved")
          : t("community.favorites.toast.removed"),
      )
      setOpen(false)
    } catch (error) {
      const message = error instanceof Error ? error.message : t("community.favorites.toast.saveFailed")
      setPanelError(message)
      toast.error(message)
    } finally {
      setSaving(false)
    }
  }

  const triggerLabel = favorited
    ? t("community.favorites.action.favorited")
    : t("community.favorites.action.favorite")

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        {variant === "icon" ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={triggerLabel}
            title={triggerLabel}
            aria-pressed={favorited}
            className={`h-8 w-8 rounded-[10px] border ${
              favorited
                ? "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]"
                : "border-transparent text-[color:var(--px-shell-muted)]"
            } ${className}`}
          >
            <Bookmark className={`h-4 w-4 ${favorited ? "fill-current" : ""}`} />
          </Button>
        ) : (
          <Button
            type="button"
            variant={favorited ? "secondary" : "ghost"}
            size="chip"
            aria-label={triggerLabel}
            title={triggerLabel}
            aria-pressed={favorited}
            className={`gap-1.5 rounded-full px-3 normal-case tracking-normal ${
              favorited
                ? "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]"
                : ""
            } ${className}`}
          >
            <Bookmark className={`h-3.5 w-3.5 ${favorited ? "fill-current" : ""}`} />
            <span>{favoriteCount}</span>
          </Button>
        )}
      </PopoverTrigger>

      <PopoverContent
        align="end"
        sideOffset={10}
        className="w-[22rem] rounded-[20px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-4 shadow-[0_28px_60px_-38px_rgba(15,23,42,0.4)]"
      >
        <div className="space-y-4">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-[color:var(--px-shell-ink)]">
              {t("community.favorites.picker.title")}
            </h3>
            <p className="text-xs leading-5 text-[color:var(--px-shell-muted)]">
              {t("community.favorites.picker.description", {
                count: favoriteFolderCount,
              })}
            </p>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={newFolderName}
              onChange={(event) => setNewFolderName(event.target.value)}
              placeholder={t("community.favorites.create.placeholder")}
              aria-label={t("community.favorites.create.placeholder")}
              className="min-h-10 flex-1 rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-3 text-sm text-[color:var(--px-shell-ink)] outline-none transition-colors focus:border-[color:var(--px-shell-accent)]"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!newFolderName.trim() || creating}
              onClick={() => void handleCreateFolder()}
              className="rounded-2xl px-3 text-[11px] normal-case tracking-normal"
            >
              {creating ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <FolderPlus className="h-3.5 w-3.5" />}
              {t("community.favorites.create.action")}
            </Button>
          </div>

          <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
            {loading ? (
              <div className="flex min-h-28 items-center justify-center text-[color:var(--px-shell-muted)]">
                <LoaderCircle className="h-4 w-4 animate-spin" />
              </div>
            ) : null}

            {!loading && folders.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-4 py-5 text-center text-sm text-[color:var(--px-shell-muted)]">
                {t("community.favorites.picker.empty")}
              </div>
            ) : null}

            {!loading
              ? folders.map((folder) => {
                  const selected = selectedFolderIds.includes(folder.id)
                  return (
                    <button
                      key={folder.id}
                      type="button"
                      onClick={() => toggleFolder(folder.id)}
                      className={`flex w-full items-center justify-between rounded-2xl border px-3 py-3 text-left transition-colors ${
                        selected
                          ? "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]"
                          : "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)]"
                      }`}
                    >
                      <div className="space-y-1">
                        <p className="text-sm font-semibold">{folder.name}</p>
                        <p className="text-xs text-[color:var(--px-shell-muted)]">
                          {t("community.favorites.folder.paperCount", { count: folder.paper_count })}
                        </p>
                      </div>
                      <span
                        className={`flex h-6 w-6 items-center justify-center rounded-full border ${
                          selected
                            ? "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent)] text-white"
                            : "border-[color:var(--px-shell-line)] text-transparent"
                        }`}
                      >
                        <Check className="h-3.5 w-3.5" />
                      </span>
                    </button>
                  )
                })
              : null}
          </div>

          {panelError ? (
            <p className="text-xs font-medium text-[color:var(--px-shell-danger)]">{panelError}</p>
          ) : null}

          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-[color:var(--px-shell-muted)]">
              {hasChanges
                ? t("community.favorites.picker.pending")
                : t("community.favorites.picker.idle")}
            </p>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setOpen(false)}
                className="rounded-2xl px-4 text-[11px] normal-case tracking-normal"
              >
                {t("common.actions.cancel")}
              </Button>
              <Button
                type="button"
                variant={hasChanges ? "default" : "outline"}
                size="sm"
                disabled={!hasChanges || saving}
                onClick={() => void handleConfirm()}
                className="rounded-2xl px-4 text-[11px] normal-case tracking-normal"
              >
                {saving ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : null}
                {t("community.favorites.picker.confirm")}
              </Button>
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
