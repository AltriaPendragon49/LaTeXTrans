"""
配置拦截器测试工具

用途:
1. 截获真实启用的配置参数
2. 验证高级配置选项是否真实影响翻译行为
3. 输出配置文件供测试使用

使用方法:
方法1 - 独立运行拦截器:
    python tests/test_config_interceptor.py

方法2 - 嵌入到代码中:
    在 translate.py 的 run_translation 函数中添加拦截代码

作者: LaTeXTrans Team
日期: 2026-02-04
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 配置输出目录
CONFIG_OUTPUT_DIR = Path(__file__).parent / "captured_configs"
CONFIG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConfigInterceptor:
    """配置拦截器 - 捕获真实配置数据"""
    
    def __init__(self, output_dir: Path = CONFIG_OUTPUT_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def capture_config(
        self,
        task_id: str,
        advanced_config: Dict[str, Any],
        agent_config: Dict[str, Any],
        llm_config: Dict[str, Any],
        additional_info: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        捕获完整配置快照
        
        Args:
            task_id: 任务ID
            advanced_config: 前端传入的高级配置
            agent_config: 构建的Agent配置
            llm_config: LLM配置
            additional_info: 额外信息(如源语言、目标语言等)
        
        Returns:
            保存的配置文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"config_{task_id[:8]}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        # 构建完整配置快照
        config_snapshot = {
            "metadata": {
                "task_id": task_id,
                "captured_at": datetime.now().isoformat(),
                "timestamp": timestamp
            },
            "advanced_config": advanced_config,
            "agent_config": agent_config,
            "llm_config": {
                "base_url": llm_config.get("base_url", ""),
                "model": llm_config.get("model", ""),
                "timeout": llm_config.get("timeout", 60),
                "api_key_masked": "*" * 20 if llm_config.get("api_key") else None
            },
            "additional_info": additional_info or {}
        }
        
        # 保存到文件
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config_snapshot, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 配置已捕获: {filepath}")
        logger.info(f"📋 配置摘要:")
        logger.info(f"   - 翻译模式: {advanced_config.get('translation_mode', 'N/A')}")
        logger.info(f"   - 编译策略: {advanced_config.get('compile_strategy', 'N/A')}")
        logger.info(f"   - 双语输出: {advanced_config.get('bilingual_output', 'N/A')}")
        logger.info(f"   - 翻译模型: {advanced_config.get('translation_model', 'N/A')}")
        logger.info(f"   - Agent模式: {agent_config.get('mode', 'N/A')}")
        logger.info(f"   - LaTeX引擎: {agent_config.get('latex_engine', 'N/A')}")
        
        return filepath
    
    def compare_configs(self, filepath1: Path, filepath2: Path) -> Dict[str, Any]:
        """
        比较两个配置文件的差异
        
        Args:
            filepath1: 配置文件1
            filepath2: 配置文件2
        
        Returns:
            差异字典
        """
        with open(filepath1, "r", encoding="utf-8") as f:
            config1 = json.load(f)
        
        with open(filepath2, "r", encoding="utf-8") as f:
            config2 = json.load(f)
        
        differences = {
            "advanced_config": self._compare_dicts(
                config1.get("advanced_config", {}),
                config2.get("advanced_config", {})
            ),
            "agent_config": self._compare_dicts(
                config1.get("agent_config", {}),
                config2.get("agent_config", {})
            )
        }
        
        return differences
    
    def _compare_dicts(self, dict1: Dict, dict2: Dict) -> Dict[str, tuple]:
        """比较字典差异"""
        all_keys = set(dict1.keys()) | set(dict2.keys())
        differences = {}
        
        for key in all_keys:
            val1 = dict1.get(key)
            val2 = dict2.get(key)
            
            if val1 != val2:
                differences[key] = (val1, val2)
        
        return differences


def create_test_config_samples():
    """创建测试配置样例"""
    samples_dir = CONFIG_OUTPUT_DIR / "samples"
    samples_dir.mkdir(exist_ok=True)
    
    # 样例1: 默认配置
    default_config = {
        "name": "默认配置",
        "advanced_config": {
            "translation_mode": "full",
            "compile_strategy": "auto",
            "bilingual_output": False,
            "translation_model": "deepseek",
            "use_author_api": True,
            "custom_base_url": None,
            "custom_api_key": None
        }
    }
    
    # 样例2: 仅摘要翻译
    abstract_only_config = {
        "name": "仅摘要翻译",
        "advanced_config": {
            "translation_mode": "abstract",
            "compile_strategy": "pdflatex",
            "bilingual_output": False,
            "translation_model": "gpt-4.1-mini",
            "use_author_api": True,
            "custom_base_url": None,
            "custom_api_key": None
        }
    }
    
    # 样例3: 双语输出 + XeLaTeX
    bilingual_config = {
        "name": "双语输出_XeLaTeX",
        "advanced_config": {
            "translation_mode": "full",
            "compile_strategy": "xelatex",
            "bilingual_output": True,
            "translation_model": "deepseek",
            "use_author_api": True,
            "custom_base_url": None,
            "custom_api_key": None
        }
    }
    
    # 样例4: 自定义API
    custom_api_config = {
        "name": "自定义API配置",
        "advanced_config": {
            "translation_mode": "full",
            "compile_strategy": "auto",
            "bilingual_output": False,
            "translation_model": "gpt-4",
            "use_author_api": False,
            "custom_base_url": "https://aicanapi.com",
            "custom_api_key": "sk-test-key-xxxxx"
        }
    }
    
    samples = [
        default_config,
        abstract_only_config,
        bilingual_config,
        custom_api_config
    ]
    
    for sample in samples:
        filename = f"sample_{sample['name']}.json"
        filepath = samples_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(sample, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 样例配置已创建: {filepath}")


# ============================================
# 嵌入代码片段 - 方法1
# ============================================

INTERCEPTOR_CODE_SNIPPET = '''
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
'''


def generate_injection_guide():
    """生成嵌入指南"""
    guide_file = CONFIG_OUTPUT_DIR / "INJECTION_GUIDE.md"
    
    guide_content = f"""# 配置拦截器嵌入指南

