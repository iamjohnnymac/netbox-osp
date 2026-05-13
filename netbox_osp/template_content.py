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


template_extensions = [SiteOspMapTab]
