import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

export default function Modal({
  isOpen,
  onClose,
  children,
  ariaLabel = 'Dialog',
}) {
  const firstFocusRef = useRef(null);
  const scrollYRef = useRef(0);

  useEffect(() => {
    if (!isOpen) return;

    // --- Lock scroll (works reliably on iOS too) ---
    scrollYRef.current = window.scrollY || window.pageYOffset || 0;
    const body = document.body;
    body.style.position = 'fixed';
    body.style.top = `-${scrollYRef.current}px`;
    body.style.left = '0';
    body.style.right = '0';
    body.style.width = '100%';
    body.style.overflow = 'hidden'; // belt + suspenders
    // Helps prevent overscroll chaining on Android/Chrome
    document.documentElement.style.overscrollBehavior = 'contain';

    // Focus the first interactive element for a11y
    const t = setTimeout(() => firstFocusRef.current?.focus(), 0);

    // ESC to close
    const onKey = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    document.addEventListener('keydown', onKey);

    return () => {
      document.removeEventListener('keydown', onKey);
      // --- Restore scroll ---
      body.style.position = '';
      body.style.top = '';
      body.style.left = '';
      body.style.right = '';
      body.style.width = '';
      body.style.overflow = '';
      document.documentElement.style.overscrollBehavior = '';
      window.scrollTo(0, scrollYRef.current);
      clearTimeout(t);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Full-viewport fixed overlay ensures we’re centered
  const node = (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/75"
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel}
      onMouseDown={(e) => {
        // Click outside to close (but not when clicking the panel itself)
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      <div
        className="homepage-glass-section p-4 sm:p-6 w-full max-w-md outline-none"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="homepage-glass-content">
          {/* The element we’ll autofocus */}
          <div tabIndex={-1} ref={firstFocusRef} />
          {children}
        </div>
      </div>
    </div>
  );

  return createPortal(node, document.body);
}
