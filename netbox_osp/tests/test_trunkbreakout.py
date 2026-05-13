"""Tests for the TrunkBreakout through-table added in PR B of the
v0.2.0 cycle.

Coverage:
- Model: __str__, default description, fibre_count property, clean()
  boundary cases (start<1, end<start, end>parent.fibre_count, sibling
  overlap, adjacent ranges, self-update), unique_together constraints.
- Parent invariants: FibreTrunk.fibres_used / fibres_remaining /
  fibres_utilization_pct arithmetic; FibreTrunk.clean() rejects when
  sum-of-children > fibre_count.
- REST: list (auth required), create, retrieve, update, delete; create
  rejects overlap; create rejects end > parent.fibre_count.
- GraphQL: types / filters / schema modules expose the new attributes.
- Wizard view: GET candidate cables, exclude already-attached cables,
  POST happy path assigns ranges, atomic rollback on overlap and on
  overrun.

Per the Phase-2 canary pattern, no `ViewTestCases.PrimaryObjectViewTestCase`
in this PR — view-test coverage for TrunkBreakout will land alongside
the rest in a focused follow-up.
"""
import importlib

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase as DjangoTestCase
from rest_framework import status

from dcim.models import Cable
from utilities.testing import APITestCase, TestCase

from netbox_osp.models import FibreTrunk, TrunkBreakout


def _make_cable(label="C-001"):
    """Create a minimal dcim.Cable for breakout tests.

    Cable.clean() requires A+B terminations, but .objects.create()
    bypasses clean() so we can use a pure-ORM minimal row. This matches
    how NetBox itself shortcuts dcim setup in adjacent test suites.
    """
    return Cable.objects.create(label=label)


def _make_trunk(cid="T-001", fibre_count=24):
    return FibreTrunk.objects.create(cid=cid, fibre_count=fibre_count)


# ============================================================================
# Model tests
# ============================================================================

