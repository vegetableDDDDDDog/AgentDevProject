/**
 * 头部导航组件
 *
 * 显示用户信息和登出按钮。
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { logout } from '../../services/auth';
import { getUserInfo } from '../../utils/token';
import type { User } from '../../types';

export const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // 从 localStorage 获取用户信息
    const userInfo = getUserInfo();
    setUser(userInfo);
  }, []);

  const handleLogout = () => {
    logout();
  };

  /**
   * 导航链接样式
   */
  const navLinkStyle = (path: string) => ({
    padding: '8px 16px',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
    backgroundColor: location.pathname === path ? '#e6f7ff' : 'transparent',
    color: location.pathname === path ? '#1890ff' : '#333',
    border: 'none',
    transition: 'all 0.3s',
  });

  return (
    <header
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '16px 24px',
        backgroundColor: '#fff',
        borderBottom: '1px solid #e0e0e0',
        boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
        <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#1976d2' }}>
          Agent PaaS 平台
        </div>
        <nav style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => navigate('/chat')}
            style={navLinkStyle('/chat')}
          >
            聊天
          </button>
          <button
            onClick={() => navigate('/knowledge')}
            style={navLinkStyle('/knowledge')}
          >
            知识库
          </button>
        </nav>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <span style={{ fontSize: '14px', color: '#666' }}>
          {user?.email}
        </span>
        <button
          onClick={handleLogout}
          style={{
            padding: '8px 16px',
            backgroundColor: '#f5f5f5',
            color: '#333',
            border: '1px solid #ddd',
            borderRadius: '6px',
            fontSize: '14px',
            cursor: 'pointer',
          }}
        >
          登出
        </button>
      </div>
    </header>
  );
};
