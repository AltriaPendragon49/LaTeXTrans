# web-ui Spec Delta

## ADDED Requirements

### Requirement: Interactive Dismissible Tips

前端 SHALL 在 Dashboard 页面提供交互式提示框，用于引导用户并平衡页面空间，支持手动快速影藏。

#### Scenario: 提示框显示与点击消失
- **GIVEN** Dashboard 页面加载
- **WHEN** 对应的显示状态为真（默认每次加载为真）
- **THEN** 页面显示相关的 Info Tip（如 ArXiv 下载耗时提示、Nvidia API 性能预警）
- **WHEN** 用户点击提示框任何区域
- **THEN** 提示框通过渐隐缩放动画（fade-out & zoom-out）消失
- **AND** 该提示框在本次页面会话期间不再出现

#### Scenario: 悬停显示关闭反馈
- **GIVEN** 提示框处于显示状态
- **WHEN** 用户将鼠标悬停在提示框上方
- **THEN** 提示框背景色产生微弱变化（交互反馈）
- **AND** 提示框右侧显示 `X` 关闭图标，提示该区域可点击影藏

### Requirement: API Quality and Performance Warnings

前端 SHALL 在翻译配置面板显式提醒默认 API 的性能局限，引导用户进行优化设置。

#### Scenario: 显示 Nvidia 免费 API 警告
- **GIVEN** Dashboard 页面加载
- **THEN** 在 "Advanced Configuration" 栏右侧显示琥珀色（Amber）警告标签
- **AND** 文本告知用户默认 API 为英伟达免费层级，可能影响质量和速度
- **AND** 该警告标签支持交互式点击消失逻辑
