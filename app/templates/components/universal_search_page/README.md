# Universal Search Page Components

This directory contains the modular components for the Universal Search page, providing a comprehensive search experience across all content types in the system.

## Components Overview

### Core Components
- **main.html** - Main page structure and layout
- **header.html** - Search page header with title and stats
- **filters_bar.html** - Filter controls and active filter display
- **search_results.html** - Search results container
- **pagination.html** - Pagination controls
- **loading_state.html** - Loading spinner and text
- **no_results.html** - No results found state with suggestions

### Modal Components
- **pdf_modal.html** - PDF document viewer modal
- **note_modal.html** - Note viewing and editing modal
- **filter_modal.html** - Advanced filtering modal

### Styling Components
- **styles.html** - Main page styles and responsive design
- **modal_styles.html** - Modal-specific styles and animations

### JavaScript Components
- **script.html** - Main search functionality and note modal handling
- **modal_functions.html** - PDF modal functions
- **suggestions.html** - Search suggestions and "did you mean" functionality

## Note Modal Functionality

The note modal provides a comprehensive note viewing and editing experience:

### Features
- **Owner Detection**: Automatically detects if the current user owns the note
- **Permission-Based Access**: 
  - Owners can view and edit their notes
  - Non-owners can only view public notes
  - Private notes show access denied for non-owners
- **Rich Text Editing**: Full Quill.js editor integration for note owners
- **Content Formatting**: Proper display of Quill.js Delta format content
- **Error Handling**: Graceful error handling with user-friendly messages

### Modal States
1. **View-Only Mode**: For public notes from other users
2. **Editable Mode**: For notes owned by the current user
3. **Access Denied**: For private notes from other users
4. **Error Mode**: When note loading fails

### API Integration
- Fetches note data from `/notes/api/notes/{id}` for owners
- Fetches from `/notes/api/notes/public/{id}` for public notes
- Updates notes via PUT to `/notes/api/notes/{id}`

### Content Processing
- Handles Quill.js Delta format content
- Converts rich text formatting to HTML
- Supports tags, metadata, and privacy settings
- Fallback handling for plain text content

## Usage

The note modal is automatically triggered when clicking on note search results. The system:

1. Extracts the note ID from the search result
2. Attempts to fetch the note as the owner
3. Falls back to public endpoint if access denied
4. Displays appropriate modal based on permissions
5. Provides editing capabilities for owners

## Styling

All modal styles are defined in `modal_styles.html` with:
- Dark theme consistent with the application
- Responsive design for mobile devices
- Smooth animations and transitions
- Quill.js editor dark theme overrides

## Browser Compatibility

- Modern browsers with ES6+ support
- Quill.js editor for rich text editing
- Responsive design for mobile and desktop 