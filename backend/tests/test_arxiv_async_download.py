"""
arXiv 异步下载流程测试

用于验证 add-arxiv-download-progress OpenSpec 变更中的以下功能：
1. TaskManager 正确管理下载任务状态
2. 进度更新正确同步到 TaskManager
3. 失败场景正确处理

测试日期: 2026-02-06
"""

import pytest
from pathlib import Path
import sys

# Add backend to path for proper imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.services.task_manager import TaskManager
from backend.app.core.config import TaskStatus


class TestArxivTaskStatus:
    """arXiv 任务状态管理测试套件"""
    
    @pytest.fixture
    def task_manager(self):
        """创建测试用 TaskManager 实例"""
        return TaskManager()
    
    def test_create_arxiv_task(self, task_manager):
        """测试：创建 arXiv 类型任务"""
        # Act
        task_id = task_manager.create_task(
            source_type="arxiv", 
            arxiv_id="2301.12345"
        )
        
        # Assert
        task = task_manager.get_task(task_id)
        assert task is not None
        assert task["source_type"] == "arxiv"
        assert task["arxiv_id"] == "2301.12345"
        assert task["status"] == TaskStatus.PENDING.value
        assert task["progress"] == 0
    
    def test_update_downloading_status(self, task_manager):
        """测试：更新下载中状态"""
        # Arrange
        task_id = task_manager.create_task(source_type="arxiv")
        
        # Act
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.PROCESSING.value,
            progress=0,
            stage="downloading",
            message="开始下载 arXiv 论文..."
        )
        
        # Assert
        task = task_manager.get_task(task_id)
        assert task["status"] == TaskStatus.PROCESSING.value
        assert task["stage"] == "downloading"
        assert task["progress"] == 0
    
    def test_download_success_updates_status(self, task_manager):
        """测试：下载成功后更新状态为 ready"""
        # Arrange
        task_id = task_manager.create_task(source_type="arxiv")
        
        # Act - 模拟成功下载后的状态更新
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.PENDING.value,  # Ready for translation
            progress=100,
            message="arXiv paper downloaded successfully",
            source_path="/path/to/source",
            source_available=True
        )
        
        # Assert
        task = task_manager.get_task(task_id)
        assert task["status"] == TaskStatus.PENDING.value
        assert task["progress"] == 100
        assert task["source_available"] == True
        assert task["source_path"] == "/path/to/source"
    
    def test_download_failure_updates_status(self, task_manager):
        """测试：下载失败时正确记录错误"""
        # Arrange
        task_id = task_manager.create_task(source_type="arxiv")
        
        # Act - 模拟下载失败
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            error="Network timeout",
            message="Failed to download arXiv paper"
        )
        
        # Assert
        task = task_manager.get_task(task_id)
        assert task["status"] == TaskStatus.FAILED.value
        assert "Network timeout" in task["error"]
    
    def test_no_source_failure(self, task_manager):
        """测试：arXiv 无源码时失败状态"""
        # Arrange
        task_id = task_manager.create_task(source_type="arxiv")
        
        # Act
        task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED.value,
            message="arXiv 论文没有可用的 TeX 源码"
        )
        
        # Assert
        task = task_manager.get_task(task_id)
        assert task["status"] == TaskStatus.FAILED.value
        assert "没有可用的 TeX 源码" in task["message"]


class TestProgressTracking:
    """进度追踪测试套件"""
    
    @pytest.fixture
    def task_manager(self):
        """创建测试用 TaskManager 实例"""
        return TaskManager()
    
    def test_progress_update_stages(self, task_manager):
        """测试：进度更新支持所有预定义阶段 (0→30→60→80→100%)"""
        # Arrange
        task_id = task_manager.create_task(source_type="arxiv")
        
        # 根据 design.md 定义的阶段和进度范围
        stages = [
            ("downloading", 15),      # 0-30%: 下载 TeX 源码
            ("extracting", 45),       # 30-60%: 解压文件
            ("downloading_pdf", 70),  # 60-80%: 下载 PDF
            ("validating", 90),       # 80-100%: 验证文件
        ]
        
        # Act & Assert
        for stage, progress in stages:
            task_manager.update_task(
                task_id=task_id,
                stage=stage,
                progress=progress
            )
            task = task_manager.get_task(task_id)
            assert task["stage"] == stage
            assert task["progress"] == progress
    
    def test_progress_clamps_to_valid_range(self, task_manager):
        """测试：进度值限制在 0-100 范围内"""
        # Arrange
        task_id = task_manager.create_task(source_type="arxiv")
        
        # Act - 负数应 clamp 到 0
        task_manager.update_task(task_id=task_id, progress=-10)
        task = task_manager.get_task(task_id)
        assert task["progress"] == 0
        
        # Act - 超过 100 应 clamp 到 100
        task_manager.update_task(task_id=task_id, progress=150)
        task = task_manager.get_task(task_id)
        assert task["progress"] == 100
    
    def test_progress_increments_correctly(self, task_manager):
        """测试：进度正确递增 (0→30→60→80→100%)"""
        # Arrange
        task_id = task_manager.create_task(source_type="arxiv")
        expected_progress = [0, 30, 60, 80, 100]
        
        # Act & Assert
        for progress in expected_progress:
            task_manager.update_task(task_id=task_id, progress=progress)
            task = task_manager.get_task(task_id)
            assert task["progress"] == progress


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
