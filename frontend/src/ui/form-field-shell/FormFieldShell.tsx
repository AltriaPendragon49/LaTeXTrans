/**
 * 表单字段外壳组件
 * 渲染带标签、图标、描述的表单字段容器，支持不同色调和尺寸
 */
import type { HTMLAttributes, ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/** 表单字段外壳样式变体：panel / muted / danger */
const formFieldShellVariants = cva(
  "rounded-[20px] border transition-colors duration-200",
  {
    variants: {
      tone: {
        panel:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] hover:bg-[color:var(--px-shell-panel)]",
        muted:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)]",
      },
      size: {
        default: "p-3",
        compact: "px-3 py-2.5",
      },
    },
    defaultVariants: {
      tone: "panel",
      size: "default",
    },
  },
)

/** FormFieldShell 组件 Props */
interface FormFieldShellProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof formFieldShellVariants> {
  /** 字段标签 */
  label: ReactNode
  /** 可选图标 */
  icon?: ReactNode
  /** 可选描述文本 */
  description?: ReactNode
  /** 头部右侧附加内容 */
  headerAside?: ReactNode
  /** 标签额外样式 */
  labelClassName?: string
  /** 描述额外样式 */
  descriptionClassName?: string
  /** 主体区域额外样式 */
  bodyClassName?: string
}

/** 表单字段外壳，包含头部（图标+标签+描述）和主体内容区域 */
export function FormFieldShell({
  label,
  icon,
  description,
  headerAside,
  tone,
  size,
  className,
  labelClassName,
  descriptionClassName,
  bodyClassName,
  children,
  ...props
}: FormFieldShellProps) {
  return (
    <div
      className={cn(formFieldShellVariants({ tone, size }), className)}
      {...props}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {icon ? (
              <span className="text-[color:var(--px-shell-muted)]">{icon}</span>
            ) : null}
            <div className={cn("text-sm font-medium text-[color:var(--px-shell-ink)]", labelClassName)}>
              {label}
            </div>
          </div>
          {description ? (
            <div className={cn("mt-1 text-xs text-[color:var(--px-shell-muted)]", descriptionClassName)}>
              {description}
            </div>
          ) : null}
        </div>

        {headerAside ? <div className="shrink-0">{headerAside}</div> : null}
      </div>

      <div className={cn("mt-2", bodyClassName)}>
        {children}
      </div>
    </div>
  )
}
