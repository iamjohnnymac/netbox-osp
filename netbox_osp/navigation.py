from netbox.plugins import PluginMenu, PluginMenuItem, PluginMenuButton


cable_buttons = (
    PluginMenuButton(
        link="plugins:netbox_osp:ospcable_add",
        title="Add",
        icon_class="mdi mdi-plus-thick",
    ),
)

closure_buttons = (
    PluginMenuButton(
        link="plugins:netbox_osp:spliceclosure_add",
        title="Add",
        icon_class="mdi mdi-plus-thick",
    ),
)

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
            ),
            PluginMenuItem(
                link="plugins:netbox_osp:strand_list",
                link_text="Strands",
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
            ),
            PluginMenuItem(
                link="plugins:netbox_osp:splice_list",
                link_text="Splices",
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
