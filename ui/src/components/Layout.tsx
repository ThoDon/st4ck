import { Activity, BookOpen, Download, Tag, Settings } from "lucide-react";
import React from "react";
import { Link, useLocation } from "react-router-dom";
import DarkModeToggle from "./DarkModeToggle";
import { useAllStatuses } from "../hooks/useFetching";

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { downloading, converting, tagging } = useAllStatuses();

  const tabs = [
    {
      path: "/",
      label: "Catalog",
      icon: BookOpen,
      hasIndicator: false, // Catalog doesn't need an indicator
    },
    {
      path: "/torrents",
      label: "Torrents",
      icon: Download,
      hasIndicator: downloading.hasActiveDownloads,
      indicatorCount: downloading.count,
    },

    {
      path: "/conversions",
      label: "Conversions",
      icon: Settings,
      hasIndicator: converting.hasActiveConversions,
      indicatorCount: converting.count,
    },
    {
      path: "/tagging",
      label: "Tagging",
      icon: Tag,
      hasIndicator: tagging.hasPendingTagging,
      indicatorCount: tagging.count,
    },
    {
      path: "/logs",
      label: "Logs",
      icon: Activity,
      hasIndicator: false, // Logs doesn't need an indicator
    },
  ];

  return (
    <div className="h-screen bg-gray-50 dark:bg-gray-900 flex flex-col transition-colors duration-200">
      <nav className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 flex-shrink-0 transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                  Audiobook Pipeline
                </h1>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = location.pathname === tab.path;
                  return (
                    <Link
                      key={tab.path}
                      to={tab.path}
                      className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors duration-200 relative ${
                        isActive
                          ? "border-indigo-500 text-gray-900 dark:text-white"
                          : "border-transparent text-gray-500 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600 hover:text-gray-700 dark:hover:text-gray-200"
                      }`}
                    >
                      <Icon className="w-4 h-4 mr-2" />
                      {tab.label}
                      {tab.hasIndicator && (
                        <span className="ml-2 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white bg-red-500 rounded-full animate-pulse">
                          {tab.indicatorCount}
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>
            <div className="flex items-center">
              <DarkModeToggle />
            </div>
          </div>
        </div>
      </nav>

      <main className="w-full mx-auto py-6 sm:px-6 lg:px-8 flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  );
};

export default Layout;
