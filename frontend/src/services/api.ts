/**
 * API 服务 - Axios 配置和请求封装
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { getToken, removeToken } from '../utils/token';
import type { APIError } from '../types';

// API 基础 URL
const BASE_URL = import.meta.env.VITE_API_URL || '/api';

// 创建 Axios 实例
const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加 Token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
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
