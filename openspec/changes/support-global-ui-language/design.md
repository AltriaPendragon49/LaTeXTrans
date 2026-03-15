# 全局多语言 UI 架构设计

## 组件设计 (ui-ux-pro-max 指导原则)
语言选择器组件必须满足高品质的 UX 设计标准：

1. **交互设计**: 
    - 不建议使用系统原生 Select 如果它的样式无法统一适配主题。应优先考虑使用 `shadcn/ui` 现有的 `Select` 或 `DropdownMenu` 进行封装定制。
    - 提供清晰直观的语言切换图标 (例如 `Languages` icon 搭配 lucide-react)。
    - 提供顺滑的悬浮反馈（通过 Tailwind `transition-colors`, `hover:bg-accent` 实现），避免瞬间状体突变。

2. **可访问性与性能 (CRITICAL/HIGH)**:
    - 遵循可访问性标准，支持键盘导航 (`Tab` 键聚焦，回车或空格展开)，且具备极高对比度（文本 4.5:1）。
    - 具备合理的 `aria-label="选择全局界面语言"`，避免仅通过颜色区分交互状态。
    - 避免为了动画而使用宽度/高度变化导致的重绘，尽量使用 `transform/opacity` 实现下拉菜单出现效果。

3. **状态持久化与延迟加载**: 
    - 在组件初次加载时读取系统的 local state/store 设置值，避免服务端甚至客户端 hydration 期间的语言闪烁跳动 (Layout Shift)。
    - 根据需要后续可支持对大型翻译 JSON 进行懒加载分割。
