import { useLayoutEffect } from 'react';
import { useLocation } from 'react-router-dom';

export default function ScrollToTop() {
  const { pathname, search, hash } = useLocation();

  useLayoutEffect(() => {
    const html = document.documentElement;
    const prev = html.style.scrollBehavior;
    // Disable smooth scrolling during the jump to avoid races
    html.style.scrollBehavior = 'auto';

    // Reset the real root
    (document.scrollingElement || html).scrollTo(0, 0);
    // Also call window for broader compatibility
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });

    // Restore prior behavior
    html.style.scrollBehavior = prev || '';
  }, [pathname, search, hash]);

  return null;
}
