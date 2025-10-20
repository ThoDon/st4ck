import axios from "axios";
import {
  Download,
  LogEntry,
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

};

export const taggingService = {
  async getTaggingItems(): Promise<TaggingItem[]> {
    const response = await api.get("/tagging");
    return response.data;
  },

  async updateTaggingItemStatus(itemId: number, status: string): Promise<void> {
    await api.put(`/tagging/items/${itemId}/status`, null, {
      params: { status },
    });
  },

  async searchAudibleBooks(
    query: string,
    locale: string = "fr"
  ): Promise<any[]> {
    const response = await api.post("/tagging/search", { query, locale });
    return response.data.results;
  },

  async tagFileByAsin(filePath: string, asin: string, locale: string = "fr"): Promise<void> {
    await api.post("/tagging/tag-file-by-asin", {
      file_path: filePath,
      asin,
      locale,
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

  async retryConversion(
    conversionId: number,
    force: boolean = false
  ): Promise<void> {
    await api.post(`/conversions/${conversionId}/retry`, { force });
  },

  async cancelConversion(conversionId: number): Promise<void> {
    await api.post(`/conversions/${conversionId}/cancel`);
  },

};

// YGG Gateway service
export interface YGGTorrent {
  id: number;
  title: string;
  category_id: number;
  size: number;
  seeders: number;
  leechers: number;
  downloads?: number;
  uploaded_at: string;
  link: string;
  slug?: string; // deprecated field
}

export interface YGGSearchResponse {
  torrents: YGGTorrent[];
  total: number;
  page: number;
  per_page: number;
}

// Categories interfaces removed - YGG API doesn't provide categories

export const yggService = {
  async searchTorrents(query: string, category?: string, limit: number = 100, page: number = 1): Promise<YGGSearchResponse> {
    const params = new URLSearchParams({
      q: query,
      limit: limit.toString(),
      page: page.toString(),
    });
    
    if (category) {
      params.append('category', category);
    }
    
    const response = await api.get(`/ygg/search?${params.toString()}`);
    return response.data;
  },

  async addTorrentToTransmission(torrentId: string, downloadType: string = "magnet"): Promise<void> {
    await api.post("/ygg/torrent/add", {
      torrent_id: torrentId,
      download_type: downloadType,
    });
  },
};

export default api;
