import axios from "axios";
import {
  Download,
  LogEntry,
  RSSItem,
  TaggingItem,
  TorrentInfo,
} from "../shared/types/api";

export interface ConversionTracking {
  id: number;
  book_name: string;
  total_files: number;
  converted_files: number;
  current_file: string | null;
  status: string;
  progress_percentage: number;
  estimated_eta_seconds: number | null;
  merge_folder_path: string | null;
  temp_folder_path: string | null;
  created_at: string;
  updated_at: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8081";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

export const rssService = {
  async getRSSItems(): Promise<RSSItem[]> {
    const response = await api.get("/rss-items");
    return response.data;
  },
};

export const downloadService = {
  async getDownloads(): Promise<Download[]> {
    const response = await api.get("/downloads");
    return response.data;
  },
};

export const torrentService = {
  async getTorrents(): Promise<TorrentInfo[]> {
    const response = await api.get("/torrents");
    return response.data;
  },

  async startTorrent(torrentId: number): Promise<void> {
    await api.post(`/torrents/${torrentId}/start`);
  },

  async stopTorrent(torrentId: number): Promise<void> {
    await api.post(`/torrents/${torrentId}/stop`);
  },

  async getAvailableTorrents(): Promise<
    { filename: string; size: number; path: string }[]
  > {
    const response = await api.get("/torrents/available");
    return response.data.torrents;
  },

  async addTorrent(rssItemId: number): Promise<void> {
    await api.post("/torrents/add", { rss_item_id: rssItemId });
  },
};

export const taggingService = {
  async getTaggingItems(): Promise<TaggingItem[]> {
    const response = await api.get("/tagging");
    return response.data;
  },

  async getTaggingStatus(): Promise<{
    service: string;
    status: string;
    url: string;
    error?: string;
  }> {
    const response = await api.get("/tagging/status");
    return response.data;
  },

  async updateTaggingItemStatus(itemId: number, status: string): Promise<void> {
    await api.put(`/tagging/items/${itemId}/status`, null, {
      params: { status },
    });
  },

  async searchAudibleBooks(
    query: string,
    locale: string = "com"
  ): Promise<any[]> {
    const response = await api.post("/tagging/search", { query, locale });
    return response.data.results;
  },

  async tagFile(filePath: string, bookData: any): Promise<void> {
    await api.post("/tagging/tag-file", {
      file_path: filePath,
      book_data: bookData,
    });
  },

  async parseFilename(filename: string): Promise<{
    filename: string;
    title: string;
    author: string;
    suggested_query: string;
  }> {
    const response = await api.post("/tagging/parse-filename", { filename });
    return response.data;
  },
};

export const logService = {
  async getLogs(): Promise<LogEntry[]> {
    const response = await api.get("/logs");
    return response.data;
  },
};

export const conversionService = {
  async getConversions(): Promise<ConversionTracking[]> {
    const response = await api.get("/conversions");
    return response.data;
  },

  async getConversion(conversionId: number): Promise<ConversionTracking> {
    const response = await api.get(`/conversions/${conversionId}`);
    return response.data;
  },

  async triggerConversion(
    bookName: string,
    sourcePath: string,
    rssItemId?: number
  ): Promise<void> {
    await api.post("/conversions/trigger", {
      book_name: bookName,
      source_path: sourcePath,
      rss_item_id: rssItemId,
    });
  },

  async retryConversion(
    conversionId: number,
    force: boolean = false
  ): Promise<void> {
    await api.post(`/conversions/${conversionId}/retry`, { force });
  },

  async cancelConversion(conversionId: number): Promise<void> {
    await api.post(`/conversions/${conversionId}/cancel`);
  },

  async getConversionJobs(): Promise<any[]> {
    const response = await api.get("/conversions/jobs");
    return response.data;
  },

  async getBackups(): Promise<any[]> {
    const response = await api.get("/conversions/backups");
    return response.data;
  },

  async deleteBackup(backupName: string): Promise<void> {
    await api.delete(`/conversions/backups/${backupName}`);
  },

  async getSystemHealth(): Promise<any> {
    const response = await api.get("/system/health");
    return response.data;
  },

  async getRedisStatus(): Promise<any> {
    const response = await api.get("/system/redis/status");
    return response.data;
  },
};

export default api;
