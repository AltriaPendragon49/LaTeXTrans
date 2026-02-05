"""
快速应用配置拦截代码补丁

运行此脚本将自动在 translate.py 中添加配置拦截代码

使用方法:
    python tests/apply_interceptor_patch.py       # 应用补丁
    python tests/apply_interceptor_patch.py undo  # 撤销补丁

作者: LaTeXTrans Team
日期: 2026-02-04
"""

import sys
from pathlib import Path


# 目标文件
TARGET_FILE = Path(__file__).parent.parent / "app" / "api" / "routes" / "translate.py"

# 查找标记 (在这一行后插入代码)
INSERTION_MARKER = 'Agent config: mode='

# 拦截代码
INTERCEPTOR_CODE = '''
        # ========== 配置拦截代码 - 开始 ==========
        from backend.tests.test_config_interceptor import ConfigInterceptor
        
        interceptor = ConfigInterceptor()
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

# 备份标记
BACKUP_MARKER = "# ========== 配置拦截代码 - 开始 =========="


def apply_patch():
    """应用补丁"""
    if not TARGET_FILE.exists():
        print(f"❌ 目标文件不存在: {TARGET_FILE}")
        return False
    
    # 读取文件
    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    # 检查是否已经应用
    if any(BACKUP_MARKER in line for line in lines):
        print("⚠️  补丁已经应用,无需重复操作")
        return False
    
    # 查找插入位置
    insert_index = None
    for i, line in enumerate(lines):
        if INSERTION_MARKER in line:
            # 找到包含 "Agent config: mode=" 的行
            # 继续往下查找,直到找到不是logger.info续行的空行或下一个语句
            j = i + 1
            # 跳过logger.info的多行续写
            while j < len(lines) and (lines[j].strip().startswith('f"') or 
                                       lines[j].strip().startswith('"') or
                                       'verify=' in lines[j]):
                j += 1
            # 在logger.info语句结束后的空行处插入
            insert_index = j
            break
    
    if insert_index is None:
        print(f"❌ 未找到插入位置标记: {INSERTION_MARKER}")
        return False
    
    # 插入代码
    lines.insert(insert_index, INTERCEPTOR_CODE)
    
    # 创建备份
    backup_file = TARGET_FILE.with_suffix(".py.backup")
    with open(backup_file, "w", encoding="utf-8") as f:
        # 写入原始文件内容(未修改的)
        with open(TARGET_FILE, "r", encoding="utf-8") as orig:
            f.write(orig.read())
    
    # 写入修改后的文件
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    print(f"✅ 补丁已应用到: {TARGET_FILE}")
    print(f"💾 备份文件: {backup_file}")
    print(f"📍 插入位置: 第 {insert_index + 1} 行")
    return True


def undo_patch():
    """撤销补丁"""
    backup_file = TARGET_FILE.with_suffix(".py.backup")
    
    if not backup_file.exists():
        print(f"❌ 未找到备份文件: {backup_file}")
        return False
    
    # 读取备份文件
    with open(backup_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 恢复原文件
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"✅ 已恢复原文件: {TARGET_FILE}")
    print(f"🗑️  可以删除备份文件: {backup_file}")
    return True


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "undo":
        print("撤销配置拦截补丁...")
        undo_patch()
    else:
        print("应用配置拦截补丁...")
        success = apply_patch()
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 补丁应用成功!")
            print("=" * 60)
            print("\n现在可以:")
            print("1. 启动后端服务")
            print("2. 在前端进行翻译操作")
            print("3. 查看 backend/tests/captured_configs/ 目录")
            print("4. 运行验证器: python tests/config_validator.py tests/captured_configs/config_*.json")
            print("\n撤销补丁: python tests/apply_interceptor_patch.py undo")


if __name__ == "__main__":
    main()
