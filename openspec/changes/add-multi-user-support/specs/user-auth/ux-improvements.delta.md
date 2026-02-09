# UX 交互改进 Spec Delta

**日期**: 2026-02-10  
**类型**: 前端交互优化  
**影响范围**: 前端 UI/UX

## 变更概述

修复两个用户反馈的前端交互问题：
1. Load Source 按钮点击无即时反馈
2. 登录后系统配置未自动加载

## 文件变更

### 1. frontend/src/pages/Dashboard.tsx

**变更类型**: MODIFY  
**变更内容**:
- 添加 `isLoadingSource` 本地状态追踪按钮加载
- 导入 `toast` 用于即时通知
- `handleLoadArxiv` 函数在调用 API 前立即设置 loading 状态并显示 Toast
- 按钮添加 `active:scale-95` 缩放动画和即时 loading 图标切换

**代码差异**:
```diff
+ import { toast } from 'sonner'

  export default function Dashboard() {
+     const [isLoadingSource, setIsLoadingSource] = useState(false)

      const handleLoadArxiv = async () => {
          if (!localArxivId.trim()) return
+         setIsLoadingSource(true)
+         toast.info('正在加载源文件，请稍候...')
          try {
              await startArxivDownload(localArxivId)
          } catch (e) {
          } finally {
+             setIsLoadingSource(false)
          }
      }

      <Button
          onClick={handleLoadArxiv}
+         disabled={!localArxivId || isLoadingSource || isDownloading || (status === 'processing')}
+         className="transition-all duration-150 active:scale-95"
      >
+         {(isLoadingSource || isDownloading) ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
          Load Source
      </Button>
```

---

### 2. frontend/src/store/useStore.ts

**变更类型**: MODIFY  
**变更内容**:
- `loadUserSettings` 接口签名添加可选参数 `forceReload?: boolean`
- 实现逻辑支持强制重新加载，绕过 `userSettingsLoaded` 缓存检查

**代码差异**:
```diff
  interface TranslationState {
-     loadUserSettings: () => Promise<void>
+     loadUserSettings: (forceReload?: boolean) => Promise<void>
  }

  export const useStore = create<TranslationState>((set, get) => ({
-     loadUserSettings: async () => {
-         if (get().userSettingsLoaded) return
+     loadUserSettings: async (forceReload = false) => {
+         if (get().userSettingsLoaded && !forceReload) return
          // ... rest of implementation
      }
  }))
```

---

### 3. frontend/src/contexts/AuthContext.tsx

**变更类型**: MODIFY  
**变更内容**:
- 导入 `toast` 用于登录成功通知
- `signIn` 函数在登录成功后调用 `invalidateUserSettings()` 和 `loadUserSettings(true)` 强制重新加载配置
- 显示 Toast 通知用户配置已加载

**代码差异**:
```diff
+ import { toast } from 'sonner'

  const signIn = async (email: string, password: string) => {
      if (error) {
          setError(error.message)
+     } else {
+         try {
+             const { useStore } = await import('@/store/useStore')
+             useStore.getState().invalidateUserSettings()
+             await useStore.getState().loadUserSettings(true)
+             toast.success('系统设置已加载', {
+                 description: '您保存的默认配置已自动应用',
+                 duration: 4000,
+             })
+         } catch (e) {
+             console.warn('[Auth] Failed to load user settings after login:', e)
+         }
      }
      return { error }
  }
```

---

## 用户体验改进

| 交互场景 | 改进前 | 改进后 |
|----------|--------|--------|
| 点击 Load Source 按钮 | 延迟 2-3 秒无反馈 | 立即显示 loading 图标、Toast 提示、按钮缩放动画 |
| 登录后访问 Dashboard | 配置未自动应用，需手动刷新 | 自动加载配置并显示 Toast 确认 |
| 新建翻译配置 | 使用系统默认值 | 自动应用保存的用户配置 |

## 测试验证

### Test 1: Load Source 按钮反馈
1. 访问 Dashboard 页面
2. 输入有效 ArXiv ID
3. 点击 Load Source 按钮
4. **预期**: 按钮立即显示 loading 图标 + Toast 提示

### Test 2: 登录后配置自动加载
1. 登出（如已登录）
2. 登录测试账户
3. 观察登录成功后的行为
4. **预期**: Toast 显示「系统设置已加载」
5. 访问 Dashboard 高级配置
6. **预期**: 配置显示为用户保存的值

## 依赖关系

- 无新增外部依赖
- 使用已有的 `sonner` toast 库
- 兼容现有的 Zustand store 架构
