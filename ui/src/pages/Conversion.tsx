import { useQuery } from "@tanstack/react-query";
import { Download, Pause, Play, RotateCcw } from "lucide-react";
import React from "react";
import { conversionService, torrentService } from "../services/api";

const Conversion: React.FC = () => {
  const { data: conversionItems, isLoading: conversionLoading } = useQuery({
    queryKey: ["conversion-items"],
    queryFn: conversionService.getConversionItems,
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  const { data: torrents, isLoading: torrentsLoading } = useQuery({
    queryKey: ["torrents"],
    queryFn: torrentService.getTorrents,
    refetchInterval: 5000, // Refetch every 5 seconds
  });

  const handleStartTorrent = async (torrentId: number) => {
    try {
      await torrentService.startTorrent(torrentId);
    } catch (error) {
      console.error("Failed to start torrent:", error);
    }
  };

  const handleStopTorrent = async (torrentId: number) => {
    try {
      await torrentService.stopTorrent(torrentId);
    } catch (error) {
      console.error("Failed to stop torrent:", error);
    }
  };

  if (conversionLoading || torrentsLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="space-y-6">
        {/* Active Torrents */}
        <div className="border-4 border-dashed border-gray-200 rounded-lg p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            Active Torrents
          </h2>

          {torrents && torrents.length > 0 ? (
            <div className="space-y-4">
              {torrents.map((torrent) => (
                <div
                  key={torrent.id}
                  className="bg-white overflow-hidden shadow rounded-lg border border-gray-200"
                >
                  <div className="px-4 py-5 sm:p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h3 className="text-lg font-medium text-gray-900 mb-2">
                          {torrent.name}
                        </h3>
                        <div className="flex items-center space-x-4">
                          <div className="flex items-center">
                            <span className="text-sm text-gray-500">
                              Progress: {torrent.progress.toFixed(1)}%
                            </span>
                          </div>
                          <div className="flex items-center">
                            <span
                              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                torrent.status === "4"
                                  ? "bg-green-100 text-green-800"
                                  : "bg-yellow-100 text-yellow-800"
                              }`}
                            >
                              {torrent.status === "4"
                                ? "Seeding"
                                : "Downloading"}
                            </span>
                          </div>
                        </div>
                        <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-indigo-600 h-2 rounded-full"
                            style={{ width: `${torrent.progress}%` }}
                          ></div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handleStartTorrent(torrent.id)}
                          className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                        >
                          <Play className="w-4 h-4 mr-1" />
                          Start
                        </button>
                        <button
                          onClick={() => handleStopTorrent(torrent.id)}
                          className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                        >
                          <Pause className="w-4 h-4 mr-1" />
                          Stop
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
                No active torrents
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                No torrents are currently downloading.
              </p>
            </div>
          )}
        </div>

        {/* Conversion Queue */}
        <div className="border-4 border-dashed border-gray-200 rounded-lg p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">
            Conversion Queue
          </h2>

          {conversionItems && conversionItems.length > 0 ? (
            <div className="space-y-4">
              {conversionItems.map((item, index) => (
                <div
                  key={index}
                  className="bg-white overflow-hidden shadow rounded-lg border border-gray-200"
                >
                  <div className="px-4 py-5 sm:p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <h3 className="text-lg font-medium text-gray-900 mb-2">
                          {item.name}
                        </h3>
                        <div className="flex items-center">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              item.status === "waiting"
                                ? "bg-yellow-100 text-yellow-800"
                                : "bg-green-100 text-green-800"
                            }`}
                          >
                            {item.status}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <button className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                          <RotateCcw className="w-4 h-4 mr-1" />
                          Retry
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <RotateCcw className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">
                No items in conversion queue
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                No items are waiting for conversion to M4B.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Conversion;
