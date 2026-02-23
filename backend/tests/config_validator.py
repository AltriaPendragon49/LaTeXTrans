"""
配置验证工具

用于验证高级配置的每个选项是否真实影响翻译行为

使用方法:
    python tests/config_validator.py <配置文件1> <配置文件2> ...

示例:
    python tests/config_validator.py captured_configs/config_*.json

作者: LaTeXTrans Team
日期: 2026-02-04
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class ConfigImpact(Enum):
    """配置影响级别"""
    CRITICAL = "关键影响"      # 直接影响翻译结果
    MODERATE = "中等影响"      # 影响编译或输出格式
    MINOR = "轻微影响"         # 影响性能或日志
    NONE = "无影响"           # 未生效或被覆盖


@dataclass
class ValidationResult:
    """验证结果"""
    config_key: str
    expected_impact: ConfigImpact
    actual_value: Any
    agent_value: Any
    is_effective: bool
    notes: str


class ConfigValidator:
    """配置验证器"""
    
    # 配置项映射关系 (advanced_config -> agent_config)
    CONFIG_MAPPINGS = {
        "translation_mode": {
            "agent_key": "mode",
            "transform": lambda x: {"full": 0, "abstract": 1, "terminology": 2}.get(x, 0),
            "impact": ConfigImpact.CRITICAL,
            "description": "翻译模式直接决定翻译范围"
        },
        "compile_strategy": {
            "agent_key": "latex_engine",
            "transform": lambda x: x,  # 直接传递
            "impact": ConfigImpact.MODERATE,
            "description": "编译策略影响PDF生成方式"
        },
        "bilingual_output": {
            "agent_key": "bilingual_mode",
            "transform": lambda x: x,  # 布尔值直接传递
            "impact": ConfigImpact.MODERATE,
            "description": "双语模式影响输出格式"
        },
        "translation_model": {
            "agent_key": "llm_config.model",
            "transform": lambda x: x,
            "impact": ConfigImpact.CRITICAL,
            "description": "翻译模型直接影响翻译质量"
        },
        "use_author_api": {
            "agent_key": "llm_config.base_url",
            "transform": None,  # 间接影响,需特殊处理
            "impact": ConfigImpact.MODERATE,
            "description": "API选择影响调用地址"
        },
        "custom_base_url": {
            "agent_key": "llm_config.base_url",
            "transform": None,  # 需要配合 use_author_api 检查
            "impact": ConfigImpact.MODERATE,
            "description": "自定义API地址"
        }
    }
    
    def validate_config_file(self, filepath: Path) -> List[ValidationResult]:
        """验证单个配置文件"""
        with open(filepath, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        advanced_config = config.get("advanced_config", {})
        agent_config = config.get("agent_config", {})
        llm_config = config.get("llm_config", {})
        
        results = []
        
        for config_key, mapping in self.CONFIG_MAPPINGS.items():
            result = self._validate_single_config(
                config_key,
                advanced_config.get(config_key),
                agent_config,
                llm_config,
                mapping
            )
            results.append(result)
        
        return results
    
    def _validate_single_config(
        self,
        config_key: str,
        config_value: Any,
        agent_config: Dict,
        llm_config: Dict,
        mapping: Dict
    ) -> ValidationResult:
        """验证单个配置项"""
        agent_key = mapping["agent_key"]
        transform = mapping["transform"]
        expected_impact = mapping["impact"]
        
        # 获取agent中的实际值
        if "." in agent_key:
            # 处理嵌套键 (如 llm_config.model)
            parts = agent_key.split(".")
            if parts[0] == "llm_config":
                agent_value = llm_config.get(parts[1])
            else:
                agent_value = agent_config.get(parts[1])
        else:
            agent_value = agent_config.get(agent_key)
        
        # 特殊处理: use_author_api 和 custom_base_url
        if config_key == "use_author_api":
            # 检查是否使用了自定义API
            is_custom = not config_value
            has_custom_url = bool(llm_config.get("base_url"))
            is_effective = (is_custom and has_custom_url) or (not is_custom and has_custom_url)
            notes = "使用作者API" if config_value else "使用自定义API"
            
            return ValidationResult(
                config_key=config_key,
                expected_impact=expected_impact,
                actual_value=config_value,
                agent_value=llm_config.get("base_url"),
                is_effective=is_effective,
                notes=notes
            )
        
        elif config_key == "custom_base_url":
            # 检查自定义URL是否生效
            use_author = agent_config.get("use_author_api", True)
            is_effective = not use_author and bool(config_value)
            notes = "已生效" if is_effective else "被use_author_api覆盖"
            
            return ValidationResult(
                config_key=config_key,
                expected_impact=expected_impact,
                actual_value=config_value,
                agent_value=llm_config.get("base_url"),
                is_effective=is_effective,
                notes=notes
            )
        
        # 通用验证
        if transform:
            expected_value = transform(config_value)
        else:
            expected_value = config_value
        
        is_effective = (agent_value == expected_value)
        notes = "✅ 配置已生效" if is_effective else f"⚠️ 期望 {expected_value}, 实际 {agent_value}"
        
        return ValidationResult(
            config_key=config_key,
            expected_impact=expected_impact,
            actual_value=config_value,
            agent_value=agent_value,
            is_effective=is_effective,
            notes=notes
        )
    
    def print_validation_report(self, filepath: Path, results: List[ValidationResult]):
        """打印验证报告"""
        print(f"\n{'=' * 80}")
        print(f"配置验证报告: {filepath.name}")
        print(f"{'=' * 80}\n")
        
        total = len(results)
        effective = sum(1 for r in results if r.is_effective)
        ineffective = total - effective
        
        # 统计信息
        print(f"📊 总计: {total} 项配置")
        print(f"   ✅ 生效: {effective} 项")
        print(f"   ⚠️  未生效: {ineffective} 项\n")
        
        # 详细列表
        print(f"{'配置项':<25} {'原始值':<20} {'Agent值':<20} {'状态':<10} {'备注'}")
        print(f"{'-' * 100}")
        
        for result in results:
            status = "✅" if result.is_effective else "⚠️"
            print(f"{result.config_key:<25} "
                  f"{str(result.actual_value):<20} "
                  f"{str(result.agent_value):<20} "
                  f"{status:<10} "
                  f"{result.notes}")
        
        print(f"\n{'=' * 80}\n")
    
    def compare_config_effects(self, filepaths: List[Path]):
        """比较多个配置文件的差异"""
        if len(filepaths) < 2:
            print("⚠️  需要至少2个配置文件进行比较")
            return
        
        print(f"\n{'=' * 80}")
        print(f"配置差异对比")
        print(f"{'=' * 80}\n")
        
        configs_data = []
        for filepath in filepaths:
            with open(filepath, "r", encoding="utf-8") as f:
                configs_data.append({
                    "name": filepath.name,
                    "data": json.load(f)
                })
        
        # 提取关键配置进行对比
        print(f"{'配置项':<25}", end="")
        for config in configs_data:
            print(f"{config['name'][:20]:<25}", end="")
        print()
        print(f"{'-' * (25 + 25 * len(configs_data))}")
        
        # 对比各项配置
        keys_to_compare = [
            "translation_mode",
            "compile_strategy",
            "bilingual_output",
            "translation_model"
        ]
        
        for key in keys_to_compare:
            print(f"{key:<25}", end="")
            for config in configs_data:
                value = config["data"].get("advanced_config", {}).get(key, "N/A")
                print(f"{str(value):<25}", end="")
            print()
        
        print(f"\n{'=' * 80}\n")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法: python config_validator.py <配置文件1> [配置文件2] ...")
        print("示例: python config_validator.py captured_configs/config_*.json")
        sys.exit(1)
    
    # 收集所有配置文件
    config_files = []
    for pattern in sys.argv[1:]:
        path = Path(pattern)
        if path.is_file():
            config_files.append(path)
        else:
            # 支持通配符
            parent = path.parent if path.parent.exists() else Path.cwd()
            config_files.extend(parent.glob(path.name))
    
    if not config_files:
        print("❌ 未找到配置文件")
        sys.exit(1)
    
    print(f"📁 找到 {len(config_files)} 个配置文件")
    
    # 验证每个配置文件
    validator = ConfigValidator()
    for config_file in config_files:
        results = validator.validate_config_file(config_file)
        validator.print_validation_report(config_file, results)
    
    # 如果有多个配置文件,进行对比
    if len(config_files) > 1:
        validator.compare_config_effects(config_files)


if __name__ == "__main__":
    main()
