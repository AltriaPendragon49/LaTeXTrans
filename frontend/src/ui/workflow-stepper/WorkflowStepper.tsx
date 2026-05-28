/**
 * 工作流步骤指示器组件
 * 渲染带状态图标（完成/进行中/错误/待处理）的垂直步骤列表
 */
import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"

/** 工作流步骤状态 */
export type WorkflowStepState = "complete" | "current" | "error" | "upcoming"

/** 单个工作流步骤 */
interface WorkflowStepItem {
  /** 步骤唯一标识 */
  id: string
  /** 步骤标签 */
  label: string
  /** 可选描述 */
  description?: string | null
  /** 步骤当前状态 */
  state: WorkflowStepState
}

/** WorkflowStepper 组件 Props */
interface WorkflowStepperProps {
  /** 步骤列表 */
  items: WorkflowStepItem[]
  /** 额外样式 */
  className?: string
}

/** 根据步骤状态返回圆圈样式类 */
function stepCircleClass(state: WorkflowStepState) {
  switch (state) {
    case "complete":
      return "border-[color:var(--px-shell-success)] bg-[color:var(--px-shell-success)] text-[color:var(--px-shell-danger-contrast)]"
    case "error":
      return "border-[color:var(--px-shell-danger-strong)] bg-[color:var(--px-shell-danger-strong)] text-[color:var(--px-shell-danger-contrast)]"
    case "current":
      return "border-[color:var(--px-shell-accent)] text-[color:var(--px-shell-accent)] shadow-[0_0_0_4px_color-mix(in_srgb,var(--px-shell-accent)_12%,transparent)]"
    default:
      return "border-[color:var(--px-shell-line)] text-[color:var(--px-shell-muted)]"
  }
}

/** 根据步骤状态返回文本样式类 */
function stepTextClass(state: WorkflowStepState) {
  switch (state) {
    case "complete":
      return "text-[color:var(--px-shell-success)]"
    case "error":
      return "text-[color:var(--px-shell-danger)]"
    case "current":
      return "text-[color:var(--px-shell-accent)]"
    default:
      return "text-[color:var(--px-shell-muted)]"
  }
}

/** 根据步骤状态渲染对应的图标 */
function renderStepIcon(state: WorkflowStepState) {
  switch (state) {
    case "complete":
      return <CheckCircle2 className="h-3 w-3" />
    case "error":
      return <AlertTriangle className="h-3 w-3" />
    case "current":
      return <Loader2 className="h-3 w-3 animate-spin" />
    default:
      return <span className="h-2 w-2 rounded-full bg-current" />
  }
}

/** 工作流步骤指示器，垂直时间线样式，左侧竖线连接各步骤节点 */
export function WorkflowStepper({ items, className }: WorkflowStepperProps) {
  return (
    <div className={cn("relative ml-2 space-y-5 border-l-2 border-[color:var(--px-shell-line)] py-1 pl-5", className)}>
      {items.map((item) => (
        <div key={item.id} className="relative">
          <span
            className={cn(
              "absolute -left-[23px] flex h-5 w-5 items-center justify-center rounded-full border-2 bg-[color:var(--px-shell-panel-strong)]",
              stepCircleClass(item.state),
            )}
          >
            {renderStepIcon(item.state)}
          </span>
          <div className="flex flex-col">
            <span className={cn("text-sm font-medium", stepTextClass(item.state))}>{item.label}</span>
            {item.description ? (
              <span className={cn("text-xs", item.state === "upcoming" ? "text-[color:var(--px-shell-muted)]/75" : stepTextClass(item.state))}>
                {item.description}
              </span>
            ) : null}
          </div>
        </div>
      ))}
    </div>
  )
}
