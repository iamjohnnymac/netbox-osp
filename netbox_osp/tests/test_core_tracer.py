"""Tests for the visual core tracer added in PR E of the v0.2.0 cycle.

Coverage (per the v0.2.0 PR-E spec):
1. Trace endpoint returns 200 for a strand with both terminations.
2. Trace JSON shape — keys present.
3. Walking through a splice produces 2+ strand hops.
4. Strand with no terminations returns an "incomplete" trace.
5. Loss math sums correctly across hops.
6. Template extension renders the "Trace this core" button on Strand
   detail.
7. Anonymous user gets 403 / redirect on the trace view.

The tracer logic itself lives in `netbox_osp.tracer` and is exercised
both directly (model-level) and through the REST + UI views.
"""
from __future__ import annotations

from decimal import Decimal

from django.test import TestCase as DjangoTestCase, override_settings
from django.urls import reverse
from rest_framework import status

from dcim.models import Site
from utilities.testing import APITestCase, TestCase

from netbox_osp.models import (
    OspCable,
    Splice,
    SpliceClosure,
    SpliceTray,
    Strand,
    Tube,
)
from netbox_osp.tracer import trace_strand


# ============================================================================
# Fixtures
# ============================================================================

def _make_universe(prefix="CT"):
    """Build a two-cable / two-strand topology bridged by a splice.

    Returns the start strand (a-side cable) plus references to all the
    pieces so individual tests can mix-and-match.
    """
    site_a = Site.objects.create(name=f"{prefix} Site A", slug=f"{prefix.lower()}-site-a")
    site_b = Site.objects.create(name=f"{prefix} Site B", slug=f"{prefix.lower()}-site-b")

    cable_a = OspCable.objects.create(
        cid=f"{prefix}-OSP-A",
        fibre_count=12, tube_count=1, fibres_per_tube=12,
        length_m=1000,
        attenuation_db_per_km=Decimal("0.220"),
        site_a=site_a, site_b=site_b,
    )
    cable_b = OspCable.objects.create(
        cid=f"{prefix}-OSP-B",
        fibre_count=12, tube_count=1, fibres_per_tube=12,
        length_m=2500,
        attenuation_db_per_km=Decimal("0.220"),
        site_a=site_a, site_b=site_b,
    )
    Tube.objects.create(cable=cable_a, number=1)
    Tube.objects.create(cable=cable_b, number=1)
    strand_a = Strand.objects.create(cable=cable_a, position=1)
    strand_b = Strand.objects.create(cable=cable_b, position=1)

    closure = SpliceClosure.objects.create(name=f"{prefix}-CL-001")
    tray = SpliceTray.objects.create(closure=closure, number=1)
    splice = Splice.objects.create(
        tray=tray, position=1,
        strand_a=strand_a, strand_b=strand_b,
        loss_db=Decimal("0.080"),
    )
    return {
        "start": strand_a,
        "strand_a": strand_a,
        "strand_b": strand_b,
        "cable_a": cable_a,
        "cable_b": cable_b,
        "splice": splice,
    }


# ============================================================================
# Unit tests: pure trace_strand() logic
# ============================================================================

