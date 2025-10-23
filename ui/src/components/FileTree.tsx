import {
  BookOpen,
  ChevronDown,
  ChevronRight,
  File,
  FileText,
  Folder,
  Image,
  Loader2,
  Tag,
} from "lucide-react";
import React, { useEffect, useState } from "react";
import api from "../services/api";
import { ActionButton } from "./ActionButtonGroup";

interface LibraryItem {
  name: string;
  path: string;
  type: "file" | "directory";
  size?: number;
  isM4B?: boolean;
  children?: LibraryItem[];
}

interface FileTreeProps {
  items: LibraryItem[];
  onRetagFile: (filePath: string) => void;
  retaggingItems: Set<string>;
  onLoadChildren?: (folderPath: string) => Promise<LibraryItem[]>;
  loadingFolders: Set<string>;
}

interface TreeNodeProps {
  item: LibraryItem;
  level: number;
  onRetagFile: (filePath: string) => void;
  retaggingItems: Set<string>;
  onLoadChildren?: (folderPath: string) => Promise<LibraryItem[]>;
  loadingFolders: Set<string>;
  expandedFolders: Set<string>;
  onToggleExpand: (folderPath: string) => void;
}

const TreeNode: React.FC<TreeNodeProps> = ({
  item,
  level,
  onRetagFile,
  retaggingItems,
  onLoadChildren,
  loadingFolders,
  expandedFolders,
  onToggleExpand,
}) => {
  const [children, setChildren] = useState<LibraryItem[]>(item.children || []);
  const [childrenLoaded, setChildrenLoaded] = useState(false);
  const [showPopover, setShowPopover] = useState(false);
  const [m4bTags, setM4bTags] = useState<string>("");
  const [loadingTags, setLoadingTags] = useState(false);
  const [hideTimeout, setHideTimeout] = useState<number | null>(null);
  const isExpanded = expandedFolders.has(item.path);
  const isLoading = loadingFolders.has(item.path);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (hideTimeout) {
        clearTimeout(hideTimeout);
      }
    };
  }, [hideTimeout]);

  const handleToggleExpand = async () => {
    if (item.type === "directory") {
      if (!childrenLoaded && onLoadChildren) {
        try {
          const childItems = await onLoadChildren(item.path);
          setChildren(childItems);
          setChildrenLoaded(true);
        } catch (error) {
          console.error("Failed to load children:", error);
        }
      }
      onToggleExpand(item.path);
    }
  };

  const handleM4BHover = async () => {
    // Clear any existing hide timeout
    if (hideTimeout) {
      clearTimeout(hideTimeout);
      setHideTimeout(null);
    }

    if (isM4B && !m4bTags && !loadingTags) {
      setLoadingTags(true);
      try {
        // Call API to get M4B tags with cache-busting parameter
        const cacheBuster = Date.now();
        try {
          const response = await api.get(
            `/m4b/tags?file_path=${encodeURIComponent(
              item.path
            )}&_t=${cacheBuster}`
          );
          setM4bTags(response.data);
        } catch (error) {
          console.error("Failed to load M4B tags:", error);
          setM4bTags("Failed to load tags");
        }
      } catch (error) {
        console.error("Failed to load M4B tags:", error);
        setM4bTags("Error loading tags");
      } finally {
        setLoadingTags(false);
      }
    }
    setShowPopover(true);
  };

  const handleM4BLeave = () => {
    // Set a delay before hiding the popover
    const timeout = setTimeout(() => {
      setShowPopover(false);
    }, 300); // 300ms delay
    setHideTimeout(timeout);
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const isM4BFile = (fileName: string): boolean => {
    return fileName.toLowerCase().endsWith(".m4b");
  };

  const getFileIcon = (fileName: string, isDirectory: boolean) => {
    if (isDirectory) {
      return <Folder className="w-4 h-4 text-blue-500" />;
    }

    const lowerName = fileName.toLowerCase();
    if (lowerName.endsWith(".m4b")) {
      return <BookOpen className="w-4 h-4 text-green-500" />;
    } else if (lowerName.endsWith(".txt")) {
      return <FileText className="w-4 h-4 text-gray-600" />;
    } else if (
      lowerName.endsWith(".jpg") ||
      lowerName.endsWith(".jpeg") ||
      lowerName.endsWith(".png")
    ) {
      return <Image className="w-4 h-4 text-purple-500" />;
    } else if (lowerName.endsWith(".opf")) {
      return <FileText className="w-4 h-4 text-orange-500" />;
    } else {
      return <File className="w-4 h-4 text-gray-500" />;
    }
  };

  const isM4B = isM4BFile(item.name);

  // Check if this is a book folder (directory that contains M4B files)
  const isBookFolder =
    item.type === "directory" &&
    // If children are already loaded, check if any child is an M4B file
    ((childrenLoaded && children.some((child) => isM4BFile(child.name))) ||
      // If children are not loaded but we have some children data, check them
      (!childrenLoaded &&
        children.length > 0 &&
        children.some((child) => isM4BFile(child.name))));

  return (
    <div className="select-none relative">
      <div
        className={`flex items-center py-1 px-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors duration-150 ${
          item.type === "directory" ? "cursor-pointer" : ""
        }`}
        style={{
          paddingLeft:
            item.type === "file"
              ? `${level * 24 + 32}px` // Files get extra padding
              : `${level * 24 + 8}px`, // Folders get normal padding
        }}
        onClick={item.type === "directory" ? handleToggleExpand : undefined}
        onMouseEnter={isM4B ? handleM4BHover : undefined}
        onMouseLeave={isM4B ? handleM4BLeave : undefined}
      >
        {/* Expand/Collapse Button */}
        {item.type === "directory" && (
          <div className="flex items-center justify-center w-4 h-4 mr-2">
            {isLoading ? (
              <Loader2 className="w-3 h-3 animate-spin text-gray-400" />
            ) : isExpanded ? (
              <ChevronDown className="w-3 h-3 text-gray-500" />
            ) : (
              <ChevronRight className="w-3 h-3 text-gray-500" />
            )}
          </div>
        )}

        {/* File/Folder Icon */}
        <div className="flex items-center mr-2">
          {getFileIcon(item.name, item.type === "directory")}
        </div>

        {/* File/Folder Name */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {item.name}
            </span>
            {isM4B && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                M4B
              </span>
            )}
          </div>
          {item.size && (
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {formatFileSize(item.size)}
            </div>
          )}
        </div>

        {/* Actions - Show retag button for directories */}
        <div className="flex items-center space-x-2">
          {isBookFolder && (
            <ActionButton
              icon={<Tag className="w-4 h-4" />}
              onClick={async (e) => {
                e.stopPropagation(); // Prevent folder toggle when clicking button

                // Load children if not already loaded
                if (!childrenLoaded && onLoadChildren) {
                  try {
                    const childItems = await onLoadChildren(item.path);
                    setChildren(childItems);
                    setChildrenLoaded(true);
                  } catch (error) {
                    console.error("Failed to load children:", error);
                    return;
                  }
                }

                // Find the M4B file in this folder
                const m4bFile = children.find((child) => isM4BFile(child.name));
                if (m4bFile) {
                  if (
                    confirm(
                      `Are you sure you want to retag "${m4bFile.name}"? This will move it to the toTag folder and delete the book folder.`
                    )
                  ) {
                    onRetagFile(m4bFile.path);
                  }
                } else {
                  alert("No M4B file found in this folder.");
                }
              }}
              disabled={retaggingItems.has(item.path)}
              title={
                retaggingItems.has(item.path) ? "Retagging..." : "Retag book"
              }
              className="bg-blue-500 hover:bg-blue-600 text-white"
            />
          )}
        </div>
      </div>

      {/* M4B Tags Popover */}
      {isM4B && showPopover && (
        <div
          className="absolute z-50 left-0 top-full mt-1 w-96 max-w-md bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-4"
          onMouseEnter={() => {
            // Clear hide timeout when hovering over popover
            if (hideTimeout) {
              clearTimeout(hideTimeout);
              setHideTimeout(null);
            }
          }}
          onMouseLeave={() => {
            // Set delay when leaving popover
            const timeout = setTimeout(() => {
              setShowPopover(false);
            }, 300);
            setHideTimeout(timeout);
          }}
        >
          <div className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            M4B Tags
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-400 max-h-64 overflow-y-auto">
            {loadingTags ? (
              <div className="flex items-center space-x-2">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>Loading tags...</span>
              </div>
            ) : (
              <pre className="whitespace-pre-wrap font-mono text-xs">
                {m4bTags || "No tags available"}
              </pre>
            )}
          </div>
        </div>
      )}

      {/* Children */}
      {item.type === "directory" && isExpanded && children.length > 0 && (
        <div>
          {children.map((child, index) => (
            <TreeNode
              key={`${child.path}-${index}`}
              item={child}
              level={level + 1}
              onRetagFile={onRetagFile}
              retaggingItems={retaggingItems}
              onLoadChildren={onLoadChildren}
              loadingFolders={loadingFolders}
              expandedFolders={expandedFolders}
              onToggleExpand={onToggleExpand}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const FileTree: React.FC<FileTreeProps> = ({
  items,
  onRetagFile,
  retaggingItems,
  onLoadChildren,
  loadingFolders,
}) => {
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(
    new Set()
  );

  const handleToggleExpand = (folderPath: string) => {
    setExpandedFolders((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(folderPath)) {
        newSet.delete(folderPath);
      } else {
        newSet.add(folderPath);
      }
      return newSet;
    });
  };

  return (
    <div className="w-full">
      {items.map((item, index) => (
        <TreeNode
          key={`${item.path}-${index}`}
          item={item}
          level={0}
          onRetagFile={onRetagFile}
          retaggingItems={retaggingItems}
          onLoadChildren={onLoadChildren}
          loadingFolders={loadingFolders}
          expandedFolders={expandedFolders}
          onToggleExpand={handleToggleExpand}
        />
      ))}
    </div>
  );
};

export default FileTree;
