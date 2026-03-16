# global-language-selection Specification

## Purpose
定义全局 UI 语言选择、即时切换、偏好持久化以及壳层辅助文案本地化规则，确保前端所有用户可见静态界面文案能够随所选语言统一呈现，并在后续访问中保持一致。

## Requirements
### Requirement: 用户应当能够从 8 种系统支持语言中选择并更改全局的用户界面呈现语言。
系统界面 SHALL (必须) 允许全局切换为这 8 种语言上下文，与现有的翻译选项保持一致。

#### Scenario: 切换界面语言
- **WHEN** 用户点击应用全局导航区域上的语言选择器时
- **THEN** 他们 MUST (必须) 看到 8 种可用语言选项（英语、中文、日语、韩语、德语、法语、西班牙语、俄语）。
- **WHEN** 用户点击并选择其中一种新语言（例如：“英语”）时
- **THEN** 整个系统前端界面的静态文本和组件语言 SHALL (必须) 立即切换为所选语言。
- **THEN** 此偏好设置 SHALL (必须) 被无感持久化保存，在未来的会话乃至页面刷新时自动应用。

### Requirement: 语言选择组件必须符合针对深浅色模式与桌面移动端自适应的高标准 UI/UX 规范。
UI/UX SHALL (必须) 满足高对比度与无障碍访问准则的要求。

#### Scenario: 可访问性与主题适配
- **WHEN** 用户使用键盘（按 Tab 键等）进行导航选中交互组件时
- **THEN** 该语言选择组件 SHALL (必须) 呈现出外边框轮廓 Focus Ring，支持无障碍屏幕阅读器播报（Aria Label）。
- **THEN** 无论当前操作系统切换为亮色（Light）模式还是暗色（Dark）模式，该选项悬停背景反馈 SHALL (必须) 均有足够对比度的颜色区分，保证整体排版不发生跳动脱节（Layout Shift）。

### Requirement: Users can switch the global UI language across all supported locales
The frontend MUST allow users to switch the application UI language between `en`, `zh`, `ja`, `ko`, `de`, `fr`, `es`, and `ru`, and MUST persist the selected language across reloads.

#### Scenario: Switching the UI language
- **WHEN** the user opens the global language selector from the application shell
- **THEN** the system MUST display all 8 supported UI languages
- **WHEN** the user selects a different language
- **THEN** the visible UI copy MUST update immediately without requiring a page refresh
- **AND** the preference MUST be restored on the next visit

### Requirement: The global language selector provides localized accessibility copy
The application shell MUST localize the selector label, related navigation labels, and accessibility text used by shell components.

#### Scenario: Shell a11y copy follows the active language
- **WHEN** the active UI language changes
- **THEN** the selector label, sidebar toggle label, sheet close label, and related accessible text MUST switch to the same language
- **AND** keyboard and screen-reader interaction MUST continue to work
