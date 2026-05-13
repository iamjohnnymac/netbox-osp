"""Model-level tests for netbox_osp.

We exercise the small bits of model logic that aren't already covered by
NetBox's generic CRUD machinery:
    - OspCable.save() computes route_length_m from geometry
    - OspCable.clean() rejects fibre_count vs tube_count * fibres_per_tube
    - OspCable.clean() enforces PLUGINS_CONFIG['netbox_osp']['plant_boundary']
      on the cable route when configured, and silently passes when not
    - Tube uniqueness on (cable, number)
    - Strand auto-assigns TIA-598 colour when blank
    - Splice.clean() rejects a strand spliced to itself
    - SpliceClosure.utilization_pct is zero when capacity is zero
"""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import override_settings

from utilities.testing import TestCase

from dcim.models import Manufacturer, Site
from tenancy.models import Tenant

from netbox_osp.choices import TIA598ColorChoices
from netbox_osp.models import (
    OspCable,
    Splice,
    SpliceClosure,
    SpliceTray,
    Strand,
    Tube,
)


def _make_site(name="Site A", slug="site-a"):
    return Site.objects.create(name=name, slug=slug)


def _make_cable(**overrides):
    site_a = overrides.pop("site_a", None) or _make_site("Site A", "site-a")
    site_b = overrides.pop("site_b", None) or _make_site("Site B", "site-b")
    defaults = {
        "cid": "TST-OSP-001",
        "fibre_count": 24,
        "tube_count": 2,
        "fibres_per_tube": 12,
        "site_a": site_a,
        "site_b": site_b,
    }
    defaults.update(overrides)
    return OspCable.objects.create(**defaults)


class OspCableTests(TestCase):
    def test_save_computes_route_length_m(self):
        cable = _make_cable(
            cid="TST-LEN-001",
            route={
                "type": "LineString",
                "coordinates": [
                    [115.013, -21.671],
                    [115.020, -21.675],
                ],
            },
        )
        cable.refresh_from_db()
        self.assertIsNotNone(cable.route_length_m)
        # ~830m for that span — generous bounds keep this stable against
        # any tweak to the equirectangular helper.
        self.assertGreater(cable.route_length_m, 100)
        self.assertLess(cable.route_length_m, 2000)

    def test_save_clears_route_length_when_route_unset(self):
        cable = _make_cable(
            cid="TST-LEN-002",
            route={
                "type": "LineString",
                "coordinates": [
                    [115.013, -21.671],
                    [115.020, -21.675],
                ],
            },
        )
        cable.refresh_from_db()
        self.assertIsNotNone(cable.route_length_m)
        cable.route = None
        cable.save()
        cable.refresh_from_db()
        self.assertIsNone(cable.route_length_m)

    def test_clean_rejects_mismatched_fibre_count(self):
        cable = OspCable(
            cid="TST-BAD-001",
            fibre_count=25,           # 25 != 2 * 12
            tube_count=2,
            fibres_per_tube=12,
            site_a=_make_site("X1", "x1"),
            site_b=_make_site("X2", "x2"),
        )
        with self.assertRaises(ValidationError) as cm:
            cable.clean()
        self.assertIn("fibre_count", cm.exception.message_dict)

    def test_clean_accepts_matching_fibre_count(self):
        cable = OspCable(
            cid="TST-OK-001",
            fibre_count=24,           # 24 == 2 * 12
            tube_count=2,
            fibres_per_tube=12,
            site_a=_make_site("Y1", "y1"),
            site_b=_make_site("Y2", "y2"),
        )
        # Should not raise.
        cable.clean()


# A 1° x 1° square in the [0,0]-[1,1] quadrant used by the boundary tests.
_BOUND_SQUARE_LON_LAT = [
    [0.0, 0.0],
    [1.0, 0.0],
    [1.0, 1.0],
    [0.0, 1.0],
]


