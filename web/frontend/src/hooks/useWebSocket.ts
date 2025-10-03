import { useEffect, useCallback, useRef } from 'react';
import { wsService } from '@services/websocket';
import { useUIStore } from '@store/uiStore';
import type { WebSocketMessage } from '@types/index';

export const useWebSocket = (onMessage?: (message: WebSocketMessage) => void) => {
  const wsConnected = useUIStore(state => state.wsConnected);
  const setWSConnected = useUIStore(state => state.setWSConnected);
  const enableWebSocket = useUIStore(state => state.enableWebSocket);
  const unsubscribeRef = useRef<Array<() => void>>([]);

  useEffect(() => {
    if (!enableWebSocket) return;

    const connect = async () => {
      try {
        await wsService.connect();
        setWSConnected(true);
      } catch (error) {
        console.error('WebSocket connection failed:', error);
        setWSConnected(false);
      }
    };

    const handleConnect = () => setWSConnected(true);
    const handleDisconnect = () => setWSConnected(false);
    const handleError = () => setWSConnected(false);

    const unsubConnect = wsService.onConnect(handleConnect);
    const unsubDisconnect = wsService.onDisconnect(handleDisconnect);
    const unsubError = wsService.onError(handleError);

    unsubscribeRef.current.push(unsubConnect, unsubDisconnect, unsubError);

    if (onMessage) {
      const unsubMessage = wsService.onMessage(onMessage);
      unsubscribeRef.current.push(unsubMessage);
    }

    connect();

    return () => {
      unsubscribeRef.current.forEach(unsub => unsub());
      unsubscribeRef.current = [];
      wsService.disconnect();
    };
  }, [enableWebSocket, onMessage, setWSConnected]);

  const send = useCallback(
    (type: string, data: any) => {
      if (wsConnected) {
        wsService.send(type, data);
      }
    },
    [wsConnected]
  );

  return {
    connected: wsConnected,
    send,
  };
};
