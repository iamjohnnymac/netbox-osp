"""Tests for the v0.3.0 field QR code panel on SpliceClosure / SpliceTray
detail pages.

The QR panel is rendered by `_QrCodeMixin.right_page()` on
`SpliceClosureQrCode` and `SpliceTrayQrCode` (in
`netbox_osp/template_content.py`), encodes the page's absolute URL,
and uses the pure-Python `qrcode` library's SVG factory so we don't
require Pillow.

We can't easily exercise NetBox's plugin-template-extension hook in
DjangoTestCase isolation (the registry is wired at process start-up).
The tests below cover the registration list, the SVG renderer helper,
and the partial template — together they're enough to catch any
regression that would break the in-process integration.
"""

from django.template.loader import get_template
from django.test import TestCase as DjangoTestCase


class QrCodePanelRegistrationTests(DjangoTestCase):
    """The QR PluginTemplateExtension subclasses are registered and aimed
    at the documented models."""

    def test_qr_template_extensions_are_registered(self):
        from netbox_osp import template_content as tc

        names = {cls.__name__ for cls in tc.template_extensions}
        for expected in ("SpliceClosureQrCode", "SpliceTrayQrCode"):
            self.assertIn(
                expected, names,
                f"{expected} missing from template_extensions",
            )

    def test_qr_extensions_target_the_right_models(self):
        from netbox_osp import template_content as tc

        cls_by_name = {c.__name__: c for c in tc.template_extensions}
        self.assertEqual(
            cls_by_name["SpliceClosureQrCode"].models,
            ["netbox_osp.spliceclosure"],
        )
        self.assertEqual(
            cls_by_name["SpliceTrayQrCode"].models,
            ["netbox_osp.splicetray"],
        )


class QrSvgRendererTests(DjangoTestCase):
    """The internal `_render_qr_svg` helper produces inline SVG without
    the leading XML declaration, suitable for embedding directly in an
    HTML page."""

    def test_render_qr_svg_returns_inline_svg(self):
        from netbox_osp.template_content import QRCODE_AVAILABLE, _render_qr_svg

        if not QRCODE_AVAILABLE:
            self.skipTest("qrcode library not installed (optional [qrcode] extra)")
        svg = _render_qr_svg("https://demo.example.com/plugins/osp/closures/42/")
        self.assertIsInstance(svg, str)
        self.assertNotEqual(svg, "")
        # XML declaration must be stripped — it confuses inline HTML parsers.
        self.assertFalse(svg.startswith("<?xml"))
        # Must contain a real SVG element with QR path data.
        self.assertIn("<svg", svg)
        self.assertIn("<path", svg)
        self.assertIn("</svg>", svg)

    def test_render_qr_svg_encodes_different_urls_differently(self):
        from netbox_osp.template_content import QRCODE_AVAILABLE, _render_qr_svg

        if not QRCODE_AVAILABLE:
            self.skipTest("qrcode library not installed (optional [qrcode] extra)")
        svg_a = _render_qr_svg("https://example.com/a/")
        svg_b = _render_qr_svg("https://example.com/b-much-longer-path/")
        # Different URLs must produce different QR matrices.
        self.assertNotEqual(svg_a, svg_b)


class QrPanelTemplateTests(DjangoTestCase):
    """The partial template at `netbox_osp/inc/qrcode_panel.html` loads
    and renders with the expected context keys."""

    def test_partial_renders_with_url_and_svg(self):
        template = get_template("netbox_osp/inc/qrcode_panel.html")
        rendered = template.render({
            "absolute_url": "https://demo.example.com/plugins/osp/closures/42/",
            "qr_svg": "<svg><path d='M0 0'/></svg>",
        })
        self.assertIn("Field QR code", rendered)
        self.assertIn("https://demo.example.com/plugins/osp/closures/42/", rendered)
        self.assertIn("<svg>", rendered)
        self.assertIn("Scan this code", rendered)


class QrPanelGracefulDegradationTests(DjangoTestCase):
    """When the qrcode library isn't importable, `right_page()` must
    return an empty string rather than raising — the base install of
    `netbox-osp` without the [qrcode] extra must keep working."""

    def test_right_page_returns_empty_when_qrcode_unavailable(self):
        from netbox_osp import template_content as tc

        # Force the unavailable path without uninstalling qrcode.
        original = tc.QRCODE_AVAILABLE
        tc.QRCODE_AVAILABLE = False
        try:
            ext = tc.SpliceClosureQrCode(context={})
            self.assertEqual(ext.right_page(), "")
        finally:
            tc.QRCODE_AVAILABLE = original
