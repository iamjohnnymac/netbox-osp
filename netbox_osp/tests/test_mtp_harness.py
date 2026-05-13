"""Tests for the MTP harness one-click deploy view added in PR C of the
v0.2.0 cycle.

Coverage:
- GET: anonymous redirects to login; authenticated renders the form.
- POST happy path: N=2 and N=3 destinations create exactly the expected
  rows (1 trunk + N devices + N cables + N TrunkBreakouts).
- POST validation failures: overlapping fibre ranges, missing dest_rack,
  fibre sum > trunk.fibre_count, duplicate dest_racks. Each asserts a
  full rollback via pre/post row counts.
- Preview-confirm round trip: POST without `confirm=1` renders the
  preview template; POST with `confirm=1` + a valid signed state token
  runs the atomic deploy.
- Permission denial: user without `dcim.add_device` + `dcim.add_cable` +
  `netbox_osp.add_trunkbreakout` perms is rejected before any DB write.

Notes on test infrastructure:
- We DO NOT use a `DynamicModelChoiceField`-friendly DOM round-trip; the
  view treats the form fields as PK-bearing strings (which they are) so
  POSTing the raw PK works.
- `Cable.save()` triggers the dcim `trace_paths` signal which validates
  the cable path. For unit tests we want the trace to succeed, so the
  source + destination ports are both RearPorts on distinct devices.
"""
from decimal import Decimal

from django.urls import reverse

from dcim.models import (
    Cable,
    Device,
    DeviceRole,
    DeviceType,
    Manufacturer,
    Rack,
    RearPortTemplate,
    Site,
)
from utilities.testing import TestCase

from netbox_osp.models import FibreTrunk, TrunkBreakout


# ============================================================================
# Shared fixtures
# ============================================================================


def _build_fixtures():
    """Build the minimal dcim universe the harness view needs.

    Returns a dict with the model instances tests will reference. Called
    from `setUp` (NOT `setUpTestData`) on each test class so each test
    starts with a clean object graph and FibreTrunk row count of zero.
    """
    site = Site.objects.create(name="Test Site", slug="test-site")
    manufacturer = Manufacturer.objects.create(name="Test Mfg", slug="test-mfg")

    # Source patch panel device-type with one 24-position RearPort template.
    src_type = DeviceType.objects.create(
        manufacturer=manufacturer,
        model="PatchPanel-24",
        slug="patchpanel-24",
        u_height=1,
    )
    # Source patch panel needs one RearPort per destination — the deploy
    # consumes one free source-side port per destination row.
    for i in range(1, 7):
        RearPortTemplate.objects.create(
            device_type=src_type,
            name=f"panel-mpo-{i:02d}",
            type="mpo",
            positions=12,
        )

    # Cassette device-type with one 12-position RearPort template.
    cassette_type = DeviceType.objects.create(
        manufacturer=manufacturer,
        model="Cassette-12",
        slug="cassette-12",
        u_height=1,
    )
    RearPortTemplate.objects.create(
        device_type=cassette_type,
        name="cassette-trunk",
        type="lc",
        positions=12,
    )

    role = DeviceRole.objects.create(name="Patch Panel", slug="patch-panel")

    rack_mmr = Rack.objects.create(name="MMR", site=site, u_height=42)
    rack_a = Rack.objects.create(name="RackA", site=site, u_height=42)
    rack_b = Rack.objects.create(name="RackB", site=site, u_height=42)
    rack_c = Rack.objects.create(name="RackC", site=site, u_height=42)

    src_device = Device.objects.create(
        name="MMR-PANEL-1",
        site=site,
        rack=rack_mmr,
        device_type=src_type,
        role=role,
        position=Decimal("1.0"),
        face="front",
        status="active",
    )
    # `Device.save()` auto-creates 6 RearPorts via the templates.

    return {
        "site": site,
        "manufacturer": manufacturer,
        "src_type": src_type,
        "cassette_type": cassette_type,
        "role": role,
        "rack_mmr": rack_mmr,
        "rack_a": rack_a,
        "rack_b": rack_b,
        "rack_c": rack_c,
        "src_device": src_device,
    }


def _form_data(fx, destinations):
    """Build a POST payload matching `MtpHarnessForm` +
    `MtpHarnessDestinationFormSet`. `destinations` is a list of dicts
    spelling out each row's fields.
    """
    data = {
        "trunk_cid": "MTP-TEST-001",
        "trunk_type": "mpo-24",
        "fibre_count": 24,
        "manufacturer": str(fx["manufacturer"].pk),
        "source_rack": str(fx["rack_mmr"].pk),
        "source_device": str(fx["src_device"].pk),
        "cassette_device_type": str(fx["cassette_type"].pk),
        "cassette_device_role": str(fx["role"].pk),
        "cable_type": "smf",
        # Formset management form.
        "form-TOTAL_FORMS": str(len(destinations)),
        "form-INITIAL_FORMS": "0",
        "form-MIN_NUM_FORMS": "1",
        "form-MAX_NUM_FORMS": "24",
    }
    for idx, dest in enumerate(destinations):
        prefix = f"form-{idx}-"
        for key, value in dest.items():
            data[prefix + key] = "" if value is None else str(value)
        # Sensible defaults for required-but-not-provided fields.
        data.setdefault(prefix + "dest_device_mode", "create")
        data.setdefault(prefix + "dest_face", "front")
    return data


