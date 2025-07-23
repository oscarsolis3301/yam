# YAM Monotone Mode

## Overview

The YAM dashboard now includes a **Monotone Mode** that reduces visual distractions by showing colors and animations only when needed. This creates a cleaner, more focused user experience while maintaining the interactive and engaging aspects of the dashboard.

## Features

### 🎨 **Smart Color Management**
- **Default State**: Clean, monotone appearance with white text and subtle borders
- **Interactive States**: Colors appear only on hover, focus, or specific states
- **Status Indicators**: Colors are shown for errors, warnings, success, and loading states

### 🎭 **Conditional Animations**
- **Static by Default**: No constant animations or shimmer effects
- **Interactive Animations**: Animations trigger only on user interaction
- **Accessibility**: Respects `prefers-reduced-motion` user preference

### 🔧 **Easy Toggle**
- **Toggle Button**: Fixed position button in the top-right corner
- **Visual Feedback**: Button changes appearance to indicate current mode
- **Keyboard Accessible**: Can be activated with Tab + Enter/Space

## How It Works

### Default Monotone State
- All cards have a clean, dark background
- Text is white for maximum readability
- Icons are white by default
- No shimmer animations
- Subtle borders and shadows

### Interactive States (Colors Appear)
- **Hover**: Cards show shimmer effect and colored icons
- **Focus**: Keyboard navigation highlights elements
- **Click**: Brief color flash on button clicks
- **Error**: Red shimmer for error states
- **Success**: Green shimmer for success states
- **Warning**: Yellow shimmer for warning states
- **Loading**: Blue shimmer for loading states

## Usage

### Toggle Between Modes
1. Look for the palette icon button in the top-right corner
2. Click to switch between Monotone and Colorful modes
3. The button shows the current mode and changes appearance accordingly

### Programmatic Control
```javascript
// Toggle monotone mode
window.yamMonotone.toggleMonotone();

// Check current state
const isMonotone = window.yamMonotone.config.enableMonotone;

// Update configuration
window.yamMonotone.updateConfig({
    showColorsOnHover: true,
    showColorsOnFocus: true,
    showColorsOnError: true
});

// Show specific states
const card = document.querySelector('.yam-card-enhanced');
window.yamMonotone.showError(card);    // Red shimmer
window.yamMonotone.showSuccess(card);  // Green shimmer
window.yamMonotone.showWarning(card);  // Yellow shimmer
window.yamMonotone.showLoading(card);  // Blue shimmer
window.yamMonotone.clearStates(card);  // Remove all states
```

## Configuration Options

```javascript
window.yamMonotone.config = {
    enableMonotone: true,        // Enable/disable monotone mode
    showColorsOnHover: true,     // Show colors on hover
    showColorsOnFocus: true,     // Show colors on focus
    showColorsOnError: true,     // Show colors for errors
    showColorsOnSuccess: true,   // Show colors for success
    showColorsOnWarning: true,   // Show colors for warnings
    showColorsOnLoading: true,   // Show colors for loading
    respectReducedMotion: true   // Respect user's motion preferences
};
```

## Accessibility Features

### Reduced Motion Support
- Automatically detects `prefers-reduced-motion: reduce`
- Disables all animations when user prefers reduced motion
- Respects changes in user preference

### Keyboard Navigation
- Full keyboard accessibility
- Focus indicators with colors
- Tab navigation support

### High Contrast Support
- Enhanced borders for high contrast mode
- Maintains readability in all conditions

## Performance Benefits

### GPU Optimization
- Reduces GPU usage by disabling animations when not needed
- Uses `will-change` property only during interactions
- Intersection Observer for visible elements only

### Battery Life
- Fewer animations mean less battery drain
- Reduced CPU usage for mobile devices
- Optimized for performance on all devices

## Browser Support

- **Modern Browsers**: Full support for all features
- **Older Browsers**: Graceful degradation to basic functionality
- **Mobile**: Optimized for touch interactions
- **Print**: Clean, black and white output for printing

## Customization

### Adding Custom States
```javascript
// Add custom state with specific colors
const customCard = document.querySelector('.my-custom-card');
customCard.classList.add('custom-state');

// CSS for custom state
.yam-card-enhanced.custom-state::before {
    background: linear-gradient(90deg, #your-color, #your-color-2) !important;
    animation: shimmer 2s ease-in-out infinite !important;
}
```

### Styling Overrides
```css
/* Override monotone styles for specific elements */
.my-special-element {
    color: #your-color !important;
    background: #your-background !important;
}

/* Force colors even in monotone mode */
.yam-monotone-mode .my-special-element {
    color: #your-color !important;
}
```

## Troubleshooting

### Colors Not Appearing
1. Check if monotone mode is enabled
2. Verify the element has proper hover/focus states
3. Ensure JavaScript is loaded and initialized

### Animations Not Working
1. Check browser support for CSS animations
2. Verify `prefers-reduced-motion` is not set to `reduce`
3. Ensure elements are visible in viewport

### Toggle Button Not Visible
1. Check if the toggle component is included in your template
2. Verify z-index and positioning
3. Ensure no other elements are covering it

## Best Practices

### When to Use Monotone Mode
- **Focus Work**: When users need to concentrate on content
- **Low Light**: In dimly lit environments
- **Accessibility**: For users sensitive to motion or colors
- **Performance**: On slower devices or limited bandwidth

### When to Use Colorful Mode
- **Presentations**: When showcasing features
- **Engagement**: To make the interface more lively
- **Branding**: When brand colors are important
- **User Preference**: When users prefer colorful interfaces

## Future Enhancements

- **Theme Persistence**: Remember user's preference across sessions
- **Custom Color Schemes**: Allow users to choose their own colors
- **Animation Intensity**: Adjustable animation levels
- **Time-based Switching**: Automatic switching based on time of day
- **Integration with System Theme**: Sync with OS dark/light mode

---

*The YAM Monotone Mode is designed to provide a clean, distraction-free experience while maintaining the interactive and engaging nature of the dashboard. It respects user preferences and accessibility needs while offering performance benefits.* 