"""Tests for the CSV bulk-import forms.

Covers the five new ImportForm classes added in 0.1.0.dev0:
SpliceClosureImportForm, TubeImportForm, StrandImportForm,
SpliceTrayImportForm, SpliceImportForm. (OspCableImportForm existed
prior and is exercised indirectly by test_models.py.)
"""
from utilities.testing import TestCase

from netbox_osp.forms import (
    LocationGeoImportForm,
    SpliceClosureImportForm,
    SpliceImportForm,
    SpliceTrayImportForm,
    StrandImportForm,
    TubeImportForm,
)
from netbox_osp.models import (
    LocationGeo,
    Splice,
    SpliceClosure,
    SpliceTray,
    Strand,
    Tube,
)
from netbox_osp.tests.test_models import _make_cable, _make_site


class TubeImportTests(TestCase):
    def test_happy_path_three_rows(self):
        cable = _make_cable(cid="IMP-TUBE-001", tube_count=3, fibre_count=36, fibres_per_tube=12)
        rows = [
            {"cable": cable.cid, "number": 1, "color": "blue", "description": ""},
            {"cable": cable.cid, "number": 2, "color": "orange", "description": ""},
            {"cable": cable.cid, "number": 3, "color": "", "description": "spare"},
        ]
        for row in rows:
            form = TubeImportForm(data=row)
            self.assertTrue(form.is_valid(), form.errors)
            form.save()
        self.assertEqual(Tube.objects.filter(cable=cable).count(), 3)

    def test_rejects_duplicate_number(self):
        cable = _make_cable(cid="IMP-TUBE-002", tube_count=2)
        Tube.objects.create(cable=cable, number=1)
        form = TubeImportForm(data={"cable": cable.cid, "number": 1})
        self.assertFalse(form.is_valid())
        self.assertIn("number", form.errors)

    def test_rejects_missing_cable(self):
        form = TubeImportForm(data={"cable": "DOES-NOT-EXIST", "number": 1})
        self.assertFalse(form.is_valid())
        self.assertIn("cable", form.errors)

    def test_rejects_number_exceeds_tube_count(self):
        cable = _make_cable(cid="IMP-TUBE-003", tube_count=2)
        form = TubeImportForm(data={"cable": cable.cid, "number": 5})
        self.assertFalse(form.is_valid())
        self.assertIn("number", form.errors)


