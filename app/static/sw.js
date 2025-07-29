// YAM Dashboard Service Worker
// Version: 1.0.1
// Purpose: Provide offline support and performance optimization

const CACHE_NAME = 'yam-dashboard-v1.0.1';
const STATIC_CACHE_NAME = 'yam-static-v1.0.1';
const DYNAMIC_CACHE_NAME = 'yam-dynamic-v1.0.1';

// Files to cache immediately
const STATIC_FILES = [
    '/',
    '/static/CSS/yam-enhanced.css',
    '/static/CSS/styles.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.5/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap'
];

// Install event - cache static files
self.addEventListener('install', event => {
    console.log('YAM Service Worker: Installing...');
    
    event.waitUntil(
        caches.open(STATIC_CACHE_NAME)
            .then(cache => {
                console.log('YAM Service Worker: Caching static files');
                return cache.addAll(STATIC_FILES);
            })
            .then(() => {
                console.log('YAM Service Worker: Static files cached successfully');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('YAM Service Worker: Failed to cache static files:', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('YAM Service Worker: Activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== STATIC_CACHE_NAME && cacheName !== DYNAMIC_CACHE_NAME) {
                            console.log('YAM Service Worker: Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
            .then(() => {
                console.log('YAM Service Worker: Activated successfully');
                return self.clients.claim();
            })
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        return;
    }
    
    // Skip chrome-extension and other non-http requests
    if (!url.protocol.startsWith('http')) {
        return;
    }
    
    // Handle different types of requests
    if (isStaticFile(request)) {
        // Static files - cache first strategy
        event.respondWith(handleStaticFile(request));
    } else if (isAPIRequest(request)) {
        // API requests - network first strategy
        event.respondWith(handleAPIRequest(request));
    } else {
        // Other requests - network first with cache fallback
        event.respondWith(handleOtherRequest(request));
    }
});

// Check if request is for a static file
function isStaticFile(request) {
    const url = new URL(request.url);
    return (
        url.pathname.startsWith('/static/') ||
        url.pathname.includes('.css') ||
        url.pathname.includes('.js') ||
        url.pathname.includes('.png') ||
        url.pathname.includes('.jpg') ||
        url.pathname.includes('.svg') ||
        url.pathname.includes('.ico') ||
        url.pathname.includes('.woff') ||
        url.pathname.includes('.woff2') ||
        url.hostname.includes('cdn.jsdelivr.net') ||
        url.hostname.includes('fonts.googleapis.com') ||
        url.hostname.includes('fonts.gstatic.com')
    );
}

// Check if request is for an API endpoint
function isAPIRequest(request) {
    const url = new URL(request.url);
    return (
        url.pathname.startsWith('/api/') ||
        url.pathname.startsWith('/auth/') ||
        url.pathname.includes('/socket.io/')
    );
}

// Handle static file requests
async function handleStaticFile(request) {
    try {
        // Try cache first
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // If not in cache, fetch from network
        const networkResponse = await fetch(request);
        
        // Cache the response for future use
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.error('YAM Service Worker: Error handling static file:', error);
        
        // Return a fallback response
        return new Response('Offline - Static file not available', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'text/plain' }
        });
    }
}

// Handle API requests
async function handleAPIRequest(request) {
    try {
        // Try network first
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.error('YAM Service Worker: Error handling API request:', error);
        
        // Try to serve from cache as fallback
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // Return offline response
        return new Response(JSON.stringify({
            error: 'Network error',
            message: 'You are offline. Please check your connection.',
            offline: true
        }), {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

// Handle other requests
async function handleOtherRequest(request) {
    try {
        // Try network first
        const networkResponse = await fetch(request);
        
        // Cache successful responses
        if (networkResponse.ok) {
            const cache = await caches.open(DYNAMIC_CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        
        return networkResponse;
    } catch (error) {
        console.error('YAM Service Worker: Error handling request:', error);
        
        // Try to serve from cache as fallback
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        
        // For HTML requests, return offline page
        if (request.headers.get('accept').includes('text/html')) {
            return caches.match('/offline.html');
        }
        
        // Return generic offline response
        return new Response('Offline - Please check your connection', {
            status: 503,
            statusText: 'Service Unavailable',
            headers: { 'Content-Type': 'text/plain' }
        });
    }
}

// Background sync for offline actions
self.addEventListener('sync', event => {
    console.log('YAM Service Worker: Background sync triggered:', event.tag);
    
    if (event.tag === 'background-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

// Handle background sync
async function doBackgroundSync() {
    try {
        // Get any pending requests from IndexedDB
        const pendingRequests = await getPendingRequests();
        
        for (const request of pendingRequests) {
            try {
                await fetch(request.url, request.options);
                await removePendingRequest(request.id);
            } catch (error) {
                console.error('YAM Service Worker: Background sync failed for request:', error);
            }
        }
    } catch (error) {
        console.error('YAM Service Worker: Background sync error:', error);
    }
}

// Push notification handling
self.addEventListener('push', event => {
    console.log('YAM Service Worker: Push notification received');
    
    const options = {
        body: event.data ? event.data.text() : 'YAM Dashboard Notification',
        icon: '/static/images/yam-icon.png',
        badge: '/static/images/yam-badge.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'explore',
                title: 'View Dashboard',
                icon: '/static/images/yam-icon.png'
            },
            {
                action: 'close',
                title: 'Close',
                icon: '/static/images/close-icon.png'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification('YAM Dashboard', options)
    );
});

// Notification click handling
self.addEventListener('notificationclick', event => {
    console.log('YAM Service Worker: Notification clicked');
    
    event.notification.close();
    
    if (event.action === 'explore') {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Helper functions for IndexedDB operations
async function getPendingRequests() {
    // Implementation would depend on your IndexedDB setup
    return [];
}

async function removePendingRequest(id) {
    // Implementation would depend on your IndexedDB setup
    return Promise.resolve();
}

// Message handling for communication with main thread
self.addEventListener('message', event => {
    console.log('YAM Service Worker: Message received:', event.data);
    
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data && event.data.type === 'GET_VERSION') {
        event.ports[0].postMessage({ version: CACHE_NAME });
    }
});

console.log('YAM Service Worker: Loaded successfully'); 