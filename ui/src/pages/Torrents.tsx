import { Download } from "lucide-react";
import React from "react";
import { useTorrents } from "../hooks/useFetching";
import PageContainer from "../components/PageContainer";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import LoadingSpinner from "../components/LoadingSpinner";
import DataTable, { TableColumn } from "../components/DataTable";

const Torrents: React.FC = () => {
  const { data: torrents, isLoading: torrentsLoading } = useTorrents();

  // Define table columns for Torrents
  const torrentColumns: TableColumn[] = [
    {
      key: "name",
      label: "Name",
      render: (torrent) => (
        <div className="font-medium text-gray-900 dark:text-white">
          {torrent.name}
        </div>
      ),
    },
    {
      key: "status",
      label: "Status",
      render: (torrent) => (
        <span
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
            torrent.status === "4"
              ? "bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200"
              : "bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200"
          }`}
        >
          {torrent.status === "4" ? "Downloading" : "Seeding"}
        </span>
      ),
    },
    {
      key: "progress",
      label: "Progress",
      render: (torrent) => (
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
            <span>{torrent.progress.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className="bg-indigo-600 dark:bg-indigo-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${torrent.progress}%` }}
            ></div>
          </div>
        </div>
      ),
    },
  ];

  if (torrentsLoading) {
    return <LoadingSpinner />;
  }

  return (
    <PageContainer>
      <PageHeader title="Active Torrents" />

      {torrents && torrents.length > 0 ? (
        <DataTable data={torrents} columns={torrentColumns} />
      ) : (
        <EmptyState
          icon={Download}
          title="No active torrents"
          description="No torrents are currently downloading."
        />
      )}
    </PageContainer>
  );
};

export default Torrents;
