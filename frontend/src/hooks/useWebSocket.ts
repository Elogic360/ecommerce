/**
 * WebSocket Hook - Real-time connection for live updates
 * Handles inventory updates, order status, notifications
 */
import { useEffect, useRef, useCallback, useState } from 'react';
import { config } from '@/config/env';
import type { WebSocketMessage, WebSocketAction } from '../types/features';

interface UseWebSocketOptions {
  autoConnect?: boolean;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    autoConnect = true,
    reconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [isConnected, setIsConnected] = useState(false);
  const [connectionId, setConnectionId] = useState<string | null>(null);

  const getToken = useCallback(() => {
    return localStorage.getItem('token');
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Validate WebSocket URL is configured
    if (!config.websocket.url) {
      console.error('WebSocket URL not configured. Please set VITE_WS_URL in your environment.');
      return;
    }

    const token = getToken();
    const url = token
      ? `${config.websocket.url}/ws?token=${token}`
      : `${config.websocket.url}/ws`;

    try {
      wsRef.current = new WebSocket(url);

      wsRef.current.onopen = () => {
        setIsConnected(true);
        reconnectAttempts.current = 0;
        onConnect?.();
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        setConnectionId(null);
        onDisconnect?.();

        // Attempt reconnect
        if (reconnect && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, reconnectInterval);
        }
      };

      wsRef.current.onerror = (error) => {
        onError?.(error);
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          // Handle connection confirmation
          if (message.type === 'connected') {
            setConnectionId((message.data as { connection_id: string })?.connection_id || null);
          }

          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }, [getToken, onConnect, onDisconnect, onError, onMessage, reconnect, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    reconnectAttempts.current = maxReconnectAttempts; // Prevent reconnect
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
    setConnectionId(null);
  }, [maxReconnectAttempts]);

  const send = useCallback((action: WebSocketAction) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(action));
    }
  }, []);

  const subscribe = useCallback((channel: string) => {
    send({ action: 'subscribe', channel });
  }, [send]);

  const unsubscribe = useCallback((channel: string) => {
    send({ action: 'unsubscribe', channel });
  }, [send]);

  const watchProduct = useCallback((productId: number) => {
    send({ action: 'watch_product', product_id: productId });
  }, [send]);

  const unwatchProduct = useCallback((productId: number) => {
    send({ action: 'unwatch_product', product_id: productId });
  }, [send]);

  const watchOrder = useCallback((orderId: number) => {
    send({ action: 'watch_order', order_id: orderId });
  }, [send]);

  const unwatchOrder = useCallback((orderId: number) => {
    send({ action: 'unwatch_order', order_id: orderId });
  }, [send]);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  // Ping to keep connection alive
  useEffect(() => {
    if (!isConnected) return;

    const pingInterval = setInterval(() => {
      send({ action: 'ping' });
    }, 30000); // Ping every 30 seconds

    return () => clearInterval(pingInterval);
  }, [isConnected, send]);

  return {
    isConnected,
    connectionId,
    send,
    subscribe,
    unsubscribe,
    watchProduct,
    unwatchProduct,
    watchOrder,
    unwatchOrder,
    connect,
    disconnect,
  };
}

export type UseWebSocketReturn = ReturnType<typeof useWebSocket>;
