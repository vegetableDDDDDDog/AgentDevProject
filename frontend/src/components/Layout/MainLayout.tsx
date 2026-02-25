/**
 * 主布局组件
 *
 * 包含头部和内容区域的页面布局。
 */

import React from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';

export const MainLayout: React.FC = () => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
      }}
    >
      <Header />
      <main
        style={{
          flex: 1,
          overflow: 'auto',
        }}
      >
        <Outlet />
      </main>
    </div>
  );
};