class TraceStrandLogicTests(TestCase):
    """Direct calls into the pure traversal — no HTTP involved."""

    def test_trace_returns_dict_with_required_keys(self):
        u = _make_universe(prefix="LOGIC1")
        result = trace_strand(u["start"])
        for key in (
            "strand_id", "hops", "total_loss_db",
            "target_loss_budget_db", "loss_pct", "band", "incomplete",
        ):
            self.assertIn(key, result, f"missing key {key!r}")
        self.assertEqual(result["strand_id"], u["start"].pk)
        self.assertIsInstance(result["hops"], list)

    def test_walk_through_splice_yields_two_strand_hops(self):
        u = _make_universe(prefix="SPL1")
        result = trace_strand(u["start"])
        strand_hops = [h for h in result["hops"] if h["kind"] == "osp_strand"]
        self.assertGreaterEqual(
            len(strand_hops), 2,
            f"expected 2 osp_strand hops, got {len(strand_hops)}: "
            f"{[h['label'] for h in result['hops']]}",
        )

    def test_splice_hop_present_between_strands(self):
        u = _make_universe(prefix="SPL2")
        hops = trace_strand(u["start"])["hops"]
        kinds = [h["kind"] for h in hops]
        # Expect the sequence to include osp_strand, splice, osp_strand
        # somewhere in order.
        try:
            i = kinds.index("osp_strand")
            j = kinds.index("splice", i)
            k = kinds.index("osp_strand", j)
        except ValueError:
            self.fail(f"missing strand→splice→strand sequence in hops: {kinds}")
        self.assertLess(i, j)
        self.assertLess(j, k)

    def test_strand_without_terminations_is_marked_incomplete(self):
        site_a = Site.objects.create(name="Iso A", slug="iso-a")
        site_b = Site.objects.create(name="Iso B", slug="iso-b")
        cable = OspCable.objects.create(
            cid="ISO-001",
            fibre_count=12, tube_count=1, fibres_per_tube=12,
            length_m=500, site_a=site_a, site_b=site_b,
        )
        strand = Strand.objects.create(cable=cable, position=1)
        result = trace_strand(strand)
        self.assertTrue(result["incomplete"])
        # Hops still emitted — at least the strand itself.
        self.assertGreaterEqual(len(result["hops"]), 1)
        self.assertEqual(result["hops"][-1]["kind"], "osp_strand")

    def test_loss_math_sums_correctly(self):
        # cable_a 1000m × 0.22 dB/km = 0.22 dB
        # splice 0.080 dB
        # cable_b 2500m × 0.22 dB/km = 0.55 dB
        # total = 0.85 dB
        u = _make_universe(prefix="LOSS1")
        result = trace_strand(u["start"])
        summed = sum(h["loss_db"] for h in result["hops"])
        self.assertAlmostEqual(summed, result["total_loss_db"], places=3)
        self.assertAlmostEqual(result["total_loss_db"], 0.85, delta=0.005)

    def test_band_ok_for_low_loss(self):
        u = _make_universe(prefix="BAND1")
        result = trace_strand(u["start"])
        # 0.85 dB / 8 dB budget = ~10.6% → "ok"
        self.assertEqual(result["band"], "ok")
        self.assertLess(result["loss_pct"], 80)

    @override_settings(PLUGINS_CONFIG={
        "netbox_osp": {
            "default_attenuation_db_per_km": 0.22,
            "default_splice_loss_db": 0.10,
            "default_connector_loss_db": 0.30,
            "default_cassette_loss_db": 0.5,
            "default_patch_cord_loss_db": 0.1,
            "default_loss_budget_db": 0.5,
        },
    })
    def test_band_flips_to_fail_when_budget_tight(self):
        u = _make_universe(prefix="BAND2")
        result = trace_strand(u["start"])
        # 0.85 dB over a 0.5 dB budget = 170% → "fail"
        self.assertEqual(result["band"], "fail")
        self.assertGreater(result["loss_pct"], 100)


# ============================================================================
# Integration: trace JSON endpoint
# ============================================================================

class TraceEndpointTests(APITestCase):
    """`GET /api/plugins/osp/cores/<id>/trace/` integration tests."""

    def _url(self, pk):
        return f"/api/plugins/osp/cores/{pk}/trace/"

    def test_unauthenticated_request_is_rejected(self):
        u = _make_universe(prefix="EP1")
        self.client.logout()
        resp = self.client.get(self._url(u["start"].pk), format="json")
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_authenticated_request_returns_200(self):
        u = _make_universe(prefix="EP2")
        resp = self.client.get(self._url(u["start"].pk), **self.header)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

    def test_json_shape(self):
        u = _make_universe(prefix="EP3")
        resp = self.client.get(self._url(u["start"].pk), **self.header)
        body = resp.json()
        self.assertEqual(body["strand_id"], u["start"].pk)
        self.assertIn("hops", body)
        self.assertIn("total_loss_db", body)
        self.assertIn("target_loss_budget_db", body)
        self.assertIn("loss_pct", body)
        self.assertIn("band", body)
        # Each hop has at least kind/label.
        for h in body["hops"]:
            self.assertIn("kind", h)
            self.assertIn("label", h)

    def test_404_on_unknown_strand(self):
        resp = self.client.get(self._url(999_999_999), **self.header)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# ============================================================================
# Integration: full-page tracer view
# ============================================================================

