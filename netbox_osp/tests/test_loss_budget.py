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
