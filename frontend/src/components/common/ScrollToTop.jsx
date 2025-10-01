import { useLayoutEffect } from 'react';
import { useLocation } from 'react-router-dom';

export default function ScrollToTop() {
  const { pathname, search, hash } = useLocation();

  useLayoutEffect(() => {
    // iOS Safari and modern browsers need different approaches
    const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);

    // Method 1: Direct scroll (works on most browsers)
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;

    // Method 2: Use scrollingElement (preferred modern approach)
    if (document.scrollingElement) {
      document.scrollingElement.scrollTop = 0;
    }

    // iOS specific: Sometimes needs a slight delay
    if (isIOS) {
      setTimeout(() => {
        window.scrollTo(0, 0);
        document.documentElement.scrollTop = 0;
      }, 0);
    }
  }, [pathname, search, hash]);

  return null;
}
