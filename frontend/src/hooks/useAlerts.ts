import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';
import type { Alert } from '@/types';

export type { Alert };

export interface UseAlertsReturn {
  alerts: Alert[];
  unreadCount: number;
  loading: boolean;
  refresh: () => Promise<void>;
  markRead: (id: number) => Promise<void>;
  markAllRead: () => Promise<void>;
}

export const useAlerts = (pollIntervalMs = 60_000): UseAlertsReturn => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getAlerts(false, 50);
      setAlerts(data.alerts ?? []);
    } catch {
      // silently fail — badge just won't update
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch + polling
  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, pollIntervalMs);
    return () => clearInterval(timer);
  }, [refresh, pollIntervalMs]);

  const markRead = useCallback(async (id: number) => {
    await api.markAlertRead(id);
    setAlerts(prev =>
      prev.map(a => (a.id === id ? { ...a, is_read: 1 } : a))
    );
  }, []);

  const markAllRead = useCallback(async () => {
    await api.markAllAlertsRead();
    setAlerts(prev => prev.map(a => ({ ...a, is_read: 1 })));
  }, []);

  const unreadCount = alerts.filter(a => !a.is_read).length;

  return { alerts, unreadCount, loading, refresh, markRead, markAllRead };
};

export default useAlerts;
