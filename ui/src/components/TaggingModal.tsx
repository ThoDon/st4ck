import React, { useState, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  X,
  Search,
  Tag,
  BookOpen,
  User,
  Clock,
  Star,
  FileText,
} from "lucide-react";
import { taggingService } from "../services/api";

interface TaggingModalProps {
  isOpen: boolean;
  onClose: () => void;
  item: {
    id?: number;
    name: string;
    path: string;
    folder?: string;
  };
  onSuccess: () => void;
}

interface AudibleBook {
  asin: string;
  title: string;
  author: string;
  narrator?: string;
  series?: string;
  series_part?: string;
  description?: string;
  cover_url?: string;
  duration?: string;
  release_date?: string;
  language?: string;
  publisher?: string;
  locale: string;
}

const TaggingModal: React.FC<TaggingModalProps> = ({
  isOpen,
  onClose,
  item,
  onSuccess,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<AudibleBook[]>([]);
  const [selectedBook, setSelectedBook] = useState<AudibleBook | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Parse filename when modal opens
  const { data: filenameData, isLoading: isParsingFilename } = useQuery({
    queryKey: ["parse-filename", item.name],
    queryFn: () => taggingService.parseFilename(item.name),
    enabled: isOpen,
  });

  useEffect(() => {
    if (filenameData?.suggested_query && !searchQuery) {
      setSearchQuery(filenameData.suggested_query);
      handleSearch(filenameData.suggested_query);
    }
  }, [filenameData, searchQuery]);

  const tagFileMutation = useMutation({
    mutationFn: ({ asin }: { asin: string; }) =>
      taggingService.tagFileByAsin(item.path, asin, "fr"),
    onSuccess: () => {
      onSuccess();
      onClose();
      setSelectedBook(null);
      setSearchResults([]);
      setSearchQuery("");
    },
    onError: (error) => {
      console.error("Error tagging file:", error);
    },
  });

  const handleSearch = async (query?: string) => {
    const resolvedQuery = query?.trim() || searchQuery.trim();
    if (!resolvedQuery) return;

    setIsSearching(true);
    setSearchError(null);

    try {
      const results = await taggingService.searchAudibleBooks(resolvedQuery);
      setSearchResults(results);
    } catch (error) {
      setSearchError("Failed to search Audible. Please try again.");
      console.error("Search error:", error);
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleTagFile = () => {
    if (selectedBook) {
      tagFileMutation.mutate({ asin: selectedBook.asin });
    }
  };

  const formatDuration = (duration: string) => {
    if (!duration) return "";
    // Convert duration to readable format
    return duration;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <Tag className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Tag Audiobook
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {isParsingFilename ? (
            <div className="mt-3 flex items-center space-x-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-500"></div>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Parsing filename...
              </span>
            </div>
          ) : filenameData ? (
            <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded">
              <div className="flex items-center space-x-2 mb-2">
                <FileText className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                  Parsed Information
                </span>
              </div>
              <div className="space-y-1 text-sm text-blue-700 dark:text-blue-300">
                <p>
                  <strong>Title:</strong> {filenameData.title}
                </p>
                <p>
                  <strong>Author:</strong> {filenameData.author}
                </p>
                <p>
                  <strong>Suggested Query:</strong> "
                  {filenameData.suggested_query}"
                </p>
              </div>
            </div>
          ) : null}

          {/* Search Section */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Search Audible
            </label>
            <div className="flex space-x-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Enter book title, author, or keywords..."
                className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 dark:bg-gray-700 dark:text-white"
              />
              <button
                onClick={() => handleSearch()}
                disabled={isSearching || !searchQuery.trim()}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                {isSearching ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                ) : (
                  <Search className="w-4 h-4" />
                )}
                <span>Search</span>
              </button>
            </div>
            {searchError && (
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">
                {searchError}
              </p>
            )}
          </div>

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Search Results ({searchResults.length})
              </h3>
              <div className="space-y-3 max-h-60 overflow-y-auto">
                {searchResults.map((book) => (
                  <div
                    key={book.asin}
                    className={`p-4 border rounded-lg cursor-pointer transition-colors ${selectedBook?.asin === book.asin
                        ? "border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20"
                        : "border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500"
                      }`}
                    onClick={() => setSelectedBook(book)}
                  >
                    <div className="flex space-x-4">
                      {/* Cover */}
                      {book.cover_url && (
                        <img
                          src={book.cover_url}
                          alt={book.title}
                          className="w-16 h-20 object-cover rounded"
                        />
                      )}

                      {/* Book Info */}
                      <div className="flex-1">
                        <h4 className="font-medium text-gray-900 dark:text-white mb-1">
                          {book.title}
                        </h4>
                        <div className="space-y-1 text-sm text-gray-600 dark:text-gray-300">
                          <div className="flex items-center space-x-2">
                            <User className="w-4 h-4" />
                            <span>{book.author}</span>
                          </div>
                          {book.narrator && (
                            <div className="flex items-center space-x-2">
                              <BookOpen className="w-4 h-4" />
                              <span>Narrated by: {book.narrator}</span>
                            </div>
                          )}
                          {book.series && (
                            <div className="flex items-center space-x-2">
                              <Star className="w-4 h-4" />
                              <span>
                                {book.series}
                                {book.series_part && ` #${book.series_part}`}
                              </span>
                            </div>
                          )}
                          {book.duration && (
                            <div className="flex items-center space-x-2">
                              <Clock className="w-4 h-4" />
                              <span>{formatDuration(book.duration)}</span>
                            </div>
                          )}
                        </div>
                        {book.description && (
                          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                            {book.description.substring(0, 150)}...
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500"
          >
            Cancel
          </button>
          <button
            onClick={handleTagFile}
            disabled={!selectedBook || tagFileMutation.isPending}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {tagFileMutation.isPending ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <Tag className="w-4 h-4" />
            )}
            <span>{tagFileMutation.isPending ? "Tagging..." : "Tag File"}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default TaggingModal;
