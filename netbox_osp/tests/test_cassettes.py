"""Tests for the bundled MPO/MTP cassette device-type JSONs and the
`load_osp_cassettes` management command added in PR D of the v0.2.0
cycle.

Coverage:
- Each JSON file parses cleanly.
- Each JSON file has the required top-level keys (manufacturer, model,
  slug, u_height) NetBox's importer expects.
- Every `front-ports[i].rear_port` reference matches a defined entry in
  `rear-ports` for the same cassette.
- Every `front-ports[i].rear_port_position` is ≤ that rear-port's
  `positions` (so the catalogue doesn't ship invalid pin maps).
- `load_osp_cassettes` imports all five cleanly into an in-memory DB.
- Re-running `load_osp_cassettes` is idempotent (counts unchanged).
- A spot check on the materialised port-template structure for one
  cassette confirms the FK wiring landed correctly.
"""

import json
from io import StringIO

from dcim.models import (
    DeviceType,
    FrontPortTemplate,
    Manufacturer,
    PortTemplateMapping,
    RearPortTemplate,
)
from django.core.management import call_command
from utilities.testing import TestCase

from netbox_osp.management.commands.load_osp_cassettes import (
    CASSETTES_DIR,
    discover_cassette_files,
    load_cassette_spec,
)

# Required top-level keys per the netbox-community/devicetype-library
# schema. Subset the importer actually consumes for cassettes — full
# upstream list is broader, but we only ship cassettes here.
REQUIRED_KEYS = ("manufacturer", "model", "slug", "u_height")

# We ship exactly five cassettes in PR D. Test guards against accidental
# adds/removes — bump this if a new cassette is intentionally added.
EXPECTED_CASSETTE_COUNT = 5


class CassetteJSONShapeTests(TestCase):
    """Static checks over the shipped JSON files — no DB writes."""

    def test_expected_cassette_file_count(self):
        files = discover_cassette_files()
        self.assertEqual(
            len(files),
            EXPECTED_CASSETTE_COUNT,
            f"Expected {EXPECTED_CASSETTE_COUNT} cassette JSON files, got {len(files)}: {[f.name for f in files]}",
        )

    def test_each_json_is_valid_json(self):
        # Iterate so the failure message points at the bad file.
        for path in discover_cassette_files():
            with self.subTest(file=path.name), path.open(encoding="utf-8") as fh:
                try:
                    json.load(fh)
                except json.JSONDecodeError as e:
                    self.fail(f"{path.name} is not valid JSON: {e}")

    def test_each_json_has_required_keys(self):
        for path in discover_cassette_files():
            with self.subTest(file=path.name):
                spec = load_cassette_spec(path)
                missing = [k for k in REQUIRED_KEYS if k not in spec]
                self.assertFalse(
                    missing,
                    f"{path.name} missing required keys: {missing}",
                )

    def test_each_json_front_port_references_existing_rear(self):
        """Catch typos like `rear_port: "mpo-2"` when only `mpo-1` exists."""
        for path in discover_cassette_files():
            with self.subTest(file=path.name):
                spec = load_cassette_spec(path)
                rear_names = {r["name"] for r in spec.get("rear-ports", [])}
                for i, front in enumerate(spec.get("front-ports", [])):
                    ref = front.get("rear_port")
                    if ref is None:
                        continue
                    self.assertIn(
                        ref,
                        rear_names,
                        f"{path.name}: front-ports[{i}] references unknown rear-port '{ref}'",
                    )

    def test_each_json_rear_port_position_within_bounds(self):
        """`rear_port_position` must be 1..positions of the target rear-port."""
        for path in discover_cassette_files():
            with self.subTest(file=path.name):
                spec = load_cassette_spec(path)
                rear_by_name = {r["name"]: r.get("positions", 1) for r in spec.get("rear-ports", [])}
                for i, front in enumerate(spec.get("front-ports", [])):
                    ref = front.get("rear_port")
                    if ref is None:
                        continue
                    pos = front.get("rear_port_position", 1)
                    bound = rear_by_name.get(ref, 1)
                    self.assertGreaterEqual(
                        pos,
                        1,
                        f"{path.name}: front-ports[{i}].rear_port_position must be >= 1 (got {pos})",
                    )
                    self.assertLessEqual(
                        pos,
                        bound,
                        f"{path.name}: front-ports[{i}].rear_port_position "
                        f"= {pos} exceeds rear-port '{ref}'.positions={bound}",
                    )

    def test_no_wheatstone_or_chevron_references_in_json(self):
        """Generic-templated catalogue: must not bake operator-specific
        names into the device-type files."""
        forbidden = ("wheatstone", "chevron", "onslow", "pilbara", "mckenzie")
        for path in discover_cassette_files():
            with self.subTest(file=path.name):
                raw = path.read_text(encoding="utf-8").lower()
                for token in forbidden:
                    self.assertNotIn(
                        token,
                        raw,
                        f"{path.name} contains forbidden token '{token}'",
                    )


