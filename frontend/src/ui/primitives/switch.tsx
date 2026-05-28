/**
 * 开关组件 - 基于 Radix UI Switch 封装
 * 渲染可切换 on/off 状态的开关控件
 */
import * as React from "react"
import * as SwitchPrimitives from "@radix-ui/react-switch"

import { cn } from "@/lib/utils"

/** 开关组件，支持 checked/unchecked 状态切换，带滑动动画 */
const Switch = React.forwardRef<
    React.ElementRef<typeof SwitchPrimitives.Root>,
    React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root>
>(({ className, ...props }, ref) => (
    <SwitchPrimitives.Root
        className={cn(
            "peer inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border border-transparent transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--px-shell-panel)] disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:bg-[color:var(--px-shell-accent)] data-[state=checked]:shadow-[0_0_0_4px_color-mix(in_srgb,var(--px-shell-accent)_16%,transparent)] data-[state=unchecked]:bg-[color:var(--px-shell-line)]",
            className
        )}
        {...props}
        ref={ref}
    >
        <SwitchPrimitives.Thumb
            className={cn(
                "pointer-events-none block h-5 w-5 rounded-full bg-white shadow-sm ring-1 ring-black/5 transition-transform duration-200 data-[state=checked]:translate-x-5 data-[state=unchecked]:translate-x-0"
            )}
        />
    </SwitchPrimitives.Root>
))
Switch.displayName = SwitchPrimitives.Root.displayName

export { Switch }
