"""REST API permission-matrix tests for netbox_osp.

APIViewTestCases.APIViewTestCase auto-generates ~12 permission tests per
model covering get / list / create / update / delete for the REST endpoints
under /api/plugins/osp/<plural>/.

Note: NetBox's APITestCase setUp creates a v1 (plaintext) Token, so the
API_TOKEN_PEPPERS setting only required for v2 tokens does NOT need to be
defined in the CI configuration.
"""
from utilities.testing import APIViewTestCases

from netbox_osp.choices import (
    ClosureTypeChoices,
    FibreLinkStatusChoices,
    LocationMarkerColorChoices,
    OspCableTypeChoices,
    OspStatusChoices,
    SpliceTypeChoices,
    StrandStatusChoices,
)
from netbox_osp.models import (
    FibreLink,
    LocationGeo,
    OspCable,
    Splice,
    SpliceClosure,
    SpliceTray,
    Strand,
    Tube,
)
from netbox_osp.tests._fixtures import (
    make_cable,
    make_closure,
    make_locations,
    make_sites,
    make_tubes_and_strands,
)


class _OSPAPITestCase(APIViewTestCases.APIViewTestCase):
    """Shared base — every netbox_osp REST viewset lives under this namespace."""

    view_namespace = "plugins-api:netbox_osp"


class OspCableAPITestCase(_OSPAPITestCase):
    model = OspCable
    brief_fields = ["cid", "display", "id", "status", "url"]
    user_permissions = ("dcim.view_site",)
    bulk_update_data = {"status": OspStatusChoices.STATUS_ACTIVE}

    @classmethod
    def setUpTestData(cls):
        site_a, site_b = make_sites(2)
        OspCable.objects.bulk_create([
            OspCable(cid="API-OSP-001", site_a=site_a, site_b=site_b,
                     fibre_count=24, tube_count=2, fibres_per_tube=12),
            OspCable(cid="API-OSP-002", site_a=site_a, site_b=site_b,
                     fibre_count=24, tube_count=2, fibres_per_tube=12),
            OspCable(cid="API-OSP-003", site_a=site_a, site_b=site_b,
                     fibre_count=24, tube_count=2, fibres_per_tube=12),
        ])
        cls.create_data = [
            {"cid": "API-OSP-NEW-1", "site_a": site_a.pk, "site_b": site_b.pk,
             "fibre_count": 24, "tube_count": 2, "fibres_per_tube": 12,
             "type": OspCableTypeChoices.TYPE_LOOSE_TUBE,
             "status": OspStatusChoices.STATUS_PLANNED},
            {"cid": "API-OSP-NEW-2", "site_a": site_a.pk, "site_b": site_b.pk,
             "fibre_count": 24, "tube_count": 2, "fibres_per_tube": 12,
             "type": OspCableTypeChoices.TYPE_LOOSE_TUBE,
             "status": OspStatusChoices.STATUS_PLANNED},
            {"cid": "API-OSP-NEW-3", "site_a": site_a.pk, "site_b": site_b.pk,
             "fibre_count": 24, "tube_count": 2, "fibres_per_tube": 12,
             "type": OspCableTypeChoices.TYPE_LOOSE_TUBE,
             "status": OspStatusChoices.STATUS_PLANNED},
        ]


class TubeAPITestCase(_OSPAPITestCase):
    model = Tube
    brief_fields = ["color", "display", "id", "number", "url"]
    user_permissions = ("netbox_osp.view_ospcable",)
    bulk_update_data = {"description": "Bulk-updated tube"}

    @classmethod
    def setUpTestData(cls):
        site_a, site_b = make_sites(2)
        cable = make_cable("API-TUBE-CABLE", site_a, site_b,
                           fibre_count=120, tube_count=10, fibres_per_tube=12)
        Tube.objects.bulk_create([
            Tube(cable=cable, number=1),
            Tube(cable=cable, number=2),
            Tube(cable=cable, number=3),
        ])
        cls.create_data = [
            {"cable": cable.pk, "number": 4},
            {"cable": cable.pk, "number": 5},
            {"cable": cable.pk, "number": 6},
        ]


class StrandAPITestCase(_OSPAPITestCase):
    model = Strand
    brief_fields = ["color", "display", "id", "position", "status", "url"]
    user_permissions = ("netbox_osp.view_ospcable",)
    bulk_update_data = {"status": StrandStatusChoices.STATUS_IN_USE}

    @classmethod
    def setUpTestData(cls):
        site_a, site_b = make_sites(2)
        cable = make_cable("API-STR-CABLE", site_a, site_b,
                           fibre_count=144, tube_count=12, fibres_per_tube=12)
        Tube.objects.create(cable=cable, number=1)
        Strand.objects.bulk_create([
            Strand(cable=cable, position=1),
            Strand(cable=cable, position=2),
            Strand(cable=cable, position=3),
        ])
        cls.create_data = [
            {"cable": cable.pk, "position": 4},
            {"cable": cable.pk, "position": 5},
            {"cable": cable.pk, "position": 6},
        ]


