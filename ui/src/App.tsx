import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  Navigate,
  Route,
  BrowserRouter as Router,
  Routes,
} from "react-router-dom";
import Layout from "./components/Layout";
import { DarkModeProvider } from "./contexts/DarkModeContext";
import Catalog from "./pages/Catalog";
import Conversion from "./pages/Conversion";
import Logs from "./pages/Logs";
import Tagging from "./pages/Tagging";
import Torrents from "./pages/Torrents";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const AppRoutes: React.FC = () => {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Catalog />} />
        <Route path="/torrents" element={<Torrents />} />
        <Route path="/tagging" element={<Tagging />} />
        <Route path="/conversions" element={<Conversion />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
};

const App: React.FC = () => {
  return (
    <DarkModeProvider>
      <QueryClientProvider client={queryClient}>
        <Router>
          <AppRoutes />
        </Router>
      </QueryClientProvider>
    </DarkModeProvider>
  );
};

export default App;
