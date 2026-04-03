import { useEffect, useState, useCallback } from 'react';

/**
 * Hook for real-time WebSocket notifications from the backend.
 */
export function useWebSocket(userId: number) {
  const [lastMessage, setLastMessage] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!userId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host; // or use an env var
    const ws = new WebSocket(`${protocol}//${host}/ws/${userId}`);

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastMessage(data);
      } catch (err) {
        console.error("Failed to parse WS message", err);
      }
    };

    return () => {
      ws.close();
    };
  }, [userId]);

  return { lastMessage, isConnected };
}