class SpliceClosureAPITestCase(_OSPAPITestCase):
    model = SpliceClosure
    brief_fields = ["display", "id", "name", "status", "url"]
    bulk_update_data = {"status": OspStatusChoices.STATUS_ACTIVE}

    @classmethod
    def setUpTestData(cls):
        SpliceClosure.objects.bulk_create([
            SpliceClosure(name="API-CL-001"),
            SpliceClosure(name="API-CL-002"),
            SpliceClosure(name="API-CL-003"),
        ])
        cls.create_data = [
            {"name": "API-CL-NEW-1", "closure_type": ClosureTypeChoices.DOME,
             "capacity_splices": 288, "status": OspStatusChoices.STATUS_PLANNED},
            {"name": "API-CL-NEW-2", "closure_type": ClosureTypeChoices.DOME,
             "capacity_splices": 288, "status": OspStatusChoices.STATUS_PLANNED},
            {"name": "API-CL-NEW-3", "closure_type": ClosureTypeChoices.DOME,
             "capacity_splices": 288, "status": OspStatusChoices.STATUS_PLANNED},
        ]


class SpliceTrayAPITestCase(_OSPAPITestCase):
    model = SpliceTray
    brief_fields = ["display", "id", "number", "url"]
    user_permissions = ("netbox_osp.view_spliceclosure",)
    bulk_update_data = {"description": "Bulk-updated tray"}

    @classmethod
    def setUpTestData(cls):
        closure = make_closure("API-CL-TRAY")
        SpliceTray.objects.bulk_create([
            SpliceTray(closure=closure, number=1),
            SpliceTray(closure=closure, number=2),
            SpliceTray(closure=closure, number=3),
        ])
        cls.create_data = [
            {"closure": closure.pk, "number": 4, "capacity": 12},
            {"closure": closure.pk, "number": 5, "capacity": 12},
            {"closure": closure.pk, "number": 6, "capacity": 12},
        ]


class SpliceAPITestCase(_OSPAPITestCase):
    model = Splice
    brief_fields = ["display", "id", "position", "splice_type", "url"]
    user_permissions = (
        "netbox_osp.view_splicetray", "netbox_osp.view_strand",
    )
    bulk_update_data = {"splice_type": SpliceTypeChoices.MECHANICAL}

    @classmethod
    def setUpTestData(cls):
        site_a, site_b = make_sites(2)
        cable = make_cable("API-SP-CABLE", site_a, site_b,
                           fibre_count=12, tube_count=1, fibres_per_tube=12)
        _, strands = make_tubes_and_strands(cable)
        closure = make_closure("API-CL-SP")
        tray = SpliceTray.objects.create(closure=closure, number=1, capacity=12)
        Splice.objects.bulk_create([
            Splice(tray=tray, position=1, strand_a=strands[0], strand_b=strands[1]),
            Splice(tray=tray, position=2, strand_a=strands[2], strand_b=strands[3]),
            Splice(tray=tray, position=3, strand_a=strands[4], strand_b=strands[5]),
        ])
        cls.create_data = [
            {"tray": tray.pk, "position": 4,
             "strand_a": strands[6].pk, "strand_b": strands[7].pk},
            {"tray": tray.pk, "position": 5,
             "strand_a": strands[8].pk, "strand_b": strands[9].pk},
            {"tray": tray.pk, "position": 6,
             "strand_a": strands[10].pk, "strand_b": strands[11].pk},
        ]


class FibreLinkAPITestCase(_OSPAPITestCase):
    model = FibreLink
    brief_fields = ["display", "id", "name", "status", "url"]
    bulk_update_data = {"status": FibreLinkStatusChoices.STATUS_ACTIVE}

    @classmethod
    def setUpTestData(cls):
        FibreLink.objects.bulk_create([
            FibreLink(name="API-LINK-001"),
            FibreLink(name="API-LINK-002"),
            FibreLink(name="API-LINK-003"),
        ])
        cls.create_data = [
            {"name": "API-LINK-NEW-1",
             "status": FibreLinkStatusChoices.STATUS_PLANNED,
             "connector_loss_db": "0.30", "connectors_per_end": 2,
             "target_loss_budget_db": "10.00"},
            {"name": "API-LINK-NEW-2",
             "status": FibreLinkStatusChoices.STATUS_PLANNED,
             "connector_loss_db": "0.30", "connectors_per_end": 2,
             "target_loss_budget_db": "10.00"},
            {"name": "API-LINK-NEW-3",
             "status": FibreLinkStatusChoices.STATUS_PLANNED,
             "connector_loss_db": "0.30", "connectors_per_end": 2,
             "target_loss_budget_db": "10.00"},
        ]


class LocationGeoAPITestCase(_OSPAPITestCase):
    model = LocationGeo
    brief_fields = ["display", "id", "location", "url"]
    user_permissions = ("dcim.view_location",)
    bulk_update_data = {"marker_color": LocationMarkerColorChoices.GREEN}

    @classmethod
    def setUpTestData(cls):
        (site_a,) = make_sites(1)
        locs = make_locations(site_a, n=7)
        LocationGeo.objects.bulk_create([
            LocationGeo(location=locs[0], latitude="-21.671", longitude="115.013"),
            LocationGeo(location=locs[1], latitude="-21.672", longitude="115.014"),
            LocationGeo(location=locs[2], latitude="-21.673", longitude="115.015"),
        ])
        cls.create_data = [
            {"location": locs[3].pk, "latitude": "-21.674", "longitude": "115.016"},
            {"location": locs[4].pk, "latitude": "-21.675", "longitude": "115.017"},
            {"location": locs[5].pk, "latitude": "-21.676", "longitude": "115.018"},
        ]
