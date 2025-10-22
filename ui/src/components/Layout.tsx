import { Activity, BookOpen, Download, Tag, Settings, Menu, X, Library } from "lucide-react";
import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import DarkModeToggle from "./DarkModeToggle";
import { useAllStatuses } from "../hooks/useFetching";

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();
  const { downloading, converting, tagging } = useAllStatuses();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

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
      path: "/library",
      label: "Library",
      icon: Library,
      hasIndicator: false, // Library doesn't need an indicator
    },
    {
      path: "/logs",
      label: "Logs",
      icon: Activity,
      hasIndicator: false, // Logs doesn't need an indicator
    },
  ];

  const NavLink: React.FC<{ tab: typeof tabs[0] }> = ({ tab }) => {
    const Icon = tab.icon;
    const isActive = location.pathname === tab.path;
    return (
      <Link
        to={tab.path}
        onClick={() => setMobileMenuOpen(false)}
        className={`inline-flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 relative ${
          isActive
            ? "bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-200"
            : "text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white"
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
  };

  return (
    <div className="h-screen bg-gray-50 dark:bg-gray-900 flex flex-col transition-colors duration-200">
      <nav className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 flex-shrink-0 transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white">
                  Audiobook Pipeline
                </h1>
              </div>
              
              {/* Desktop Navigation */}
              <div className="hidden md:ml-6 md:flex md:space-x-1">
                {tabs.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = location.pathname === tab.path;
                  return (
                    <Link
                      key={tab.path}
                      to={tab.path}
                      className={`inline-flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 relative ${
                        isActive
                          ? "bg-indigo-100 dark:bg-indigo-900 text-indigo-700 dark:text-indigo-200"
                          : "text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white"
                      }`}
                    >
                      <Icon className="w-4 h-4 mr-2" />
                      <span className="hidden lg:inline">{tab.label}</span>
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

            <div className="flex items-center space-x-2">
              <DarkModeToggle />
              
              {/* Mobile menu button */}
              <button
                type="button"
                className="md:hidden inline-flex items-center justify-center p-2 rounded-md text-gray-400 dark:text-gray-300 hover:text-gray-500 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                aria-expanded="false"
              >
                <span className="sr-only">Open main menu</span>
                {mobileMenuOpen ? (
                  <X className="block h-6 w-6" aria-hidden="true" />
                ) : (
                  <Menu className="block h-6 w-6" aria-hidden="true" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden">
            <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
              {tabs.map((tab) => (
                <NavLink key={tab.path} tab={tab} />
              ))}
            </div>
          </div>
        )}
      </nav>

      <main className="w-full mx-auto py-4 sm:py-6 px-4 sm:px-6 lg:px-8 flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  );
};

export default Layout;
