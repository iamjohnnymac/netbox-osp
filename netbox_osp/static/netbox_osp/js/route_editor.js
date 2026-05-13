/* OSP cable route editor.

   Renders a Leaflet map with leaflet-geoman draw controls so the user can
   sketch / edit / drag / delete a polyline. The polyline is serialised back
   into the hidden form input as a GeoJSON LineString in [lon, lat] order
   (RFC 7946; Leaflet uses [lat, lon] so we swap at the boundary).

   Loaded from ospcable_edit.html which provides:
       <div id="osp-route-editor"
            data-route-input-id="id_route"
            data-tile-url=".../tiles/0/0/0.png">
*/
(function () {
    'use strict';

    function ready(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    function lineLengthM(coords) {
        // equirectangular flat-earth approx, accurate to ~0.5% for short runs
        const R = 6371008.8;
        let total = 0;
        for (let i = 0; i < coords.length - 1; i++) {
            const [lon1, lat1] = coords[i];
            const [lon2, lat2] = coords[i + 1];
            const phi1 = lat1 * Math.PI / 180;
            const phi2 = lat2 * Math.PI / 180;
            const x = (lon2 - lon1) * Math.PI / 180 * Math.cos((phi1 + phi2) / 2);
            const y = (lat2 - lat1) * Math.PI / 180;
            total += R * Math.hypot(x, y);
        }
        return total;
    }

    function safeParse(raw) {
        if (!raw) return null;
        try {
            const parsed = JSON.parse(raw);
            if (parsed && parsed.type === 'LineString' && Array.isArray(parsed.coordinates)) {
                return parsed;
            }
        } catch (e) {
            // ignore — start blank if input is junk
        }
        return null;
    }

    function latLngsToGeoJsonCoords(latLngs) {
        // Leaflet provides [lat, lon]; GeoJSON wants [lon, lat].
        return latLngs.map(ll => {
            const lat = (typeof ll.lat === 'number') ? ll.lat : ll[0];
            const lon = (typeof ll.lng === 'number') ? ll.lng : ll[1];
            return [lon, lat];
        });
    }

    function geoJsonCoordsToLatLngs(coords) {
        return coords.map(c => [c[1], c[0]]);
    }

    ready(function () {
        const editorEl = document.getElementById('osp-route-editor');
        if (!editorEl) return;

        const inputId = editorEl.dataset.routeInputId || 'id_route';
        const routeInput = document.getElementById(inputId);
        if (!routeInput) {
            console.warn('OSP route editor: hidden form input #' + inputId + ' not found');
            return;
        }

        const rawTileUrl = editorEl.dataset.tileUrl || '';
        const tileUrl = rawTileUrl.replace('/0/0/0.png', '/{z}/{x}/{y}.png');

        // Status banner — prepended into editor parent so the map fills its own div.
        const status = document.createElement('div');
        status.className = 'osp-route-editor-status';
        status.textContent = 'Length: 0 m';
        if (editorEl.parentNode) {
            editorEl.parentNode.insertBefore(status, editorEl);
        }

        const DEFAULT_CENTER = [0.0, 0.0];
        const DEFAULT_ZOOM = 2;

        const map = L.map(editorEl, { preferCanvas: true });
        map.setView(DEFAULT_CENTER, DEFAULT_ZOOM);

        // Multi-base-layer manager — same machinery as the network-map page.
        // The 'offline' layer points back to this plugin's tile
        // proxy so air-gapped sites still get imagery. See base_layers.js.
        const baseLayerDropdownEl = document.getElementById('osp-base-layer-dropdown');
        window.OspBaseLayers.attach(map, baseLayerDropdownEl, tileUrl);

        // Single editable polyline lives in this layer group; only the last one
        // survives so duplicate draws don't desync state.
        const routeLayer = L.featureGroup().addTo(map);

        function currentPolyline() {
            const layers = routeLayer.getLayers();
            return layers.length ? layers[layers.length - 1] : null;
        }

        function dropOlderPolylines() {
            const layers = routeLayer.getLayers();
            if (layers.length <= 1) return;
            // Keep only the most recently added polyline.
            for (let i = 0; i < layers.length - 1; i++) {
                routeLayer.removeLayer(layers[i]);
            }
        }

        function updateStatus(coords) {
            if (!coords || coords.length < 2) {
                status.textContent = 'Length: 0 m (draw a polyline between the two sites)';
            } else {
                const m = lineLengthM(coords);
                status.textContent = 'Length: ' + Math.round(m).toLocaleString() + ' m (' +
                    coords.length + ' vertices)';
            }
        }

        function persist() {
            dropOlderPolylines();
            const pl = currentPolyline();
            if (!pl) {
                routeInput.value = '';
                updateStatus(null);
                return;
            }
            const latLngs = pl.getLatLngs();
            const coords = latLngsToGeoJsonCoords(latLngs);
            if (coords.length < 2) {
                // A single-vertex draw isn't a valid LineString — clear it.
                routeInput.value = '';
                updateStatus(null);
                return;
            }
            const geojson = { type: 'LineString', coordinates: coords };
            routeInput.value = JSON.stringify(geojson);
            updateStatus(coords);
        }

        // Hydrate from existing form value.
        const existing = safeParse(routeInput.value);
        if (existing && Array.isArray(existing.coordinates) && existing.coordinates.length >= 2) {
            const latLngs = geoJsonCoordsToLatLngs(existing.coordinates);
            const pl = L.polyline(latLngs, { color: '#0d6efd', weight: 4, opacity: 0.85 });
            pl.addTo(routeLayer);
            try {
                map.fitBounds(pl.getBounds(), { padding: [40, 40], maxZoom: 14 });
            } catch (e) {
                // empty/degenerate bounds — leave default view
            }
            updateStatus(existing.coordinates);
        } else {
            updateStatus(null);
        }

        // leaflet-geoman: polyline-only.
        if (map.pm && typeof map.pm.addControls === 'function') {
            map.pm.addControls({
                position: 'topleft',
                drawPolyline: true,
                drawPolygon: false,
                drawRectangle: false,
                drawCircle: false,
                drawMarker: false,
                drawCircleMarker: false,
                drawText: false,
                editMode: true,
                dragMode: true,
                cutPolygon: false,
                removalMode: true,
                rotateMode: false,
            });
            // Style the in-progress + finished polyline.
            if (typeof map.pm.setPathOptions === 'function') {
                map.pm.setPathOptions({ color: '#0d6efd', weight: 4, opacity: 0.85 });
            }
            if (typeof map.pm.setGlobalOptions === 'function') {
                map.pm.setGlobalOptions({ snappable: true, snapDistance: 15 });
            }
        }

        // Geoman fires pm:create on the map when a new shape is finished.
        map.on('pm:create', function (e) {
            if (!e || !e.layer) return;
            // If the user draws a second polyline, drop the older one(s).
            const layers = routeLayer.getLayers();
            layers.forEach(layer => routeLayer.removeLayer(layer));
            e.layer.addTo(routeLayer);
            // Make the new layer editable + listen to per-layer events.
            if (e.layer.pm && typeof e.layer.pm.enable === 'function') {
                // leave it disabled so the user must click "edit" to mutate vertices,
                // but bind events for when they do
            }
            bindLayerEvents(e.layer);
            // Geoman occasionally leaves the freshly-drawn layer on the map
            // (not inside our routeLayer); ensure we own it.
            if (e.layer._map && !routeLayer.hasLayer(e.layer)) {
                e.layer.addTo(routeLayer);
            }
            persist();
        });

        // Removal — wired both at the map level (geoman) and per layer.
        map.on('pm:remove', function (e) {
            if (e && e.layer && routeLayer.hasLayer(e.layer)) {
                routeLayer.removeLayer(e.layer);
            }
            persist();
        });

        // Drag / edit completion fires on the layer; wire any existing layer too.
        function bindLayerEvents(layer) {
            if (!layer || !layer.on) return;
            layer.on('pm:edit', persist);
            layer.on('pm:update', persist);
            layer.on('pm:dragend', persist);
            layer.on('pm:markerdragend', persist);
            layer.on('pm:vertexadded', persist);
            layer.on('pm:vertexremoved', persist);
            layer.on('pm:cut', persist);
        }

        routeLayer.eachLayer(bindLayerEvents);

        // Global geoman edit events as a safety net.
        map.on('pm:globaleditmodetoggled', function () { persist(); });
        map.on('pm:globaldragmodetoggled', function () { persist(); });

        // If the editor lives inside a Bootstrap tab that's initially hidden,
        // Leaflet computes a zero-size container. Refresh on tab show.
        document.querySelectorAll('a[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', () => map.invalidateSize());
        });
        // Also refresh on window resize so the map redraws cleanly.
        window.addEventListener('resize', () => map.invalidateSize());
    });
})();