class StrandImportTests(TestCase):
    def test_happy_path_with_auto_tube(self):
        cable = _make_cable(cid="IMP-STR-001")
        Tube.objects.create(cable=cable, number=1)
        for pos in (1, 2, 3):
            form = StrandImportForm(data={"cable": cable.cid, "position": pos})
            self.assertTrue(form.is_valid(), form.errors)
            form.save()
        self.assertEqual(Strand.objects.filter(cable=cable).count(), 3)

    def test_rejects_position_exceeds_fibre_count(self):
        cable = _make_cable(cid="IMP-STR-002", fibre_count=24)
        form = StrandImportForm(data={"cable": cable.cid, "position": 25})
        self.assertFalse(form.is_valid())
        self.assertIn("position", form.errors)

    def test_rejects_tube_wrong_cable(self):
        cable_a = _make_cable(
            cid="IMP-STR-A",
            site_a=_make_site("StrA-A", "stra-a"),
            site_b=_make_site("StrA-B", "stra-b"),
        )
        cable_b = _make_cable(
            cid="IMP-STR-B",
            site_a=_make_site("StrB-A", "strb-a"),
            site_b=_make_site("StrB-B", "strb-b"),
        )
        tube_b = Tube.objects.create(cable=cable_b, number=1)
        form = StrandImportForm(data={
            "cable": cable_a.cid,
            "tube": tube_b.pk,
            "position": 1,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("tube", form.errors)


class LocationGeoImportTests(TestCase):
    def _make_location(self, name, slug):
        from dcim.models import Location
        site = _make_site(name=f"{name}-site", slug=f"{slug}-site")
        return Location.objects.create(name=name, slug=slug, site=site)

    def test_happy_path(self):
        loc = self._make_location("IMP-LOC-1", "imp-loc-1")
        form = LocationGeoImportForm(data={
            "location": loc.slug,
            "latitude": "-31.95",
            "longitude": "115.86",
            "marker_color": "#1565c0",
        })
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertEqual(LocationGeo.objects.filter(location=loc).count(), 1)

    def test_rejects_duplicate_location(self):
        loc = self._make_location("IMP-LOC-2", "imp-loc-2")
        LocationGeo.objects.create(location=loc)
        form = LocationGeoImportForm(data={
            "location": loc.slug,
            "latitude": "-31.95",
            "longitude": "115.86",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("location", form.errors)


class SpliceClosureImportTests(TestCase):
    def test_happy_path(self):
        for i in (1, 2, 3):
            form = SpliceClosureImportForm(data={
                "name": f"IMP-CLO-{i:03d}",
                "closure_type": "dome",
                "capacity_splices": 144,
                "status": "active",
            })
            self.assertTrue(form.is_valid(), form.errors)
            form.save()
        self.assertEqual(SpliceClosure.objects.filter(name__startswith="IMP-CLO-").count(), 3)

    def test_rejects_duplicate_name(self):
        SpliceClosure.objects.create(name="IMP-CLO-DUP")
        form = SpliceClosureImportForm(data={"name": "IMP-CLO-DUP", "closure_type": "dome"})
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)


class SpliceTrayImportTests(TestCase):
    def test_happy_path(self):
        closure = SpliceClosure.objects.create(name="IMP-CLO-001")
        for n in (1, 2, 3):
            form = SpliceTrayImportForm(data={"closure": closure.name, "number": n, "capacity": 12})
            self.assertTrue(form.is_valid(), form.errors)
            form.save()
        self.assertEqual(SpliceTray.objects.filter(closure=closure).count(), 3)

    def test_rejects_duplicate_number(self):
        closure = SpliceClosure.objects.create(name="IMP-CLO-002")
        SpliceTray.objects.create(closure=closure, number=1)
        form = SpliceTrayImportForm(data={"closure": closure.name, "number": 1})
        self.assertFalse(form.is_valid())
        self.assertIn("number", form.errors)


class SpliceImportTests(TestCase):
    def _bootstrap(self, cid_suffix):
        """Build a cable + 2 strands + closure + tray for splice tests."""
        cable = _make_cable(cid=f"IMP-SPL-{cid_suffix}")
        tube = Tube.objects.create(cable=cable, number=1)
        s1 = Strand.objects.create(cable=cable, tube=tube, position=1)
        s2 = Strand.objects.create(cable=cable, tube=tube, position=2)
        closure = SpliceClosure.objects.create(name=f"IMP-SPL-CLO-{cid_suffix}")
        tray = SpliceTray.objects.create(closure=closure, number=1, capacity=12)
        return s1, s2, tray

    def test_happy_path(self):
        s1, s2, tray = self._bootstrap("001")
        form = SpliceImportForm(data={
            "tray": tray.pk,
            "position": 1,
            "splice_type": "fusion",
            "loss_db": "0.10",
            "strand_a": s1.pk,
            "strand_b": s2.pk,
        })
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertEqual(Splice.objects.filter(tray=tray).count(), 1)

    def test_rejects_self_splice(self):
        s1, _s2, tray = self._bootstrap("002")
        form = SpliceImportForm(data={
            "tray": tray.pk,
            "position": 1,
            "strand_a": s1.pk,
            "strand_b": s1.pk,
        })
        self.assertFalse(form.is_valid())

    def test_rejects_position_exceeds_capacity(self):
        s1, s2, tray = self._bootstrap("003")
        tray.capacity = 6
        tray.save()
        form = SpliceImportForm(data={
            "tray": tray.pk,
            "position": 7,
            "strand_a": s1.pk,
            "strand_b": s2.pk,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("position", form.errors)

    def test_rejects_duplicate_position_in_tray(self):
        s1, s2, tray = self._bootstrap("004")
        Splice.objects.create(tray=tray, position=1, strand_a=s1, strand_b=s2)
        # Make another strand pair for the duplicate-position attempt
        cable2 = _make_cable(
            cid="IMP-SPL-DUP-CBL",
            site_a=_make_site("DupA", "dup-a"),
            site_b=_make_site("DupB", "dup-b"),
        )
        tube2 = Tube.objects.create(cable=cable2, number=1)
        s3 = Strand.objects.create(cable=cable2, tube=tube2, position=1)
        s4 = Strand.objects.create(cable=cable2, tube=tube2, position=2)
        form = SpliceImportForm(data={
            "tray": tray.pk,
            "position": 1,           # collision with the existing splice
            "strand_a": s3.pk,
            "strand_b": s4.pk,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("position", form.errors)
