import { Routes, Route, Navigate } from "react-router-dom";
import AppLayout from "@/components/AppLayout";
import Index from "@/pages/Index";
import Auth from "@/pages/Auth";
import Dashboard from "@/pages/Dashboard";
import Chat from "@/pages/Chat";
import Transactions from "@/pages/Transactions";
import Categories from "@/pages/Categories";
import SettingsPage from "@/pages/Settings";
import NotFound from "@/pages/NotFound";

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<Index />} />
      <Route path="/auth" element={<Auth />} />

      {/* Protected — wrapped by AppLayout */}
      <Route
        path="/dashboard"
        element={
          <AppLayout>
            <Dashboard />
          </AppLayout>
        }
      />
      <Route
        path="/chat"
        element={
          <AppLayout>
            <Chat />
          </AppLayout>
        }
      />
      <Route
        path="/transactions"
        element={
          <AppLayout>
            <Transactions />
          </AppLayout>
        }
      />
      <Route
        path="/categories"
        element={
          <AppLayout>
            <Categories />
          </AppLayout>
        }
      />
      <Route
        path="/settings"
        element={
          <AppLayout>
            <SettingsPage />
          </AppLayout>
        }
      />

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
