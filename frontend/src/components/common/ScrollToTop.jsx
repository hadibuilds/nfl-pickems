import { useLayoutEffect } from 'react';
import { useLocation } from 'react-router-dom';

export default function ScrollToTop() {
  const { pathname, search, hash } = useLocation();

  useLayoutEffect(() => {
    // Force body to be scrollable (in case dropdown or modal interfered)
    document.body.style.overflow = 'auto';
    document.documentElement.style.overflow = 'auto';

    // Direct scroll - works on all browsers including iOS
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;

    // Use scrollingElement (preferred modern approach)
    if (document.scrollingElement) {
      document.scrollingElement.scrollTop = 0;
    }
  }, [pathname, search, hash]);

  return null;
}
