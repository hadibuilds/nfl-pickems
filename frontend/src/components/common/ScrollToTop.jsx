import { useLayoutEffect } from 'react';
import { useLocation } from 'react-router-dom';

export default function ScrollToTop() {
  const { pathname, search, hash } = useLocation();

  useLayoutEffect(() => {
    // iOS Safari and modern browsers need different approaches
    const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);

    // Force body to be scrollable (in case dropdown or modal interfered)
    document.body.style.overflow = 'auto';
    document.documentElement.style.overflow = 'auto';

    const performScroll = () => {
      // Method 1: Direct scroll (works on most browsers)
      window.scrollTo(0, 0);
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;

      // Method 2: Use scrollingElement (preferred modern approach)
      if (document.scrollingElement) {
        document.scrollingElement.scrollTop = 0;
      }
    };

    // Immediate scroll
    performScroll();

    // iOS specific: Multiple attempts to ensure scroll happens
    if (isIOS) {
      // First attempt after microtask
      setTimeout(() => performScroll(), 0);

      // Second attempt after dropdown animation (300ms)
      setTimeout(() => performScroll(), 300);
    }
  }, [pathname, search, hash]);

  return null;
}
