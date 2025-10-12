import { useQuery } from "@tanstack/react-query";
import {
  rssService,
  torrentService,
  taggingService,
  conversionService,
  logService,
} from "../services/api";

// Centralized query keys
export const QUERY_KEYS = {
  RSS_ITEMS: ["rss-items"],
  TORRENTS: ["torrents"],
  TAGGING_ITEMS: ["tagging-items"],
  CONVERSIONS: ["conversions"],
  LOGS: ["logs"],
} as const;

// RSS Items hook
export const useRSSItems = () => {
  return useQuery({
    queryKey: QUERY_KEYS.RSS_ITEMS,
    queryFn: rssService.getRSSItems,
    refetchInterval: 30000, // Refetch every 30 seconds
  });
};

// Torrents hook
export const useTorrents = () => {
  return useQuery({
    queryKey: QUERY_KEYS.TORRENTS,
    queryFn: torrentService.getTorrents,
    refetchInterval: 5000, // Refetch every 5 seconds
  });
};

// Tagging Items hook
export const useTaggingItems = () => {
  return useQuery({
    queryKey: QUERY_KEYS.TAGGING_ITEMS,
    queryFn: taggingService.getTaggingItems,
    refetchInterval: 10000, // Refetch every 10 seconds
  });
};

// Conversions hook
export const useConversions = () => {
  return useQuery({
    queryKey: QUERY_KEYS.CONVERSIONS,
    queryFn: conversionService.getConversions,
    refetchInterval: 5000, // Refresh every 5 seconds
  });
};

// Logs hook
export const useLogs = () => {
  return useQuery({
    queryKey: QUERY_KEYS.LOGS,
    queryFn: logService.getLogs,
    refetchInterval: 5000, // Refetch every 5 seconds
  });
};

// Status indicator hooks
export const useDownloadingStatus = () => {
  const { data: torrents, isLoading } = useTorrents();

  const hasActiveDownloads =
    torrents?.some(
      (torrent) =>
        torrent.status === "downloading" ||
        torrent.status === "seeding" ||
        (torrent.progress > 0 && torrent.progress < 100)
    ) ?? false;

  return {
    hasActiveDownloads,
    isLoading,
    count:
      torrents?.filter(
        (torrent) =>
          torrent.status === "downloading" ||
          torrent.status === "seeding" ||
          (torrent.progress > 0 && torrent.progress < 100)
      ).length ?? 0,
  };
};

export const useConvertingStatus = () => {
  const { data: conversions, isLoading } = useConversions();

  const hasActiveConversions =
    conversions?.some(
      (conversion) =>
        conversion.status === "converting" || conversion.status === "pending"
    ) ?? false;

  return {
    hasActiveConversions,
    isLoading,
    count:
      conversions?.filter(
        (conversion) =>
          conversion.status === "converting" || conversion.status === "pending"
      ).length ?? 0,
  };
};

export const useTaggingStatus = () => {
  const { data: taggingItems, isLoading } = useTaggingItems();

  const hasPendingTagging =
    taggingItems?.some(
      (item) => item.status === "pending" || item.status === "waiting"
    ) ?? false;

  return {
    hasPendingTagging,
    isLoading,
    count:
      taggingItems?.filter(
        (item) => item.status === "pending" || item.status === "waiting"
      ).length ?? 0,
  };
};

// Combined status hook for easy access to all statuses
export const useAllStatuses = () => {
  const downloadingStatus = useDownloadingStatus();
  const convertingStatus = useConvertingStatus();
  const taggingStatus = useTaggingStatus();

  return {
    downloading: downloadingStatus,
    converting: convertingStatus,
    tagging: taggingStatus,
    isLoading:
      downloadingStatus.isLoading ||
      convertingStatus.isLoading ||
      taggingStatus.isLoading,
  };
};
