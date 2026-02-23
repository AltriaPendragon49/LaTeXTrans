# web-ui Specification Delta

## MODIFIED Requirements

### Requirement: Advanced Configuration Panel
前端 SHALL 在 Dashboard 页面提供完整的高级配置面板，包含翻译模式、编译策略、术语表生成等选项。

#### Scenario: 配置使用作者默认API
- **WHEN** 用户在 Dashboard 高级配置面板查看功能开关区域
- **THEN** 系统显示两个并排的 toggle 卡片：
  - 「使用作者默认 API」toggle（左侧）
  - 「生成术语表」toggle（右侧）
- **AND** 无"验证代理"选项

## REMOVED Requirements

（无整体移除的 requirement。原"验证代理"从未作为独立 requirement 存在于 web-ui spec 中，仅在 toggle 布局中隐含。此 delta 明确记录了布局变更。）
