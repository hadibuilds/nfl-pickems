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

    // Dynamically get navbar height from actual navbar element
    const navbar = document.querySelector('.navbar-container');
    let navbarBottomPosition = 64; // Default fallback

    if (navbar) {
      // Get the actual bottom position of navbar (includes safe area)
      const navbarRect = navbar.getBoundingClientRect();
      navbarBottomPosition = navbarRect.bottom;
    } else {
      // No navbar (auth pages) - just use safe area inset
      const safeAreaTop = getComputedStyle(document.documentElement)
        .getPropertyValue('env(safe-area-inset-top)') || '0px';
      navbarBottomPosition = parseInt(safeAreaTop) || 0;
    }

    indicator.style.cssText = `
      position: fixed;
      top: ${navbarBottomPosition}px;
      left: 50%;
      transform: translateX(-50%) translateY(0px) scale(0.8);
      width: 20px;
      height: 20px;
      border: 2px solid rgba(156, 163, 175, 0.3);
      border-top-color: rgba(156, 163, 175, 0.8);
      border-radius: 50%;
      z-index: 1000;
      transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s ease-out, border-color 0.2s ease;
      opacity: 0;
      pointer-events: none;
      animation: none;
    `;
    indicator.innerHTML = '';
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

    // Get the main content body (everything BELOW navbar that should move)
    if (!bodyElement) {
      // Target the page-content div (contains Routes, but not Navbar)
      bodyElement = document.getElementById('page-content');
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

      // Update indicator - starts at navbar bottom (0px), slides down as you pull
      const progressForPosition = Math.min(pullDistance / MAX_PULL, 1);
      // Map to 0px (at navbar bottom, hidden by opacity) to +30px (visible below navbar)
      const indicatorY = progressForPosition * 30;
      const scale = 0.8 + (Math.min(pullDistance / PULL_THRESHOLD, 1) * 0.2); // Grows from 0.8 to 1.0
      const rotation = pullDistance * 2; // Rotation as you pull

      pullIndicator.style.transform = `translateX(-50%) translateY(${indicatorY}px) scale(${scale}) rotate(${rotation}deg)`;
      pullIndicator.style.opacity = Math.min(progressForPosition * 1.5, 1);

      // Slightly darken border when threshold reached
      if (pullDistance >= PULL_THRESHOLD) {
        pullIndicator.style.borderTopColor = 'rgba(107, 114, 128, 1)';
      } else {
        pullIndicator.style.borderTopColor = 'rgba(156, 163, 175, 0.8)';
      }
    }
  }

  function handleTouchEnd() {
    if (!isPulling) return;

    const pullDistance = currentY - startY;

    if (pullDistance >= PULL_THRESHOLD) {
      // Trigger refresh - position spinner at final position (20px below navbar) and spin
      pullIndicator.style.transition = 'transform 0.3s ease';
      pullIndicator.style.transform = 'translateX(-50%) translateY(20px) scale(1)';
      pullIndicator.style.animation = 'spin 0.8s linear infinite';

      // Keep body pushed down slightly to show spinner with space
      if (bodyElement) {
        bodyElement.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        bodyElement.style.transform = 'translateY(50px)'; // 50px gap between spinner and body
      }

      // Reload after brief delay
      setTimeout(() => {
        window.location.reload();
      }, 400);
    } else {
      // Elastic bounce-back animation
      pullIndicator.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease';
      pullIndicator.style.transform = 'translateX(-50%) translateY(0px) scale(0.8) rotate(0deg)';
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
