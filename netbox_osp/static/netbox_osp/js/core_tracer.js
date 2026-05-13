/* netbox-osp visual core tracer (PR E)
 *
 * Renders a dagre-d3 graph of the strand trace returned by
 * /api/plugins/osp/cores/<id>/trace/.
 *
 * Expects two globals (vendored by strand_tracer.html):
 *   - dagreD3 (from dagre-d3.min.js)
 *   - d3      (from dagre-d3.min.js — the v0.6.4 bundle ships d3 v5 alongside)
 *
 * The template embeds a <svg id="osp-tracer"> and a script block setting
 * window.OSP_TRACE_URL to the JSON endpoint.
 */
(function () {
    'use strict';

    const COLORS = {
        interface: '#0d6efd',
        cable: '#6c757d',
        cassette: '#fd7e14',
        trunk: '#6f42c1',
        splice: '#dc3545',
        osp_strand: '#198754',
    };

    const BAND_COLORS = {
        ok: '#28a745',
        warn: '#ffc107',
        fail: '#dc3545',
    };

    const HOP_LABELS = {
        interface: 'IF',
        cable: 'Cable',
        cassette: 'Cassette',
        trunk: 'Trunk',
        splice: 'Splice',
        osp_strand: 'OSP',
    };

    function badgeHtml(hop) {
        const colour = COLORS[hop.kind] || '#6c757d';
        const subtitle = HOP_LABELS[hop.kind] || hop.kind;
        const lossStr = (hop.loss_db !== undefined && hop.loss_db !== null)
            ? (Number(hop.loss_db).toFixed(2) + ' dB')
            : '';
        const lengthStr = (hop.length_m !== undefined && hop.length_m !== null)
            ? Math.round(hop.length_m) + ' m'
            : '';
        const meta = [lossStr, lengthStr].filter(Boolean).join(' • ');
        // Escape user-controlled label content to be safe inside an SVG
        // foreignObject. Innocent strings will pass through unchanged.
        const safeLabel = escapeHtml(hop.label || '');
        return (
            '<div class="osp-tracer-node" style="border-color:' + colour + '">' +
            '  <div class="osp-tracer-node__kind" style="color:' + colour + '">'
            + escapeHtml(subtitle) + '</div>' +
            '  <div class="osp-tracer-node__label">' + safeLabel + '</div>' +
            (meta ? '  <div class="osp-tracer-node__meta">' + escapeHtml(meta) + '</div>' : '') +
            '</div>'
        );
    }

    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, function (c) {
            return ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;',
            })[c];
        });
    }

    function renderSummary(trace) {
        const totalEl = document.getElementById('osp-tracer-summary-total');
        const targetEl = document.getElementById('osp-tracer-summary-target');
        const pctEl = document.getElementById('osp-tracer-summary-pct');
        const bandEl = document.getElementById('osp-tracer-summary-band');
        const total = Number(trace.total_loss_db || 0).toFixed(2);
        const target = Number(trace.target_loss_budget_db || 0).toFixed(2);
        const pct = Number(trace.loss_pct || 0).toFixed(1);
        if (totalEl) totalEl.textContent = total;
        if (targetEl) targetEl.textContent = target;
        if (pctEl) pctEl.textContent = pct + '%';
        if (bandEl) {
            bandEl.textContent = trace.band.toUpperCase();
            bandEl.style.backgroundColor = BAND_COLORS[trace.band] || '#6c757d';
        }
        // Top-right "incomplete" badge if the trace ended early.
        const incEl = document.getElementById('osp-tracer-incomplete');
        if (incEl) {
            incEl.style.display = trace.incomplete ? 'inline-block' : 'none';
        }
    }

    function renderGraph(trace) {
        if (typeof dagreD3 === 'undefined' || typeof d3 === 'undefined') {
            const fallback = document.getElementById('osp-tracer-fallback');
            if (fallback) {
                fallback.style.display = 'block';
                fallback.textContent = (
                    'Renderer JS not loaded (dagre-d3 / d3 missing). ' +
                    'The trace data below is from the JSON API endpoint.'
                );
            }
            return;
        }

        const g = new dagreD3.graphlib.Graph()
            .setGraph({
                rankdir: 'LR',
                marginx: 20,
                marginy: 20,
                nodesep: 30,
                ranksep: 50,
            })
            .setDefaultEdgeLabel(function () { return {}; });

        const hops = trace.hops || [];
        hops.forEach(function (hop, idx) {
            g.setNode('n' + idx, {
                labelType: 'html',
                label: badgeHtml(hop),
                padding: 0,
                rx: 6,
                ry: 6,
                // Persist URL + idx as graphlib node attributes for the
                // click handler.
                osp_url: hop.url || '',
            });
            if (idx > 0) {
                g.setEdge('n' + (idx - 1), 'n' + idx, {
                    arrowhead: 'normal',
                });
            }
        });

        const svg = d3.select('#osp-tracer');
        svg.selectAll('*').remove();
        const inner = svg.append('g');

        const render = new dagreD3.render();
        render(inner, g);

        // Auto-fit SVG to graph extents.
        const gw = g.graph().width || 0;
        const gh = g.graph().height || 0;
        svg.attr('viewBox', '0 0 ' + (gw + 40) + ' ' + (gh + 40));
        svg.attr('preserveAspectRatio', 'xMinYMin meet');
        inner.attr('transform', 'translate(20, 20)');

        // Click → navigate.
        inner.selectAll('g.node').on('click', function (id) {
            const node = g.node(id);
            if (node && node.osp_url) {
                window.location.href = node.osp_url;
            }
        });
    }

    function fetchAndRender(url) {
        const headers = new Headers({ 'Accept': 'application/json' });
        const csrf = document.querySelector('meta[name="csrf-token"]');
        if (csrf && csrf.getAttribute('content')) {
            headers.set('X-CSRFToken', csrf.getAttribute('content'));
        }
        return fetch(url, { credentials: 'same-origin', headers: headers })
            .then(function (resp) {
                if (!resp.ok) {
                    throw new Error('trace fetch failed: ' + resp.status);
                }
                return resp.json();
            })
            .then(function (trace) {
                renderSummary(trace);
                renderGraph(trace);
            })
            .catch(function (err) {
                const fallback = document.getElementById('osp-tracer-fallback');
                if (fallback) {
                    fallback.style.display = 'block';
                    fallback.textContent = 'Could not load trace: ' + err.message;
                }
            });
    }

    function init() {
        const url = window.OSP_TRACE_URL;
        if (!url) {
            return;
        }
        fetchAndRender(url);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