def _destination_create(rack, name, position_u, fr_start, fr_end):
    return {
        "dest_rack": rack.pk,
        "dest_device_mode": "create",
        "dest_device_name": name,
        "dest_position_u": position_u,
        "dest_face": "front",
        "fibre_range_start": fr_start,
        "fibre_range_end": fr_end,
        "cable_label": f"CBL-{name}",
        "cable_length_m": "5.0",
    }


# ============================================================================
# View tests
# ============================================================================


class MtpHarnessGetTests(TestCase):
    """GET-side: auth gating + form rendering."""

    def _url(self):
        return reverse("plugins:netbox_osp:mtp_harness_deploy")

    def test_get_anonymous_redirects(self):
        self.client.logout()
        resp = self.client.get(self._url())
        self.assertIn(resp.status_code, (302, 403))

    def test_get_authenticated_renders_empty_form(self):
        self.add_permissions(
            "netbox_osp.add_fibretrunk",
            "netbox_osp.add_trunkbreakout",
            "dcim.add_device",
            "dcim.add_cable",
        )
        resp = self.client.get(self._url())
        self.assertEqual(resp.status_code, 200)
        # Management form for the destinations formset must be present.
        self.assertContains(resp, "form-TOTAL_FORMS")
        # At least 2 empty destination rows (formset_factory extra=2).
        body = resp.content.decode()
        self.assertIn("form-0-dest_rack", body)
        self.assertIn("form-1-dest_rack", body)