class LoadOspCassettesCommandTests(TestCase):
    """End-to-end: management command writes the catalogue to the DB."""

    def _call(self):
        out = StringIO()
        call_command("load_osp_cassettes", stdout=out)
        return out.getvalue()

    def test_imports_all_cassettes_cleanly(self):
        # Before: clean slate (the Generic manufacturer may already be
        # auto-created by other test fixtures — count what's there).
        before = DeviceType.objects.filter(slug__in=[p.stem for p in discover_cassette_files()]).count()
        self.assertEqual(before, 0)

        self._call()

        loaded = DeviceType.objects.filter(slug__in=[p.stem for p in discover_cassette_files()])
        self.assertEqual(loaded.count(), EXPECTED_CASSETTE_COUNT)
        # Manufacturer 'Generic' must exist.
        self.assertTrue(Manufacturer.objects.filter(name="Generic").exists())

    def test_idempotent_rerun_keeps_same_count(self):
        self._call()
        first = DeviceType.objects.filter(slug__in=[p.stem for p in discover_cassette_files()]).count()
        self.assertEqual(first, EXPECTED_CASSETTE_COUNT)

        # Re-run: count must not drift, slugs must remain stable.
        self._call()
        second = DeviceType.objects.filter(slug__in=[p.stem for p in discover_cassette_files()]).count()
        self.assertEqual(second, EXPECTED_CASSETTE_COUNT)

    def test_port_templates_materialise_for_mpo_12f_lc(self):
        """Spot check: load the 12F LC cassette and confirm 1 rear with
        12 positions + 12 front ports + 12 mappings landed."""
        self._call()
        dt = DeviceType.objects.get(slug="mpo-12f-lc-cassette")

        rears = RearPortTemplate.objects.filter(device_type=dt)
        self.assertEqual(rears.count(), 1)
        rear = rears.first()
        self.assertEqual(rear.type, "mpo")
        self.assertEqual(rear.positions, 12)

        fronts = FrontPortTemplate.objects.filter(device_type=dt)
        self.assertEqual(fronts.count(), 12)
        for ft in fronts:
            self.assertEqual(ft.type, "lc")

        mappings = PortTemplateMapping.objects.filter(device_type=dt)
        self.assertEqual(mappings.count(), 12)
        positions = sorted(m.rear_port_position for m in mappings)
        self.assertEqual(positions, list(range(1, 13)))

    def test_dry_run_does_not_write(self):
        out = StringIO()
        call_command("load_osp_cassettes", "--dry-run", stdout=out)
        self.assertEqual(
            DeviceType.objects.filter(slug__in=[p.stem for p in discover_cassette_files()]).count(),
            0,
        )
        # Dry-run output should list each file.
        text = out.getvalue()
        for path in discover_cassette_files():
            self.assertIn(path.name, text)


class CassetteCatalogueLocationTests(TestCase):
    """Confirm the JSONs live where the package-data glob will catch them.

    The pyproject.toml ships `device_types/**/*.json` as package-data —
    if the directory ever moves, this test (and the management command
    importing CASSETTES_DIR) must both update."""

    def test_cassettes_dir_exists(self):
        self.assertTrue(CASSETTES_DIR.is_dir(), f"{CASSETTES_DIR} not found")

    def test_cassettes_dir_under_netbox_osp(self):
        # CASSETTES_DIR == netbox_osp/device_types/cassettes
        self.assertEqual(CASSETTES_DIR.name, "cassettes")
        self.assertEqual(CASSETTES_DIR.parent.name, "device_types")
        self.assertEqual(CASSETTES_DIR.parent.parent.name, "netbox_osp")