## 方法1: 临时嵌入代码 (推荐用于测试)

在 `backend/app/api/routes/translate.py` 的 `run_translation` 函数中,
**在第152行 (logger.info 之后)** 添加以下代码:

```python
{INTERCEPTOR_CODE_SNIPPET}
```

### 具体位置:
```python
# 第148-153行附近
logger.info(f"Agent config: mode={{agent_config['mode']}}, "
            f"engine={{agent_config['latex_engine']}}, "
            f"verify={{agent_config['use_verification_agent']}}")

# 👇 在此处添加拦截代码
{INTERCEPTOR_CODE_SNIPPET}

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
    config_dict = {{...}}  # 原返回的配置字典
    logger.info(f"🔍 LLM Config: {{json.dumps(config_dict, indent=2)}}")
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
{{
  "metadata": {{
    "task_id": "...",
    "captured_at": "2026-02-04T16:05:30",
    "timestamp": "20260204_160530"
  }},
  "advanced_config": {{
    "translation_mode": "full",
    "compile_strategy": "auto",
    ...
  }},
  "agent_config": {{
    "mode": 0,
    "latex_engine": "auto",
    ...
  }},
  "llm_config": {{
    "base_url": "...",
    "model": "...",
    ...
  }}
}}
```

## 测试用例

使用不同的配置组合测试:

1. **默认配置**: 不修改任何高级选项
2. **摘要模式**: translation_mode = "abstract"
3. **XeLaTeX**: compile_strategy = "xelatex"
4. **双语输出**: bilingual_output = True
5. **自定义API**: use_author_api = False

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
"""
    
    with open(guide_file, "w", encoding="utf-8") as f:
        f.write(guide_content)
    
    logger.info(f"📖 嵌入指南已生成: {guide_file}")
    return guide_file


def main():
    """主函数 - 生成所有测试资源"""
    logger.info("=" * 60)
    logger.info("配置拦截器测试工具初始化")
    logger.info("=" * 60)
    
    # 创建输出目录
    CONFIG_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 输出目录: {CONFIG_OUTPUT_DIR}")
    
    # 生成样例配置
    logger.info("\n生成测试样例配置...")
    create_test_config_samples()
    
    # 生成嵌入指南
    logger.info("\n生成嵌入指南...")
    guide_file = generate_injection_guide()
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 初始化完成!")
    logger.info("=" * 60)
    logger.info(f"\n📖 请查看嵌入指南: {guide_file}")
    logger.info(f"📁 样例配置目录: {CONFIG_OUTPUT_DIR / 'samples'}")
    logger.info(f"📁 捕获配置将保存到: {CONFIG_OUTPUT_DIR}")
    logger.info("\n使用方法:")
    logger.info("1. 查看 INJECTION_GUIDE.md 了解如何嵌入代码")
    logger.info("2. 在 translate.py 中添加拦截代码")
    logger.info("3. 运行翻译,配置将自动保存到 captured_configs/")
    logger.info("4. 对比不同配置的差异,验证配置影响")


if __name__ == "__main__":
    main()
