from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem


def _add_import_buttons(slug: str):
    """Return (Add, Import) PluginMenuButton tuple for a model URL slug.

    Convention: every list page that has create + bulk-import gets a pair
    of buttons in the sidebar, matching the (+, upload) UX used by mature
    NetBox plugins.
    """
    return (
        PluginMenuButton(
            link=f"plugins:netbox_osp:{slug}_add",
            title="Add",
            icon_class="mdi mdi-plus-thick",
        ),
        PluginMenuButton(
            link=f"plugins:netbox_osp:{slug}_import",
            title="Import",
            icon_class="mdi mdi-upload",
        ),
    )


cable_buttons = _add_import_buttons("ospcable")
tube_buttons = _add_import_buttons("tube")
strand_buttons = _add_import_buttons("strand")
closure_buttons = _add_import_buttons("spliceclosure")
tray_buttons = _add_import_buttons("splicetray")
splice_buttons = _add_import_buttons("splice")
link_buttons = (
    PluginMenuButton(
        link="plugins:netbox_osp:fibrelink_add",
        title="Add",
        icon_class="mdi mdi-plus-thick",
    ),
)


menu = PluginMenu(
    label="OSP",
    icon_class="mdi mdi-map-marker-radius",
    groups=(
        ("Map", (
            PluginMenuItem(
                link="plugins:netbox_osp:network_map",
                link_text="Network Map",
            ),
        )),
        ("OSP Cables", (
            PluginMenuItem(
                link="plugins:netbox_osp:ospcable_list",
                link_text="OSP Cables",
                buttons=cable_buttons,
            ),
            PluginMenuItem(
                link="plugins:netbox_osp:tube_list",
                link_text="Tubes",
                buttons=tube_buttons,
            ),
            PluginMenuItem(
                link="plugins:netbox_osp:strand_list",
                link_text="Strands",
                buttons=strand_buttons,
            ),
        )),
        ("Splices", (
            PluginMenuItem(
                link="plugins:netbox_osp:spliceclosure_list",
                link_text="Splice Closures",
                buttons=closure_buttons,
            ),
            PluginMenuItem(
                link="plugins:netbox_osp:splicetray_list",
                link_text="Splice Trays",
                buttons=tray_buttons,
            ),
            PluginMenuItem(
                link="plugins:netbox_osp:splice_list",
                link_text="Splices",
                buttons=splice_buttons,
            ),
        )),
        ("Logical", (
            PluginMenuItem(
                link="plugins:netbox_osp:fibrelink_list",
                link_text="Fibre Links",
                buttons=link_buttons,
            ),
        )),
    ),
)
