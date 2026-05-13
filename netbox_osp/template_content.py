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


template_extensions = [SiteOspMapTab, LocationGeoPanel]
