/*
 * PageLayout Component - Standard Template for All Pages
 * Ensures consistent navbar alignment across entire application
 * MOBILE-OPTIMIZED: Full viewport experience on mobile, constrained on desktop
 * Use this for EVERY new page to avoid container alignment issues
 */

import React from 'react';

export default function PageLayout({
  children,
  className = '',
  maxWidth = 'max-w-6xl', // Standard max-width, can be overridden
  fullHeight = true,
  // Darker, more neutral background to match refined dashboard look
  backgroundColor = '#05060A',
  mobileFullWidth = true // New prop for mobile behavior
}) {
  return (
    <div
      className={`
        ${fullHeight ? 'min-h-screen' : ''}
        ${mobileFullWidth ? 'px-1 sm:px-4 md:px-6' : 'px-6'}
        ${className}
      `}
      style={{
        backgroundColor,
        color: 'white',
        /* Dynamic padding that matches navbar height + safe area */
        paddingTop: 'calc(64px + env(safe-area-inset-top, 0px))',
        paddingBottom: '1rem'
      }}
    >
      <div className="page-container">
        <div className={`${maxWidth} mx-auto`}>
          {children}
        </div>
      </div>
    </div>
  );
}