from django.db.models import Q

from netbox.plugins import PluginTemplateExtension


class SiteOspMapTab(PluginTemplateExtension):
    """Add an 'OSP Connectivity' panel + map link to Site detail pages."""
    models = ["dcim.site"]

    def left_page(self):
        from .models import OspCable
        site = self.context["object"]
        cables = OspCable.objects.filter(Q(site_a=site) | Q(site_b=site))
        if not cables.exists():
            return ""
        return self.render(
            "netbox_osp/inc/site_osp_tab.html",
            extra_context={
                "site": site,
                "cables": cables,
                "cable_count": cables.count(),
            },
        )


class LocationGeoPanel(PluginTemplateExtension):
    """Inject a 'GPS position' panel into dcim.Location detail pages.

    Shows the LocationGeo (if any) plus add/edit buttons. Always rendered,
    even when no LocationGeo exists, so operators have a one-click path to
    record coords.
    """
    models = ["dcim.location"]

    def right_page(self):
        from .models import LocationGeo
        location = self.context["object"]
        geo = LocationGeo.objects.filter(location=location).first()
        return self.render(
            "netbox_osp/inc/location_geo_panel.html",
            extra_context={"geo": geo},
        )


# ============================================================================
# PR E — visual core tracer
# ============================================================================

class _TraceButtonMixin:
    """Shared rendering for the "Trace this core" button on Interface /
    FrontPort / Strand detail pages.

    Subclasses set `models` and `_trace_url_view_name` — the URL the
    button links to. For Interface and FrontPort the URL resolves to a
    redirect view that finds the underlying Strand and forwards to the
    Strand trace page. For Strand the URL is the trace page directly.
    """
    _trace_url_view_name: str = ""

    def _trace_url_for(self, obj) -> str:
        from django.urls import NoReverseMatch, reverse
        try:
            return reverse(self._trace_url_view_name, args=[obj.pk])
        except NoReverseMatch:
            return ""

    def _render_button(self) -> str:
        obj = self.context["object"]
        url = self._trace_url_for(obj)
        if not url:
            return ""
        return self.render(
            "netbox_osp/inc/trace_button.html",
            extra_context={"trace_url": url},
        )


class InterfaceTraceButton(_TraceButtonMixin, PluginTemplateExtension):
    """Inject the trace button onto dcim.Interface detail pages.

    The button is shown unconditionally — clicking it on an interface
    that isn't reachable from a netbox-osp Strand yields a friendly 404
    explaining the gap (see views.InterfaceTraceRedirectView).
    """
    models = ["dcim.interface"]
    _trace_url_view_name = "plugins:netbox_osp:interface_trace"

    def right_page(self):
        return self._render_button()


class FrontPortTraceButton(_TraceButtonMixin, PluginTemplateExtension):
    """Inject the trace button onto dcim.FrontPort detail pages."""
    models = ["dcim.frontport"]
    _trace_url_view_name = "plugins:netbox_osp:frontport_trace"

    def right_page(self):
        return self._render_button()


class StrandTraceButton(_TraceButtonMixin, PluginTemplateExtension):
    """Inject the trace button onto netbox-osp Strand detail pages.

    Some installs disable template extensions on plugin pages — for
    those, the strand.html template embeds the button directly via
    {% include %}. This extension covers the standard case.
    """
    models = ["netbox_osp.strand"]
    _trace_url_view_name = "plugins:netbox_osp:strand_trace"

    def right_page(self):
        return self._render_button()


template_extensions = [
    SiteOspMapTab,
    LocationGeoPanel,
    InterfaceTraceButton,
    FrontPortTraceButton,
    StrandTraceButton,
]
