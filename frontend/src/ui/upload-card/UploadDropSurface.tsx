/**
 * 上传拖放区组件
 * 渲染虚线边框的上传拖放目标区域，带图标、标题和描述
 */
import type { HTMLAttributes, ReactNode } from "react"
import { Upload } from "lucide-react"

import { cn } from "@/lib/utils"

/** UploadDropSurface 组件 Props */
interface UploadDropSurfaceProps extends HTMLAttributes<HTMLDivElement> {
  /** 标题 */
  heading: ReactNode
  /** 描述文本 */
  body: ReactNode
  /** 可选自定义图标，默认使用 Upload 图标 */
  icon?: ReactNode
  /** 是否为拖拽激活状态 */
  isDragActive?: boolean
}

/** 上传拖放区，拖拽激活时有高亮边框和缩放效果 */
export function UploadDropSurface({
  heading,
  body,
  icon,
  isDragActive = false,
  className,
  children,
  ...props
}: UploadDropSurfaceProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[28px] border-2 border-dashed transition-all duration-300 ease-in-out",
        isDragActive
          ? "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)] shadow-[var(--px-shell-shadow)] scale-[1.01]"
          : "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] hover:border-[color:var(--px-shell-accent)]/45 hover:bg-[color:var(--px-shell-panel-strong)]",
        className,
      )}
      {...props}
    >
      <div className="flex min-h-[220px] flex-col items-center justify-center p-8 text-center">
        <div className="space-y-4">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] shadow-sm">
            {icon ?? <Upload className="h-8 w-8 text-[color:var(--px-shell-accent)]" />}
          </div>
          <div className="space-y-1.5">
            <p className="text-lg font-black text-[color:var(--px-shell-ink)]">{heading}</p>
            <p className="max-w-sm text-sm leading-6 text-[color:var(--px-shell-muted)]">{body}</p>
          </div>
          {children}
        </div>
      </div>
    </div>
  )
}
