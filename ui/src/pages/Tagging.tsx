import { useQueryClient } from "@tanstack/react-query";
import { Bot, CheckCircle, Clock, Tag, Trash2 } from "lucide-react";
import React, { useState } from "react";
import {
  ActionButton,
  ActionButtonGroup,
  getButtonClassName,
} from "../components/ActionButtonGroup";
import DataTable, { TableColumn } from "../components/DataTable";
import EmptyState from "../components/EmptyState";
import LoadingSpinner from "../components/LoadingSpinner";
import PageContainer from "../components/PageContainer";
import PageHeader from "../components/PageHeader";
import TaggingModal from "../components/TaggingModal";
import { QUERY_KEYS, useTaggingItems } from "../hooks/useFetching";
import { taggingService } from "../services/api";

const Tagging: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState<{ [key: number]: string }>(
    {}
  );
  const [clearConfirm, setClearConfirm] = useState<{
    isOpen: boolean;
    itemId: number | null;
    itemName: string;
  }>({
    isOpen: false,
    itemId: null,
    itemName: "",
  });

  const { data: taggingItems, isLoading } = useTaggingItems();

  const handleTagItem = (item: any) => {
    setSelectedItem(item);
    setIsModalOpen(true);
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setSelectedItem(null);
  };

  const handleTaggingSuccess = () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEYS.TAGGING_ITEMS });
  };

  const handleClearTagging = (itemId: number, itemName: string) => {
    setClearConfirm({
      isOpen: true,
      itemId,
      itemName,
    });
  };

  const confirmClearTagging = async () => {
    if (!clearConfirm.itemId) return;

    setActionLoading((prev) => ({ ...prev, [clearConfirm.itemId!]: "clear" }));
    try {
      const result = await taggingService.clearStuckTagging(
        clearConfirm.itemId
      );
      console.log("Clear result:", result);
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.TAGGING_ITEMS });
      setClearConfirm({ isOpen: false, itemId: null, itemName: "" });
    } catch (error) {
      console.error("Failed to clear tagging item:", error);
    } finally {
      setActionLoading((prev) => ({ ...prev, [clearConfirm.itemId!]: "" }));
    }
  };

  const cancelClearTagging = () => {
    setClearConfirm({ isOpen: false, itemId: null, itemName: "" });
  };

  // Define table columns for Tagging
  const taggingColumns: TableColumn[] = [
    {
      key: "name",
      label: "Name",
      className: "max-w-lg truncate",
      render: (item) => (
        <div className="flex items-center space-x-2">
          <div className="font-medium text-gray-900 dark:text-white">
            {item.name}
          </div>
          {item.auto_tagged && (
            <div className="flex items-center space-x-1">
              <Bot className="w-4 h-4 text-blue-500" />
              <span className="text-xs text-blue-600 dark:text-blue-400 font-medium">
                Auto
              </span>
            </div>
          )}
        </div>
      ),
    },

    {
      key: "status",
      label: "Status",
      render: (item) => (
        <div className="flex items-center justify-center space-x-2">
          {item.status === "completed" && !item.auto_tagged && (
            <CheckCircle className="w-4 h-4 text-green-500" />
          )}
          {item.status === "waiting" && (
            <Tag className="w-4 h-4 text-yellow-500" />
          )}
          {item.status === "processing" && (
            <div className="flex flex-col items-center space-y-1">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
              {item.message && (
                <span className="text-xs text-blue-600 dark:text-blue-400 text-center max-w-32 truncate">
                  {item.message}
                </span>
              )}
            </div>
          )}
        </div>
      ),
    },
    {
      key: "created_at",
      label: "Created",
      render: (item) => (
        <div className="flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
          {item.created_at && (
            <>
              <Clock className="w-4 h-4 mr-1" />
              {new Date(item.created_at).toLocaleDateString()}
            </>
          )}
        </div>
      ),
    },

    {
      key: "actions",
      label: "Actions",
      render: (item) => {
        const isLoading = actionLoading[item.id];
        const canTag = item.status === "waiting" && !item.auto_tagged;
        const canClear = item.status === "processing";

        return (
          <ActionButtonGroup>
            {canTag && (
              <ActionButton
                icon={<Tag className="w-4 h-4" />}
                onClick={() => handleTagItem(item)}
                disabled={!!isLoading}
                title="Tag this item"
                className={getButtonClassName("single")}
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
                onClick={() => handleClearTagging(item.id, item.name)}
                disabled={!!isLoading}
                title="Clear stuck tagging"
                className={getButtonClassName("clear")}
              />
            )}
            {item.auto_tagged && (
              <div className="flex items-center space-x-1 text-blue-600 dark:text-blue-400">
                <Bot className="w-4 h-4" />
                <span className="text-sm font-medium">Auto-processed</span>
              </div>
            )}
          </ActionButtonGroup>
        );
      },
    },
  ];

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <>
      <PageContainer>
        <PageHeader title="Tagging Queue" />

        {taggingItems && taggingItems.length > 0 ? (
          <DataTable data={taggingItems} columns={taggingColumns} />
        ) : (
          <EmptyState
            icon={Tag}
            title="No items in tagging queue"
            description="No M4B files are waiting for tagging."
          />
        )}
      </PageContainer>

      {/* Tagging Modal */}
      {selectedItem && (
        <TaggingModal
          isOpen={isModalOpen}
          onClose={handleModalClose}
          item={selectedItem}
          onSuccess={handleTaggingSuccess}
        />
      )}

      {/* Clear Confirmation Dialog */}
      {clearConfirm.isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center mb-4">
              <Trash2 className="w-6 h-6 text-red-500 mr-3" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Clear Stuck Tagging
              </h3>
            </div>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Are you sure you want to clear the stuck tagging for{" "}
              <span className="font-medium text-gray-900 dark:text-white">
                "{clearConfirm.itemName}"
              </span>
              ? This will reset the status to waiting so it can be reprocessed.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={cancelClearTagging}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmClearTagging}
                disabled={actionLoading[clearConfirm.itemId!] === "clear"}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {actionLoading[clearConfirm.itemId!] === "clear"
                  ? "Clearing..."
                  : "Clear"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default Tagging;