class StrandTraceViewTests(DjangoTestCase):
    """`GET /plugins/osp/strands/<id>/trace/` HTML view tests."""

    @classmethod
    def setUpTestData(cls):
        cls.universe = _make_universe(prefix="VIEW1")

    def test_anonymous_user_is_redirected_to_login(self):
        # LoginRequiredMixin redirects unauthenticated GETs to /login/?next=…
        self.client.logout()
        url = reverse(
            "plugins:netbox_osp:strand_trace",
            args=[self.universe["start"].pk],
        )
        resp = self.client.get(url)
        # NetBox uses LoginRequiredMixin's default 302 redirect for HTML
        # views; some installs (with custom auth back-ends) might 403.
        # Either is acceptable for this test.
        self.assertIn(resp.status_code, (302, 403))

    def test_authenticated_user_sees_trace_page(self):
        # Reuse NetBox's TestCase pre-wired user (avoids the custom
        # create_user signature on NetBox 4.6's User model).
        from utilities.testing import create_test_user

        self.client.force_login(create_test_user("trace-tester"))
        url = reverse(
            "plugins:netbox_osp:strand_trace",
            args=[self.universe["start"].pk],
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "osp-tracer")
        self.assertContains(resp, "OSP_TRACE_URL")


# ============================================================================
# Template-content integration
# ============================================================================

class TraceButtonTemplateExtensionTests(DjangoTestCase):
    """The PluginTemplateExtension subclasses inject the trace button on
    dcim.Interface, dcim.FrontPort, and netbox-osp Strand detail pages.

    Strand detail also embeds the partial directly via {% include %}, so
    we can assert the button anchor href appears on the rendered HTML
    without needing the PluginTemplateExtension hook to fire (which
    requires NetBox's plugin loader to have wired the extensions into
    the template-tag registry at process start-up — true in production,
    not always true in DjangoTestCase isolation).
    """

    @classmethod
    def setUpTestData(cls):
        cls.universe = _make_universe(prefix="TC1")

    def test_strand_detail_page_includes_trace_button(self):
        from utilities.testing import create_test_user

        user = create_test_user("tc-tester")
        user.is_superuser = True
        user.save()
        self.client.force_login(user)
        url = reverse(
            "plugins:netbox_osp:strand",
            args=[self.universe["start"].pk],
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200, resp.content)
        # The href the button targets.
        expected_href = f"/plugins/osp/strands/{self.universe['start'].pk}/trace/"
        self.assertContains(resp, expected_href)
        # And the button text from the partial.
        self.assertContains(resp, "Trace this core")

    def test_template_extension_subclasses_are_registered(self):
        # The three new PluginTemplateExtension subclasses should be in
        # the module-level template_extensions list and aimed at the
        # documented models.
        from netbox_osp import template_content as tc

        names = {cls.__name__ for cls in tc.template_extensions}
        for expected in (
            "InterfaceTraceButton",
            "FrontPortTraceButton",
            "StrandTraceButton",
        ):
            self.assertIn(
                expected, names,
                f"{expected} missing from template_extensions",
            )
        # Sanity check the models lists.
        cls_by_name = {c.__name__: c for c in tc.template_extensions}
        self.assertEqual(
            cls_by_name["InterfaceTraceButton"].models, ["dcim.interface"],
        )
        self.assertEqual(
            cls_by_name["FrontPortTraceButton"].models, ["dcim.frontport"],
        )
        self.assertEqual(
            cls_by_name["StrandTraceButton"].models, ["netbox_osp.strand"],
        )


# ============================================================================
# Smoke test: the dagre-d3 vendored file is present
# ============================================================================

class VendoredAssetSmokeTests(DjangoTestCase):
    def test_dagre_d3_min_js_is_shipped(self):
        from pathlib import Path
        path = (
            Path(__file__).resolve().parent.parent
            / "static" / "netbox_osp" / "js" / "dagre-d3.min.js"
        )
        self.assertTrue(
            path.is_file(),
            f"vendored dagre-d3 bundle missing at {path}",
        )
        # Should weigh in well above 1KB (rules out an empty placeholder).
        self.assertGreater(path.stat().st_size, 10_000)

    def test_core_tracer_js_is_shipped(self):
        from pathlib import Path
        path = (
            Path(__file__).resolve().parent.parent
            / "static" / "netbox_osp" / "js" / "core_tracer.js"
        )
        self.assertTrue(
            path.is_file(),
            f"core_tracer.js missing at {path}",
        )