@override_settings(PLUGINS_CONFIG={"netbox_osp": {"plant_boundary": _BOUND_SQUARE_LON_LAT}})
class OspCableBoundaryTests(TestCase):
    """OspCable.clean() should honour PLUGINS_CONFIG['netbox_osp']['plant_boundary']
    if configured, and pass through silently if not."""

    def test_route_inside_boundary_ok(self):
        cable = OspCable(
            cid="TST-BND-IN",
            fibre_count=24, tube_count=2, fibres_per_tube=12,
            site_a=_make_site("In1", "in1"),
            site_b=_make_site("In2", "in2"),
            route={"type": "LineString", "coordinates": [[0.25, 0.25], [0.75, 0.75]]},
        )
        cable.clean()       # must not raise

    def test_route_outside_boundary_raises(self):
        cable = OspCable(
            cid="TST-BND-OUT",
            fibre_count=24, tube_count=2, fibres_per_tube=12,
            site_a=_make_site("Out1", "out1"),
            site_b=_make_site("Out2", "out2"),
            route={"type": "LineString", "coordinates": [[0.5, 0.5], [1.5, 1.5]]},
        )
        with self.assertRaises(ValidationError) as cm:
            cable.clean()
        # Error is keyed to the route field so the form surfaces it correctly.
        self.assertIn("route", cm.exception.message_dict)

    def test_no_route_no_validation(self):
        cable = OspCable(
            cid="TST-BND-NORT",
            fibre_count=24, tube_count=2, fibres_per_tube=12,
            site_a=_make_site("Nr1", "nr1"),
            site_b=_make_site("Nr2", "nr2"),
        )
        cable.clean()       # must not raise


@override_settings(PLUGINS_CONFIG={"netbox_osp": {}})
class OspCableNoBoundaryTests(TestCase):
    """If no boundary is configured, OspCable.clean() must not enforce one
    even on wildly out-of-area routes."""

    def test_arbitrary_route_accepted(self):
        cable = OspCable(
            cid="TST-NO-BND",
            fibre_count=24, tube_count=2, fibres_per_tube=12,
            site_a=_make_site("Nb1", "nb1"),
            site_b=_make_site("Nb2", "nb2"),
            route={"type": "LineString", "coordinates": [[-150.0, -85.0], [150.0, 85.0]]},
        )
        cable.clean()       # must not raise


