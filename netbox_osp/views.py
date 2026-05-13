import json
import os
import sqlite3
import hashlib
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound, JsonResponse
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

from netbox.views import generic

from . import forms, models, tables, filtersets


# ============================================================================
# OspCable
# ============================================================================

class OspCableView(generic.ObjectView):
    queryset = models.OspCable.objects.all()

    def get_extra_context(self, request, instance):
        strands = instance.strands.select_related("tube", "cable_link").order_by("position")
        tubes = instance.tubes.order_by("number")
        strand_table = tables.StrandTable(strands)
        strand_table.configure(request)
        tube_table = tables.TubeTable(tubes)
        tube_table.configure(request)
        in_use = strands.exclude(status="spare").exclude(status="dark").count()
        return {
            "strand_table": strand_table,
            "tube_table": tube_table,
            "strand_in_use_count": in_use,
        }


class OspCableListView(generic.ObjectListView):
    queryset = models.OspCable.objects.all()
    table = tables.OspCableTable
    filterset = filtersets.OspCableFilterSet
    filterset_form = forms.OspCableFilterForm


class OspCableEditView(generic.ObjectEditView):
    queryset = models.OspCable.objects.all()
    form = forms.OspCableForm
    template_name = "netbox_osp/ospcable_edit.html"


class OspCableDeleteView(generic.ObjectDeleteView):
    queryset = models.OspCable.objects.all()


class OspCableBulkEditView(generic.BulkEditView):
    queryset = models.OspCable.objects.all()
    filterset = filtersets.OspCableFilterSet
    table = tables.OspCableTable
    form = forms.OspCableBulkEditForm


class OspCableBulkDeleteView(generic.BulkDeleteView):
    queryset = models.OspCable.objects.all()
    filterset = filtersets.OspCableFilterSet
    table = tables.OspCableTable


class OspCableBulkImportView(generic.BulkImportView):
    queryset = models.OspCable.objects.all()
    model_form = forms.OspCableImportForm
    table = tables.OspCableTable


# ============================================================================
# Tube
# ============================================================================

class TubeView(generic.ObjectView):
    queryset = models.Tube.objects.all()

    def get_extra_context(self, request, instance):
        strands = instance.strands.order_by("position")
        strand_table = tables.StrandTable(strands)
        strand_table.configure(request)
        return {"strand_table": strand_table}


class TubeListView(generic.ObjectListView):
    queryset = models.Tube.objects.select_related("cable").all()
    table = tables.TubeTable
    filterset = filtersets.TubeFilterSet
    filterset_form = forms.TubeFilterForm


class TubeEditView(generic.ObjectEditView):
    queryset = models.Tube.objects.all()
    form = forms.TubeForm


class TubeDeleteView(generic.ObjectDeleteView):
    queryset = models.Tube.objects.all()


class TubeBulkEditView(generic.BulkEditView):
    queryset = models.Tube.objects.select_related("cable").all()
    filterset = filtersets.TubeFilterSet
    table = tables.TubeTable
    form = forms.TubeBulkEditForm


class TubeBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Tube.objects.select_related("cable").all()
    filterset = filtersets.TubeFilterSet
    table = tables.TubeTable


class TubeBulkImportView(generic.BulkImportView):
    queryset = models.Tube.objects.all()
    model_form = forms.TubeImportForm
    table = tables.TubeTable


# ============================================================================
# Strand
# ============================================================================

class StrandView(generic.ObjectView):
    queryset = models.Strand.objects.select_related("cable", "tube", "cable_link").all()


class StrandListView(generic.ObjectListView):
    queryset = models.Strand.objects.select_related("cable", "tube").all()
    table = tables.StrandTable
    filterset = filtersets.StrandFilterSet
    filterset_form = forms.StrandFilterForm


class StrandEditView(generic.ObjectEditView):
    queryset = models.Strand.objects.all()
    form = forms.StrandForm


class StrandDeleteView(generic.ObjectDeleteView):
    queryset = models.Strand.objects.all()


class StrandBulkEditView(generic.BulkEditView):
    queryset = models.Strand.objects.select_related("cable", "tube").all()
    filterset = filtersets.StrandFilterSet
    table = tables.StrandTable
    form = forms.StrandBulkEditForm


class StrandBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Strand.objects.select_related("cable", "tube").all()
    filterset = filtersets.StrandFilterSet
    table = tables.StrandTable


class StrandBulkImportView(generic.BulkImportView):
    queryset = models.Strand.objects.all()
    model_form = forms.StrandImportForm
    table = tables.StrandTable


# ============================================================================
# SpliceClosure
# ============================================================================

class SpliceClosureView(generic.ObjectView):
    queryset = models.SpliceClosure.objects.all()

    def get_extra_context(self, request, instance):
        trays = instance.trays.order_by("number")
        tray_table = tables.SpliceTrayTable(trays)
        tray_table.configure(request)
        return {"tray_table": tray_table}


