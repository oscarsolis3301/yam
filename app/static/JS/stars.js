// Optimized starfield animation with no downtime
(function() {
  'use strict';
  
  const canvas = document.getElementById('starfield');
  if (!canvas) {
    console.warn('Starfield canvas not found');
    return;
  }
  
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    console.warn('Canvas 2D context not available');
    return;
  }

  let stars = [];
  const numStars = 180;
  let width, height, dpr, centerX, centerY;
  let animationId = null;
  let isRunning = false;
  let isFormSubmitting = false;

  function resizeStarfield() {
    try {
      dpr = window.devicePixelRatio || 1;
      width = window.innerWidth;
      height = window.innerHeight;

      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = '100vw';
      canvas.style.height = '100vh';

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);

      centerX = width / 2;
      centerY = height / 2;
    } catch (error) {
      console.warn('Error resizing starfield:', error);
    }
  }

  function createStar() {
    return {
      x: Math.random() * width - width / 2,
      y: Math.random() * height - height / 2,
      z: Math.random() * width,
      o: 0.2 + Math.random() * 0.8
    };
  }

  function initStars() {
    try {
      stars = [];
      for (let i = 0; i < numStars; i++) {
        stars.push(createStar());
      }
    } catch (error) {
      console.warn('Error initializing stars:', error);
    }
  }

  function updateAndDrawStars(deltaTime) {
    try {
      const speed = 120 * (deltaTime / 1000); // px/sec
      ctx.clearRect(0, 0, width, height);

      for (let i = 0; i < stars.length; i++) {
        let star = stars[i];
        star.z -= speed;

        if (star.z <= 1) {
          stars[i] = createStar();
          continue;
        }

        const k = 128.0 / star.z;
        const sx = star.x * k + centerX;
        const sy = star.y * k + centerY;

        if (sx < 0 || sx >= width || sy < 0 || sy >= height) {
          stars[i] = createStar();
          continue;
        }

        const size = (1 - star.z / width) * 2.2;
        ctx.beginPath();
        ctx.arc(sx, sy, size, 0, 2 * Math.PI);
        ctx.fillStyle = `rgba(255, 255, 255, ${star.o})`;
        ctx.fill();
      }
    } catch (error) {
      console.warn('Error updating stars:', error);
      // Restart animation if there's an error
      stopAnimation();
      startAnimation();
    }
  }

  let lastTime = performance.now();

  function animate(now) {
    if (!isRunning) return;
    
    try {
      const deltaTime = now - lastTime;
      lastTime = now;
      updateAndDrawStars(deltaTime);
      animationId = requestAnimationFrame(animate);
    } catch (error) {
      console.warn('Animation error:', error);
      stopAnimation();
      startAnimation();
    }
  }

  function startAnimation() {
    if (isRunning) return;
    isRunning = true;
    lastTime = performance.now();
    animationId = requestAnimationFrame(animate);
  }

  function stopAnimation() {
    isRunning = false;
    if (animationId) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }
  }

  // Handle page visibility changes to save resources
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopAnimation();
    } else {
      // Small delay to ensure page is fully visible before restarting
      setTimeout(() => {
        if (!document.hidden) {
          startAnimation();
        }
      }, 100);
    }
  });

  // Handle window resize with debouncing
  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      try {
        resizeStarfield();
        initStars();
      } catch (error) {
        console.warn('Error handling resize:', error);
      }
    }, 100);
  });

  // Enhanced form submission handling to ensure animation continues
  document.addEventListener('submit', (e) => {
    // Mark that form is submitting but don't stop animation
    isFormSubmitting = true;
    
    // Ensure animation continues during form submission
    if (!isRunning) {
      startAnimation();
    }
    
    // Add a small delay to ensure animation continues even if page starts to unload
    setTimeout(() => {
      isFormSubmitting = false;
    }, 1000);
  });

  // Handle button clicks that might trigger form submission
  document.addEventListener('click', (e) => {
    if (e.target.type === 'submit' || e.target.classList.contains('btn-login')) {
      // Ensure animation continues when login button is clicked
      if (!isRunning) {
        startAnimation();
      }
    }
  });

  // Prevent any interference with the animation during page transitions
  window.addEventListener('beforeunload', () => {
    // Only stop animation if we're actually leaving the page
    // Don't stop for form submissions that stay on the same page
    if (!isFormSubmitting) {
      stopAnimation();
    }
  });

  // Initialize starfield
  try {
    resizeStarfield();
    initStars();
    startAnimation();
    
    // Ensure animation is always running
    setInterval(() => {
      if (!isRunning && !document.hidden) {
        console.log('Restarting starfield animation');
        startAnimation();
      }
    }, 5000); // Check every 5 seconds
    
  } catch (error) {
    console.warn('Error initializing starfield:', error);
  }

  // Cleanup on page unload
  window.addEventListener('unload', () => {
    stopAnimation();
  });
})();
