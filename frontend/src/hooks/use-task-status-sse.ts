/**
 * useTaskStatusSSE — 通过 Server-Sent Events 获取任务实时状态更新
 *
 * 功能：
 * - SSE 连接接收实时更新
 * - SSE 失败后自动切换到轮询降级模式
 * - 心跳检测以监控连接健康状态
 * - 组件卸载时自动清理连接
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { API_BASE_URL } from '@/api-base';

/** 任务状态数据 */
export interface TaskStatus {
    task_id: string;
    status: string;
    progress: number;
    stage: string;
    message: string;
    detail_code?: string | null;
    detail_params?: Record<string, string | number | boolean | null> | null;
    error?: string | null;
    warnings?: string | null;
    failure_reason_code?: string | null;
    failure_class?: string | null;
    guard_phase?: string | null;
    replay_bundle_ref?: string | null;
    source_available: boolean;
}

/** useTaskStatusSSE 配置选项 */
interface UseTaskStatusSSEOptions {
    /** 是否启用 SSE 连接，默认 true */
    enabled?: boolean;
    /** 降级轮询间隔（毫秒），默认 2000 */
    pollInterval?: number;
    /** 任务完成回调 */
    onComplete?: (status: TaskStatus) => void;
    /** 错误回调 */
    onError?: (error: Error) => void;
}

/** useTaskStatusSSE 返回值 */
interface UseTaskStatusSSEReturn {
    /** 当前任务状态 */
    status: TaskStatus | null;
    /** 是否通过 SSE 连接 */
    isConnected: boolean;
    /** 是否使用轮询降级模式 */
    isPolling: boolean;
    /** 当前错误 */
    error: Error | null;
    /** 是否正在加载 */
    isLoading: boolean;
    /** 手动重试连接 */
    retry: () => void;
}

/**
 * SSE 任务状态 Hook
 *
 * @param taskId - 任务 ID，null 时不发起连接
 * @param options - 配置选项
 * @returns 包含状态、连接状态和重试方法的对象
 */
export function useTaskStatusSSE(
    taskId: string | null,
    options: UseTaskStatusSSEOptions = {}
): UseTaskStatusSSEReturn {
    const {
        enabled = true,
        pollInterval = 2000,
        onComplete,
        onError,
    } = options;

    const [status, setStatus] = useState<TaskStatus | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [isPolling, setIsPolling] = useState(false);
    const [error, setError] = useState<Error | null>(null);
    const [isLoading, setIsLoading] = useState(false);

    const eventSourceRef = useRef<EventSource | null>(null);
    const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const retryCountRef = useRef(0);
    const maxRetries = 3;

    /** 清理 SSE 连接和轮询定时器 */
    const cleanup = useCallback(() => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
        }
        if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
        }
        setIsConnected(false);
        setIsPolling(false);
    }, []);

    /** 启动轮询降级模式 */
    const startPolling = useCallback(async () => {
        if (!taskId || isPolling) return;

        setIsPolling(true);
        console.log('[SSE] Starting polling fallback');

        const poll = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/api/task/${taskId}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                const data = await response.json();
                setStatus(data);
                setError(null);

                // 检查是否为终止状态
                if (
                    data.status === 'completed' ||
                    data.status === 'completed_with_warnings' ||
                    data.status === 'failed_compilation' ||
                    data.status === 'structure_invalid' ||
                    data.status === 'failed'
                ) {
                    cleanup();
                    onComplete?.(data);
                }
            } catch (err) {
                console.error('[SSE] Polling error:', err);
                setError(err instanceof Error ? err : new Error(String(err)));
                onError?.(err instanceof Error ? err : new Error(String(err)));
            }
        };

        // 立即执行首次轮询
        await poll();

        // 设置定时轮询
        pollIntervalRef.current = setInterval(poll, pollInterval);
    }, [taskId, isPolling, pollInterval, cleanup, onComplete, onError]);

    /** 建立 SSE 连接，失败时自动降级为轮询 */
    const connectSSE = useCallback(() => {
        if (!taskId || !enabled) return;

        cleanup();
        setIsLoading(true);
        setError(null);

        try {
            const url = `${API_BASE_URL}/api/task/${taskId}/stream`;
            console.log('[SSE] Connecting to:', url);

            const eventSource = new EventSource(url);
            eventSourceRef.current = eventSource;

            eventSource.onopen = () => {
                console.log('[SSE] Connection opened');
                setIsConnected(true);
                setIsLoading(false);
                retryCountRef.current = 0;
            };

            eventSource.addEventListener('update', (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('[SSE] Update received:', data);
                    setStatus(data);
                    setError(null);
                } catch (err) {
                    console.error('[SSE] Parse error:', err);
                }
            });

            eventSource.addEventListener('complete', (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('[SSE] Task complete:', data);
                    setStatus(data);
                    cleanup();
                    onComplete?.(data);
                } catch (err) {
                    console.error('[SSE] Parse error:', err);
                }
            });

            eventSource.addEventListener('heartbeat', () => {
                console.log('[SSE] Heartbeat received');
            });

            eventSource.addEventListener('deleted', () => {
                console.log('[SSE] Task deleted');
                cleanup();
            });

            eventSource.addEventListener('error', (event) => {
                try {
                    const data = JSON.parse((event as MessageEvent).data);
                    console.error('[SSE] Server error:', data);
                    setError(new Error(data.message || 'SSE Error'));
                    onError?.(new Error(data.message || 'SSE Error'));
                } catch {
                    // 通用连接错误
                    console.error('[SSE] Connection error');
                }
            });

            eventSource.onerror = () => {
                console.error('[SSE] Connection error, switching to polling');
                setIsConnected(false);
                setIsLoading(false);

                // 指数退避重试，最多 3 次
                if (retryCountRef.current < maxRetries) {
                    retryCountRef.current++;
                    console.log(`[SSE] Retry ${retryCountRef.current}/${maxRetries}`);
                    setTimeout(connectSSE, 1000 * retryCountRef.current);
                } else {
                    // 重试用尽，降级为轮询
                    cleanup();
                    startPolling();
                }
            };
        } catch (err) {
            console.error('[SSE] Setup error:', err);
            setIsLoading(false);
            setError(err instanceof Error ? err : new Error(String(err)));
            startPolling();
        }
    }, [taskId, enabled, cleanup, startPolling, onComplete, onError]);

    /** 手动重试连接（重置重试计数并重新建立 SSE） */
    const retry = useCallback(() => {
        retryCountRef.current = 0;
        connectSSE();
    }, [connectSSE]);

    /** 副作用：当 taskId 变更时建立/清理连接 */
    useEffect(() => {
        if (!taskId || !enabled) {
            cleanup();
            return;
        }

        connectSSE();

        return cleanup;
    }, [taskId, enabled, connectSSE, cleanup]);

    return {
        status,
        isConnected,
        isPolling,
        error,
        isLoading,
        retry,
    };
}

export default useTaskStatusSSE;
