/**
 * API 服务 - Axios 配置和请求封装
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { getToken, isTokenExpiring } from '../utils/token';
import { refreshAccessToken, forceLogout } from './auth';
import type { APIError } from '../types';

// API 基础 URL
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// 创建 Axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 刷新锁：防止并发刷新
let isRefreshing = false;
// 等待队列：存储刷新期间的请求
let failedQueue: Array<{
  resolve: (value?: any) => void;
  reject: (reason?: any) => void;
}> = [];

/**
 * 处理队列：刷新成功后重试所有请求
 */
const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });

  failedQueue = [];
};

// 请求拦截器 - 添加 Token + 主动刷新
apiClient.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const token = getToken();
    if (!token) {
      return config;
    }

    // 主动刷新：检查 Token 是否即将过期
    if (isTokenExpiring()) {
      if (!isRefreshing) {
        isRefreshing = true;
        try {
          await refreshAccessToken();
          isRefreshing = false;
          processQueue(null, getToken());
        } catch (error) {
          isRefreshing = false;
          processQueue(error, null);
          forceLogout();
          return Promise.reject(error);
        }
      } else {
        // 如果正在刷新，将请求加入队列
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => {
            config.headers.Authorization = `Bearer ${getToken()}`;
            return config;
          })
          .catch((error) => {
            return Promise.reject(error);
          });
      }
    }

    config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 被动刷新（401 错误处理）
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<APIError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // 401 错误处理
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      // 如果正在刷新，将请求加入队列
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then(() => {
            originalRequest.headers.Authorization = `Bearer ${getToken()}`;
            return apiClient(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      // 标记为重试，避免无限循环
      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // 刷新 Token
        await refreshAccessToken();
        isRefreshing = false;
        processQueue(null, getToken());

        // 重试原请求
        originalRequest.headers.Authorization = `Bearer ${getToken()}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // 刷新失败，强制登出
        isRefreshing = false;
        processQueue(refreshError, null);
        forceLogout();
        return Promise.reject(refreshError);
      }
    }

    // 区分 401 登出错误和其他错误
    if (error.response?.status === 401) {
      // 非 Token 过期的 401 错误（如无效凭证），直接登出
      forceLogout();
    }

    // 网络/5xx 错误：保留错误信息，不登出
    const apiError: APIError = error.response?.data || {
      error: 'UNKNOWN_ERROR',
      message: '未知错误',
    };

    return Promise.reject(apiError);
  }
);

export default apiClient;
