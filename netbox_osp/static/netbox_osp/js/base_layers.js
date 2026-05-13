/* OSP map base-layer manager.

   Exposes window.OspBaseLayers.attach(map, dropdownEl, offlineTileUrl)
   which:
     - Adds a tile layer chosen from the user's persisted preference
       (localStorage 'osp.baseLayer'), defaulting to CartoDB Positron.
     - Populates a Bootstrap dropdown grouped by tile-type so the user
       can switch on the fly. mdi icons per provider.
     - Watches the active layer's tileerror events. If 3 failures land
       within a 5s window on an *online* layer, it switches to the
       bundled offline MBTiles automatically and shows a Bootstrap toast
       with a "Retry online" button.
     - Remembers the failure for 5 minutes in localStorage so reloads
       go straight to offline instead of flashing 3 broken tiles each
       time.

   Designed to be loaded BEFORE network_map.js / route_editor.js — both
   call OspBaseLayers.attach() instead of L.tileLayer().addTo(map).
*/
(function () {
    'use strict';

    const LS_PREF        = 'osp.baseLayer';
    const LS_LAST_FAIL   = 'osp.baseLayer.lastFail';
    const FAIL_WINDOW_MS = 5000;
    const FAIL_THRESHOLD = 3;
    const FAIL_COOLDOWN  = 5 * 60 * 1000;   // skip online probe for 5 min after a failure
    const DEFAULT_KEY    = 'cartodb-positron';
    const OFFLINE_KEY    = 'offline';
    const GROUP_ORDER    = ['Street', 'Topographic', 'Satellite', 'Offline'];

    // Tile-provider catalog. All URLs are free public endpoints. No API
    // keys. attribution complies with each provider's terms.
    //
    // Inspired by cesnet_service_path_plugin's map_layers_config.html
    // (Apache-2.0). We add one entry — offline — that points
    // at the netbox-osp MBTiles tile proxy, making the plugin usable on
    // air-gapped OT networks.
    function buildLayers(offlineTileUrl) {
        return {
            'osm': {
                name: 'OpenStreetMap', group: 'Street', icon: 'mdi-map',
                url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                options: {
                    attribution: '&copy; OpenStreetMap contributors',
                    maxZoom: 19, minZoom: 0,
                    referrerPolicy: 'strict-origin-when-cross-origin',
                },
                online: true,
            },
            'osm-hot': {
                name: 'Humanitarian OSM', group: 'Street', icon: 'mdi-map-marker',
                url: 'https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png',
                options: {
                    attribution: '&copy; OpenStreetMap contributors · Tiles courtesy of Humanitarian OSM Team',
                    maxZoom: 19, minZoom: 0,
                    referrerPolicy: 'strict-origin-when-cross-origin',
                },
                online: true,
            },
            'cartodb-positron': {
                name: 'CartoDB Positron', group: 'Street', icon: 'mdi-map-outline',
                url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
                options: {
                    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
                    subdomains: 'abcd',
                    maxZoom: 19, minZoom: 0,
                    referrerPolicy: 'strict-origin-when-cross-origin',
                },
                online: true,
            },
            'cartodb-dark': {
                name: 'CartoDB Dark Matter', group: 'Street', icon: 'mdi-weather-night',
                url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
                options: {
                    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
                    subdomains: 'abcd',
                    maxZoom: 19, minZoom: 0,
                    referrerPolicy: 'strict-origin-when-cross-origin',
                },
                online: true,
            },
            'opentopomap': {
                name: 'OpenTopoMap', group: 'Topographic', icon: 'mdi-terrain',
                url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
                options: {
                    attribution: 'Map data &copy; OpenStreetMap contributors, SRTM · Style &copy; OpenTopoMap (CC-BY-SA)',
                    maxZoom: 17, minZoom: 0,
                    referrerPolicy: 'strict-origin-when-cross-origin',
                },
                online: true,
            },
            'cyclosm': {
                name: 'CyclOSM', group: 'Topographic', icon: 'mdi-bike',
                url: 'https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png',
                options: {
                    attribution: '&copy; OpenStreetMap contributors · Tiles courtesy of CyclOSM',
                    maxZoom: 20, minZoom: 0,
                    referrerPolicy: 'strict-origin-when-cross-origin',
                },
                online: true,
            },
            'esri-satellite': {
                name: 'Esri World Imagery', group: 'Satellite', icon: 'mdi-satellite-variant',
                url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                options: {
                    attribution: 'Tiles &copy; Esri · Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, GIS User Community',
                    maxZoom: 18, minZoom: 0,
                    referrerPolicy: 'strict-origin-when-cross-origin',
                },
                online: true,
            },
            'offline': {
                name: 'Offline (MBTiles)', group: 'Offline', icon: 'mdi-wifi-off',
                url: offlineTileUrl,
                options: {
                    attribution: 'OSP map · tiles via MBTiles',
                    maxNativeZoom: 16, maxZoom: 18, minZoom: 0,
                },
                online: false,
            },
        };
    }

    class LayerManager {
        constructor(map, offlineTileUrl) {
            this.map = map;
            this.layers = buildLayers(offlineTileUrl);
            this.currentKey = null;
            this.currentLayer = null;
            this.failures = [];             // timestamps within rolling window
            this.preferredOnlineKey = this._readPreferredOnline();
            this.dropdownEl = null;
        }

        _readPreferredOnline() {
            const saved = localStorage.getItem(LS_PREF);
            if (saved && this.layers[saved] && this.layers[saved].online) return saved;
            return DEFAULT_KEY;
        }

        _inFailCooldown() {
            const ts = localStorage.getItem(LS_LAST_FAIL);
            if (!ts) return false;
            const elapsed = Date.now() - parseInt(ts, 10);
            if (elapsed < FAIL_COOLDOWN) return true;
            localStorage.removeItem(LS_LAST_FAIL);
            return false;
        }

        attach(dropdownEl) {
            this.dropdownEl = dropdownEl;
            this._renderDropdown();
            const initialKey = this._inFailCooldown() ? OFFLINE_KEY : this.preferredOnlineKey;
            this.switchTo(initialKey, { persist: false });
        }

        switchTo(key, opts) {
            opts = opts || {};
            const def = this.layers[key];
            if (!def) return;
            if (this.currentLayer) {
                this.map.removeLayer(this.currentLayer);
                this.currentLayer = null;
            }
            const layer = L.tileLayer(def.url, def.options).addTo(this.map);
            layer.on('tileerror', () => this._onTileError());
            layer.on('tileload', () => this._onTileLoad());
            this.currentLayer = layer;
            this.currentKey = key;
            this.failures = [];
            if (opts.persist && def.online) {
                localStorage.setItem(LS_PREF, key);
                this.preferredOnlineKey = key;
            }
            // Manual selection (persist=true) clears the cooldown timer
            // since the user is explicitly asking for this layer now.
            if (opts.persist) {
                localStorage.removeItem(LS_LAST_FAIL);
            }
            this._updateDropdownLabel();
        }

        _onTileError() {
            const def = this.layers[this.currentKey];
            if (!def || !def.online) return;          // offline already; nothing to do
            const now = Date.now();
            this.failures = this.failures.filter(t => now - t < FAIL_WINDOW_MS);
            this.failures.push(now);
            if (this.failures.length >= FAIL_THRESHOLD) {
                console.warn('[OSP] base-layer offline — falling back to bundled tiles');
                localStorage.setItem(LS_LAST_FAIL, String(now));
                this.switchTo(OFFLINE_KEY, { persist: false });
                this._showOfflineToast();
            }
        }

        _onTileLoad() {
            // First successful load resets the failure window — the
            // network is fine, those early errors were transient.
            if (this.failures.length) this.failures = [];
        }

        retryOnline() {
            localStorage.removeItem(LS_LAST_FAIL);
            this.switchTo(this.preferredOnlineKey || DEFAULT_KEY, { persist: false });
        }

        _renderDropdown() {
            if (!this.dropdownEl) return;
            const menu = this.dropdownEl.querySelector('.dropdown-menu');
            if (!menu) return;
            menu.innerHTML = '';

            const groups = {};
            Object.entries(this.layers).forEach(([key, def]) => {
                (groups[def.group] = groups[def.group] || []).push([key, def]);
            });

            let first = true;
            GROUP_ORDER.forEach((g) => {
                const entries = groups[g];
                if (!entries) return;
                if (!first) {
                    const sep = document.createElement('li');
                    sep.innerHTML = '<hr class="dropdown-divider">';
                    menu.appendChild(sep);
                }
                first = false;
                const header = document.createElement('li');
                header.innerHTML = '<h6 class="dropdown-header">' + g + '</h6>';
                menu.appendChild(header);
                entries.forEach(([key, def]) => {
                    const li = document.createElement('li');
                    const a = document.createElement('a');
                    a.className = 'dropdown-item';
                    a.href = '#';
                    a.dataset.layer = key;
                    a.innerHTML = '<i class="mdi ' + def.icon + ' me-2"></i>' + def.name;
                    a.addEventListener('click', (e) => {
                        e.preventDefault();
                        this.switchTo(key, { persist: true });
                    });
                    li.appendChild(a);
                    menu.appendChild(li);
                });
            });
        }

        _updateDropdownLabel() {
            if (!this.dropdownEl) return;
            const def = this.layers[this.currentKey];
            if (!def) return;
            const labelEl = this.dropdownEl.querySelector('.osp-current-layer-name');
            const iconEl = this.dropdownEl.querySelector('.osp-current-layer-icon');
            if (labelEl) labelEl.textContent = def.name;
            if (iconEl) iconEl.className = 'mdi ' + def.icon + ' osp-current-layer-icon';
            // Highlight active item in the menu.
            this.dropdownEl.querySelectorAll('.dropdown-item').forEach(el => {
                el.classList.toggle('active', el.dataset.layer === this.currentKey);
            });
        }

        _showOfflineToast() {
            const toastEl = document.getElementById('osp-offline-toast');
            if (!toastEl) return;
            const retryBtn = toastEl.querySelector('.osp-offline-retry');
            if (retryBtn && !retryBtn.dataset.wired) {
                retryBtn.dataset.wired = '1';
                retryBtn.addEventListener('click', () => {
                    this.retryOnline();
                    if (window.bootstrap && bootstrap.Toast) {
                        bootstrap.Toast.getInstance(toastEl)?.hide();
                    }
                });
            }
            if (window.bootstrap && bootstrap.Toast) {
                bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 8000 }).show();
            }
        }
    }

    window.OspBaseLayers = {
        LayerManager: LayerManager,
        attach: function (map, dropdownEl, offlineTileUrl) {
            const mgr = new LayerManager(map, offlineTileUrl);
            mgr.attach(dropdownEl);
            return mgr;
        },
    };
})();
