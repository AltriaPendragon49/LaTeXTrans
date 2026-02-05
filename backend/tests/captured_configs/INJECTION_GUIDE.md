# 配置拦截器嵌入指南

## 方法1: 临时嵌入代码 (推荐用于测试)

在 `backend/app/api/routes/translate.py` 的 `run_translation` 函数中,
**在第152行 (logger.info 之后)** 添加以下代码:

```python

# ========== 配置拦截代码 - 开始 ==========
from backend.tests.test_config_interceptor import ConfigInterceptor

# 创建拦截器实例
interceptor = ConfigInterceptor()

# 捕获配置
config_file = interceptor.capture_config(
    task_id=task_id,
    advanced_config=advanced_config.model_dump(),
    agent_config=agent_config,
    llm_config=llm_config,
    additional_info={
        "target_language": target_language,
        "source_language": source_language,
        "source_path": str(source_path),
        "output_dir": str(output_dir)
    }
)

logger.info(f"🔍 配置已拦截并保存到: {config_file}")
# ========== 配置拦截代码 - 结束 ==========

```

### 具体位置:
```python
# 第148-153行附近
logger.info(f"Agent config: mode={agent_config['mode']}, "
            f"engine={agent_config['latex_engine']}, "
            f"verify={agent_config['use_verification_agent']}")

# 👇 在此处添加拦截代码

# ========== 配置拦截代码 - 开始 ==========
from backend.tests.test_config_interceptor import ConfigInterceptor

# 创建拦截器实例
interceptor = ConfigInterceptor()

# 捕获配置
config_file = interceptor.capture_config(
    task_id=task_id,
    advanced_config=advanced_config.model_dump(),
    agent_config=agent_config,
    llm_config=llm_config,
    additional_info={
        "target_language": target_language,
        "source_language": source_language,
        "source_path": str(source_path),
        "output_dir": str(output_dir)
    }
)

logger.info(f"🔍 配置已拦截并保存到: {config_file}")
# ========== 配置拦截代码 - 结束 ==========


# 第154行继续原代码
# Create coordinator agent
coordinator = CoordinatorAgent(
    config=agent_config,
    ...
)
```

## 方法2: 修改 build_llm_config 函数

在 `build_llm_config` 函数返回前添加日志:

```python
def build_llm_config(advanced_config: AdvancedConfig) -> Dict[str, Any]:
    # ... 原有代码 ...
    
    # 👇 在return前添加
    config_dict = {...}  # 原返回的配置字典
    logger.info(f"🔍 LLM Config: {json.dumps(config_dict, indent=2)}")
    return config_dict
```

## 方法3: 使用装饰器 (适合长期测试)

```python
from backend.tests.test_config_interceptor import ConfigInterceptor

def intercept_config(func):
    def wrapper(task_id, target_language, source_language, advanced_config):
        # 调用原函数前拦截
        interceptor = ConfigInterceptor()
        
        result = func(task_id, target_language, source_language, advanced_config)
        
        # 在这里添加拦截逻辑...
        return result
    return wrapper

@intercept_config
async def run_translation(...):
    ...
```

## 验证配置捕获是否成功

运行翻译后,检查:
```bash
backend/tests/captured_configs/
```

应该会生成类似:
```
config_a1b2c3d4_20260204_160530.json
```

## 配置文件结构

```json
{
  "metadata": {
    "task_id": "...",
    "captured_at": "2026-02-04T16:05:30",
    "timestamp": "20260204_160530"
  },
  "advanced_config": {
    "translation_mode": "full",
    "compile_strategy": "auto",
    ...
  },
  "agent_config": {
    "mode": 0,
    "latex_engine": "auto",
    ...
  },
  "llm_config": {
    "base_url": "...",
    "model": "...",
    ...
  }
}
```

## 测试用例

使用不同的配置组合测试:

1. **默认配置**: 不修改任何高级选项
2. **摘要模式**: translation_mode = "abstract"
3. **XeLaTeX**: compile_strategy = "xelatex"
4. **关闭验证**: enable_verification = False
5. **双语输出**: bilingual_output = True
6. **自定义API**: use_author_api = False

每次测试后,检查生成的配置文件,对比差异。

## 比较配置差异

```python
from backend.tests.test_config_interceptor import ConfigInterceptor

interceptor = ConfigInterceptor()
diff = interceptor.compare_configs(
    Path("captured_configs/config_abc_20260204_160530.json"),
    Path("captured_configs/config_def_20260204_160545.json")
)

print(json.dumps(diff, indent=2))
```
