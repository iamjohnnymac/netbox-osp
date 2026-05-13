"""Tests for the offline MBTiles proxy view.

Requires a bundled tiles/basemap.mbtiles file under the plugin's static
directory. If it isn't present (devs without an extract checked out)
every test is skipped.
"""
import unittest
from pathlib import Path

from django.contrib.auth import get_user_model
from django.urls import reverse

from utilities.testing import TestCase

import netbox_osp


PLUGIN_DIR = Path(netbox_osp.__file__).resolve().parent
BUNDLED_TILES = PLUGIN_DIR / "static" / "netbox_osp" / "tiles" / "basemap.mbtiles"

TILES_AVAILABLE = BUNDLED_TILES.is_file()


@unittest.skipUnless(
    TILES_AVAILABLE,
    f"bundled basemap.mbtiles not present at {BUNDLED_TILES}",
)
class TileProxyTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="tile-tester",
            email="tile@example.com",
            password="not-used-because-force-login",
        )
        self.client.force_login(self.user)
        self.url = reverse(
            "plugins:netbox_osp:tile_proxy",
            kwargs={"z": 0, "x": 0, "y": 0, "ext": "png"},
        )

    def test_returns_tile(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            resp["Content-Type"].startswith("image/"),
            f"unexpected content-type {resp['Content-Type']!r}",
        )
        self.assertIn("ETag", resp)
        self.assertIn("Cache-Control", resp)

    def test_returns_304_with_matching_etag(self):
        first = self.client.get(self.url)
        self.assertEqual(first.status_code, 200)
        etag = first["ETag"]
        self.assertTrue(etag, "tile proxy did not emit an ETag")
        second = self.client.get(self.url, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(second.status_code, 304)
