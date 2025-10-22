import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Folder,
  RefreshCw,
  Loader2,
  AlertTriangle,
  CheckCircle,
} from "lucide-react";
import React, { useState } from "react";
import { apiService } from "../services/api";
import FileTree from "../components/FileTree";
import EmptyState from "../components/EmptyState";
import ErrorAlert from "../components/ErrorAlert";

interface LibraryItem {
  name: string;
  path: string;
  type: "file" | "directory";
  size?: number;
  isM4B?: boolean;
  children?: LibraryItem[];
}

// Remove unused interface - using the one from api.ts

const Library: React.FC = () => {
  const [currentPath, setCurrentPath] = useState<string>("");
  const [retaggingItems, setRetaggingItems] = useState<Set<string>>(new Set());
  const [loadingFolders, setLoadingFolders] = useState<Set<string>>(new Set());

  // Fetch library items
  const { 
    data: libraryData, 
    isLoading, 
    error, 
    refetch 
  } = useQuery({
    queryKey: ["library", currentPath],
    queryFn: () => apiService.getLibraryItems(currentPath || undefined),
    staleTime: 30 * 1000, // 30 seconds
  });

  // Retag M4B file mutation
  const retagMutation = useMutation({
    mutationFn: async (filePath: string) => {
      await apiService.retagM4BFile(filePath);
    },
    onSuccess: () => {
      refetch();
    },
    onError: (error) => {
      console.error("Retag failed:", error);
    },
  });

  const handleRetag = async (filePath: string) => {
    setRetaggingItems((prev) => new Set(prev).add(filePath));
    try {
      await retagMutation.mutateAsync(filePath);
    } catch (error) {
      console.error("Retag failed:", error);
    } finally {
      setRetaggingItems((prev) => {
        const newSet = new Set(prev);
        newSet.delete(filePath);
        return newSet;
      });
    }
  };

  const handleLoadChildren = async (folderPath: string): Promise<LibraryItem[]> => {
    setLoadingFolders((prev) => new Set(prev).add(folderPath));
    try {
      // Extract relative path from the full path for the API
      const relativePath = folderPath.replace(/^.*\/library\//, '');
      const response = await apiService.getLibraryItems(relativePath);
      return response.items;
    } catch (error) {
      console.error("Failed to load folder contents:", error);
      return [];
    } finally {
      setLoadingFolders((prev) => {
        const newSet = new Set(prev);
        newSet.delete(folderPath);
        return newSet;
      });
    }
  };

  const handleNavigateUp = () => {
    const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
    setCurrentPath(parentPath);
  };

  if (error) {
    return (
      <ErrorAlert
        title="Error loading library"
        message={error instanceof Error ? error.message : "Unknown error"}
      />
    );
  }

  return (
    <div className="h-full flex flex-col px-4 py-6 sm:px-0">
      <div className="border-4 border-dashed border-gray-200 dark:border-gray-700 rounded-lg p-6 flex flex-col h-full">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6 flex-shrink-0">
          <div className="flex items-center space-x-4">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Library Browser
            </h2>
            <button
              onClick={() => refetch()}
              disabled={isLoading}
              className="p-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {/* Breadcrumb Navigation */}
          <div className="flex items-center space-x-2 text-sm">
            <button
              onClick={handleNavigateUp}
              disabled={currentPath === "/data/library"}
              className="px-3 py-1 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
            >
              ← Up
            </button>
            <span className="text-gray-500 dark:text-gray-400">
              {currentPath}
            </span>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="flex items-center space-x-2">
              <Loader2 className="h-6 w-6 animate-spin text-indigo-500" />
              <span className="text-gray-600 dark:text-gray-400">Loading library...</span>
            </div>
          </div>
        )}

        {/* Library Content */}
        {!isLoading && libraryData && (
          <>
            {libraryData.items.length > 0 ? (
              <div className="flex-1 overflow-auto">
                <FileTree
                  items={libraryData.items}
                  onRetagFile={handleRetag}
                  retaggingItems={retaggingItems}
                  onLoadChildren={handleLoadChildren}
                  loadingFolders={loadingFolders}
                />
              </div>
            ) : (
              <div className="flex-1 flex flex-col justify-center">
                <EmptyState
                  icon={Folder}
                  title="Empty folder"
                  description="This folder is empty."
                />
              </div>
            )}
          </>
        )}

        {/* Success/Error Messages */}
        {retagMutation.isSuccess && (
          <div className="mt-4 p-4 bg-green-50 dark:bg-green-900 border border-green-200 dark:border-green-700 rounded-md">
            <div className="flex items-center">
              <CheckCircle className="h-5 w-5 text-green-400 mr-2" />
              <span className="text-green-800 dark:text-green-200">
                File successfully moved to retag queue!
              </span>
            </div>
          </div>
        )}

        {retagMutation.isError && (
          <div className="mt-4 p-4 bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700 rounded-md">
            <div className="flex items-center">
              <AlertTriangle className="h-5 w-5 text-red-400 mr-2" />
              <span className="text-red-800 dark:text-red-200">
                Failed to retag file. Please try again.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Library;