class MtpHarnessPostTests(TestCase):
    """POST-side: validation, atomic deploy, rollback semantics."""

    def setUp(self):
        super().setUp()
        self.add_permissions(
            "netbox_osp.add_fibretrunk",
            "netbox_osp.add_trunkbreakout",
            "dcim.add_device",
            "dcim.add_cable",
        )
        self.fx = _build_fixtures()

    def _url(self):
        return reverse("plugins:netbox_osp:mtp_harness_deploy")

    def _post_confirm(self, data):
        """Submit twice — once to preview (gets a signed state token),
        once with `confirm=1` to actually deploy. Returns the confirm
        response.
        """
        resp_preview = self.client.post(self._url(), data=data)
        if resp_preview.status_code != 200 or b"harness-preview" not in resp_preview.content:
            return resp_preview
        # Pluck the state token out of the rendered preview page.
        body = resp_preview.content.decode()
        marker = 'name="state_token" value="'
        start = body.index(marker) + len(marker)
        end = body.index('"', start)
        token = body[start:end]
        return self.client.post(self._url(), data={
            "confirm": "1",
            "state_token": token,
        })

    def test_post_happy_path_two_destinations(self):
        data = _form_data(self.fx, [
            _destination_create(self.fx["rack_a"], "CST-A", "10.0", 1, 12),
            _destination_create(self.fx["rack_b"], "CST-B", "10.0", 13, 24),
        ])
        resp = self._post_confirm(data)
        # DEBUG: dump response body if assertion would fail
        if FibreTrunk.objects.count() != 1:
            print("=== DEBUG: response status:", resp.status_code)
            print("=== DEBUG: response location:", resp.get("Location", "(none)"))
            try:
                body = resp.content.decode()[:3000]
            except Exception:
                body = "(no content)"
            print("=== DEBUG: response body[:3000]:")
            print(body)
        self.assertEqual(resp.status_code, 302, resp.content[:500])
        self.assertEqual(FibreTrunk.objects.count(), 1)
        trunk = FibreTrunk.objects.first()
        self.assertEqual(
            Device.objects.filter(rack__in=[self.fx["rack_a"], self.fx["rack_b"]]).count(),
            2,
        )
        self.assertEqual(Cable.objects.count(), 2)
        self.assertEqual(TrunkBreakout.objects.count(), 2)
        ranges = list(
            TrunkBreakout.objects
            .filter(trunk=trunk)
            .order_by("fibre_range_start")
            .values_list("fibre_range_start", "fibre_range_end")
        )
        self.assertEqual(ranges, [(1, 12), (13, 24)])
        # Each cable must have exactly two CableTermination rows.
        for cable in Cable.objects.all():
            self.assertEqual(cable.terminations.count(), 2)

    def test_post_happy_path_three_destinations(self):
        data = _form_data(self.fx, [
            _destination_create(self.fx["rack_a"], "CST-A", "10.0", 1, 8),
            _destination_create(self.fx["rack_b"], "CST-B", "10.0", 9, 16),
            _destination_create(self.fx["rack_c"], "CST-C", "10.0", 17, 24),
        ])
        resp = self._post_confirm(data)
        self.assertEqual(resp.status_code, 302, resp.content[:500])
        self.assertEqual(FibreTrunk.objects.count(), 1)
        self.assertEqual(Cable.objects.count(), 3)
        self.assertEqual(TrunkBreakout.objects.count(), 3)
        self.assertEqual(
            Device.objects.filter(
                rack__in=[self.fx["rack_a"], self.fx["rack_b"], self.fx["rack_c"]],
            ).count(),
            3,
        )

    def test_post_overlapping_fibre_ranges_rolls_back(self):
        device_count_before = Device.objects.count()
        data = _form_data(self.fx, [
            _destination_create(self.fx["rack_a"], "CST-A", "10.0", 1, 12),
            _destination_create(self.fx["rack_b"], "CST-B", "10.0", 10, 21),
        ])
        resp = self.client.post(self._url(), data=data)
        # Preview validation catches the overlap — re-renders the form.
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(FibreTrunk.objects.count(), 0)
        self.assertEqual(Cable.objects.count(), 0)
        self.assertEqual(TrunkBreakout.objects.count(), 0)
        self.assertEqual(Device.objects.count(), device_count_before)

    def test_post_missing_dest_rack_rolls_back(self):
        data = _form_data(self.fx, [
            _destination_create(self.fx["rack_a"], "CST-A", "10.0", 1, 12),
            {
                "dest_rack": "",  # MISSING — formset.is_valid() fails.
                "dest_device_mode": "create",
                "dest_device_name": "CST-B",
                "dest_position_u": "10.0",
                "dest_face": "front",
                "fibre_range_start": 13,
                "fibre_range_end": 24,
                "cable_label": "CBL-B",
                "cable_length_m": "5.0",
            },
        ])
        resp = self.client.post(self._url(), data=data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(FibreTrunk.objects.count(), 0)
        self.assertEqual(Cable.objects.count(), 0)
        self.assertEqual(TrunkBreakout.objects.count(), 0)

    def test_post_fibre_sum_exceeds_count_rolls_back(self):
        data = _form_data(self.fx, [
            _destination_create(self.fx["rack_a"], "CST-A", "10.0", 1, 12),
            _destination_create(self.fx["rack_b"], "CST-B", "10.0", 13, 24),
        ])
        # Override fibre_count down to 12 — the two [1-12]+[13-24] rows
        # sum to 24 fibres, well over the trunk capacity.
        data["fibre_count"] = "12"
        resp = self.client.post(self._url(), data=data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(FibreTrunk.objects.count(), 0)
        # The parent-form field-keyed error must surface on fibre_count.
        self.assertContains(resp, "fibre_count")
        self.assertIn(b"sum to", resp.content)

    def test_post_duplicate_dest_racks_rolls_back(self):
        data = _form_data(self.fx, [
            _destination_create(self.fx["rack_a"], "CST-A1", "10.0", 1, 12),
            _destination_create(self.fx["rack_a"], "CST-A2", "20.0", 13, 24),
        ])
        resp = self.client.post(self._url(), data=data)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(FibreTrunk.objects.count(), 0)
        self.assertEqual(TrunkBreakout.objects.count(), 0)
        self.assertContains(resp, "Each destination rack must be unique.")

    def test_post_preview_then_confirm(self):
        data = _form_data(self.fx, [
            _destination_create(self.fx["rack_a"], "CST-A", "10.0", 1, 12),
            _destination_create(self.fx["rack_b"], "CST-B", "10.0", 13, 24),
        ])
        resp_preview = self.client.post(self._url(), data=data)
        self.assertEqual(resp_preview.status_code, 200)
        self.assertContains(resp_preview, 'id="harness-preview"')
        # Pluck the state token and re-submit with confirm=1.
        body = resp_preview.content.decode()
        marker = 'name="state_token" value="'
        start = body.index(marker) + len(marker)
        end = body.index('"', start)
        token = body[start:end]
        # No FibreTrunk yet — preview must not have written anything.
        self.assertEqual(FibreTrunk.objects.count(), 0)
        resp_confirm = self.client.post(self._url(), data={
            "confirm": "1",
            "state_token": token,
        })
        self.assertEqual(resp_confirm.status_code, 302)
        self.assertEqual(FibreTrunk.objects.count(), 1)
        self.assertEqual(TrunkBreakout.objects.count(), 2)


class MtpHarnessPermissionTests(TestCase):
    """User logged in but lacking the required perms must be rejected
    before any DB write."""

    def setUp(self):
        super().setUp()
        # Deliberately add NONE of the required permissions.
        self.fx = _build_fixtures()

    def _url(self):
        return reverse("plugins:netbox_osp:mtp_harness_deploy")

    def test_permission_denied_for_user_without_perm(self):
        data = _form_data(self.fx, [
            _destination_create(self.fx["rack_a"], "CST-A", "10.0", 1, 12),
        ])
        resp = self.client.post(self._url(), data=data)
        # PermissionRequiredMixin returns 403 on Django>=3.2 / NetBox 4.6
        # for an authenticated-but-unauthorised user.
        self.assertIn(resp.status_code, (302, 403))
        # No rows should exist regardless of the redirect target.
        self.assertEqual(FibreTrunk.objects.count(), 0)
        self.assertEqual(TrunkBreakout.objects.count(), 0)
