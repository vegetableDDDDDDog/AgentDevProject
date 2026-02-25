/**
 * 头部导航组件
 *
 * 显示用户信息和登出按钮。
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { logout } from '../../services/auth';
import type { User } from '../../types';

export const Header: React.FC = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // TODO: 从 localStorage 或 API 获取用户信息
    // 这里先使用 mock 数据
    setUser({
      id: '1',
      email: 'user@example.com',
      role: 'user',
      tenant_id: 'tenant-1'
    });
  }, []);

  const handleLogout = () => {
    logout();
  };

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
      <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#1976d2' }}>
        Agent PaaS 平台
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
