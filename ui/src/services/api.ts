import axios from "axios";
import {
  ConversionItem,
  Download,
  LogEntry,
  RSSItem,
  TaggingItem,
  TorrentInfo,
} from "../shared/types/api";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// No authentication needed

// Authentication service removed

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

export const conversionService = {
  async getConversionItems(): Promise<ConversionItem[]> {
    const response = await api.get("/conversion");
    return response.data;
  },
};

export const taggingService = {
  async getTaggingItems(): Promise<TaggingItem[]> {
    const response = await api.get("/tagging");
    return response.data;
  },

  async triggerTagging(): Promise<void> {
    await api.post("/tagging/trigger");
  },
};

export const logService = {
  async getLogs(): Promise<LogEntry[]> {
    const response = await api.get("/logs");
    return response.data;
  },
};

export default api;
