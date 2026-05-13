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
# Network Map
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

        cables_qs = models.OspCable.objects.select_related("site_a", "site_b")
        if site_ids:
            cables_qs = cables_qs.filter(
                Q(site_a_id__in=site_ids) | Q(site_b_id__in=site_ids)
            )
        if statuses:
            cables_qs = cables_qs.filter(status__in=statuses)
        if types:
            cables_qs = cables_qs.filter(type__in=types)

        # Only surface sites that actually appear as an OSP cable endpoint —
        # otherwise the map auto-fit pulls in unrelated sites and zooms way
        # out past the tile coverage area.
        cable_site_ids = set(cables_qs.values_list("site_a_id", flat=True)) | set(
            cables_qs.values_list("site_b_id", flat=True)
        )
        sites_qs = (
            Site.objects
            .filter(pk__in=cable_site_ids)
            .exclude(latitude__isnull=True)
            .exclude(longitude__isnull=True)
        )
        if site_ids:
            sites_qs = sites_qs.filter(pk__in=site_ids)
        closures_qs = models.SpliceClosure.objects.exclude(location_point__isnull=True)

        return JsonResponse(build_map_geojson(sites_qs, cables_qs, closures_qs))


# ============================================================================
# Tile proxy (offline MBTiles)
# ============================================================================

import threading

_MBTILES_LOCAL = threading.local()


def _open_mbtiles(path):
    """Open one connection per thread per file. SQLite is fine for read-only
    concurrent access as long as each thread has its own handle."""
    cache = getattr(_MBTILES_LOCAL, "conns", None)
    if cache is None:
        cache = {}
        _MBTILES_LOCAL.conns = cache
    conn = cache.get(path)
    if conn is None:
        conn = sqlite3.connect(path, check_same_thread=False, uri=False)
        cache[path] = conn
    return conn


class TileProxyView(LoginRequiredMixin, View):
    """Serve a single tile from a bundled MBTiles file.

    MBTiles uses TMS y-axis (origin bottom-left); Leaflet uses XYZ (top-left).
    Convert: tms_y = (2^z - 1) - y.

    Lookup order:
      1. MEDIA_ROOT/osp_tiles/*.mbtiles (user-supplied high-res overlays)
      2. <plugin>/static/netbox_osp/tiles/basemap.mbtiles
    """

    def get(self, request, z, x, y, ext):
        if ext.lower() not in ("png", "jpg", "jpeg", "webp"):
            return HttpResponseNotFound("unsupported tile extension")

        tms_y = (1 << z) - 1 - y

        candidate_paths = []
        media_dir = Path(getattr(settings, "MEDIA_ROOT", "/opt/netbox/netbox/media")) / "osp_tiles"
        if media_dir.is_dir():
            candidate_paths.extend(sorted(media_dir.glob("*.mbtiles")))
        plugin_tiles = Path(__file__).parent / "static" / "netbox_osp" / "tiles"
        if plugin_tiles.is_dir():
            # All *.mbtiles in the plugin tiles dir, alpha-sorted, but with
            # basemap.mbtiles forced last so real-imagery bundles override
            # the stub fallback when keys overlap (e.g. z=0).
            files = [p for p in plugin_tiles.glob("*.mbtiles") if p.name != "basemap.mbtiles"]
            candidate_paths.extend(sorted(files))
            basemap = plugin_tiles / "basemap.mbtiles"
            if basemap.is_file():
                candidate_paths.append(basemap)

        tile_blob = None
        for p in candidate_paths:
            try:
                conn = _open_mbtiles(str(p))
                row = conn.execute(
                    "SELECT tile_data FROM tiles "
                    "WHERE zoom_level=? AND tile_column=? AND tile_row=?",
                    (z, x, tms_y),
                ).fetchone()
                if row is not None:
                    tile_blob = row[0]
                    break
            except sqlite3.Error:
                continue

        if tile_blob is None:
            # 1x1 transparent PNG so the map doesn't show 404s in F12
            blank = bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
                "890000000d49444154789c63600000000005000160d4a83f0000000049454e44"
                "ae426082"
            )
            resp = HttpResponse(blank, content_type="image/png")
            resp["Cache-Control"] = "public, max-age=86400"
            return resp

        etag = hashlib.md5(tile_blob).hexdigest()
        if request.META.get("HTTP_IF_NONE_MATCH") == f'"{etag}"':
            return HttpResponse(status=304)

        if ext.lower() in ("jpg", "jpeg"):
            content_type = "image/jpeg"
        elif ext.lower() == "webp":
            content_type = "image/webp"
        else:
            content_type = "image/png"

        resp = HttpResponse(tile_blob, content_type=content_type)
        resp["ETag"] = f'"{etag}"'
        resp["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp
