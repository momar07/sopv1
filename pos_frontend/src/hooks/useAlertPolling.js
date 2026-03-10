/**
 * Fix-25c: useAlertPolling
 * - totalUnresolved: عدد كل التنبيهات المفتوحة (Badge دايم)
 * - newCount: عدد التنبيهات الجديدة منذ آخر poll (Toast)
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { inventoryAPI } from '../services/api';

const POLL_INTERVAL = 30000; // 30 ثانية

export function useAlertPolling({ enabled = true, onNewAlert } = {}) {
  const [totalUnresolved, setTotalUnresolved] = useState(0); // Badge دايم
  const [newCount,        setNewCount]        = useState(0); // Toast فقط
  const [topPriority,     setTopPriority]     = useState(null);
  const [lastChecked,     setLastChecked]     = useState(null);

  const lastServerTime = useRef(null);
  const onNewAlertRef  = useRef(onNewAlert);
  const enabledRef     = useRef(enabled);

  useEffect(() => { onNewAlertRef.current = onNewAlert; }, [onNewAlert]);
  useEffect(() => { enabledRef.current = enabled; },      [enabled]);

  const poll = useCallback(async () => {
    if (!enabledRef.current) return;
    try {
      const since = lastServerTime.current;
      const res   = await inventoryAPI.pollAlerts(since);
      const { new_alerts, total_unresolved, top_priority, server_time } = res.data;

      // Badge دايم — يتحدث في كل poll
      setTotalUnresolved(total_unresolved || 0);
      setTopPriority(top_priority);

      // Toast — بس لو في جديد بعد أول poll
      if (since && new_alerts > 0) {
        setNewCount(prev => prev + new_alerts);
        if (onNewAlertRef.current) {
          onNewAlertRef.current({ count: new_alerts, priority: top_priority });
        }
      }

      lastServerTime.current = server_time;
      setLastChecked(new Date());
    } catch(e) {
      console.warn('Polling error:', e?.message);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    poll();
    const id = setInterval(poll, POLL_INTERVAL);
    return () => clearInterval(id);
  }, []);

  const clearNew = useCallback(() => setNewCount(0), []);

  return { totalUnresolved, newCount, topPriority, lastChecked, clearNew };
}
