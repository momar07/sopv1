import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { lazyPage } from '../ui/componentLoader';
import { useAuth } from '../context/AuthContext';

const ReturnsPage = lazy(() => import('../pages/ReturnsPage'));

const Fallback = () => (
  <div className="flex items-center justify-center h-[60vh]">
    <i className="fas fa-spinner fa-spin text-4xl text-blue-600"></i>
  </div>
);

export default function DynamicRoutes({ ProtectedRoute, POSProtectedRoute }) {
  const { ui } = useAuth();
  const routes = ui?.routes || [];
  if (!ui) return null;

  return (
    <Suspense fallback={<Fallback />}>
      <Routes>
        {/* مسار ثابت للمرتجعات — مش محتاج يكون في الـ DB */}
        <Route
          path="/returns"
          element={
            <ProtectedRoute>
              <ReturnsPage />
            </ProtectedRoute>
          }
        />

        {routes.map((r) => {
          const Page = lazyPage(r.component);
          const element = (() => {
            if (r.wrapper === 'public') return <Page />;
            if (r.wrapper === 'pos_shift') return (
              <POSProtectedRoute><Page /></POSProtectedRoute>
            );
            return <ProtectedRoute><Page /></ProtectedRoute>;
          })();
          return <Route key={r.key || r.path} path={r.path} element={element} />;
        })}

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
