import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Calendar,
  Calendar as CalendarIcon,
  Download,
  ExternalLink,
  HardDrive,
  User,
  Users,
} from "lucide-react";
import React, { useState } from "react";
import { rssService, torrentService } from "../services/api";

const Catalog: React.FC = () => {
  const [downloadingItems, setDownloadingItems] = useState<Set<number>>(
    new Set()
  );
  const queryClient = useQueryClient();

  const {
    data: rssItems,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["rss-items"],
    queryFn: rssService.getRSSItems,
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  const downloadMutation = useMutation({
    mutationFn: async (item: { id: number; title: string }) => {
      // Use RSS item ID instead of filename
      await torrentService.addTorrent(item.id);
    },
    onMutate: async (item: { id: number; title: string }) => {
      // Cancel any outgoing refetches (so they don't overwrite our optimistic update)
      await queryClient.cancelQueries({ queryKey: ["rss-items"] });

      // Snapshot the previous value
      const previousRssItems = queryClient.getQueryData(["rss-items"]);

      // Optimistically update to the new value
      queryClient.setQueryData(["rss-items"], (old: any) => {
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

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4">
        <div className="flex">
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">
              Error loading RSS items
            </h3>
            <div className="mt-2 text-sm text-red-700">
              {error instanceof Error ? error.message : "Unknown error"}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="border-4 border-dashed border-gray-200 rounded-lg p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-6">RSS Catalog</h2>

        {rssItems && rssItems.length > 0 ? (
          <div className="space-y-4">
            {rssItems.map((item) => (
              <div
                key={item.id}
                className="bg-white overflow-hidden shadow rounded-lg border border-gray-200"
              >
                <div className="px-4 py-5 sm:p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <h3 className="text-lg font-medium text-gray-900 mb-2">
                        {item.title}
                      </h3>

                      {/* Author and Year */}
                      <div className="flex items-center text-sm text-gray-600 mb-2 space-x-4">
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
                        {item.format && (
                          <div className="flex items-center">
                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                              {item.format}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* File size and seeders/leechers */}
                      <div className="flex items-center text-sm text-gray-500 space-x-4">
                        {item.file_size && (
                          <div className="flex items-center">
                            <HardDrive className="w-4 h-4 mr-1" />
                            {item.file_size}
                          </div>
                        )}
                        {item.seeders > 0 && (
                          <div className="flex items-center">
                            <Users className="w-4 h-4 mr-1" />
                            <span className="text-green-600">
                              {item.seeders} seeders
                            </span>
                            {item.leechers > 0 && (
                              <span className="text-gray-400 ml-1">
                                / {item.leechers} leechers
                              </span>
                            )}
                          </div>
                        )}
                        {item.pub_date && (
                          <div className="flex items-center">
                            <Calendar className="w-4 h-4 mr-1" />
                            {new Date(item.pub_date).toLocaleDateString()}
                          </div>
                        )}
                        <div className="flex items-center space-x-2">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              item.status === "new"
                                ? "bg-green-100 text-green-800"
                                : "bg-gray-100 text-gray-800"
                            }`}
                          >
                            {item.status}
                          </span>
                          {item.download_status &&
                            item.download_status === "transmission_added" && (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                In Transmission
                              </span>
                            )}
                          {item.download_status &&
                            item.download_status === "downloaded" && (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                Downloaded
                              </span>
                            )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <a
                        href={item.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                      >
                        <ExternalLink className="w-4 h-4 mr-1" />
                        View
                      </a>
                      <button
                        onClick={() => handleDownload(item)}
                        disabled={
                          downloadingItems.has(item.id) ||
                          item.download_status === "transmission_added"
                        }
                        className={`inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
                          downloadingItems.has(item.id) ||
                          item.download_status === "transmission_added"
                            ? "bg-gray-400 text-white cursor-not-allowed"
                            : "text-white bg-indigo-600 hover:bg-indigo-700"
                        }`}
                      >
                        <Download className="w-4 h-4 mr-1" />
                        {downloadingItems.has(item.id)
                          ? "Adding..."
                          : item.download_status === "transmission_added"
                          ? "In Transmission"
                          : "Download"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <Download className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">
              No RSS items
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              No RSS items found. Check your RSS feed configuration.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Catalog;
