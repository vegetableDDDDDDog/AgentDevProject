/**
 * API 服务 - Axios 配置和请求封装
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { getToken, removeToken, isTokenExpiring } from '../utils/token';
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

// 响应拦截器 - 处理错误
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<APIError>) => {
    // Token 过期，自动登出
    if (error.response?.status === 401) {
      removeToken();
      window.location.href = '/login';
    }

    // 返回统一错误格式
    const apiError: APIError = error.response?.data || {
      error: 'UNKNOWN_ERROR',
      message: '未知错误',
    };

    return Promise.reject(apiError);
  }
);

export default apiClient;