class LocationGeoTests(TestCase):
    """Model-level checks for the per-Location GPS side-table."""

    def _make_location(self, name="LG-Loc-1", slug="lg-loc-1"):
        from dcim.models import Location
        site = _make_site("LG Site", "lg-site")
        return Location.objects.create(name=name, slug=slug, site=site)

    def test_lat_lon_must_be_set_together(self):
        from netbox_osp.models import LocationGeo
        from decimal import Decimal
        loc = self._make_location()
        with self.assertRaises(ValidationError):
            LocationGeo(location=loc, latitude=Decimal("-31.95"), longitude=None).clean()
        with self.assertRaises(ValidationError):
            LocationGeo(location=loc, latitude=None, longitude=Decimal("115.86")).clean()
        # Both set -> ok
        LocationGeo(
            location=loc,
            latitude=Decimal("-31.95"),
            longitude=Decimal("115.86"),
        ).clean()
        # Both null -> ok (placeholder row)
        LocationGeo(location=loc).clean()

    def test_lat_out_of_range_rejected(self):
        from netbox_osp.models import LocationGeo
        from decimal import Decimal
        loc = self._make_location(name="LG-Loc-2", slug="lg-loc-2")
        with self.assertRaises(ValidationError) as cm:
            LocationGeo(
                location=loc, latitude=Decimal("91"), longitude=Decimal("0"),
            ).clean()
        self.assertIn("latitude", cm.exception.message_dict)

    def test_lon_out_of_range_rejected(self):
        from netbox_osp.models import LocationGeo
        from decimal import Decimal
        loc = self._make_location(name="LG-Loc-3", slug="lg-loc-3")
        with self.assertRaises(ValidationError) as cm:
            LocationGeo(
                location=loc, latitude=Decimal("0"), longitude=Decimal("181"),
            ).clean()
        self.assertIn("longitude", cm.exception.message_dict)

    def test_one_to_one_uniqueness(self):
        from netbox_osp.models import LocationGeo
        from decimal import Decimal
        loc = self._make_location(name="LG-Loc-4", slug="lg-loc-4")
        LocationGeo.objects.create(
            location=loc, latitude=Decimal("-31"), longitude=Decimal("115"),
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LocationGeo.objects.create(
                    location=loc, latitude=Decimal("-32"), longitude=Decimal("116"),
                )

    def test_has_coords_property(self):
        from netbox_osp.models import LocationGeo
        from decimal import Decimal
        loc = self._make_location(name="LG-Loc-5", slug="lg-loc-5")
        geo = LocationGeo.objects.create(location=loc)
        self.assertFalse(geo.has_coords)
        geo.latitude = Decimal("-31.95")
        geo.longitude = Decimal("115.86")
        geo.save()
        self.assertTrue(geo.has_coords)


class TubeTests(TestCase):
    def test_unique_together_cable_and_number(self):
        cable = _make_cable(cid="TST-UNIQ-001")
        Tube.objects.create(cable=cable, number=1)
        # A second tube with the same (cable, number) must fail at the DB
        # layer; wrap in an atomic block so the connection survives.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tube.objects.create(cable=cable, number=1)

    def test_auto_color_when_unset(self):
        cable = _make_cable(cid="TST-TUBE-COL")
        tube = Tube.objects.create(cable=cable, number=1)
        self.assertEqual(tube.color, TIA598ColorChoices.BLUE)
        tube2 = Tube.objects.create(cable=cable, number=2)
        self.assertEqual(tube2.color, TIA598ColorChoices.ORANGE)


class StrandTests(TestCase):
    def test_auto_color_from_position(self):
        cable = _make_cable(cid="TST-STR-001")
        Tube.objects.create(cable=cable, number=1)
        strand1 = Strand.objects.create(cable=cable, position=1)
        self.assertEqual(strand1.color, TIA598ColorChoices.BLUE)
        strand2 = Strand.objects.create(cable=cable, position=2)
        self.assertEqual(strand2.color, TIA598ColorChoices.ORANGE)
        # Position 13 wraps back to BLUE.
        strand13 = Strand.objects.create(cable=cable, position=13)
        self.assertEqual(strand13.color, TIA598ColorChoices.BLUE)

    def test_explicit_color_preserved(self):
        cable = _make_cable(cid="TST-STR-002")
        Tube.objects.create(cable=cable, number=1)
        strand = Strand.objects.create(
            cable=cable, position=1, color=TIA598ColorChoices.RED,
        )
        self.assertEqual(strand.color, TIA598ColorChoices.RED)


class SpliceTests(TestCase):
    def _setup(self):
        cable = _make_cable(cid="TST-SPL-001")
        tube = Tube.objects.create(cable=cable, number=1)
        s1 = Strand.objects.create(cable=cable, tube=tube, position=1)
        s2 = Strand.objects.create(cable=cable, tube=tube, position=2)
        closure = SpliceClosure.objects.create(name="TST-CLO-001")
        tray = SpliceTray.objects.create(closure=closure, number=1)
        return s1, s2, tray

    def test_clean_rejects_self_splice(self):
        s1, _s2, tray = self._setup()
        splice = Splice(
            tray=tray,
            position=1,
            strand_a=s1,
            strand_b=s1,
        )
        with self.assertRaises(ValidationError):
            splice.clean()

    def test_clean_accepts_distinct_strands(self):
        s1, s2, tray = self._setup()
        splice = Splice(
            tray=tray,
            position=1,
            strand_a=s1,
            strand_b=s2,
        )
        # Should not raise.
        splice.clean()


class SpliceClosureTests(TestCase):
    def test_utilization_zero_when_capacity_zero(self):
        closure = SpliceClosure.objects.create(
            name="TST-CAP-0",
            capacity_splices=0,
        )
        self.assertEqual(closure.utilization_pct, 0)

    def test_utilization_zero_with_default_capacity_and_no_splices(self):
        # capacity=288, used=0 -> 0%
        closure = SpliceClosure.objects.create(name="TST-CAP-EMPTY")
        self.assertEqual(closure.utilization_pct, 0)
