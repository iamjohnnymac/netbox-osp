import django_tables2 as tables
from netbox.tables import NetBoxTable, ChoiceFieldColumn
from netbox.tables import columns

from .models import (
    FibreLink,
    OspCable,
    Splice,
    SpliceClosure,
    SpliceTray,
    Strand,
    Tube,
)


class OspCableTable(NetBoxTable):
    cid = tables.Column(linkify=True)
    type = ChoiceFieldColumn()
    status = ChoiceFieldColumn()
    site_a = tables.Column(linkify=True)
    site_b = tables.Column(linkify=True)
    tenant = tables.Column(linkify=True)
    fibre_count = tables.Column(verbose_name="Fibres")
    effective_length_m = tables.Column(
        verbose_name="Length (m)", accessor="effective_length_m", orderable=False,
    )

    class Meta(NetBoxTable.Meta):
        model = OspCable
        fields = (
            "pk", "id", "cid", "type", "status", "site_a", "site_b",
            "tenant", "fibre_count", "tube_count", "effective_length_m",
            "manufacturer", "part_number", "description", "tags",
            "created", "last_updated",
        )
        default_columns = (
            "cid", "type", "status", "site_a", "site_b",
            "fibre_count", "effective_length_m",
        )


class TubeTable(NetBoxTable):
    cable = tables.Column(linkify=True)
    number = tables.Column(linkify=True)
    color = ChoiceFieldColumn()

    class Meta(NetBoxTable.Meta):
        model = Tube
        fields = ("pk", "id", "cable", "number", "color", "description", "tags", "created", "last_updated")
        default_columns = ("cable", "number", "color")


class StrandTable(NetBoxTable):
    cable = tables.Column(linkify=True)
    tube = tables.Column(linkify=True)
    position = tables.Column(linkify=True)
    color = ChoiceFieldColumn()
    status = ChoiceFieldColumn()
    cable_link = tables.Column(linkify=True, verbose_name="dcim.Cable")

    class Meta(NetBoxTable.Meta):
        model = Strand
        fields = (
            "pk", "id", "cable", "tube", "position", "color", "status",
            "cable_link", "description", "tags", "created", "last_updated",
        )
        default_columns = ("cable", "position", "color", "tube", "status", "cable_link")


class SpliceClosureTable(NetBoxTable):
    name = tables.Column(linkify=True)
    closure_type = ChoiceFieldColumn()
    site = tables.Column(linkify=True)
    location = tables.Column(linkify=True)
    status = ChoiceFieldColumn()
    capacity_splices = tables.Column(verbose_name="Capacity")
    utilization_pct = tables.Column(
        accessor="utilization_pct", verbose_name="Util %", orderable=False,
    )

    class Meta(NetBoxTable.Meta):
        model = SpliceClosure
        fields = (
            "pk", "id", "name", "closure_type", "manufacturer", "model",
            "site", "location", "status", "capacity_splices", "utilization_pct",
            "installed_date", "description", "tags", "created", "last_updated",
        )
        default_columns = (
            "name", "closure_type", "site", "status",
            "capacity_splices", "utilization_pct",
        )


class SpliceTrayTable(NetBoxTable):
    closure = tables.Column(linkify=True)
    number = tables.Column(linkify=True)
    used = tables.Column(orderable=False, verbose_name="Used")

    class Meta(NetBoxTable.Meta):
        model = SpliceTray
        fields = ("pk", "id", "closure", "number", "capacity", "used", "description", "tags", "created", "last_updated")
        default_columns = ("closure", "number", "capacity", "used")


class SpliceTable(NetBoxTable):
    tray = tables.Column(linkify=True)
    position = tables.Column(linkify=True)
    splice_type = ChoiceFieldColumn()
    strand_a = tables.Column(linkify=True)
    strand_b = tables.Column(linkify=True)
    loss_db = tables.Column(verbose_name="Loss (dB)")

    class Meta(NetBoxTable.Meta):
        model = Splice
        fields = (
            "pk", "id", "tray", "position", "splice_type", "loss_db",
            "strand_a", "strand_b", "spliced_date", "spliced_by",
            "description", "tags", "created", "last_updated",
        )
        default_columns = ("tray", "position", "splice_type", "strand_a", "strand_b", "loss_db")


class FibreLinkTable(NetBoxTable):
    name = tables.Column(linkify=True)
    status = ChoiceFieldColumn()
    strand_count = tables.Column(orderable=False, verbose_name="Strands")
    total_loss_db = tables.Column(orderable=False, verbose_name="Loss (dB)")
    target_loss_budget_db = tables.Column(verbose_name="Budget (dB)")

    class Meta(NetBoxTable.Meta):
        model = FibreLink
        fields = (
            "pk", "id", "name", "status", "strand_count", "total_loss_db",
            "target_loss_budget_db", "connector_loss_db", "connectors_per_end",
            "description", "tags", "created", "last_updated",
        )
        default_columns = (
            "name", "status", "strand_count", "total_loss_db", "target_loss_budget_db",
        )
