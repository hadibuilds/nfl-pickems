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
  let bodyElement = null;

  const PULL_THRESHOLD = 70; // Distance to pull before triggering refresh (reduced for better feel)
  const MAX_PULL = 120; // Maximum pull distance
  const RESISTANCE_FACTOR = 0.5; // Elastic resistance (0.5 = half the pull distance)

  function createPullIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'pull-to-refresh-indicator';

    // Position below navbar - calculate navbar height + safe area
    const navbarHeight = 64;
    const safeAreaTop = getComputedStyle(document.documentElement)
      .getPropertyValue('padding-top')
      .replace('px', '') || 0;
    const belowNavbar = navbarHeight + parseInt(safeAreaTop);

    indicator.style.cssText = `
      position: fixed;
      top: ${belowNavbar}px;
      left: 50%;
      transform: translateX(-50%) translateY(-50px) scale(0.8);
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: rgba(139, 92, 246, 0.9);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease-out;
      box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
      opacity: 0;
      pointer-events: none;
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

    // Get the main content body (everything that should move)
    if (!bodyElement) {
      bodyElement = document.getElementById('root');
      if (bodyElement) {
        bodyElement.style.transition = 'transform 0.1s ease-out';
      }
    }
  }

  function handleTouchMove(e) {
    if (!isPulling || window.scrollY > 10) return;

    currentY = e.touches[0].clientY;
    let pullDistance = Math.min(currentY - startY, MAX_PULL);

    if (pullDistance > 0) {
      // Prevent default scrolling while pulling
      e.preventDefault();

      // Apply resistance/elastic effect
      const resistedDistance = pullDistance * RESISTANCE_FACTOR;
      const progress = Math.min(pullDistance / PULL_THRESHOLD, 1);

      // Move the entire body down with elastic resistance
      if (bodyElement) {
        bodyElement.style.transform = `translateY(${resistedDistance}px)`;
      }

      // Update indicator - slide down from hidden position above navbar
      // Starts at -50px (hidden), slides to 10px (visible below navbar) as you pull
      const indicatorY = Math.max(-50, (resistedDistance - 60)); // Reveals as you pull
      const scale = 0.8 + (progress * 0.2); // Grows from 0.8 to 1.0
      const rotation = pullDistance * 1.5; // Subtle rotation

      pullIndicator.style.transform = `translateX(-50%) translateY(${indicatorY}px) scale(${scale}) rotate(${rotation}deg)`;
      pullIndicator.style.opacity = Math.min(progress * 1.2, 1);

      // Change color when threshold reached
      if (pullDistance >= PULL_THRESHOLD) {
        pullIndicator.style.background = 'rgba(16, 185, 129, 0.9)';
        pullIndicator.style.boxShadow = '0 4px 12px rgba(16, 185, 129, 0.5)';
      } else {
        pullIndicator.style.background = 'rgba(139, 92, 246, 0.9)';
        pullIndicator.style.boxShadow = '0 4px 12px rgba(139, 92, 246, 0.4)';
      }
    }
  }

  function handleTouchEnd() {
    if (!isPulling) return;

    const pullDistance = currentY - startY;

    if (pullDistance >= PULL_THRESHOLD) {
      // Trigger refresh - position spinner below navbar and spin
      pullIndicator.style.transition = 'transform 0.3s ease';
      pullIndicator.style.transform = 'translateX(-50%) translateY(15px) scale(1) rotate(360deg)';
      pullIndicator.querySelector('svg').style.animation = 'spin 1s linear infinite';

      // Keep body slightly down during reload (shows spinner in gap)
      if (bodyElement) {
        bodyElement.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        bodyElement.style.transform = 'translateY(30px)';
      }

      // Reload after brief delay
      setTimeout(() => {
        window.location.reload();
      }, 400);
    } else {
      // Elastic bounce-back animation
      pullIndicator.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease';
      pullIndicator.style.transform = 'translateX(-50%) translateY(-50px) scale(0.8) rotate(0deg)';
      pullIndicator.style.opacity = '0';

      // Reset body position with bounce
      if (bodyElement) {
        bodyElement.style.transition = 'transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)'; // Elastic ease-out
        bodyElement.style.transform = 'translateY(0)';
      }
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