class SpliceClosureListView(generic.ObjectListView):
    queryset = models.SpliceClosure.objects.all()
    table = tables.SpliceClosureTable
    filterset = filtersets.SpliceClosureFilterSet
    filterset_form = forms.SpliceClosureFilterForm


class SpliceClosureEditView(generic.ObjectEditView):
    queryset = models.SpliceClosure.objects.all()
    form = forms.SpliceClosureForm


class SpliceClosureDeleteView(generic.ObjectDeleteView):
    queryset = models.SpliceClosure.objects.all()


class SpliceClosureBulkEditView(generic.BulkEditView):
    queryset = models.SpliceClosure.objects.all()
    filterset = filtersets.SpliceClosureFilterSet
    table = tables.SpliceClosureTable
    form = forms.SpliceClosureBulkEditForm


class SpliceClosureBulkDeleteView(generic.BulkDeleteView):
    queryset = models.SpliceClosure.objects.all()
    filterset = filtersets.SpliceClosureFilterSet
    table = tables.SpliceClosureTable


class SpliceClosureBulkImportView(generic.BulkImportView):
    queryset = models.SpliceClosure.objects.all()
    model_form = forms.SpliceClosureImportForm
    table = tables.SpliceClosureTable


# ============================================================================
# SpliceTray
# ============================================================================

class SpliceTrayView(generic.ObjectView):
    queryset = models.SpliceTray.objects.all()

    def get_extra_context(self, request, instance):
        splices = instance.splices.order_by("position").select_related(
            "strand_a__cable", "strand_b__cable"
        )
        splice_table = tables.SpliceTable(splices)
        splice_table.configure(request)
        return {"splice_table": splice_table}


class SpliceTrayListView(generic.ObjectListView):
    queryset = models.SpliceTray.objects.select_related("closure").all()
    table = tables.SpliceTrayTable
    filterset = filtersets.SpliceTrayFilterSet
    filterset_form = forms.SpliceTrayFilterForm


class SpliceTrayEditView(generic.ObjectEditView):
    queryset = models.SpliceTray.objects.all()
    form = forms.SpliceTrayForm


class SpliceTrayDeleteView(generic.ObjectDeleteView):
    queryset = models.SpliceTray.objects.all()


class SpliceTrayBulkEditView(generic.BulkEditView):
    queryset = models.SpliceTray.objects.select_related("closure").all()
    filterset = filtersets.SpliceTrayFilterSet
    table = tables.SpliceTrayTable
    form = forms.SpliceTrayBulkEditForm


class SpliceTrayBulkDeleteView(generic.BulkDeleteView):
    queryset = models.SpliceTray.objects.select_related("closure").all()
    filterset = filtersets.SpliceTrayFilterSet
    table = tables.SpliceTrayTable


class SpliceTrayBulkImportView(generic.BulkImportView):
    queryset = models.SpliceTray.objects.all()
    model_form = forms.SpliceTrayImportForm
    table = tables.SpliceTrayTable


# ============================================================================
# Splice
# ============================================================================

class SpliceView(generic.ObjectView):
    queryset = models.Splice.objects.select_related("tray__closure", "strand_a", "strand_b").all()


class SpliceListView(generic.ObjectListView):
    queryset = models.Splice.objects.select_related("tray__closure").all()
    table = tables.SpliceTable
    filterset = filtersets.SpliceFilterSet
    filterset_form = forms.SpliceFilterForm


class SpliceEditView(generic.ObjectEditView):
    queryset = models.Splice.objects.all()
    form = forms.SpliceForm


class SpliceDeleteView(generic.ObjectDeleteView):
    queryset = models.Splice.objects.all()


class SpliceBulkEditView(generic.BulkEditView):
    queryset = models.Splice.objects.select_related("tray__closure").all()
    filterset = filtersets.SpliceFilterSet
    table = tables.SpliceTable
    form = forms.SpliceBulkEditForm


class SpliceBulkDeleteView(generic.BulkDeleteView):
    queryset = models.Splice.objects.select_related("tray__closure").all()
    filterset = filtersets.SpliceFilterSet
    table = tables.SpliceTable


class SpliceBulkImportView(generic.BulkImportView):
    queryset = models.Splice.objects.all()
    model_form = forms.SpliceImportForm
    table = tables.SpliceTable


# ============================================================================
# FibreLink
# ============================================================================

class FibreLinkView(generic.ObjectView):
    queryset = models.FibreLink.objects.all()

    def get_extra_context(self, request, instance):
        hops = instance.trace()
        return {"hops": hops}


class FibreLinkListView(generic.ObjectListView):
    queryset = models.FibreLink.objects.all()
    table = tables.FibreLinkTable
    filterset = filtersets.FibreLinkFilterSet
    filterset_form = forms.FibreLinkFilterForm


