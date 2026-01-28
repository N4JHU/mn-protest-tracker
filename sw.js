const CACHE_NAME = 'metro-surge-v3';
const URLS_TO_CACHE = [
    './',
    './index.html',
    './manifest.json',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2'
];

// 1. INSTALL: Cache Core Files immediately
self.addEventListener('install', event => {
    self.skipWaiting(); // FORCE ACTIVATION (Don't wait for tabs to close)
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Opened cache');
                return cache.addAll(URLS_TO_CACHE);
            })
    );
});

// 2. ACTIVATE: Delete old caches instantly
self.addEventListener('activate', event => {
    event.waitUntil(clients.claim()); // Take control of all pages immediately
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

// 3. FETCH: The "Network First" Strategy
self.addEventListener('fetch', event => {
    // If it's the main page (HTML), try Network first, then Cache
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .then(response => {
                    return caches.open(CACHE_NAME).then(cache => {
                        cache.put(event.request, response.clone()); // Update cache with new version
                        return response;
                    });
                })
                .catch(() => {
                    // If offline, return cached version
                    return caches.match(event.request);
                })
        );
    } else {
        // For images/scripts, keep using Cache First (for speed)
        event.respondWith(
            caches.match(event.request)
                .then(response => response || fetch(event.request))
        );
    }
});
