/**
 * Pull-to-Refresh for PWA mode
 * Native-like pull down gesture to refresh the app
 * Only activates in PWA/standalone mode
 */

export function initPullToRefresh() {
  // Only enable in PWA mode
  const isPWA = window.matchMedia('(display-mode: standalone)').matches ||
                window.navigator.standalone === true;

  if (!isPWA) {
    console.log('Pull-to-refresh: Not in PWA mode, skipping');
    return;
  }

  let startY = 0;
  let currentY = 0;
  let isPulling = false;
  let pullIndicator = null;

  const PULL_THRESHOLD = 80; // Distance to pull before triggering refresh
  const MAX_PULL = 150; // Maximum pull distance

  function createPullIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'pull-to-refresh-indicator';

    // Calculate position below navbar (64px base + safe area)
    const safeAreaTop = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--viewport-offset-top') || '0');
    const navbarHeight = 64;
    const startingTop = navbarHeight + safeAreaTop;

    indicator.style.cssText = `
      position: fixed;
      top: ${startingTop}px;
      left: 50%;
      transform: translateX(-50%) translateY(-100px);
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: rgba(139, 92, 246, 0.9);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1500;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
      opacity: 0;
    `;
    indicator.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
        <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
      </svg>
    `;
    document.body.appendChild(indicator);
    return indicator;
  }

  function handleTouchStart(e) {
    // Don't trigger if modal is open
    if (document.body.dataset.modalOpen === 'true') return;

    // Only trigger if at top of page
    if (window.scrollY > 10) return;

    startY = e.touches[0].clientY;
    isPulling = true;

    if (!pullIndicator) {
      pullIndicator = createPullIndicator();
    }
  }

  function handleTouchMove(e) {
    if (!isPulling || window.scrollY > 10) return;

    currentY = e.touches[0].clientY;
    const pullDistance = Math.min(currentY - startY, MAX_PULL);

    if (pullDistance > 0) {
      // Prevent default scrolling while pulling
      e.preventDefault();

      // Calculate position below navbar
      const safeAreaTop = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--viewport-offset-top') || '0');
      const navbarHeight = 64;
      const startingTop = navbarHeight + safeAreaTop;

      // Update indicator position - translateY animates from -100px up to visible
      const progress = Math.min(pullDistance / PULL_THRESHOLD, 1);
      const indicatorOffset = Math.min(pullDistance * 0.8, 100); // Slide down as you pull

      pullIndicator.style.top = `${startingTop}px`;
      pullIndicator.style.transform = `translateX(-50%) translateY(${indicatorOffset - 100}px) rotate(${pullDistance * 2}deg)`;
      pullIndicator.style.opacity = progress;

      // Change color when threshold reached
      if (pullDistance >= PULL_THRESHOLD) {
        pullIndicator.style.background = 'rgba(16, 185, 129, 0.9)';
      } else {
        pullIndicator.style.background = 'rgba(139, 92, 246, 0.9)';
      }
    }
  }

  function handleTouchEnd() {
    if (!isPulling) return;

    const pullDistance = currentY - startY;
    const safeAreaTop = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--viewport-offset-top') || '0');
    const navbarHeight = 64;
    const startingTop = navbarHeight + safeAreaTop;

    if (pullDistance >= PULL_THRESHOLD) {
      // Trigger refresh - show at final visible position below navbar
      pullIndicator.style.top = `${startingTop + 10}px`;
      pullIndicator.style.transform = 'translateX(-50%) translateY(0) rotate(360deg)';
      pullIndicator.querySelector('svg').style.animation = 'spin 1s linear infinite';

      // Reload after brief delay
      setTimeout(() => {
        window.location.reload();
      }, 300);
    } else {
      // Reset indicator - hide above navbar
      pullIndicator.style.top = `${startingTop}px`;
      pullIndicator.style.transform = 'translateX(-50%) translateY(-100px) rotate(0deg)';
      pullIndicator.style.opacity = '0';
    }

    isPulling = false;
    startY = 0;
    currentY = 0;
  }

  // Add event listeners
  document.addEventListener('touchstart', handleTouchStart, { passive: false });
  document.addEventListener('touchmove', handleTouchMove, { passive: false });
  document.addEventListener('touchend', handleTouchEnd);

  console.log('Pull-to-refresh: Enabled for PWA mode');

  // Return cleanup function
  return () => {
    document.removeEventListener('touchstart', handleTouchStart);
    document.removeEventListener('touchmove', handleTouchMove);
    document.removeEventListener('touchend', handleTouchEnd);
    if (pullIndicator) {
      pullIndicator.remove();
    }
  };
}