class TrunkBreakoutModelTests(TestCase):
    def test_str_describes_range_and_cable(self):
        trunk = _make_trunk(cid="STR-001", fibre_count=24)
        cable = _make_cable(label="STR-CBL-001")
        br = TrunkBreakout.objects.create(
            trunk=trunk, cable=cable,
            fibre_range_start=1, fibre_range_end=12,
        )
        s = str(br)
        self.assertIn("STR-001", s)
        self.assertIn("1-12", s)

    def test_default_description_empty(self):
        trunk = _make_trunk(cid="DEF-001")
        cable = _make_cable(label="DEF-CBL-001")
        br = TrunkBreakout.objects.create(
            trunk=trunk, cable=cable,
            fibre_range_start=1, fibre_range_end=12,
        )
        self.assertEqual(br.description, "")

    def test_fibre_count_property(self):
        br = TrunkBreakout(fibre_range_start=1, fibre_range_end=12)
        self.assertEqual(br.fibre_count, 12)
        # Single fibre is a valid edge case.
        br2 = TrunkBreakout(fibre_range_start=5, fibre_range_end=5)
        self.assertEqual(br2.fibre_count, 1)

    def test_clean_rejects_range_start_zero(self):
        trunk = _make_trunk(cid="BAD-001")
        cable = _make_cable(label="BAD-CBL-001")
        br = TrunkBreakout(
            trunk=trunk, cable=cable,
            fibre_range_start=0, fibre_range_end=12,
        )
        with self.assertRaises(ValidationError) as cm:
            br.clean()
        self.assertIn("fibre_range_start", cm.exception.message_dict)

    def test_clean_rejects_end_lt_start(self):
        trunk = _make_trunk(cid="BAD-002")
        cable = _make_cable(label="BAD-CBL-002")
        br = TrunkBreakout(
            trunk=trunk, cable=cable,
            fibre_range_start=12, fibre_range_end=6,
        )
        with self.assertRaises(ValidationError) as cm:
            br.clean()
        self.assertIn("fibre_range_end", cm.exception.message_dict)

    def test_clean_rejects_end_exceeds_parent_fibre_count(self):
        trunk = _make_trunk(cid="BAD-003", fibre_count=12)
        cable = _make_cable(label="BAD-CBL-003")
        br = TrunkBreakout(
            trunk=trunk, cable=cable,
            fibre_range_start=1, fibre_range_end=24,
        )
        with self.assertRaises(ValidationError) as cm:
            br.clean()
        self.assertIn("fibre_range_end", cm.exception.message_dict)

    def test_clean_rejects_overlap_with_sibling(self):
        trunk = _make_trunk(cid="OVR-001", fibre_count=24)
        cable_a = _make_cable(label="OVR-CBL-A")
        cable_b = _make_cable(label="OVR-CBL-B")
        TrunkBreakout.objects.create(
            trunk=trunk, cable=cable_a,
            fibre_range_start=1, fibre_range_end=12,
        )
        br_new = TrunkBreakout(
            trunk=trunk, cable=cable_b,
            fibre_range_start=5, fibre_range_end=18,
        )
        with self.assertRaises(ValidationError) as cm:
            br_new.clean()
        self.assertIn("fibre_range_start", cm.exception.message_dict)

    def test_clean_allows_adjacent_ranges(self):
        trunk = _make_trunk(cid="ADJ-001", fibre_count=24)
        cable_a = _make_cable(label="ADJ-CBL-A")
        cable_b = _make_cable(label="ADJ-CBL-B")
        TrunkBreakout.objects.create(
            trunk=trunk, cable=cable_a,
            fibre_range_start=1, fibre_range_end=12,
        )
        br_new = TrunkBreakout(
            trunk=trunk, cable=cable_b,
            fibre_range_start=13, fibre_range_end=24,
        )
        # Must NOT raise — [13-24] is exactly adjacent to [1-12].
        br_new.clean()

    def test_clean_self_update_does_not_collide_with_self(self):
        trunk = _make_trunk(cid="SELF-001", fibre_count=24)
        cable = _make_cable(label="SELF-CBL-001")
        br = TrunkBreakout.objects.create(
            trunk=trunk, cable=cable,
            fibre_range_start=1, fibre_range_end=12,
        )
        # Editing the same row without changing the range must not see
        # the saved row as a sibling.
        br.fibre_range_end = 18
        br.clean()  # must not raise
        br.save()
        br.refresh_from_db()
        self.assertEqual(br.fibre_range_end, 18)

    def test_unique_together_trunk_cable(self):
        trunk = _make_trunk(cid="UNQ-001", fibre_count=24)
        cable = _make_cable(label="UNQ-CBL-001")
        TrunkBreakout.objects.create(
            trunk=trunk, cable=cable,
            fibre_range_start=1, fibre_range_end=12,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TrunkBreakout.objects.create(
                    trunk=trunk, cable=cable,
                    fibre_range_start=13, fibre_range_end=24,
                )

    def test_unique_together_trunk_range_start(self):
        trunk = _make_trunk(cid="UNQ-002", fibre_count=48)
        cable_a = _make_cable(label="UNQ-CBL-A")
        cable_b = _make_cable(label="UNQ-CBL-B")
        TrunkBreakout.objects.create(
            trunk=trunk, cable=cable_a,
            fibre_range_start=1, fibre_range_end=12,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TrunkBreakout.objects.create(
                    trunk=trunk, cable=cable_b,
                    fibre_range_start=1, fibre_range_end=12,
                )


# ============================================================================
# Parent-side invariants
# ============================================================================

class FibreTrunkBreakoutInvariantTests(TestCase):
    def _setup(self, cid, fibre_count, ranges):
        trunk = _make_trunk(cid=cid, fibre_count=fibre_count)
        for idx, (start, end) in enumerate(ranges):
            cable = _make_cable(label=f"{cid}-CBL-{idx}")
            TrunkBreakout.objects.create(
                trunk=trunk, cable=cable,
                fibre_range_start=start, fibre_range_end=end,
            )
        return trunk

    def test_fibres_used_sums_children(self):
        trunk = self._setup("INV-001", 24, [(1, 12), (13, 18)])
        self.assertEqual(trunk.fibres_used, 18)

    def test_fibres_remaining_arithmetic(self):
        trunk = self._setup("INV-002", 24, [(1, 12), (13, 18)])
        self.assertEqual(trunk.fibres_remaining, 6)

    def test_fibres_utilization_pct(self):
        trunk = self._setup("INV-003", 24, [(1, 12), (13, 18)])
        self.assertEqual(trunk.fibres_utilization_pct, 75.0)

    def test_parent_clean_rejects_sum_over_count(self):
        # 12F trunk with [1-8]+[9-16] would sum to 16 — overshoots
        # fibre_count=12. We can't create the second breakout via the
        # normal model.clean() path because it would also reject on the
        # end>parent.fibre_count check. Use force_insert via objects.create
        # to skip clean() so we can exercise the trunk-side guard
        # specifically.
        trunk = _make_trunk(cid="INV-004", fibre_count=12)
        cable_a = _make_cable(label="INV-004-CBL-A")
        cable_b = _make_cable(label="INV-004-CBL-B")
        TrunkBreakout.objects.create(
            trunk=trunk, cable=cable_a,
            fibre_range_start=1, fibre_range_end=8,
        )
        # Bump fibre_count high enough that the child clean passes, then
        # tighten it back so the parent.clean() catches the sum overflow.
        trunk.fibre_count = 24
        trunk.save()
        TrunkBreakout.objects.create(
            trunk=trunk, cable=cable_b,
            fibre_range_start=9, fibre_range_end=16,
        )
        trunk.fibre_count = 12
        with self.assertRaises(ValidationError) as cm:
            trunk.clean()
        self.assertIn("fibre_count", cm.exception.message_dict)

    def test_parent_clean_allows_underfill(self):
        trunk = self._setup("INV-005", 24, [(1, 12)])
        # 12 used of 24 — well under capacity. Must not raise.
        trunk.clean()


# ============================================================================
# REST API
# ============================================================================

class TrunkBreakoutAPITests(APITestCase):
    """REST CRUD with auth. API_TOKEN_PEPPERS is wired in CI so
    APITestCase.setUp's Token.objects.create() round-trip works."""

    def _url(self, suffix=""):
        return f"/api/plugins/osp/trunk-breakouts/{suffix}"

    def test_list_requires_auth(self):
        self.client.logout()
        resp = self.client.get(self._url(), format="json")
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_create(self):
        self.add_permissions("netbox_osp.add_trunkbreakout")
        trunk = _make_trunk(cid="API-001", fibre_count=24)
        cable = _make_cable(label="API-CBL-001")
        resp = self.client.post(
            self._url(),
            data={
                "trunk": trunk.pk,
                "cable": cable.pk,
                "fibre_range_start": 1,
                "fibre_range_end": 12,
            },
            format="json",
            **self.header,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertTrue(TrunkBreakout.objects.filter(trunk=trunk, cable=cable).exists())

    def test_retrieve(self):
        self.add_permissions("netbox_osp.view_trunkbreakout")
        trunk = _make_trunk(cid="API-RT-001", fibre_count=24)
        cable = _make_cable(label="API-RT-CBL-001")
        br = TrunkBreakout.objects.create(
            trunk=trunk, cable=cable,
            fibre_range_start=1, fibre_range_end=12,
        )
        resp = self.client.get(self._url(f"{br.pk}/"), **self.header)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        body = resp.json()
        self.assertEqual(body["fibre_range_start"], 1)
        self.assertEqual(body["fibre_range_end"], 12)
        self.assertEqual(body["fibre_count"], 12)

    def test_update(self):
        self.add_permissions("netbox_osp.change_trunkbreakout")
        trunk = _make_trunk(cid="API-UP-001", fibre_count=24)
        cable = _make_cable(label="API-UP-CBL-001")
        br = TrunkBreakout.objects.create(
            trunk=trunk, cable=cable,
            fibre_range_start=1, fibre_range_end=12,
        )
        resp = self.client.patch(
            self._url(f"{br.pk}/"),
            data={"fibre_range_end": 18},
            format="json",
            **self.header,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        br.refresh_from_db()
        self.assertEqual(br.fibre_range_end, 18)

    def test_delete(self):
        self.add_permissions("netbox_osp.delete_trunkbreakout")
        trunk = _make_trunk(cid="API-DEL-001", fibre_count=24)
        cable = _make_cable(label="API-DEL-CBL-001")
        br = TrunkBreakout.objects.create(
            trunk=trunk, cable=cable,
            fibre_range_start=1, fibre_range_end=12,
        )
        resp = self.client.delete(self._url(f"{br.pk}/"), **self.header)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)
        self.assertFalse(TrunkBreakout.objects.filter(pk=br.pk).exists())

    def test_create_rejects_overlap(self):
        self.add_permissions("netbox_osp.add_trunkbreakout")
        trunk = _make_trunk(cid="API-OVR-001", fibre_count=24)
        cable_a = _make_cable(label="API-OVR-CBL-A")
        cable_b = _make_cable(label="API-OVR-CBL-B")
        TrunkBreakout.objects.create(
            trunk=trunk, cable=cable_a,
            fibre_range_start=1, fibre_range_end=12,
        )
        resp = self.client.post(
            self._url(),
            data={
                "trunk": trunk.pk,
                "cable": cable_b.pk,
                "fibre_range_start": 5,
                "fibre_range_end": 18,
            },
            format="json",
            **self.header,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertIn("fibre_range_start", resp.json())

    def test_create_rejects_end_over_parent_count(self):
        self.add_permissions("netbox_osp.add_trunkbreakout")
        trunk = _make_trunk(cid="API-OVF-001", fibre_count=12)
        cable = _make_cable(label="API-OVF-CBL-001")
        resp = self.client.post(
            self._url(),
            data={
                "trunk": trunk.pk,
                "cable": cable.pk,
                "fibre_range_start": 1,
                "fibre_range_end": 24,
            },
            format="json",
            **self.header,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertIn("fibre_range_end", resp.json())


# ============================================================================
# GraphQL smoke tests
# ============================================================================

class TrunkBreakoutGraphQLSmokeTests(DjangoTestCase):
    """Confirm the TrunkBreakout additions are exposed by the three
    GraphQL modules at import time. Module-level hasattr() is fine for
    type/filter classes; the Query class needs __annotations__ because
    @strawberry.type rewrites class attributes."""

    def test_types_module_exposes_fibretrunkbreakout_type(self):
        mod = importlib.import_module("netbox_osp.graphql.types")
        self.assertTrue(hasattr(mod, "FibreTrunkBreakoutType"))

    def test_filters_module_exposes_filter(self):
        mod = importlib.import_module("netbox_osp.graphql.filters")
        self.assertTrue(hasattr(mod, "FibreTrunkBreakoutFilter"))

    def test_schema_module_exposes_query_field(self):
        mod = importlib.import_module("netbox_osp.graphql.schema")
        query_cls = mod.NetBoxOspQuery
        # @strawberry.type rewrites attrs into descriptors that hasattr()
        # misses; __annotations__ is preserved regardless.
        self.assertIn(
            "osp_trunk_breakout_list",
            query_cls.__annotations__,
            "schema Query class missing osp_trunk_breakout_list annotation",
        )


# ============================================================================
# Wizard view: GET candidates, POST happy path, atomic rollback
# ============================================================================

class TrunkImportCablesWizardTests(TestCase):
    def _login(self, perms=("netbox_osp.add_trunkbreakout",)):
        # utilities.testing.TestCase logs the user in as self.user during
        # setUp. We just need to add the explicit permission required by
        # the wizard view.
        for p in perms:
            self.add_permissions(p)

    def _url(self, trunk_pk):
        return f"/plugins/osp/trunks/{trunk_pk}/import-cables/"

    def test_get_renders_candidate_cables(self):
        self._login()
        trunk = _make_trunk(cid="WIZ-001", fibre_count=48)
        cable = _make_cable(label="WIZ-001-CBL")
        resp = self.client.get(self._url(trunk.pk))
        self.assertEqual(resp.status_code, 200)
        # The candidate cable PK should appear in the rendered form.
        self.assertContains(resp, str(cable.pk))

    def test_get_excludes_already_attached_cables(self):
        self._login()
        trunk = _make_trunk(cid="WIZ-002", fibre_count=48)
        cable_a = _make_cable(label="WIZ-002-A")
        cable_b = _make_cable(label="WIZ-002-B")
        # cable_a is already bound to a breakout — it must be hidden.
        TrunkBreakout.objects.create(
            trunk=trunk, cable=cable_a,
            fibre_range_start=1, fibre_range_end=12,
        )
        resp = self.client.get(self._url(trunk.pk))
        self.assertEqual(resp.status_code, 200)
        # cable_b should be present; cable_a should NOT be.
        cable_a_value = f'value="{cable_a.pk}"'
        cable_b_value = f'value="{cable_b.pk}"'
        self.assertIn(cable_b_value, resp.content.decode())
        self.assertNotIn(cable_a_value, resp.content.decode())

    def test_post_happy_path_assigns_ranges(self):
        self._login()
        trunk = _make_trunk(cid="WIZ-003", fibre_count=48)
        cable_a = _make_cable(label="WIZ-003-A")
        cable_b = _make_cable(label="WIZ-003-B")
        resp = self.client.post(
            self._url(trunk.pk),
            data={
                "cables": [cable_a.pk, cable_b.pk],
                "start_fibre": 1,
            },
        )
        # 302 redirect back to the trunk detail page on success.
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(TrunkBreakout.objects.filter(trunk=trunk).count(), 2)
        # Default fibre_size per cable is 1 (Cable carries no fibre_count
        # in core), so ranges are [1-1] and [2-2].
        ranges = list(
            TrunkBreakout.objects
            .filter(trunk=trunk)
            .order_by("fibre_range_start")
            .values_list("fibre_range_start", "fibre_range_end")
        )
        self.assertEqual(ranges, [(1, 1), (2, 2)])

    def test_post_atomic_rollback_on_overlap(self):
        self._login()
        trunk = _make_trunk(cid="WIZ-004", fibre_count=48)
        cable_existing = _make_cable(label="WIZ-004-X")
        cable_new = _make_cable(label="WIZ-004-N")
        # Pre-existing breakout covering [1-1].
        TrunkBreakout.objects.create(
            trunk=trunk, cable=cable_existing,
            fibre_range_start=1, fibre_range_end=1,
        )
        before = TrunkBreakout.objects.filter(trunk=trunk).count()
        resp = self.client.post(
            self._url(trunk.pk),
            data={
                "cables": [cable_new.pk],
                "start_fibre": 1,  # Collides with [1-1].
            },
        )
        # Form re-renders (200) with errors; no new rows.
        self.assertEqual(resp.status_code, 200)
        after = TrunkBreakout.objects.filter(trunk=trunk).count()
        self.assertEqual(after, before)

    def test_post_atomic_rollback_on_overrun(self):
        self._login()
        # 1-fibre trunk; selecting two cables overruns parent.fibre_count.
        trunk = _make_trunk(cid="WIZ-005", fibre_count=1)
        cable_a = _make_cable(label="WIZ-005-A")
        cable_b = _make_cable(label="WIZ-005-B")
        resp = self.client.post(
            self._url(trunk.pk),
            data={
                "cables": [cable_a.pk, cable_b.pk],
                "start_fibre": 1,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(TrunkBreakout.objects.filter(trunk=trunk).count(), 0)
