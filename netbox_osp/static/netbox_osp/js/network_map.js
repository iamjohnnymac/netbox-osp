/* Full-screen OSP network map. Pulls a FeatureCollection from the map_data
   endpoint and renders sites, cables (color-coded by status), and splice
   closures on a Leaflet map backed by an offline-capable tile proxy.        */
(function () {
    'use strict';

    function ready(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    const STATUS_COLORS = {
        active: '#28a745',
        planned: '#17a2b8',
        installed: '#6f42c1',
        ordered: '#0d6efd',
        decommissioning: '#ffc107',
        retired: '#6c757d',
        faulty: '#dc3545',
    };

    function cableColor(status) {
        return STATUS_COLORS[status] || '#fd7e14';
    }

    ready(function () {
        const mapEl = document.getElementById('osp-map');
        if (!mapEl) return;

        const centerLat = parseFloat(mapEl.dataset.centerLat) || 0.0;
        const centerLon = parseFloat(mapEl.dataset.centerLon) || 0.0;
        const zoom = parseInt(mapEl.dataset.zoom, 10) || 2;
        const dataUrl = mapEl.dataset.dataUrl;
        const tileUrl = mapEl.dataset.tileUrl.replace('/0/0/0.png', '/{z}/{x}/{y}.png');

        const map = L.map(mapEl, {
            preferCanvas: true,
            // Fractional zoom — 4 steps per integer level so +/- and the
            // scroll wheel move in smaller increments. Tiles between
            // integer zooms are scaled by Leaflet for smooth in-betweens.
            zoomSnap: 0.25,
            zoomDelta: 0.25,
            wheelPxPerZoomLevel: 120,  // softer scroll-wheel response
            // Plain click-drag always pans (hand cursor); never the
            // Shift-drag rectangle that selects a zoom region.
            boxZoom: false,
        });
        window.ospMap = map;  // debug handle for browser console
        map.setView([centerLat, centerLon], zoom);

        // F12 helper: click anywhere on the map to print [lat, lon] to console
        // for coordinate calibration when placing plant features.
        map.on('click', (e) => {
            const ll = e.latlng;
            console.log(`OSP map click: [${ll.lat.toFixed(5)}, ${ll.lng.toFixed(5)}]`);
        });

        // -------------- Trace mode --------------
        // Click around the plant boundary. Each click drops a draggable
        // numbered vertex into a running polygon (yellow dashed).
        //   - Drag any vertex to move it (polygon updates live)
        //   - Right-click any vertex to remove it
        //   - Click "Done tracing" to dump coords into a copy-paste textarea
        let traceMode = false;
        let tracePoints = [];     // array of [lat, lon]
        let traceMarkers = [];    // array of L.marker, parallel to tracePoints
        let traceLayer = null;    // the polygon/polyline being built
        const traceBtn = document.getElementById('osp-trace-toggle');

        function startTrace() {
            traceMode = true;
            tracePoints = [];
            clearTraceMarkers();
            if (traceLayer) { map.removeLayer(traceLayer); traceLayer = null; }
            traceBtn.classList.remove('btn-outline-danger');
            traceBtn.classList.add('btn-danger');
            traceBtn.innerHTML = '<i class="mdi mdi-check"></i> Done tracing';
            toast('TRACE: click to add · drag to move · right-click to delete · Done when finished.', 'ok');
            map.getContainer().style.cursor = 'crosshair';
        }

        function endTrace() {
            traceMode = false;
            traceBtn.classList.add('btn-outline-danger');
            traceBtn.classList.remove('btn-danger');
            traceBtn.innerHTML = '<i class="mdi mdi-vector-polyline"></i> Trace';
            map.getContainer().style.cursor = '';
            if (tracePoints.length < 3) {
                toast('Need at least 3 points for a polygon.', 'error');
                return;
            }
            const coords = tracePoints.map(p => [+p[0].toFixed(5), +p[1].toFixed(5)]);
            const jsText = 'const PLANT_BOUNDARY = ' + JSON.stringify(coords, null, 4) + ';';
            showTracePanel(jsText, coords);
        }

        function clearTraceMarkers() {
            traceMarkers.forEach(m => map.removeLayer(m));
            traceMarkers = [];
        }

        function makeTraceIcon(num) {
            return L.divIcon({
                className: 'osp-trace-vertex',
                html: '<div style="background:#ffd60a;color:#111;border-radius:50%;width:22px;height:22px;display:flex;align-items:center;justify-content:center;border:2px solid #b58900;font:bold 11px monospace;cursor:move;">' + num + '</div>',
                iconSize: [22, 22],
                iconAnchor: [11, 11],
            });
        }

        function refreshTraceLayer() {
            if (traceLayer) { map.removeLayer(traceLayer); traceLayer = null; }
            if (tracePoints.length < 1) return;
            const opts = { color: '#ffd60a', weight: 2, fill: tracePoints.length >= 3, fillOpacity: 0.15, dashArray: '6,4' };
            traceLayer = (tracePoints.length >= 3
                ? L.polygon(tracePoints, opts)
                : L.polyline(tracePoints, opts)
            ).addTo(map);
            // Re-number marker labels in case order changed.
            traceMarkers.forEach((m, i) => m.setIcon(makeTraceIcon(i + 1)));
        }

        function addTracePoint(latlng) {
            const idx = tracePoints.length;
            tracePoints.push([latlng.lat, latlng.lng]);
            const mk = L.marker(latlng, {
                icon: makeTraceIcon(idx + 1),
                draggable: true,
                autoPan: false,
                bubblingMouseEvents: false,   // map handlers shouldn't see marker events
            }).addTo(map);
            // Explicitly suspend map pan while a vertex is being dragged.
            // Without this Leaflet's map-drag handler can claim the mouse
            // movement and the marker only ticks one pixel before snapping.
            mk.on('dragstart', () => {
                map.dragging.disable();
                mapEl.style.cursor = 'grabbing';
            });
            mk.on('drag', () => {
                const i = traceMarkers.indexOf(mk);
                if (i < 0) return;
                const ll = mk.getLatLng();
                tracePoints[i] = [ll.lat, ll.lng];
                refreshTraceLayer();
            });
            mk.on('dragend', () => {
                map.dragging.enable();
                mapEl.style.cursor = traceMode ? 'crosshair' : '';
            });
            mk.on('contextmenu', (ev) => {
                L.DomEvent.stopPropagation(ev);
                const i = traceMarkers.indexOf(mk);
                if (i < 0) return;
                tracePoints.splice(i, 1);
                map.removeLayer(mk);
                traceMarkers.splice(i, 1);
                refreshTraceLayer();
                toast(`Removed vertex — ${tracePoints.length} left`, 'ok');
            });
            traceMarkers.push(mk);
            refreshTraceLayer();
            toast(`Trace: ${tracePoints.length} points (drag any · right-click to delete)`, 'ok');
        }

        function showTracePanel(text, coords) {
            // Lazy-build a floating panel inside the map card.
            let panel = document.getElementById('osp-trace-output');
            if (!panel) {
                panel = document.createElement('div');
                panel.id = 'osp-trace-output';
                Object.assign(panel.style, {
                    position: 'absolute', bottom: '12px', left: '12px', zIndex: 1000,
                    background: '#1f2937', color: '#e5e7eb', padding: '12px',
                    border: '1px solid #4b5563', borderRadius: '6px',
                    maxWidth: '480px', maxHeight: '40vh', overflow: 'auto',
                    fontFamily: 'monospace', fontSize: '11px',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.6)',
                });
                document.getElementById('osp-map').appendChild(panel);
            }
            panel.innerHTML = '';
            const header = document.createElement('div');
            header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;';
            header.innerHTML = '<strong>' + coords.length + ' boundary points</strong>';
            const closeBtn = document.createElement('button');
            closeBtn.textContent = '×';
            closeBtn.style.cssText = 'background:none;border:none;color:#e5e7eb;font-size:18px;cursor:pointer;line-height:1;';
            closeBtn.onclick = () => panel.remove();
            header.appendChild(closeBtn);
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.cssText = 'width:100%;height:200px;background:#111827;color:#e5e7eb;border:1px solid #374151;font-family:inherit;font-size:11px;padding:6px;';
            ta.readOnly = true;
            const copyBtn = document.createElement('button');
            copyBtn.className = 'btn btn-sm btn-primary';
            copyBtn.textContent = 'Copy to clipboard';
            copyBtn.style.marginTop = '6px';
            copyBtn.onclick = () => {
                ta.select();
                document.execCommand('copy');
                copyBtn.textContent = 'Copied!';
                setTimeout(() => { copyBtn.textContent = 'Copy to clipboard'; }, 1500);
            };
            panel.appendChild(header);
            panel.appendChild(ta);
            panel.appendChild(copyBtn);
            ta.focus();
            ta.select();
        }

        traceBtn.addEventListener('click', () => traceMode ? endTrace() : startTrace());

        // Suppress the browser's right-click menu over the map so that the
        // contextmenu event reaches our trace-vertex delete handler.
        mapEl.addEventListener('contextmenu', (e) => {
            if (traceMode) e.preventDefault();
        });

        // Hook map clicks for trace mode (does NOT consume the existing console.log).
        // Adding via the helper so vertices come pre-wired with drag + delete.
        map.on('click', (e) => {
            if (!traceMode) return;
            // Ignore if the click landed on a vertex marker (otherwise we'd
            // add a new point on top of the one being interacted with).
            if (e.originalEvent && e.originalEvent.target && e.originalEvent.target.closest('.osp-trace-vertex')) return;
            addTracePoint(e.latlng);
        });

        // Base-layer manager — handles seven online providers (OSM, CartoDB
        // light/dark, HOT OSM, OpenTopo, CyclOSM, Esri imagery) plus our
        // offline MBTiles proxy as 'offline'. Watches tileerror
        // events and auto-falls-back to offline when 3 failures land within
        // 5s on an online provider. User's explicit picks persist via
        // localStorage. See base_layers.js for the catalog + algorithm.
        const baseLayerDropdownEl = document.getElementById('osp-base-layer-dropdown');
        window.OspBaseLayers.attach(map, baseLayerDropdownEl, tileUrl);

        const cableLayer = L.layerGroup().addTo(map);
        const siteCluster = L.markerClusterGroup ? L.markerClusterGroup() : L.layerGroup();
        const closureCluster = L.markerClusterGroup ? L.markerClusterGroup() : L.layerGroup();
        map.addLayer(siteCluster);
        map.addLayer(closureCluster);

        // The Trace tool above lets operators draw and export their own
        // site/asset boundary. Persisting it (as a PlantBoundary model or
        // a PLUGINS_CONFIG entry) is a future v0.2 feature.

        L.control.layers(null, {
            'Sites': siteCluster,
            'OSP cables': cableLayer,
            'Splice closures': closureCluster,
        }, { collapsed: false }).addTo(map);

        const siteIcon = L.divIcon({
            className: 'osp-site-icon',
            html: '<i class="mdi mdi-domain"></i>',
            iconSize: [28, 28],
            iconAnchor: [14, 14],
        });
        const closureIcon = L.divIcon({
            className: 'osp-closure-icon',
            html: '<i class="mdi mdi-circle-double"></i>',
            iconSize: [22, 22],
            iconAnchor: [11, 11],
        });

        let counts = { sites: 0, cables: 0, closures: 0 };

        function loadData() {
            const status = Array.from(document.getElementById('osp-filter-status').selectedOptions)
                .map(o => o.value);
            const qs = new URLSearchParams();
            status.forEach(s => qs.append('status', s));
            const url = qs.toString() ? `${dataUrl}?${qs}` : dataUrl;

            cableLayer.clearLayers();
            siteCluster.clearLayers();
            closureCluster.clearLayers();
            counts = { sites: 0, cables: 0, closures: 0 };

            fetch(url, { credentials: 'same-origin' })
                .then(r => r.json())
                .then(geojson => {
                    const bounds = [];
                    (geojson.features || []).forEach(f => {
                        const props = f.properties || {};
                        const geom = f.geometry || {};
                        if (props.kind === 'site' && geom.type === 'Point') {
                            const ll = [geom.coordinates[1], geom.coordinates[0]];
                            L.marker(ll, { icon: siteIcon })
                                .bindPopup(
                                    `<strong>${escapeHtml(props.name)}</strong><br>` +
                                    `<small>${escapeHtml(props.status || '')}</small><br>` +
                                    `<a href="${props.url}">Open site &raquo;</a>`
                                )
                                .addTo(siteCluster);
                            bounds.push(ll);
                            counts.sites++;
                        } else if (props.kind === 'cable' && geom.type === 'LineString') {
                            const latlngs = geom.coordinates.map(c => [c[1], c[0]]);
                            const opts = {
                                color: cableColor(props.status),
                                weight: 4,
                                opacity: 0.8,
                                dashArray: props.status === 'planned' ? '8,8' : null,
                            };
                            const line = L.polyline(latlngs, opts)
                                .bindPopup(
                                    `<strong>${escapeHtml(props.cid)}</strong><br>` +
                                    `${escapeHtml(props.site_a || '')} &harr; ${escapeHtml(props.site_b || '')}<br>` +
                                    `<small>${escapeHtml(props.type || '')} · ${escapeHtml(props.status || '')} · ${props.fibre_count} fibres · ${props.length_m || 0} m</small><br>` +
                                    `<a href="${props.url}">Open cable &raquo;</a>`
                                );
                            line.ospKind = 'cable';
                            line.ospPk = props.pk;
                            line.ospCid = props.cid;
                            line.addTo(cableLayer);
                            latlngs.forEach(ll => bounds.push(ll));
                            counts.cables++;
                        } else if (props.kind === 'closure' && geom.type === 'Point') {
                            const ll = [geom.coordinates[1], geom.coordinates[0]];
                            const mk = L.marker(ll, { icon: closureIcon })
                                .bindPopup(
                                    `<strong>${escapeHtml(props.name)}</strong><br>` +
                                    `<small>${escapeHtml(props.closure_type || '')} · ${props.used}/${props.capacity} splices</small><br>` +
                                    `<a href="${props.url}">Open closure &raquo;</a>`
                                );
                            mk.ospKind = 'closure';
                            mk.ospPk = props.pk;
                            mk.ospName = props.name;
                            mk.addTo(closureCluster);
                            bounds.push(ll);
                            counts.closures++;
                        }
                    });

                    // Only re-fit when the user has narrowed the view with a filter,
                    // otherwise stay at the configured center/zoom which is sized to
                    // show the whole plant. Without this, a single mis-placed feature
                    // would yank the camera away from the plant.
                    const hasFilter = new URLSearchParams(window.location.search).toString().length > 0;
                    if (hasFilter && bounds.length) {
                        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
                    }
                    document.getElementById('osp-map-stats').textContent =
                        `${counts.sites} sites · ${counts.cables} cables · ${counts.closures} closures`;
                })
                .catch(err => {
                    console.error('OSP map data load failed', err);
                    document.getElementById('osp-map-stats').textContent = 'Failed to load map data';
                });
        }

        function escapeHtml(s) {
            if (s == null) return '';
            return String(s).replace(/[&<>"']/g, c => ({
                '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
            }[c]));
        }

        document.getElementById('osp-filter-status').addEventListener('change', loadData);
        document.getElementById('osp-reset-view').addEventListener('click', () => {
            map.setView([centerLat, centerLon], zoom);
        });

        // -------------- Edit mode --------------
        // Toggle: when on, splice closure markers become draggable and cable
        // polylines get geoman vertex/drag editing. Drop-saves PATCH back to
        // the plugin REST API (session-auth + CSRF header). NetBox sets the
        // csrftoken cookie with HttpOnly=True, so the template renders the
        // current token into data-csrf-token for the JS to pick up.
        const csrfToken = mapEl.dataset.csrfToken || '';
        function csrfHeaders(extra) {
            return Object.assign({
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
            }, extra || {});
        }
        function toast(msg, kind) {
            const el = document.getElementById('osp-map-stats');
            if (!el) return;
            const old = el.textContent;
            el.textContent = msg;
            el.style.color = kind === 'error' ? '#dc3545' : (kind === 'ok' ? '#28a745' : '');
            setTimeout(() => { el.textContent = old; el.style.color = ''; }, 3500);
        }

        let editMode = false;
        const editBtn = document.getElementById('osp-edit-toggle');

        function enableEdit() {
            editMode = true;
            editBtn.classList.remove('btn-outline-warning');
            editBtn.classList.add('btn-warning');
            editBtn.innerHTML = '<i class="mdi mdi-check"></i> Done';
            toast('Edit mode: drag splice closures, drag cable vertices. Click Done when finished.', 'ok');

            cableLayer.eachLayer(line => {
                if (line.ospKind !== 'cable' || !line.pm) return;
                line.pm.enable({
                    allowSelfIntersection: true,
                    snappable: true,
                    draggable: true,
                });
                line.on('pm:edit pm:dragend pm:vertexadded pm:vertexremoved', () => saveCable(line));
            });
            closureCluster.eachLayer(mk => {
                if (mk.ospKind !== 'closure') return;
                mk.dragging?.enable();
                mk.on('dragend', () => saveClosure(mk));
            });
        }

        function disableEdit() {
            editMode = false;
            editBtn.classList.add('btn-outline-warning');
            editBtn.classList.remove('btn-warning');
            editBtn.innerHTML = '<i class="mdi mdi-pencil"></i> Edit';
            cableLayer.eachLayer(line => {
                if (line.pm) line.pm.disable();
                line.off('pm:edit pm:dragend pm:vertexadded pm:vertexremoved');
            });
            closureCluster.eachLayer(mk => {
                mk.dragging?.disable();
                mk.off('dragend');
            });
        }

        editBtn.addEventListener('click', () => editMode ? disableEdit() : enableEdit());

        function saveCable(line) {
            const coords = line.getLatLngs().map(ll => [ll.lng, ll.lat]);  // GeoJSON [lon, lat]
            const route = { type: 'LineString', coordinates: coords };
            fetch(`/api/plugins/osp/cables/${line.ospPk}/`, {
                method: 'PATCH',
                credentials: 'same-origin',
                headers: csrfHeaders(),
                body: JSON.stringify({ route: route }),
            })
                .then(r => {
                    if (!r.ok) throw new Error(`HTTP ${r.status}`);
                    return r.json();
                })
                .then(data => toast(`Saved ${line.ospCid} (${data.route_length_m} m)`, 'ok'))
                .catch(err => {
                    console.error('cable save failed', err);
                    toast(`Save failed for ${line.ospCid}: ${err.message}`, 'error');
                });
        }

        function saveClosure(mk) {
            const ll = mk.getLatLng();
            const point = { type: 'Point', coordinates: [ll.lng, ll.lat] };
            fetch(`/api/plugins/osp/closures/${mk.ospPk}/`, {
                method: 'PATCH',
                credentials: 'same-origin',
                headers: csrfHeaders(),
                body: JSON.stringify({ location_point: point }),
            })
                .then(r => {
                    if (!r.ok) throw new Error(`HTTP ${r.status}`);
                    return r.json();
                })
                .then(() => toast(`Moved ${mk.ospName}`, 'ok'))
                .catch(err => {
                    console.error('closure save failed', err);
                    toast(`Save failed for ${mk.ospName}: ${err.message}`, 'error');
                });
        }

        loadData();

        // If the map lives inside a hidden Bootstrap tab, invalidate size when shown.
        document.querySelectorAll('a[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', () => map.invalidateSize());
        });
    });
})();
