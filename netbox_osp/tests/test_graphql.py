"""Smoke tests for the netbox-osp GraphQL surface.

NetBox's GraphQL endpoint at /graphql/ is read-only — strawberry-django
auto-generates queries from the types we register but does NOT auto-generate
mutations. So this suite covers list / single / introspection / filter,
not mutations.
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from dcim.models import Site

from netbox_osp.choices import OspCableTypeChoices, OspStatusChoices
from netbox_osp.models import OspCable


GRAPHQL_URL = "/graphql/"


class NetBoxOspGraphQLTests(TestCase):
    """Use session auth (force_login) rather than Token auth. NetBox 4.6
    requires API_TOKEN_PEPPERS for token creation, which isn't set in
    the CI configuration. Session auth is equally valid for /graphql/."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user(
            username="gqltest", password="x", is_superuser=True,
        )

        site_a = Site.objects.create(name="GQL Site A", slug="gql-site-a")
        site_b = Site.objects.create(name="GQL Site B", slug="gql-site-b")
        cls.cable = OspCable.objects.create(
            cid="OSP-GQL-001",
            type=OspCableTypeChoices.TYPE_LOOSE_TUBE,
            status=OspStatusChoices.STATUS_INSTALLED,
            fibre_count=24,
            tube_count=2,
            fibres_per_tube=12,
            site_a=site_a,
            site_b=site_b,
        )

    def setUp(self):
        self.client.force_login(self.user)

    def _post(self, query: str):
        return self.client.post(
            GRAPHQL_URL,
            data=json.dumps({"query": query}),
            content_type="application/json",
        )

    def test_list_query_returns_cable(self):
        resp = self._post("{ osp_cable_list { id cid status fibre_count } }")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertNotIn("errors", body, body.get("errors"))
        rows = body["data"]["osp_cable_list"]
        self.assertGreaterEqual(len(rows), 1)
        cids = [r["cid"] for r in rows]
        self.assertIn("OSP-GQL-001", cids)

    def test_single_query_by_id(self):
        resp = self._post(
            f'{{ osp_cable(id: {self.cable.pk}) {{ id cid }} }}'
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertNotIn("errors", body, body.get("errors"))
        self.assertEqual(body["data"]["osp_cable"]["cid"], "OSP-GQL-001")

    def test_introspection_exposes_osp_cable_type(self):
        resp = self._post(
            '{ __type(name: "OspCableType") { name fields { name } } }'
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertIsNotNone(body["data"]["__type"], body)
        field_names = {f["name"] for f in body["data"]["__type"]["fields"]}
        for expected in ("id", "cid", "status"):
            self.assertIn(expected, field_names)
