import {
  AlertCircle,
  CheckCircle,
  Clock,
  FileAudio,
  Play,
  RefreshCw,
  RotateCcw,
  X,
  Trash2,
} from "lucide-react";
import React, { useState } from "react";
import {
  ActionButton,
  ActionButtonGroup,
  getButtonClassName,
} from "../components/ActionButtonGroup";
import DataTable, { TableColumn } from "../components/DataTable";
import EmptyState from "../components/EmptyState";
import ErrorAlert from "../components/ErrorAlert";
import LoadingSpinner from "../components/LoadingSpinner";
import PageContainer from "../components/PageContainer";
import PageHeader from "../components/PageHeader";
import { useConversions } from "../hooks/useFetching";
import { conversionService } from "../services/api";

const Conversion: React.FC = () => {
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState<{ [key: number]: string }>(
    {}
  );
  const [clearConfirm, setClearConfirm] = useState<{
    isOpen: boolean;
    conversionId: number | null;
    bookName: string;
  }>({
    isOpen: false,
    conversionId: null,
    bookName: "",
  });

  const { data: conversions, isLoading, error, refetch } = useConversions();

  const handleRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  const handleRetryConversion = async (conversionId: number) => {
    setActionLoading((prev) => ({ ...prev, [conversionId]: "retry" }));
    try {
      await conversionService.retryConversion(conversionId);
      await refetch();
    } catch (error) {
      console.error("Failed to retry conversion:", error);
    } finally {
      setActionLoading((prev) => ({ ...prev, [conversionId]: "" }));
    }
  };

  const handleCancelConversion = async (conversionId: number) => {
    setActionLoading((prev) => ({ ...prev, [conversionId]: "cancel" }));
    try {
      await conversionService.cancelConversion(conversionId);
      await refetch();
    } catch (error) {
      console.error("Failed to cancel conversion:", error);
    } finally {
      setActionLoading((prev) => ({ ...prev, [conversionId]: "" }));
    }
  };

  const handleTriggerConversion = async (conversionId: number) => {
    setActionLoading((prev) => ({ ...prev, [conversionId]: "trigger" }));
    try {
      // This would need the book name and source path - for now just show the action
      console.log("Trigger conversion for:", conversionId);
      await refetch();
    } catch (error) {
      console.error("Failed to trigger conversion:", error);
    } finally {
      setActionLoading((prev) => ({ ...prev, [conversionId]: "" }));
    }
  };

  const handleClearConversion = async (
    conversionId: number,
    bookName: string
  ) => {
    setClearConfirm({
      isOpen: true,
      conversionId,
      bookName,
    });
  };

  const confirmClearConversion = async () => {
    if (!clearConfirm.conversionId) return;

    setActionLoading((prev) => ({
      ...prev,
      [clearConfirm.conversionId!]: "clear",
    }));
    try {
      const result = await conversionService.clearStuckConversion(
        clearConfirm.conversionId
      );
      console.log("Clear result:", result);
      await refetch();
      setClearConfirm({ isOpen: false, conversionId: null, bookName: "" });
    } catch (error) {
      console.error("Failed to clear conversion:", error);
    } finally {
      setActionLoading((prev) => ({
        ...prev,
        [clearConfirm.conversionId!]: "",
      }));
    }
  };

  const cancelClearConversion = () => {
    setClearConfirm({ isOpen: false, conversionId: null, bookName: "" });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case "converting":
        return <Clock className="w-5 h-5 text-blue-500 animate-pulse" />;
      case "pending":
        return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200";
      case "converting":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
      case "pending":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const formatETA = (etaSeconds: number | null): string | null => {
    if (!etaSeconds) return null;

    if (etaSeconds < 60) {
      return `${etaSeconds}s`;
    } else if (etaSeconds < 3600) {
      const minutes = Math.floor(etaSeconds / 60);
      const remainingSeconds = etaSeconds % 60;
      return remainingSeconds > 0
        ? `${minutes}m ${remainingSeconds}s`
        : `${minutes}m`;
    } else {
      const hours = Math.floor(etaSeconds / 3600);
      const remainingMinutes = Math.floor((etaSeconds % 3600) / 60);
      return remainingMinutes > 0
        ? `${hours}h ${remainingMinutes}m`
        : `${hours}h`;
    }
  };

  // Define table columns for Conversion
  const conversionColumns: TableColumn[] = [
    {
      key: "book_name",
      label: "Book Name",
      className: "max-w-lg truncate",
      render: (conversion) => (
        <div className="flex items-center">
          <div>{getStatusIcon(conversion.status)}</div>
          <div className="ml-3">
            <div className="font-medium text-gray-900 dark:text-white">
              {conversion.book_name}
            </div>
            {conversion.current_file && (
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Converting: {conversion.current_file}
              </div>
            )}
          </div>
        </div>
      ),
    },
    {
      key: "status",
      label: "Status",
      render: (conversion) => (
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(
            conversion.status
          )}`}
        >
          {conversion.status}
        </span>
      ),
    },
    {
      key: "progress",
      label: "Progress",
      className: "min-w-48",
      render: (conversion) => (
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
            <span>
              {conversion.converted_files} / {conversion.total_files} files
            </span>
            <span>{conversion.progress_percentage.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(conversion.progress_percentage, 100)}%`,
              }}
            ></div>
          </div>
          {conversion.status === "converting" &&
            conversion.estimated_eta_seconds && (
              <div className="flex items-center text-xs text-gray-500 dark:text-gray-400">
                <Clock className="w-3 h-3 mr-1" />
                <span>ETA: {formatETA(conversion.estimated_eta_seconds)}</span>
              </div>
            )}
        </div>
      ),
    },
    {
      key: "created_at",
      label: "Created",
      render: (conversion) => (
        <div className="text-sm text-gray-500 dark:text-gray-400">
          {formatDate(conversion.created_at)}
        </div>
      ),
    },
    {
      key: "actions",
      label: "Actions",
      render: (conversion) => {
        const isLoading = actionLoading[conversion.id];
        const canRetry = conversion.status === "failed";
        const canCancel =
          conversion.status === "converting" || conversion.status === "pending";
        const canTrigger = conversion.status === "pending";
        const canClear =
          conversion.status === "converting" ||
          conversion.status === "processing";

        return (
          <ActionButtonGroup>
            {canRetry && (
              <ActionButton
                icon={
                  <RotateCcw
                    className={`w-4 h-4 ${
                      isLoading === "retry" ? "animate-spin" : ""
                    }`}
                  />
                }
                onClick={() => handleRetryConversion(conversion.id)}
                disabled={!!isLoading}
                title="Retry failed conversion"
                className={getButtonClassName("retry")}
              />
            )}
            {canCancel && (
              <ActionButton
                icon={
                  <X
                    className={`w-4 h-4 ${
                      isLoading === "cancel" ? "animate-pulse" : ""
                    }`}
                  />
                }
                onClick={() => handleCancelConversion(conversion.id)}
                disabled={!!isLoading}
                title="Cancel conversion"
                className={getButtonClassName("cancel")}
              />
            )}
            {canClear && (
              <ActionButton
                icon={
                  <Trash2
                    className={`w-4 h-4 ${
                      isLoading === "clear" ? "animate-pulse" : ""
                    }`}
                  />
                }
                onClick={() =>
                  handleClearConversion(conversion.id, conversion.book_name)
                }
                disabled={!!isLoading}
                title="Clear stuck conversion"
                className={getButtonClassName("clear")}
              />
            )}
            {canTrigger && (
              <ActionButton
                icon={
                  <Play
                    className={`w-4 h-4 ${
                      isLoading === "trigger" ? "animate-pulse" : ""
                    }`}
                  />
                }
                onClick={() => handleTriggerConversion(conversion.id)}
                disabled={!!isLoading}
                title="Start conversion"
                className={getButtonClassName("trigger")}
              />
            )}
            <ActionButton
              icon={
                <RefreshCw
                  className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`}
                />
              }
              onClick={handleRefresh}
              disabled={refreshing}
              title="Refresh conversion status"
              className={getButtonClassName("single")}
            />
          </ActionButtonGroup>
        );
      },
    },
  ];

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <ErrorAlert
        title="Error loading conversions"
        message={
          error instanceof Error ? error.message : "Unknown error occurred"
        }
      />
    );
  }

  return (
    <PageContainer>
      <PageHeader title="Conversion Progress" />

      {!conversions || conversions.length === 0 ? (
        <EmptyState
          icon={FileAudio}
          title="No conversions found"
          description="Conversion tracking will appear here when the converter service starts processing files."
        />
      ) : (
        <DataTable data={conversions} columns={conversionColumns} />
      )}

      {/* Clear Confirmation Dialog */}
      {clearConfirm.isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center mb-4">
              <Trash2 className="w-6 h-6 text-red-500 mr-3" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Clear Stuck Conversion
              </h3>
            </div>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Are you sure you want to clear the stuck conversion for{" "}
              <span className="font-medium text-gray-900 dark:text-white">
                "{clearConfirm.bookName}"
              </span>
              ? This will reset the status to failed and clean up any associated
              files and backups.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={cancelClearConversion}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmClearConversion}
                disabled={actionLoading[clearConfirm.conversionId!] === "clear"}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {actionLoading[clearConfirm.conversionId!] === "clear"
                  ? "Clearing..."
                  : "Clear"}
              </button>
            </div>
          </div>
        </div>
      )}
    </PageContainer>
  );
};

export default Conversion;
