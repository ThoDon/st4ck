import React, { useState } from "react";
import {
  ChevronRight,
  ChevronDown,
  Folder,
  File,
  BookOpen,
  Tag,
  Trash2,
  Loader2,
} from "lucide-react";
import {
  ActionButtonGroup,
  ActionButton,
  getButtonClassName,
} from "./ActionButtonGroup";

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
  const isExpanded = expandedFolders.has(item.path);
  const isLoading = loadingFolders.has(item.path);

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

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const isM4BFile = (fileName: string): boolean => {
    return fileName.toLowerCase().endsWith('.m4b');
  };

  const isM4B = isM4BFile(item.name);

  return (
    <div className="select-none">
      <div
        className={`flex items-center py-1 px-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-md transition-colors duration-150 ${
          level > 0 ? "ml-4" : ""
        }`}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
      >
        {/* Expand/Collapse Button */}
        {item.type === "directory" && (
          <button
            onClick={handleToggleExpand}
            className="flex items-center justify-center w-4 h-4 mr-2 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors duration-150"
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="w-3 h-3 animate-spin text-gray-400" />
            ) : isExpanded ? (
              <ChevronDown className="w-3 h-3 text-gray-500" />
            ) : (
              <ChevronRight className="w-3 h-3 text-gray-500" />
            )}
          </button>
        )}

        {/* File/Folder Icon */}
        <div className="flex items-center mr-2">
          {item.type === "directory" ? (
            <Folder className="w-4 h-4 text-blue-500" />
          ) : isM4B ? (
            <BookOpen className="w-4 h-4 text-green-500" />
          ) : (
            <File className="w-4 h-4 text-gray-500" />
          )}
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

        {/* Actions */}
        <div className="flex items-center space-x-2">
          {isM4B && (
            <ActionButtonGroup>
              <ActionButton
                icon={<Tag className="w-4 h-4" />}
                onClick={() => onRetagFile(item.path)}
                disabled={retaggingItems.has(item.path)}
                title={
                  retaggingItems.has(item.path)
                    ? "Retagging..."
                    : "Retag M4B file"
                }
                className={getButtonClassName("first")}
              />
              <ActionButton
                icon={<Trash2 className="w-4 h-4" />}
                onClick={() => {
                  if (confirm(`Are you sure you want to retag "${item.name}"? This will move it to the toTag folder and delete the book folder.`)) {
                    onRetagFile(item.path);
                  }
                }}
                disabled={retaggingItems.has(item.path)}
                title="Retag and clean up"
                className={getButtonClassName("last")}
              />
            </ActionButtonGroup>
          )}
        </div>
      </div>

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
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

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
