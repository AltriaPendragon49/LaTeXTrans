import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n'
import App from './App.tsx'

/** 应用启动引导函数：等待社区数据预加载完成后挂载 React 根节点 */
async function bootstrap() {
  const bootstrapPromise = window.__COMMUNITY_BOOTSTRAP_PROMISE__
  if (bootstrapPromise) {
    await Promise.race([
      bootstrapPromise.catch(() => undefined),
      new Promise((resolve) => window.setTimeout(resolve, 900)),
    ])
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void bootstrap()
