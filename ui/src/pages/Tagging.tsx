import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle, Play, Tag } from "lucide-react";
import React from "react";
import { taggingService } from "../services/api";

const Tagging: React.FC = () => {
  const queryClient = useQueryClient();

  const { data: taggingItems, isLoading } = useQuery({
    queryKey: ["tagging-items"],
    queryFn: taggingService.getTaggingItems,
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  const triggerTaggingMutation = useMutation({
    mutationFn: taggingService.triggerTagging,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tagging-items"] });
    },
  });

  const handleTriggerTagging = () => {
    triggerTaggingMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="border-4 border-dashed border-gray-200 rounded-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">Tagging Queue</h2>
          <button
            onClick={handleTriggerTagging}
            disabled={triggerTaggingMutation.isPending}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {triggerTaggingMutation.isPending ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Processing...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Trigger Tagging
              </>
            )}
          </button>
        </div>

        {taggingItems && taggingItems.length > 0 ? (
          <div className="space-y-4">
            {taggingItems.map((item, index) => (
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
                      <div className="flex items-center space-x-4">
                        <div className="flex items-center">
                          <span className="text-sm text-gray-500">
                            Path: {item.path}
                          </span>
                        </div>
                        <div className="flex items-center">
                          <span
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              item.status === "waiting"
                                ? "bg-yellow-100 text-yellow-800"
                                : item.status === "completed"
                                ? "bg-green-100 text-green-800"
                                : "bg-gray-100 text-gray-800"
                            }`}
                          >
                            {item.status}
                          </span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {item.status === "completed" && (
                        <CheckCircle className="w-5 h-5 text-green-500" />
                      )}
                      {item.status === "waiting" && (
                        <Tag className="w-5 h-5 text-yellow-500" />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <Tag className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">
              No items in tagging queue
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              No M4B files are waiting for tagging.
            </p>
          </div>
        )}

        {triggerTaggingMutation.isSuccess && (
          <div className="mt-4 bg-green-50 border border-green-200 rounded-md p-4">
            <div className="flex">
              <CheckCircle className="h-5 w-5 text-green-400" />
              <div className="ml-3">
                <h3 className="text-sm font-medium text-green-800">
                  Tagging triggered successfully
                </h3>
                <div className="mt-2 text-sm text-green-700">
                  The auto-m4b-audible-tagger has been triggered to process
                  waiting files.
                </div>
              </div>
            </div>
          </div>
        )}

        {triggerTaggingMutation.isError && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Failed to trigger tagging
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  {triggerTaggingMutation.error instanceof Error
                    ? triggerTaggingMutation.error.message
                    : "Unknown error occurred"}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Tagging;
