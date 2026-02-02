# 任务去重与并发处理 - 技术设计

## 系统架构

### 组件关系

```mermaid
graph TB
    subgraph "任务层"
        T1[Task 1]
        T2[Task 2]
        T3[Task 3]
    end
    
    subgraph "去重层"
        DC[DownloadCache]
        DL[DownloadLockManager]
    end
    
    subgraph "下载层"
        AD[ArXiv Downloader]
        DD[DOI Downloader]
    end
    
    subgraph "存储层"
        FS[File System]
    end
    
    T1 & T2 & T3 --> DC
    DC --> DL
    DL --> AD & DD
    AD & DD --> FS
```

## 核心模块

### 1. DownloadCache

```python
class DownloadCache:
    """下载缓存管理器"""
    
    def get_cache_key(self, source_type: str, source_id: str, version: str) -> str:
        """生成缓存 key"""
        return f"{source_type}:{source_id}:{version}"
    
    def get_cached_path(self, cache_key: str) -> Optional[Path]:
        """查询缓存，返回已下载的路径"""
        pass
    
    def set_cached_path(self, cache_key: str, path: Path) -> None:
        """设置缓存路径"""
        pass
```

### 2. DownloadLockManager

```python
class DownloadLockManager:
    """下载锁管理器"""
    
    def acquire(self, cache_key: str, timeout: float = 300) -> DownloadLock:
        """获取下载锁，若已锁定则等待"""
        pass
    
    def release(self, cache_key: str) -> None:
        """释放锁"""
        pass
    
    def is_locked(self, cache_key: str) -> bool:
        """检查是否被锁定"""
        pass
```

## 并发处理流程

### 场景：用户 A 和 B 同时提交 arXiv:2401.12345

```mermaid
sequenceDiagram
    participant A as User A Task
    participant B as User B Task
    participant C as DownloadCache
    participant L as LockManager
    participant D as Downloader

    A->>C: check_cache("arxiv:2401.12345:v1")
    C-->>A: None (未缓存)
    A->>L: acquire_lock("arxiv:2401.12345:v1")
    L-->>A: Lock acquired
    
    B->>C: check_cache("arxiv:2401.12345:v1")
    C-->>B: None (未缓存)
    B->>L: acquire_lock("arxiv:2401.12345:v1")
    Note over B,L: 等待锁释放...
    
    A->>D: download()
    D-->>A: /sources/arxiv_2401.12345_v1/
    A->>C: set_cache("arxiv:2401.12345:v1", path)
    A->>L: release_lock()
    
    L-->>B: Lock acquired (A 释放后)
    B->>C: check_cache("arxiv:2401.12345:v1")
    C-->>B: /sources/arxiv_2401.12345_v1/ (命中!)
    B->>L: release_lock()
```

## 存储结构

```
/sources/
├── arxiv_2401.12345_v1/     # 共享源码目录（只读）
│   ├── main.tex
│   └── figures/
├── arxiv_2401.12345_v2/     # 不同版本独立存储
└── doi_10.1000_xyz/
```

## 边界情况处理

| 场景 | 处理方式 |
|------|----------|
| 下载失败 | 释放锁，不设置缓存，下次重试 |
| 锁超时 | 强制释放，记录警告日志 |
| 进程崩溃 | 启动时清理孤立锁 |
| 缓存过期 | 可配置 TTL，定期清理 |
