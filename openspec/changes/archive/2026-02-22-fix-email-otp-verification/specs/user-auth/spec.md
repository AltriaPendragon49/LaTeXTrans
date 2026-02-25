## MODIFIED Requirements

### Requirement: User Registration

系统 SHALL 支持新用户通过邮箱密码注册，并通过 8 位数字验证码（OTP）完成邮箱确认。

#### Scenario: 用户注册后收到 OTP 验证码邮件

- **WHEN** 用户在注册页面提交邮箱和密码
- **THEN** Supabase 发送包含 8 位数字验证码的邮件
- **AND** 页面显示内嵌式 OTP 输入界面

#### Scenario: 用户输入正确验证码完成注册

- **WHEN** 用户在 OTP 输入框中输入正确的 8 位验证码
- **THEN** 系统调用 verifyOtp 验证成功
- **AND** 自动登录并跳转到首页

#### Scenario: 用户输入错误验证码

- **WHEN** 用户输入错误的验证码并提交
- **THEN** 系统显示验证码错误或已过期的错误提示
- **AND** 用户可以重新输入

#### Scenario: 用户请求重发验证码

- **WHEN** 用户点击重新发送验证码按钮
- **THEN** 系统重新发送验证码邮件
- **AND** 按钮显示 60 秒倒计时防止频繁请求

## ADDED Requirements

### Requirement: OTP Input UX

OTP 输入界面 SHALL 提供流畅的验证码输入体验。

#### Scenario: 输入与提交体验

- **WHEN** OTP 输入界面显示时
- **THEN** 验证码输入框自动获得焦点
- **AND** 输入达到 8 位后，若用户按下回车键将触发验证

#### Scenario: 粘贴验证码自动填充

- **WHEN** 用户从邮件复制 8 位验证码并粘贴到输入框
- **THEN** 系统自动填入并截断/过滤非数字字符
