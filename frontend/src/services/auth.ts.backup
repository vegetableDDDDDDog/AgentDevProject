/**
 * 认证服务
 *
 * 提供用户登录、登出、Token 刷新等认证相关功能。
 */

import apiClient from './api';
import type {
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  User
} from '../types';
import {
  setToken,
  setRefreshToken,
  setUser,
  removeToken
} from '../utils/token';

/**
 * 用户登录
 */
export const login = async (
  email: string,
  password: string
): Promise<AuthResponse> => {
  const response = await apiClient.post<AuthResponse>(
    '/auth/login',
    {
      email,
      password
    }
  );

  // 存储 Token 和用户信息
  setToken(response.data.access_token);
  setRefreshToken(response.data.refresh_token);
  setUser(response.data.user);

  return response.data;
};

/**
 * 用户注册
 */
export const register = async (
  email: string,
  password: string,
  displayName?: string
): Promise<AuthResponse> => {
  const response = await apiClient.post<AuthResponse>('/auth/register', {
    email,
    password,
    display_name: displayName,
  });

  return response.data;
};

/**
 * 登出
 */
export const logout = (): void => {
  removeToken();
  window.location.href = '/login';
};

/**
 * 获取当前用户信息
 */
export const getCurrentUser = async (): Promise<User> => {
  const response = await apiClient.get<{ user: User }>('/auth/me');
  return response.data.user;
};

/**
 * 刷新 Token
 */
export const refreshToken = async (
  refreshToken: string
): Promise<{ access_token: string }> => {
  const response = await apiClient.post<{ access_token: string }>(
    '/auth/refresh',
    { refresh_token: refreshToken }
  );

  // 更新 Token
  setToken(response.data.access_token);

  return response.data;
};
