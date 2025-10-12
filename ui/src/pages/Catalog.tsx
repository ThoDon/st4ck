import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Calendar as CalendarIcon,
  Download,
  ExternalLink,
  HardDrive,
  Search,
  User,
  Users,
  Info,
} from "lucide-react";
import React, { useState } from "react";
import { torrentService } from "../services/api";
import { useRSSItems, QUERY_KEYS } from "../hooks/useFetching";
import DataTable, { TableColumn } from "../components/DataTable";
import EmptyState from "../components/EmptyState";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorAlert from "../components/ErrorAlert";
import {
  ActionButtonGroup,
  ActionButton,
  getButtonClassName,
} from "../components/ActionButtonGroup";

const Catalog: React.FC = () => {
  const [downloadingItems, setDownloadingItems] = useState<Set<number>>(
    new Set()
  );
  const [searchQuery, setSearchQuery] = useState<string>("");
  const queryClient = useQueryClient();

  const { data: rssItems, isLoading, error } = useRSSItems();

  const downloadMutation = useMutation({
    mutationFn: async (item: { id: number; title: string }) => {
      // Use RSS item ID instead of filename
      await torrentService.addTorrent(item.id);
    },
    onMutate: async (item: { id: number; title: string }) => {
      // Cancel any outgoing refetches (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({ queryKey: QUERY_KEYS.RSS_ITEMS });

      // Snapshot the previous value
      const previousRssItems = queryClient.getQueryData(QUERY_KEYS.RSS_ITEMS);

      // Optimistically update to the new value
      queryClient.setQueryData(QUERY_KEYS.RSS_ITEMS, (old: any) => {
        if (!old) return old;
        return old.map((rssItem: any) =>
          rssItem.id === item.id
            ? {
                ...rssItem,
                download_status: "transmission_added",
                download_date: new Date().toISOString(),
              }
            : rssItem
        );
      });

      // Return a context object with the snapshotted value
      return { previousRssItems };
    },
    onError: (_, _item, context) => {
      // If the mutation fails, use the context returned from onMutate to roll back
      if (context?.previousRssItems) {
        queryClient.setQueryData(["rss-items"], context.previousRssItems);
      }
    },
    onSettled: () => {
      // Always refetch after error or success to ensure we have the latest data
      queryClient.invalidateQueries({ queryKey: ["rss-items"] });
      queryClient.invalidateQueries({ queryKey: ["torrents"] });
    },
  });

  const handleDownload = async (item: { id: number; title: string }) => {
    setDownloadingItems((prev: Set<number>) => new Set(prev).add(item.id));
    try {
      await downloadMutation.mutateAsync(item);
    } catch (error) {
      console.error("Download failed:", error);
      // You could add a toast notification here
    } finally {
      setDownloadingItems((prev: Set<number>) => {
        const newSet = new Set(prev);
        newSet.delete(item.id);
        return newSet;
      });
    }
  };

  // Filter RSS items based on search query
  const filteredRssItems =
    rssItems?.filter((item) => {
      if (!searchQuery.trim()) return true;

      const query = searchQuery.toLowerCase();
      return (
        item.title.toLowerCase().includes(query) ||
        (item.author && item.author.toLowerCase().includes(query)) ||
        (item.year && item.year.toLowerCase().includes(query)) ||
        (item.format && item.format.toLowerCase().includes(query)) ||
        (item.description && item.description.toLowerCase().includes(query))
      );
    }) || [];

  // Define table columns for Catalog
  const catalogColumns: TableColumn[] = [
    {
      key: "title",
      label: "Title",
      className: "max-w-lg truncate",
      render: (item) => (
        <div>
          <div
            title={item.title}
            className="text-sm font-medium text-gray-900 dark:text-white"
          >
            {item.title}
          </div>
          <div className="flex items-center text-sm text-gray-600 dark:text-gray-300 mt-1 space-x-4">
            {item.author && (
              <div className="flex items-center">
                <User className="w-4 h-4 mr-1" />
                {item.author}
              </div>
            )}
            {item.year && (
              <div className="flex items-center">
                <CalendarIcon className="w-4 h-4 mr-1" />
                {item.year}
              </div>
            )}
          </div>
        </div>
      ),
    },
    {
      key: "details",
      label: "Details",
      render: (item) => (
        <div className="space-y-1 flex justify-center">
          <div className="flex flex-col items-center text-sm text-gray-500 dark:text-gray-400">
            {item.file_size && (
              <div className="flex items-center mr-4">
                <HardDrive className="w-4 h-4 mr-1" />
                {item.file_size}
              </div>
            )}
            {item.seeders > 0 && (
              <div className="flex items-center">
                <Users className="w-4 h-4 mr-1" />
                <span className="text-green-600 dark:text-green-400">
                  {item.seeders} seeders
                </span>
                {item.leechers > 0 && (
                  <span className="text-gray-400 dark:text-gray-500 ml-1">
                    / {item.leechers} leechers
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      ),
    },
    {
      key: "pub_date",
      label: "Published",
      render: (item) => (
        <div className="text-sm text-gray-500 dark:text-gray-400">
          {item.pub_date ? new Date(item.pub_date).toLocaleDateString() : "N/A"}
        </div>
      ),
    },
    {
      key: "actions",
      label: "Actions",
      render: (item) => (
        <ActionButtonGroup>
          <ActionButton
            icon={<ExternalLink className="w-4 h-4" />}
            onClick={() =>
              window.open(item.link, "_blank", "noopener,noreferrer")
            }
            title="View external link"
            className={getButtonClassName("first")}
          />
          <ActionButton
            icon={<Info className="w-4 h-4" />}
            onClick={() =>
              alert(
                `Title: ${item.title}\nAuthor: ${item.author || "N/A"}\nYear: ${
                  item.year || "N/A"
                }\nFormat: ${item.format || "N/A"}`
              )
            }
            title="Show item details"
            className={getButtonClassName("middle")}
          />
          <ActionButton
            icon={<Download className="w-4 h-4" />}
            onClick={() => handleDownload(item)}
            disabled={
              downloadingItems.has(item.id) ||
              item.download_status === "transmission_added"
            }
            title={
              downloadingItems.has(item.id)
                ? "Adding to transmission..."
                : item.download_status === "transmission_added"
                ? "Already in transmission"
                : "Download torrent"
            }
            className={getButtonClassName("last")}
          />
        </ActionButtonGroup>
      ),
    },
  ];

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <ErrorAlert
        title="Error loading RSS items"
        message={error instanceof Error ? error.message : "Unknown error"}
      />
    );
  }

  return (
    <div className="h-full flex flex-col px-4 py-6 sm:px-0">
      <div className="border-4 border-dashed border-gray-200 dark:border-gray-700 rounded-lg p-6 flex flex-col h-full">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6 flex-shrink-0">
          RSS Catalog
        </h2>

        {/* Search Input */}
        <div className="mb-6 flex-shrink-0">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-5 w-5 text-gray-400 dark:text-gray-500" />
            </div>
            <input
              type="text"
              placeholder="Search by title, author, year, format, or description..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors duration-200"
            />
          </div>
        </div>

        {filteredRssItems && filteredRssItems.length > 0 ? (
          <div className="flex-1 overflow-hidden">
            <DataTable
              data={filteredRssItems}
              columns={catalogColumns}
              maxHeight="max-h-full"
            />
          </div>
        ) : (
          <div className="flex-1 flex flex-col justify-center">
            <EmptyState
              icon={Download}
              title={searchQuery.trim() ? "No matching items" : "No RSS items"}
              description={
                searchQuery.trim()
                  ? `No RSS items match your search "${searchQuery}". Try a different search term.`
                  : "No RSS items found. Check your RSS feed configuration."
              }
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default Catalog;
