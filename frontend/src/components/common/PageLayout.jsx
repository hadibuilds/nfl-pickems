/*
 * PageLayout Component - Standard Template for All Pages
 * Ensures consistent navbar alignment across entire application
 * Use this for EVERY new page to avoid container alignment issues
 */

import React from 'react';

export default function PageLayout({ 
  children, 
  className = '',
  maxWidth = 'max-w-6xl', // Standard max-width, can be overridden
  fullHeight = true,
  backgroundColor = '#1E1E20'
}) {
  return (
    <div 
      className={`${fullHeight ? 'min-h-screen' : ''} pt-16 pb-12 px-6 ${className}`}
      style={{ backgroundColor, color: 'white' }}
    >
      <div className="page-container">
        <div className={`${maxWidth} mx-auto`}>
          {children}
        </div>
      </div>
    </div>
  );
}