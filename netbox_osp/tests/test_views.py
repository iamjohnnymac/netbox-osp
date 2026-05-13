"""UI permission-matrix tests for netbox_osp.

We subclass NetBox's PrimaryObjectViewTestCase, which auto-generates ~24
permission tests per model covering get / list / create / edit / delete and
their bulk variants in three variants each: without permission, with
permission, and with constrained object-level permission.

Per-model notes are inlined where the model's invariants force specific
fixture shapes.
"""
from utilities.testing import ViewTestCases

from netbox_osp.choices import (
    ClosureTypeChoices,
    FibreLinkStatusChoices,
    InstallMethodChoices,
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


class _PluginBaseURLMixin:
    """Override the default base URL pattern for plugin-namespaced models.

    Pattern: 'plugins:<app_label>:<model_name>_<action>'.
    """
    def _get_base_url(self):
        return "plugins:{}:{}_{{}}".format(
            self.model._meta.app_label,
            self.model._meta.model_name,
        )


class OspCableTestCase(_PluginBaseURLMixin, ViewTestCases.PrimaryObjectViewTestCase):
    model = OspCable

    @classmethod
    def setUpTestData(cls):
        site_a, site_b = make_sites(2)
        OspCable.objects.bulk_create([
            OspCable(cid="V-OSP-001", site_a=site_a, site_b=site_b,
                     fibre_count=24, tube_count=2, fibres_per_tube=12),
            OspCable(cid="V-OSP-002", site_a=site_a, site_b=site_b,
                     fibre_count=24, tube_count=2, fibres_per_tube=12),
            OspCable(cid="V-OSP-003", site_a=site_a, site_b=site_b,
                     fibre_count=24, tube_count=2, fibres_per_tube=12),
        ])
        cls.form_data = {
            "cid": "V-OSP-NEW",
            "type": OspCableTypeChoices.TYPE_LOOSE_TUBE,
            "status": OspStatusChoices.STATUS_PLANNED,
            "install_method": InstallMethodChoices.METHOD_DIRECT_BURIED,
            "fibre_count": 48, "tube_count": 4, "fibres_per_tube": 12,
            "attenuation_db_per_km": "0.22",
            "site_a": site_a.pk, "site_b": site_b.pk,
            "description": "View-test cable",
            "comments": "", "tags": [],
        }
        cls.bulk_edit_data = {
            "status": OspStatusChoices.STATUS_ACTIVE,
            "description": "Bulk-edited",
        }
        cls.csv_data = (
            "cid,type,status,fibre_count,tube_count,fibres_per_tube,site_a,site_b",
            f"V-OSP-CSV-1,loose-tube-armoured,planned,24,2,12,{site_a.pk},{site_b.pk}",
            f"V-OSP-CSV-2,loose-tube-armoured,planned,24,2,12,{site_a.pk},{site_b.pk}",
            f"V-OSP-CSV-3,loose-tube-armoured,planned,24,2,12,{site_a.pk},{site_b.pk}",
        )


class TubeTestCase(_PluginBaseURLMixin, ViewTestCases.PrimaryObjectViewTestCase):
    model = Tube

    @classmethod
    def setUpTestData(cls):
        site_a, site_b = make_sites(2)
        cable = make_cable("V-TUBE-CABLE", site_a, site_b,
                           fibre_count=120, tube_count=10, fibres_per_tube=12)
        Tube.objects.bulk_create([
            Tube(cable=cable, number=1),
            Tube(cable=cable, number=2),
            Tube(cable=cable, number=3),
        ])
        cls.form_data = {
            "cable": cable.pk,
            "number": 4,
            "color": "brown",
            "description": "View-test tube",
            "tags": [],
        }
        cls.bulk_edit_data = {"description": "Bulk-edited tube"}
        cls.csv_data = (
            "cable,number,color,description",
            f"{cable.cid},5,slate,",
            f"{cable.cid},6,white,",
            f"{cable.cid},7,red,",
        )


class StrandTestCase(_PluginBaseURLMixin, ViewTestCases.PrimaryObjectViewTestCase):
    model = Strand

    @classmethod
    def setUpTestData(cls):
        site_a, site_b = make_sites(2)
        cable = make_cable("V-STR-CABLE", site_a, site_b,
                           fibre_count=144, tube_count=12, fibres_per_tube=12)
        Tube.objects.create(cable=cable, number=1)
        Strand.objects.bulk_create([
            Strand(cable=cable, position=1),
            Strand(cable=cable, position=2),
            Strand(cable=cable, position=3),
        ])
        cls.form_data = {
            "cable": cable.pk,
            "position": 4,
            "color": "brown",
            "status": StrandStatusChoices.STATUS_SPARE,
            "description": "View-test strand",
            "tags": [],
        }
        cls.bulk_edit_data = {
            "status": StrandStatusChoices.STATUS_IN_USE,
            "description": "Bulk-edited strand",
        }
        cls.csv_data = (
            "cable,position,status,description",
            f"{cable.cid},5,spare,",
            f"{cable.cid},6,spare,",
            f"{cable.cid},7,spare,",
        )


class SpliceClosureTestCase(_PluginBaseURLMixin, ViewTestCases.PrimaryObjectViewTestCase):
    model = SpliceClosure

    @classmethod
    def setUpTestData(cls):
        SpliceClosure.objects.bulk_create([
            SpliceClosure(name="V-CL-001"),
            SpliceClosure(name="V-CL-002"),
            SpliceClosure(name="V-CL-003"),
        ])
        cls.form_data = {
            "name": "V-CL-NEW",
            "closure_type": ClosureTypeChoices.DOME,
            "capacity_splices": 144,
            "status": OspStatusChoices.STATUS_PLANNED,
            "description": "View-test closure",
            "comments": "", "tags": [],
        }
        cls.bulk_edit_data = {
            "status": OspStatusChoices.STATUS_ACTIVE,
            "description": "Bulk-edited closure",
        }
        cls.csv_data = (
            "name,closure_type,capacity_splices,status",
            "V-CL-CSV-1,dome,288,planned",
            "V-CL-CSV-2,dome,288,planned",
            "V-CL-CSV-3,dome,288,planned",
        )


class SpliceTrayTestCase(_PluginBaseURLMixin, ViewTestCases.PrimaryObjectViewTestCase):
    model = SpliceTray

    @classmethod
    def setUpTestData(cls):
        closure = make_closure("V-TRAY-CLO")
        SpliceTray.objects.bulk_create([
            SpliceTray(closure=closure, number=1),
            SpliceTray(closure=closure, number=2),
            SpliceTray(closure=closure, number=3),
        ])
        cls.form_data = {
            "closure": closure.pk,
            "number": 4,
            "capacity": 12,
            "description": "View-test tray",
            "tags": [],
        }
        cls.bulk_edit_data = {"description": "Bulk-edited tray"}
        cls.csv_data = (
            "closure,number,capacity,description",
            f"{closure.name},5,12,",
            f"{closure.name},6,12,",
            f"{closure.name},7,12,",
        )


class SpliceTestCase(_PluginBaseURLMixin, ViewTestCases.PrimaryObjectViewTestCase):
    model = Splice

    @classmethod
    def setUpTestData(cls):
        site_a, site_b = make_sites(2)
        cable = make_cable("V-SP-CABLE", site_a, site_b,
                           fibre_count=12, tube_count=1, fibres_per_tube=12)
        _, strands = make_tubes_and_strands(cable)
        closure = make_closure("V-SP-CLO")
        tray = SpliceTray.objects.create(closure=closure, number=1, capacity=12)
        Splice.objects.bulk_create([
            Splice(tray=tray, position=1, strand_a=strands[0], strand_b=strands[1]),
            Splice(tray=tray, position=2, strand_a=strands[2], strand_b=strands[3]),
            Splice(tray=tray, position=3, strand_a=strands[4], strand_b=strands[5]),
        ])
        cls.form_data = {
            "tray": tray.pk,
            "position": 4,
            "splice_type": SpliceTypeChoices.FUSION,
            "loss_db": "0.10",
            "strand_a": strands[6].pk,
            "strand_b": strands[7].pk,
            "description": "View-test splice",
            "tags": [],
        }
        cls.bulk_edit_data = {"splice_type": SpliceTypeChoices.MECHANICAL}
        cls.csv_data = (
            "tray,position,splice_type,loss_db,strand_a,strand_b",
            f"{tray.pk},5,fusion,0.10,{strands[8].pk},{strands[9].pk}",
            f"{tray.pk},6,fusion,0.10,{strands[10].pk},{strands[11].pk}",
            f"{tray.pk},7,fusion,0.10,{strands[0].pk},{strands[2].pk}",
        )


class FibreLinkTestCase(_PluginBaseURLMixin, ViewTestCases.PrimaryObjectViewTestCase):
    """FibreLink has no bulk_edit/bulk_delete/import URLs registered, so we
    disable the inherited bulk-action tests."""

    model = FibreLink

    test_bulk_edit_objects_without_permission = None
    test_bulk_edit_objects_with_permission = None
    test_bulk_edit_objects_with_constrained_permission = None
    test_bulk_delete_objects_without_permission = None
    test_bulk_delete_objects_with_permission = None
    test_bulk_delete_objects_with_constrained_permission = None
    test_bulk_import_objects_without_permission = None
    test_bulk_import_objects_with_permission = None
    test_bulk_import_objects_with_constrained_permission = None

    @classmethod
    def setUpTestData(cls):
        FibreLink.objects.bulk_create([
            FibreLink(name="V-LINK-001"),
            FibreLink(name="V-LINK-002"),
            FibreLink(name="V-LINK-003"),
        ])
        cls.form_data = {
            "name": "V-LINK-NEW",
            "status": FibreLinkStatusChoices.STATUS_PLANNED,
            "connector_loss_db": "0.30",
            "connectors_per_end": 2,
            "target_loss_budget_db": "10.00",
            "description": "View-test link",
            "comments": "", "tags": [],
        }


class LocationGeoTestCase(_PluginBaseURLMixin, ViewTestCases.PrimaryObjectViewTestCase):
    """LocationGeo has a OneToOneField → Location, so every row needs a
    distinct Location. Pre-create 7 Locations: 3 for existing rows, 1 for
    form_data, 3 for csv_data."""

    model = LocationGeo

    @classmethod
    def setUpTestData(cls):
        (site_a,) = make_sites(1)
        cls.locs = make_locations(site_a, n=7)
        LocationGeo.objects.bulk_create([
            LocationGeo(location=cls.locs[0], latitude="-21.671", longitude="115.013"),
            LocationGeo(location=cls.locs[1], latitude="-21.672", longitude="115.014"),
            LocationGeo(location=cls.locs[2], latitude="-21.673", longitude="115.015"),
        ])
        cls.form_data = {
            "location": cls.locs[3].pk,
            "latitude": "-21.674",
            "longitude": "115.016",
            "marker_color": LocationMarkerColorChoices.RED,
            "description": "View-test LocationGeo",
            "tags": [],
        }
        cls.bulk_edit_data = {"marker_color": LocationMarkerColorChoices.GREEN}
        cls.csv_data = (
            "location,latitude,longitude,marker_color",
            f"{cls.locs[4].slug},-21.675,115.017,#1565c0",
            f"{cls.locs[5].slug},-21.676,115.018,#1565c0",
            f"{cls.locs[6].slug},-21.677,115.019,#1565c0",
        )
