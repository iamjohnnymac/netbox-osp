"""Tests for the FibreTrunk model added in PR A of the v0.2.0 cycle.

Coverage:
- Model: __str__, defaults, clean() rejects fibre_count<=0, clean() route
  validation accepts null + well-formed, rejects malformed type and
  out-of-range coordinates.
- Tagging: NetBoxModel.tags.add() round-trip.
- REST: list (auth required), create, retrieve, update, delete; create
  rejects fibre_count=0.
- GraphQL: types / filters / schema modules expose the new attributes.

Per the Phase-2 canary pattern, no ViewTestCases.PrimaryObjectViewTestCase
in this PR — view-test coverage for FibreTrunk will land alongside the
other 7 missing models in a focused later PR.
"""
import importlib

from django.core.exceptions import ValidationError
from django.test import TestCase as DjangoTestCase
from django.urls import reverse
from rest_framework import status

from utilities.testing import APITestCase, TestCase

from netbox_osp.choices import OspStatusChoices, TrunkTypeChoices
from netbox_osp.models import FibreTrunk


class FibreTrunkModelTests(TestCase):
    def test_str_returns_cid(self):
        self.assertEqual(FibreTrunk(cid="MTP-X").__str__(), "MTP-X")

    def test_default_status_planned(self):
        trunk = FibreTrunk(cid="DEF-001")
        self.assertEqual(trunk.status, OspStatusChoices.STATUS_PLANNED)

    def test_default_trunk_type_mpo_24(self):
        trunk = FibreTrunk(cid="DEF-002")
        self.assertEqual(trunk.trunk_type, TrunkTypeChoices.MPO_24)
        self.assertEqual(trunk.fibre_count, 24)

    def test_default_show_on_map_true(self):
        trunk = FibreTrunk(cid="DEF-003")
        self.assertTrue(trunk.show_on_map)

    def test_clean_rejects_fibre_count_zero(self):
        trunk = FibreTrunk(cid="BAD-001", fibre_count=0)
        with self.assertRaises(ValidationError) as cm:
            trunk.clean()
        self.assertIn("fibre_count", cm.exception.message_dict)

    def test_clean_rejects_negative_fibre_count(self):
        # PositiveSmallIntegerField blocks at the DB layer too, but
        # clean() must surface a form-friendly error first.
        trunk = FibreTrunk(cid="BAD-002", fibre_count=-1)
        with self.assertRaises(ValidationError) as cm:
            trunk.clean()
        self.assertIn("fibre_count", cm.exception.message_dict)

    def test_clean_accepts_valid_route(self):
        trunk = FibreTrunk(
            cid="OK-RT-001",
            route={"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
        )
        trunk.clean()       # must not raise

    def test_clean_rejects_malformed_route_type(self):
        trunk = FibreTrunk(
            cid="BAD-RT-001",
            route={"type": "Point", "coordinates": [0, 0]},
        )
        with self.assertRaises(ValidationError) as cm:
            trunk.clean()
        self.assertIn("route", cm.exception.message_dict)

    def test_clean_rejects_route_coords_out_of_range(self):
        trunk = FibreTrunk(
            cid="BAD-RT-002",
            route={"type": "LineString", "coordinates": [[181, 0], [0, 0]]},
        )
        with self.assertRaises(ValidationError) as cm:
            trunk.clean()
        self.assertIn("route", cm.exception.message_dict)

    def test_clean_accepts_null_route(self):
        trunk = FibreTrunk(cid="OK-NULL-RT", route=None)
        trunk.clean()       # must not raise


class FibreTrunkTagTests(TestCase):
    def test_can_attach_tag(self):
        from extras.models import Tag
        trunk = FibreTrunk.objects.create(cid="TAG-001")
        tag = Tag.objects.create(name="ot-critical", slug="ot-critical")
        trunk.tags.add(tag)
        trunk.refresh_from_db()
        self.assertIn(tag, trunk.tags.all())


class FibreTrunkAPITests(APITestCase):
    """REST CRUD with auth. Mirrors PR #6's permission-test sidestep
    where a default-created token gives the user full plugin-model perms.
    """

    def _url(self, suffix=""):
        return f"/api/plugins/osp/trunks/{suffix}"

    def test_list_requires_auth(self):
        # APITestCase doesn't auto-authenticate; an unauthenticated client
        # should get 403 (NetBox's default DRF auth class enforces login).
        self.client.logout()
        resp = self.client.get(self._url(), format="json")
        # NetBox API rejects unauthenticated requests with 403, not 401.
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_create(self):
        self.add_permissions("netbox_osp.add_fibretrunk")
        resp = self.client.post(
            self._url(),
            data={"cid": "API-001"},
            format="json",
            **self.header,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertTrue(FibreTrunk.objects.filter(cid="API-001").exists())

    def test_retrieve(self):
        self.add_permissions("netbox_osp.view_fibretrunk")
        trunk = FibreTrunk.objects.create(cid="API-RT-001")
        resp = self.client.get(self._url(f"{trunk.pk}/"), **self.header)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.json()["cid"], "API-RT-001")

    def test_update(self):
        self.add_permissions("netbox_osp.change_fibretrunk")
        trunk = FibreTrunk.objects.create(cid="API-UP-001")
        resp = self.client.patch(
            self._url(f"{trunk.pk}/"),
            data={"status": OspStatusChoices.STATUS_ACTIVE},
            format="json",
            **self.header,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        trunk.refresh_from_db()
        self.assertEqual(trunk.status, OspStatusChoices.STATUS_ACTIVE)

    def test_delete(self):
        self.add_permissions("netbox_osp.delete_fibretrunk")
        trunk = FibreTrunk.objects.create(cid="API-DEL-001")
        resp = self.client.delete(self._url(f"{trunk.pk}/"), **self.header)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)
        self.assertFalse(FibreTrunk.objects.filter(pk=trunk.pk).exists())

    def test_create_rejects_zero_fibre_count(self):
        self.add_permissions("netbox_osp.add_fibretrunk")
        resp = self.client.post(
            self._url(),
            data={"cid": "API-BAD-001", "fibre_count": 0},
            format="json",
            **self.header,
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)


class FibreTrunkGraphQLSmokeTests(DjangoTestCase):
    """Mirror the existing test_graphql.py pattern: confirm the FibreTrunk
    additions are exposed by the three GraphQL modules at import time."""

    def test_types_module_exposes_fibretrunk_type(self):
        mod = importlib.import_module("netbox_osp.graphql.types")
        self.assertTrue(hasattr(mod, "FibreTrunkType"))

    def test_filters_module_exposes_fibretrunk_filter(self):
        mod = importlib.import_module("netbox_osp.graphql.filters")
        self.assertTrue(hasattr(mod, "FibreTrunkFilter"))

    def test_schema_module_exposes_fibre_trunk_query(self):
        mod = importlib.import_module("netbox_osp.graphql.schema")
        # @strawberry.type rewrites class attributes into descriptors that
        # don't surface via hasattr(); check __annotations__ instead.
        query_cls = mod.NetBoxOspQuery
        self.assertIn(
            "osp_fibre_trunk_list",
            query_cls.__annotations__,
            "schema Query class missing osp_fibre_trunk_list annotation",
        )
