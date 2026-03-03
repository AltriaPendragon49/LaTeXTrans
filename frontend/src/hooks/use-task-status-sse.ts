/**
 * useTaskStatusSSE - Real-time task status updates via Server-Sent Events
 * 
 * Features:
 * - SSE connection for real-time updates
 * - Automatic polling fallback if SSE fails
 * - Heartbeat detection for connection health
 * - Auto-cleanup on component unmount
 */

import { useState, useEffect, useCallback, useRef } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export interface TaskStatus {
    task_id: string;
    status: string;
    progress: number;
    stage: string;
    message: string;
    error?: string | null;
    warnings?: string | null;
    failure_reason_code?: string | null;
    failure_class?: string | null;
    guard_phase?: string | null;
    replay_bundle_ref?: string | null;
    source_available: boolean;
}

interface UseTaskStatusSSEOptions {
    /** Enable SSE connection (default: true) */
    enabled?: boolean;
    /** Polling interval in ms for fallback (default: 2000) */
    pollInterval?: number;
    /** Callback when task completes */
    onComplete?: (status: TaskStatus) => void;
    /** Callback on error */
    onError?: (error: Error) => void;
}

interface UseTaskStatusSSEReturn {
    /** Current task status */
    status: TaskStatus | null;
    /** Whether currently connected via SSE */
    isConnected: boolean;
    /** Whether using polling fallback */
    isPolling: boolean;
    /** Current error if any */
    error: Error | null;
    /** Loading state */
    isLoading: boolean;
    /** Manually retry connection */
    retry: () => void;
}

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

    // Cleanup function
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

    // Polling fallback
    const startPolling = useCallback(async () => {
        if (!taskId || isPolling) return;

        setIsPolling(true);
        console.log('[SSE] Starting polling fallback');

        const poll = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/task/${taskId}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                const data = await response.json();
                setStatus(data);
                setError(null);

                // Check for terminal state
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

        // Initial poll
        await poll();

        // Setup interval
        pollIntervalRef.current = setInterval(poll, pollInterval);
    }, [taskId, isPolling, pollInterval, cleanup, onComplete, onError]);

    // SSE connection
    const connectSSE = useCallback(() => {
        if (!taskId || !enabled) return;

        cleanup();
        setIsLoading(true);
        setError(null);

        try {
            const url = `${API_BASE_URL}/task/${taskId}/stream`;
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
                    // General connection error
                    console.error('[SSE] Connection error');
                }
            });

            eventSource.onerror = () => {
                console.error('[SSE] Connection error, switching to polling');
                setIsConnected(false);
                setIsLoading(false);

                if (retryCountRef.current < maxRetries) {
                    retryCountRef.current++;
                    console.log(`[SSE] Retry ${retryCountRef.current}/${maxRetries}`);
                    setTimeout(connectSSE, 1000 * retryCountRef.current);
                } else {
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

    // Retry function
    const retry = useCallback(() => {
        retryCountRef.current = 0;
        connectSSE();
    }, [connectSSE]);

    // Effect: connect when taskId changes
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
