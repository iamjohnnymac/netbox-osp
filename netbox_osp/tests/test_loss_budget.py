"""End-to-end loss-budget arithmetic for FibreLink.

Builds a tiny 1 km cable with two strands, attaches them to a fresh
FibreLink, and asserts the computed strand / connector / total / budget
values match the documented arithmetic:

    strand_loss     = 2 strands x (1.0 km x 0.22 dB/km)         = 0.44 dB
    connector_total = 2 ends x 2 connectors/end x 0.30 dB       = 1.20 dB
    splice_loss     = 0 (no splices in this fixture)
    total_loss      = 0.44 + 1.20 + 0                            = 1.64 dB
    budget_pct      = 1.64 / 10.0 * 100                          ≈ 16.4 %
    band            = "ok"      (pct <= 80)

Then bump connector_loss_db high enough to blow the budget and confirm
the band flips to "fail".
"""
from decimal import Decimal

from utilities.testing import TestCase

from dcim.models import Site

from netbox_osp.models import (
    FibreLink,
    FibreLinkStrand,
    OspCable,
    Strand,
    Tube,
)


class LossBudgetTests(TestCase):
    def setUp(self):
        site_a = Site.objects.create(name="LB Site A", slug="lb-site-a")
        site_b = Site.objects.create(name="LB Site B", slug="lb-site-b")
        # 1000m cable, 0.22 dB/km — clean numbers for the budget arithmetic.
        self.cable = OspCable.objects.create(
            cid="LB-CABLE-001",
            fibre_count=12,
            tube_count=1,
            fibres_per_tube=12,
            length_m=1000,
            attenuation_db_per_km=Decimal("0.220"),
            site_a=site_a,
            site_b=site_b,
        )
        self.tube = Tube.objects.create(cable=self.cable, number=1)
        self.s1 = Strand.objects.create(
            cable=self.cable, tube=self.tube, position=1,
        )
        self.s2 = Strand.objects.create(
            cable=self.cable, tube=self.tube, position=2,
        )

        self.link = FibreLink.objects.create(
            name="LB-LINK-001",
            connector_loss_db=Decimal("0.300"),
            connectors_per_end=2,
            target_loss_budget_db=Decimal("10.000"),
        )
        FibreLinkStrand.objects.create(link=self.link, strand=self.s1, position=1)
        FibreLinkStrand.objects.create(link=self.link, strand=self.s2, position=2)

    def test_strand_loss(self):
        # Each strand: 1.0 km * 0.22 dB/km = 0.22 dB; two strands = 0.44 dB.
        strand_loss = float(self.link.strand_loss_db)
        self.assertAlmostEqual(strand_loss, 0.44, delta=0.001)

    def test_connector_total_loss(self):
        # 2 ends * 2 connectors/end * 0.30 = 1.20 dB
        c_loss = float(self.link.connector_total_loss_db)
        self.assertAlmostEqual(c_loss, 1.20, delta=0.001)

    def test_splice_loss_zero_with_no_splices(self):
        self.assertEqual(float(self.link.splice_loss_db), 0.0)

    def test_total_loss(self):
        total = float(self.link.total_loss_db)
        self.assertAlmostEqual(total, 1.64, delta=0.001)

    def test_budget_pct_ok_band(self):
        pct = float(self.link.loss_budget_pct)
        self.assertAlmostEqual(pct, 16.4, delta=0.05)
        self.assertEqual(self.link.loss_budget_band, "ok")

    def test_budget_band_flips_to_fail_on_high_connector_loss(self):
        # 2 * 2 * 3.0 = 12.0 dB on connectors alone — already over the 10 dB
        # budget without counting strand loss, so the band must be "fail".
        self.link.connector_loss_db = Decimal("3.000")
        self.link.save()
        self.link.refresh_from_db()
        total = float(self.link.total_loss_db)
        self.assertGreater(total, float(self.link.target_loss_budget_db))
        self.assertGreater(float(self.link.loss_budget_pct), 100.0)
        self.assertEqual(self.link.loss_budget_band, "fail")


class LossBudgetGaugeTests(TestCase):
    """The loss_budget_gauge property pre-computes everything the SVG template
    on FibreLink detail needs. viewBox is 200 wide; the 100%-of-target mark
    is at x=133.33; the 80% threshold is at x=106.66; >150% gets clipped to
    the right edge so over-budget links don't render off-canvas.

    We isolate the gauge math from the cables/strands plumbing by patching
    FibreLink.total_loss_db for the lifetime of each test. mock.patch is
    used in preference to a proxy-model trick because the latter would
    register a transient class into Django's app registry and pollute the
    rest of the test suite.
    """

    def _gauge(self, target_db, total_pct):
        """Build a bare FibreLink with `target_loss_budget_db=target_db` and
        return its `loss_budget_gauge` dict while `total_loss_db` is mocked
        to be exactly `total_pct%` of the target."""
        from unittest.mock import PropertyMock, patch

        link = FibreLink(
            name=f"GAUGE-{total_pct}",
            target_loss_budget_db=Decimal(str(target_db)),
        )
        fake_total = (
            Decimal(str(total_pct)) * Decimal(str(target_db)) / Decimal("100")
        )
        with patch.object(
            FibreLink, "total_loss_db",
            new_callable=PropertyMock, return_value=fake_total,
        ):
            return link.loss_budget_gauge

    def test_ok_band(self):
        gauge = self._gauge(target_db=10.0, total_pct=30)
        self.assertEqual(gauge["band"], "ok")
        self.assertEqual(gauge["color"], "#28a745")
        # 30% of 150 = 20% of viewbox width -> 40 viewbox units.
        self.assertAlmostEqual(gauge["width_vb"], 40.0, places=2)
        self.assertAlmostEqual(gauge["pct"], 30.0, places=1)

    def test_warn_band(self):
        gauge = self._gauge(target_db=10.0, total_pct=90)
        self.assertEqual(gauge["band"], "warn")
        self.assertEqual(gauge["color"], "#ffc107")
        # 90% of 150 = 60% of viewbox -> 120 viewbox units.
        self.assertAlmostEqual(gauge["width_vb"], 120.0, places=2)

    def test_fail_band(self):
        gauge = self._gauge(target_db=10.0, total_pct=120)
        self.assertEqual(gauge["band"], "fail")
        self.assertEqual(gauge["color"], "#dc3545")
        # 120% of 150 = 80% of viewbox -> 160 viewbox units.
        self.assertAlmostEqual(gauge["width_vb"], 160.0, places=2)

    def test_fail_band_clipped_at_150_pct(self):
        gauge = self._gauge(target_db=10.0, total_pct=400)
        self.assertEqual(gauge["band"], "fail")
        # 400% gets clipped to 150% -> width_vb == 200 (right edge of viewbox).
        self.assertEqual(gauge["width_vb"], 200.0)
        # But pct still reflects reality so the label reads "400.0%".
        self.assertAlmostEqual(gauge["pct"], 400.0, places=1)

    def test_zero_target_returns_zero_pct(self):
        from unittest.mock import PropertyMock, patch

        link = FibreLink(name="GAUGE-ZERO", target_loss_budget_db=Decimal("0"))
        with patch.object(
            FibreLink, "total_loss_db",
            new_callable=PropertyMock, return_value=Decimal("0"),
        ):
            gauge = link.loss_budget_gauge
        # loss_budget_pct returns 0 when target is 0 — avoid divide-by-zero.
        self.assertAlmostEqual(gauge["pct"], 0.0, places=2)
        self.assertAlmostEqual(gauge["width_vb"], 0.0, places=2)
        self.assertEqual(gauge["band"], "ok")
