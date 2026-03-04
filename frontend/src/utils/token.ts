/**
 * Token 管理
 */

const TOKEN_KEY = 'token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const USER_KEY = 'user';
const EXPIRES_AT_KEY = 'expires_at';

/**
 * 获取访问 token
 */
export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

/**
 * 保存访问 token
 */
export const setToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

/**
 * 移除 token
 */
export const removeToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(EXPIRES_AT_KEY);
};

/**
 * 获取刷新 token
 */
export const getRefreshToken = (): string | null => {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
};

/**
 * 保存刷新 token
 */
export const setRefreshToken = (token: string): void => {
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
};

/**
 * 保存用户信息
 */
export const setUser = (user: any): void => {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
};

/**
 * 获取用户信息
 */
export const getUser = (): any | null => {
  const userStr = localStorage.getItem(USER_KEY);
  if (userStr) {
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }
  return null;
};

/**
 * 获取用户信息（别名，兼容性）
 */
export const getUserInfo = getUser;

/**
 * 检查是否已认证
 */
export const isAuthenticated = (): boolean => {
  return !!getToken();
};

/**
 * 保存 Token 过期时间戳
 */
export const setExpiresAt = (expiresIn: number): void => {
  const expiresAt = Date.now() + expiresIn * 1000;
  localStorage.setItem(EXPIRES_AT_KEY, expiresAt.toString());
};

/**
 * 获取 Token 过期时间戳
 */
export const getExpiresAt = (): number | null => {
  const expiresAtStr = localStorage.getItem(EXPIRES_AT_KEY);
  if (expiresAtStr) {
    try {
      return parseInt(expiresAtStr, 10);
    } catch {
      return null;
    }
  }
  return null;
};

/**
 * 判断 Token 是否即将过期（剩余时间 ≤ 2 分钟）
 */
export const isTokenExpiring = (): boolean => {
  const expiresAt = getExpiresAt();
  if (!expiresAt) {
    return false;
  }
  const now = Date.now();
  const timeRemaining = expiresAt - now;
  return timeRemaining <= 2 * 60 * 1000; // 2 分钟
};