class FibreLinkEditView(generic.ObjectEditView):
    queryset = models.FibreLink.objects.all()
    form = forms.FibreLinkForm


class FibreLinkDeleteView(generic.ObjectDeleteView):
    queryset = models.FibreLink.objects.all()


# ============================================================================
# Map (full-screen + GeoJSON data + tile proxy)
# ============================================================================

class NetworkMapView(LoginRequiredMixin, View):
    """Render the full-screen Leaflet map. JS hydrates from /map/data/."""
    template_name = "netbox_osp/network_map.html"

    def get(self, request):
        from django.shortcuts import render
        from django.conf import settings as dj_settings
        plugin_config = dj_settings.PLUGINS_CONFIG.get("netbox_osp", {})
        return render(request, self.template_name, {
            "map_center": plugin_config.get("map_default_center", [0.0, 0.0]),
            "map_zoom": plugin_config.get("map_default_zoom", 2),
        })


class NetworkMapDataView(LoginRequiredMixin, View):
    """Return GeoJSON FeatureCollection: sites (as Points), osp cables (as LineStrings),
    and splice closures (as Points). Filterable by ?site=&status=&type=."""

    def get(self, request):
        from dcim.models import Site
        from django.db.models import Q
        from ._geo_helpers import build_map_geojson

        site_ids = request.GET.getlist("site")
        statuses = request.GET.getlist("status")
        types = request.GET.getlist("type")

        site_qs = Site.objects.all()
        cable_qs = models.OspCable.objects.select_related("site_a", "site_b").all()
        closure_qs = models.SpliceClosure.objects.select_related("site").all()

        if site_ids:
            site_qs = site_qs.filter(pk__in=site_ids)
            cable_qs = cable_qs.filter(Q(site_a__in=site_ids) | Q(site_b__in=site_ids))
            closure_qs = closure_qs.filter(site__in=site_ids)
        if statuses:
            cable_qs = cable_qs.filter(status__in=statuses)
            closure_qs = closure_qs.filter(status__in=statuses)
        if types:
            cable_qs = cable_qs.filter(type__in=types)

        geojson = build_map_geojson(site_qs, cable_qs, closure_qs)
        return JsonResponse(geojson)


# ----------------------------------------------------------------------------
# Tile proxy — serves PNG / JPEG / WebP tiles from one or more MBTiles files.
# ----------------------------------------------------------------------------

_TILE_DB_CACHE = {}                 # thread-local in _open_mbtiles
_TILE_CONN_CACHE = {}               # thread-local connections per file

_MIME_BY_EXT = {
    "png":  "image/png",
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}


def _open_mbtiles(path: Path) -> sqlite3.Connection:
    """Return a thread-local sqlite3 connection for the given file."""
    import threading
    tls = getattr(_open_mbtiles, "_tls", None)
    if tls is None:
        tls = threading.local()
        _open_mbtiles._tls = tls
    key = str(path)
    conn = getattr(tls, "conns", {}).get(key)
    if conn is None:
        conn = sqlite3.connect(str(path), check_same_thread=False)
        if not hasattr(tls, "conns"):
            tls.conns = {}
        tls.conns[key] = conn
    return conn


class TileProxyView(LoginRequiredMixin, View):
    """Serve a single tile from the first MBTiles bundle that has it."""

    def get(self, request, z, x, y, ext):
        ext = ext.lower()
        if ext not in _MIME_BY_EXT:
            return HttpResponseNotFound("Unsupported tile extension.")

        # MBTiles stores rows TMS-style (origin bottom-left); incoming y is XYZ.
        tms_y = (1 << z) - 1 - y
        candidate_paths = []
        media_dir = Path(getattr(settings, "MEDIA_ROOT", "/opt/netbox/netbox/media")) / "osp_tiles"
        if media_dir.is_dir():
            candidate_paths.extend(sorted(media_dir.glob("*.mbtiles")))
        plugin_tiles = Path(__file__).parent / "static" / "netbox_osp" / "tiles"
        if plugin_tiles.is_dir():
            files = [p for p in plugin_tiles.glob("*.mbtiles") if p.name != "basemap.mbtiles"]
            candidate_paths.extend(sorted(files))
            basemap = plugin_tiles / "basemap.mbtiles"
            if basemap.is_file():
                candidate_paths.append(basemap)

        for path in candidate_paths:
            try:
                conn = _open_mbtiles(path)
                cur = conn.execute(
                    "SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?",
                    (z, x, tms_y),
                )
                row = cur.fetchone()
                if row:
                    response = HttpResponse(row[0], content_type=_MIME_BY_EXT[ext])
                    response["Cache-Control"] = "public, max-age=86400"
                    return response
            except sqlite3.Error:
                continue

        # No bundle had this tile.
        return HttpResponseNotFound(f"No tile at z={z} x={x} y={y}")
