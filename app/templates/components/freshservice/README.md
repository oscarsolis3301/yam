# FreshService Component - Modular Structure

This directory contains a fully modularized FreshService component with separated concerns for better maintainability and reusability.

## Structure Overview

```
freshservice/
├── modules/                          # Modular components
│   ├── styles-main.html             # Main styles entry point
│   ├── scripts-main.html            # Main scripts entry point
│   ├── main-content.html            # Main content wrapper
│   ├── base-styles.html             # Base styles and utilities
│   ├── header-styles.html           # Header-specific styles
│   ├── sidebar-styles.html          # Sidebar and filter styles
│   ├── table-styles.html            # Table and controls styles
│   ├── modal-styles.html            # Modal-specific styles
│   ├── core.js                      # Core application logic
│   ├── data-service.js              # API and data management
│   └── ui-renderer.js               # DOM manipulation and rendering
├── header.html                      # Header component
├── filters_sidebar.html             # Filters sidebar component
├── controls.html                    # Controls bar component
├── tickets_table.html               # Tickets table component
├── ticket_modal.html                # Ticket detail modal
├── styles.html                      # Legacy monolithic styles (deprecated)
├── scripts.html                     # Legacy monolithic scripts (deprecated)
├── freshservice-modular.html        # New modular entry point
└── README.md                        # This documentation
```

## Module Descriptions

### Style Modules

#### `base-styles.html`
- Global styles and container styling
- Utility classes (text colors, backgrounds)
- Loading and state indicators
- Base layout and viewport management

#### `header-styles.html`
- Header component styling
- Search input styling
- User profile and actions styling
- Responsive header behavior

#### `sidebar-styles.html`
- Filters sidebar styling
- Form controls styling
- Requester suggestions styling
- Filter input containers and interactions

#### `table-styles.html`
- Main content area styling
- Controls bar styling
- Table styling and interactions
- Status and priority badges
- Pagination controls
- Button styling

#### `modal-styles.html`
- Modal dialog styling
- Ticket detail content styling
- Comments and metadata styling
- Responsive modal behavior

### JavaScript Modules

#### `core.js`
- Global state management
- Application initialization
- Event listener setup
- Filter handling logic
- Search functionality

#### `data-service.js`
- API calls and data fetching
- Database monitoring
- Loading state management
- Error handling
- Utility functions (date formatting, initials)

#### `ui-renderer.js`
- DOM manipulation and rendering
- Table row creation
- Modal content rendering
- Ticket selection handling
- UI state management

### Entry Points

#### `styles-main.html`
Main entry point for all styles. Includes all style modules in the correct order.

#### `scripts-main.html`
Main entry point for all JavaScript. Includes all script modules in dependency order.

#### `main-content.html`
Wrapper for the main content area, combining controls and table components.

#### `freshservice-modular.html`
Complete modular component that includes all modules and components.

## Usage

### Using the Modular Component

To use the new modular structure, include the main entry point:

```html
{% include 'components/freshservice/freshservice-modular.html' %}
```

### Using Individual Modules

You can also include individual modules as needed:

```html
<!-- Include only styles -->
{% include 'components/freshservice/modules/styles-main.html' %}

<!-- Include only scripts -->
{% include 'components/freshservice/modules/scripts-main.html' %}

<!-- Include specific style module -->
{% include 'components/freshservice/modules/table-styles.html' %}
```

## Benefits of Modular Structure

1. **Maintainability**: Each module has a single responsibility
2. **Reusability**: Individual modules can be reused in other components
3. **Debugging**: Easier to locate and fix issues in specific modules
4. **Performance**: Can load only required modules
5. **Team Development**: Multiple developers can work on different modules
6. **Testing**: Individual modules can be tested in isolation

## Migration from Legacy Structure

The legacy monolithic files (`styles.html` and `scripts.html`) are still available for backward compatibility but are deprecated. The new modular structure provides the same functionality with better organization.

## Dependencies

- Bootstrap 5 (for modal functionality)
- Bootstrap Icons (for icons)
- Inter font family (for typography)

## Browser Support

- Modern browsers with ES6+ support
- CSS Grid and Flexbox support required
- Backdrop-filter support for blur effects (optional enhancement) 