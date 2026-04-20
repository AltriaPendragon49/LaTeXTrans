import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react"

import { cn } from "@/lib/utils"

export type WorkflowStepState = "complete" | "current" | "error" | "upcoming"

interface WorkflowStepItem {
  id: string
  label: string
  description?: string | null
  state: WorkflowStepState
}

interface WorkflowStepperProps {
  items: WorkflowStepItem[]
  className?: string
}

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
