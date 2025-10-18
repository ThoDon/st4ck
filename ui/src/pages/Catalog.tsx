import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Download,
  HardDrive,
  Search,
  Users,
  Info,
  Filter,
  ChevronDown,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Clock,
} from "lucide-react";
import React, { useState } from "react";
import { yggService, YGGTorrent } from "../services/api";
import DataTable, { TableColumn } from "../components/DataTable";
import EmptyState from "../components/EmptyState";
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
  const [selectedCategory, setSelectedCategory] = useState<string>("2151");
  const [currentPage, setCurrentPage] = useState<number>(1);

  // Common torrent categories
  const categories = [
    { value: "", label: "All Categories" },
    { value: "2151", label: "Audiobooks" },
    { value: "ebook", label: "E-books" },
    { value: "movie", label: "Movies" },
    { value: "tv", label: "TV Shows" },
    { value: "music", label: "Music" },
    { value: "software", label: "Software" },
    { value: "game", label: "Games" },
    { value: "documentary", label: "Documentaries" },
  ];

  // Search torrents
  const { data: searchResults, isLoading: searchLoading, error: searchError, refetch } = useQuery({
    queryKey: ["ygg-search", selectedCategory, currentPage],
    queryFn: () => yggService.searchTorrents(searchQuery || "", selectedCategory, 100, currentPage),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const downloadMutation = useMutation({
    mutationFn: async (torrent: YGGTorrent) => {
      await yggService.addTorrentToTransmission(torrent.id.toString(), "magnet");
    },
    onSuccess: (_, torrent) => {
      // Show success message or update UI
      console.log(`Successfully added ${torrent.title} to Transmission`);
    },
    onError: (error, torrent) => {
      console.error(`Failed to add ${torrent.title} to Transmission:`, error);
    },
  });

  const handleDownload = async (torrent: YGGTorrent) => {
    setDownloadingItems((prev: Set<number>) => new Set(prev).add(torrent.id));
    try {
      await downloadMutation.mutateAsync(torrent);
    } catch (error) {
      console.error("Download failed:", error);
    } finally {
      setDownloadingItems((prev: Set<number>) => {
        const newSet = new Set(prev);
        newSet.delete(torrent.id);
        return newSet;
      });
    }
  };

  const handleSearch = () => {
    refetch();
    setCurrentPage(1);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handlePreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  const handleNextPage = () => {
    if (searchResults && currentPage < Math.ceil(searchResults.total / searchResults.per_page)) {
      setCurrentPage(currentPage + 1);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  // Define table columns for YGG Catalog
  const catalogColumns: TableColumn[] = [
    {
      key: "name",
      label: "Title",
      className: "max-w-lg truncate",
      render: (item: YGGTorrent) => (
        <div>
          <div
            title={item.title}
            className="text-sm font-medium text-gray-900 dark:text-white"
          >
            {item.title}
          </div>
          <div className="flex items-center text-sm text-gray-600 dark:text-gray-300 mt-1 space-x-4">
            <div className="flex items-center">
              <Filter className="w-4 h-4 mr-1" />
              Category: {item.category_id}
            </div>
          </div>
        </div>
      ),
    },
    {
      key: "details",
      label: "Details",
      render: (item: YGGTorrent) => (
        <div className="space-y-1 flex justify-center">
          <div className="flex flex-col items-center text-sm text-gray-500 dark:text-gray-400">
            <div className="flex items-center mr-4">
              <HardDrive className="w-4 h-4 mr-1" />
              {formatFileSize(item.size)}
            </div>
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
      key: "uploaded_at",
      label: "Uploaded",
      className: "text-center",
      render: (item: YGGTorrent) => (
        <div className="flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
          {item.uploaded_at ? <div className="flex flex-col items-center"><div className="flex items-center"><Clock className="w-4 h-4 mr-1" /> {new Date(item.uploaded_at).toLocaleDateString()}</div>
            <span className="text-gray-500 dark:text-gray-400">
              {new Date(item.uploaded_at).toLocaleTimeString()}
            </span>
          </div> : "N/A"}
        </div>
      ),
    },
    {
      key: "actions",
      label: "Actions",
      className: "text-center",
      render: (item: YGGTorrent) => (
        <ActionButtonGroup >
          <ActionButton
            icon={<Info className="w-4 h-4" />}
            onClick={() =>
              alert(
                `Title: ${item.title}\nCategory ID: ${item.category_id}\nSize: ${formatFileSize(item.size)}\nSeeders: ${item.seeders}\nLeechers: ${item.leechers}`
              )
            }
            title="Show torrent details"
            className={getButtonClassName("first")}
          />
          <ActionButton
            icon={<Download className="w-4 h-4" />}
            onClick={() => handleDownload(item)}
            disabled={downloadingItems.has(item.id)}
            title={
              downloadingItems.has(item.id)
                ? "Adding to transmission..."
                : "Download torrent"
            }
            className={getButtonClassName("last")}
          />
        </ActionButtonGroup>
      ),
    },
  ];


  if (searchError) {
    return (
      <ErrorAlert
        title="Error searching torrents"
        message={searchError instanceof Error ? searchError.message : "Unknown error"}
      />
    );
  }

  return (
    <div className="h-full flex flex-col px-4 py-6 sm:px-0">
      <div className="border-4 border-dashed border-gray-200 dark:border-gray-700 rounded-lg p-6 flex flex-col h-full">
        {/* Header with title and search */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6 flex-shrink-0">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            YGG Torrent Catalog
          </h2>

          {/* Search Controls */}
          <div className="flex flex-col sm:flex-row gap-3">
            {/* Search Input */}
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-4 w-4 text-gray-400 dark:text-gray-500" />
              </div>
              {searchLoading && (
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                  <Loader2 className="h-4 w-4 text-indigo-500 animate-spin" />
                </div>
              )}
              <input
                type="text"
                placeholder="Search for torrents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                className={`block w-64 pl-9 ${searchLoading ? 'pr-9' : 'pr-3'} py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md leading-5 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors duration-200`}
              />
            </div>

            {/* Category Dropdown */}
            <div className="relative">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="block w-40 pl-3 pr-8 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors duration-200 appearance-none"
              >
                {categories.map((category) => (
                  <option key={category.value} value={category.value}>
                    {category.label}
                  </option>
                ))}
              </select>
              <div className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
                <ChevronDown className="h-4 w-4 text-gray-400 dark:text-gray-500" />
              </div>
            </div>

            {/* Search Button */}
            <button
              onClick={handleSearch}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 transition-colors duration-200 text-sm"
            >
              Search
            </button>
          </div>
        </div>

        {/* Search Results Info and Pagination */}
        {searchResults && (
          <div className="flex items-center justify-between mb-4 flex-shrink-0">
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Found {searchResults.total} torrents
              {searchResults.total > 0 && (
                <span className="ml-2">
                  (Page {searchResults.page} of {Math.ceil(searchResults.total / searchResults.per_page)})
                </span>
              )}
            </div>

            {/* Pagination Controls */}
            {searchResults.total > searchResults.per_page && (
              <div className="flex items-center space-x-2">
                <button
                  onClick={handlePreviousPage}
                  disabled={currentPage <= 1}
                  className="p-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                  title="Previous page"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>

                <span className="text-sm text-gray-600 dark:text-gray-400 px-2">
                  {currentPage} / {Math.ceil(searchResults.total / searchResults.per_page)}
                </span>

                <button
                  onClick={handleNextPage}
                  disabled={currentPage >= Math.ceil(searchResults.total / searchResults.per_page)}
                  className="p-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                  title="Next page"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        )}

        {searchResults && searchResults.torrents.length > 0 ? (
          <div className="flex-1 overflow-hidden">
            <DataTable
              data={searchResults.torrents}
              columns={catalogColumns}
              maxHeight="max-h-full"
            />
          </div>
        ) : (
          <div className="flex-1 flex flex-col justify-center">
            <EmptyState
              icon={Search}
              title="No torrents found"
              description={searchQuery.trim().length > 0
                ? `No torrents match your search "${searchQuery}". Try a different search term or category.`
                : `No ${selectedCategory === "audiobook" ? "audiobooks" : "torrents"} found. Try a different category.`
              }
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default Catalog;
