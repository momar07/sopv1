import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { lazyPage } from '../ui/componentLoader';
import { useAuth } from '../context/AuthContext';

// ── Static pages (مضمونة دايماً حتى لو مش في الـ DB) ────────────────────────
const ReturnsPage     = lazy(() => import('../pages/ReturnsPage'));
const FinancialReport = lazy(() => import('../pages/FinancialReport'));
const Dashboard       = lazy(() => import('../pages/Dashboard'));

const Fallback = () => (
  <div className="flex items-center justify-center h-[60vh]">
    <i className="fas fa-spinner fa-spin text-4xl text-blue-600"></i>
  </div>
);

export default function DynamicRoutes({ ProtectedRoute, POSProtectedRoute }) {
  const { ui } = useAuth();
  const routes = ui?.routes || [];

  // لو الـ ui لسه بيتحمل، نعرض spinner مش null
  if (!ui) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <i className="fas fa-spinner fa-spin text-4xl text-blue-600"></i>
      </div>
    );
  }

  return (
    <Suspense fallback={<Fallback />}>
      <Routes>

        {/* ── Redirect from root ─────────────────────────────────────────── */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* ── Static routes (مضمونة دايماً) ────────────────────────────── */}
        <Route
          path="/dashboard"
          element={<ProtectedRoute><Dashboard /></ProtectedRoute>}
        />
        <Route
          path="/returns"
          element={<ProtectedRoute><ReturnsPage /></ProtectedRoute>}
        />
        <Route
          path="/financial-report"
          element={<ProtectedRoute><FinancialReport /></ProtectedRoute>}
        />

        {/* ── Dynamic routes من الـ DB ──────────────────────────────────── */}
        {routes.map((r) => {
          // تجنب تكرار الـ static routes
          if (['/dashboard', '/returns', '/financial-report'].includes(r.path)) {
            return null;
          }

          let Page;
          try {
            Page = lazyPage(r.component);
          } catch (e) {
            console.warn(`[DynamicRoutes] component not found: ${r.component}`, e);
            return null;
          }

          const element = (() => {
            if (r.wrapper === 'public')    return <Page />;
            if (r.wrapper === 'pos_shift') return <POSProtectedRoute><Page /></POSProtectedRoute>;
            return <ProtectedRoute><Page /></ProtectedRoute>;
          })();

          return (
            <Route
              key={r.key || r.path}
              path={r.path}
              element={element}
            />
          );
        })}

        {/* ── Catch-all ───────────────────────────────────────────────────── */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />

      </Routes>
    </Suspense>
  );
}
