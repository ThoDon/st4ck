import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle, Tag, Clock } from "lucide-react";
import React, { useState } from "react";
import TaggingModal from "../components/TaggingModal";
import { useTaggingItems, QUERY_KEYS } from "../hooks/useFetching";
import PageContainer from "../components/PageContainer";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import LoadingSpinner from "../components/LoadingSpinner";
import DataTable, { TableColumn } from "../components/DataTable";
import {
  ActionButton,
  getButtonClassName,
} from "../components/ActionButtonGroup";

const Tagging: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

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

  // Define table columns for Tagging
  const taggingColumns: TableColumn[] = [
    {
      key: "name",
      label: "Name",
      className: "max-w-lg truncate",
      render: (item) => (
        <div className="font-medium text-gray-900 dark:text-white">
          {item.name}
        </div>
      ),
    },

    {
      key: "status",
      label: "Status",
      render: (item) => (
        <div className="flex items-center justify-center space-x-2">
          {item.status === "completed" && (
            <CheckCircle className="w-4 h-4 text-green-500" />
          )}
          {item.status === "waiting" && (
            <Tag className="w-4 h-4 text-yellow-500" />
          )}
          {item.status === "processing" && (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
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
      render: (item) => (
        <div className="flex items-center justify-center">
          <ActionButton
            icon={<Tag className="w-4 h-4" />}
            onClick={() => handleTagItem(item)}
            disabled={item.status !== "waiting"}
            title={
              item.status === "waiting"
                ? "Tag this item"
                : "Item not available for tagging"
            }
            className={getButtonClassName("single")}
          />
        </div>
      ),
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
    </>
  );
};

export default Tagging;
