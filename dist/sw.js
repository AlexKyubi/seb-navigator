const CACHE = "seb-navigator-v32";
const ASSETS = ["./", "./auth", "./overview", "./sales", "./assets/shared.css", "./assets/core.js", "./assets/commission.js", "./assets/auth.js", "./assets/catalog.js", "./assets/overview.js", "./assets/sales.js", "./assets/xlsx.full.min.js", "./assets/jszip.min.js", "./data/catalog.json", "./data/commission-template.xlsx", "./manifest.webmanifest", "./icons/icon-180.png", "./icons/icon-192.png", "./icons/icon-512.png"];
const PROTECTED = ["/data/catalog.json", "/data/commission-template.xlsx"];
function hasLocalAccess(){return new Promise((resolve)=>{const request=indexedDB.open("seb-navigator-local",1);request.onerror=()=>resolve(false);request.onupgradeneeded=()=>resolve(false);request.onsuccess=()=>{const db=request.result;if(!db.objectStoreNames.contains("settings")){db.close();resolve(false);return}const tx=db.transaction("settings","readonly"),profile=tx.objectStore("settings").get("authorized-profile");profile.onsuccess=()=>{const value=profile.result;db.close();resolve(Boolean(value?.firstName&&value?.lastName))};profile.onerror=()=>{db.close();resolve(false)}}})}
self.addEventListener("install", (event) => event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())));
self.addEventListener("activate", (event) => event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))).then(() => self.clients.claim())));
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (event.request.mode === "navigate" && /\/[^/]+\.html$/.test(url.pathname)) {
    const canonical = new URL(url.href);
    canonical.pathname = canonical.pathname.replace(/(?:\/index)?\.html$/, "") || "/";
    event.respondWith(Response.redirect(canonical.href, 302));
    return;
  }
  if (url.origin === self.location.origin && PROTECTED.some((path) => url.pathname.endsWith(path))) {
    event.respondWith(hasLocalAccess().then((allowed) => allowed ? caches.match(event.request).then((cached) => cached || fetch(event.request).then((response) => {if(response.ok)caches.open(CACHE).then((cache)=>cache.put(event.request,response.clone()));return response})) : new Response("Authorization required",{status:403,headers:{"Content-Type":"text/plain;charset=utf-8","Cache-Control":"no-store"}})));
    return;
  }
  const appShell = event.request.mode === "navigate" || (url.origin === self.location.origin && /\.(?:html|js|css)$/.test(url.pathname));
  if (appShell) {
    event.respondWith(caches.match(event.request).then((cached) => {
      const refresh = fetch(event.request).then((response) => {
        if (response.ok) caches.open(CACHE).then((cache) => cache.put(event.request, response.clone()));
        return response;
      }).catch(() => cached);
      return cached || refresh;
    }));
    return;
  }
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request).then((response) => {
    if (response.ok) caches.open(CACHE).then((cache) => cache.put(event.request, response.clone()));
    return response;
  })));
});
