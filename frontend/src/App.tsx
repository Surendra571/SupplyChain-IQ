import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { AppLayout } from './components/layout/AppLayout';

// Pages
import { DashboardPage } from './pages/DashboardPage';
import { DemandPage } from './pages/DemandPage';
import { InventoryPage } from './pages/InventoryPage';
import { SuppliersPage } from './pages/SuppliersPage';
import { PurchaseOrdersPage } from './pages/PurchaseOrdersPage';
import { ProductionPage } from './pages/ProductionPage';
import { ShortagesPage } from './pages/ShortagesPage';
import { MitigationPage } from './pages/MitigationPage';
import { DataQualityPage } from './pages/DataQualityPage';
import { AuditPage } from './pages/AuditPage';
import { LoginPage } from './pages/LoginPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 1000 * 30, // 30 seconds
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/" element={<AppLayout />}>
                <Route index element={<DashboardPage />} />
                <Route path="demand" element={<DemandPage />} />
                <Route path="inventory" element={<InventoryPage />} />
                <Route path="suppliers" element={<SuppliersPage />} />
                <Route path="purchase-orders" element={<PurchaseOrdersPage />} />
                <Route path="production" element={<ProductionPage />} />
                <Route path="shortages" element={<ShortagesPage />} />
                <Route path="mitigations" element={<MitigationPage />} />
                <Route path="data-quality" element={<DataQualityPage />} />
                <Route path="audit" element={<AuditPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;

