/**
 * Fix-25: useAlertPolling — Smart Polling Hook
 * يسأل السيرفر كل 30 ثانية عن تنبيهات جديدة
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { inventoryAPI } from '../services/api';

const POLL_INTERVAL = 30000; // 30 ثانية

export function useAlertPolling({ enabled = true, onNewAlert } = {}) {
  const [unreadCount, setUnreadCount]   = useState(0);
  const [topPriority, setTopPriority]   = useState(null);
  const [lastChecked, setLastChecked]   = useState(null);
  const [isPolling, setIsPolling]       = useState(false);
  const lastServerTime = useRef(null);
  const intervalRef    = useRef(null);

  const poll = useCallback(async () => {
    if (!enabled) return;
    try {
      const res = await inventoryAPI.pollAlerts(lastServerTime.current);
      const { new_alerts, total_unresolved, top_priority, server_time } = res.data;

      // لو في تنبيهات جديدة منذ آخر poll
      if (lastServerTime.current && new_alerts > 0) {
        setUnreadCount(prev => prev + new_alerts);
        setTopPriority(top_priority);
        if (onNewAlert) onNewAlert({ count: new_alerts, priority: top_priority });
      } else if (!lastServerTime.current) {
        // أول poll — نحدد الـ baseline بس
        setTopPriority(top_priority);
      }

      lastServerTime.current = server_time;
      setLastChecked(new Date());
    } catch(e) {
      console.warn('Polling error:', e?.message);
    }
  }, [enabled, onNewAlert]);

  // بدء الـ polling
  useEffect(() => {
    if (!enabled) return;
    setIsPolling(true);
    poll(); // أول استدعاء فوري
    intervalRef.current = setInterval(poll, POLL_INTERVAL);
    return () => {
      clearInterval(intervalRef.current);
      setIsPolling(false);
    };
  }, [enabled, poll]);

  const clearUnread = useCallback(() => {
    setUnreadCount(0);
    setTopPriority(null);
  }, []);

  return { unreadCount, topPriority, lastChecked, isPolling, clearUnread };
}
