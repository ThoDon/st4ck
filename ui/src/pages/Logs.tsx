import { Activity, AlertCircle, AlertTriangle, Info } from "lucide-react";
import React from "react";
import { useLogs } from "../hooks/useFetching";
import PageContainer from "../components/PageContainer";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorAlert from "../components/ErrorAlert";
import DataTable, { TableColumn } from "../components/DataTable";

const Logs: React.FC = () => {
  const { data: logs, isLoading, error } = useLogs();

  const getLogIcon = (level: string) => {
    switch (level.toLowerCase()) {
      case "error":
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case "warning":
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case "info":
        return <Info className="w-4 h-4 text-blue-500" />;
      default:
        return <Activity className="w-4 h-4 text-gray-500" />;
    }
  };

  // Define table columns for Logs
  const logColumns: TableColumn[] = [
    {
      key: "level",
      label: "Level",
      render: (log) => (
        <div className="flex items-center justify-center space-x-2">
          {getLogIcon(log.level)}
        </div>
      ),
    },
    {
      key: "service",
      label: "Service",
      render: (log) => (
        <div>
          {log.service && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
              {log.service}
            </span>
          )}
        </div>
      ),
    },
    {
      key: "message",
      label: "Message",
      className: "max-w-lg truncate",
      render: (log) => (
        <div
          title={log.message}
          className="text-sm text-gray-700 dark:text-gray-300"
        >
          {log.message}
        </div>
      ),
    },
    {
      key: "created_at",
      label: "Time",
      render: (log) => (
        <div className="text-xs text-gray-500 dark:text-gray-400">
          {new Date(log.created_at).toLocaleString()}
        </div>
      ),
    },
  ];

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <ErrorAlert
        title="Error loading logs"
        message={error instanceof Error ? error.message : "Unknown error"}
      />
    );
  }

  return (
    <PageContainer>
      <PageHeader title="System Logs" />

      {logs && logs.length > 0 ? (
        <DataTable data={logs} columns={logColumns} />
      ) : (
        <EmptyState
          icon={Activity}
          title="No logs available"
          description="No log entries found in the system."
        />
      )}
    </PageContainer>
  );
};

export default Logs;
