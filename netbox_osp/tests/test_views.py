"""UI permission-matrix tests for netbox_osp.

We subclass NetBox's PrimaryObjectViewTestCase, which auto-generates ~24
permission tests per model covering get / list / create / edit / delete and
their bulk variants in three variants each: without permission, with
permission, and with constrained object-level permission.

Scope for v0.1.0: start with SpliceClosure as the canary. It's standalone
(no FK dependency on other netbox_osp models), exercises every CRUD path,
and validates the plugin URL-namespace override pattern. The other 7 models
follow in a focused follow-up — they each have invariants (fibre arithmetic
on OspCable, strand-pair check on Splice, OneToOne uniqueness on
LocationGeo) that need careful per-test fixtures.

REST API permission tests (APIViewTestCases.APIViewTestCase) are deferred
because NetBox 4.6's APITestCase.setUp() creates a v2 Token, which fails
without API_TOKEN_PEPPERS in the test configuration. Will revisit once the
CI config sets that.
"""
from utilities.testing import ViewTestCases

from netbox_osp.choices import ClosureTypeChoices, OspStatusChoices
from netbox_osp.models import SpliceClosure


class _PluginBaseURLMixin:
    """Override the default base URL pattern for plugin-namespaced models.

    Pattern: 'plugins:<app_label>:<model_name>_<action>'.
    """
    def _get_base_url(self):
        return "plugins:{}:{}_{{}}".format(
            self.model._meta.app_label,
            self.model._meta.model_name,
        )


class SpliceClosureTestCase(_PluginBaseURLMixin, ViewTestCases.PrimaryObjectViewTestCase):
    """SpliceClosure has no FK dependency on other plugin models — the
    cleanest model to exercise the permission matrix on.
    """
    model = SpliceClosure

    # `capacity_splices` round-trips fine but `comments` is Markdown-rendered
    # on the model and the mixin's assertInstanceEqual compares raw vs.
    # rendered. Easiest fix: exclude comments from the post-save comparison.
    validation_excluded_fields = ("comments",)

    @classmethod
    def setUpTestData(cls):
        SpliceClosure.objects.bulk_create([
            SpliceClosure(name="V-CL-001"),
            SpliceClosure(name="V-CL-002"),
            SpliceClosure(name="V-CL-003"),
        ])
        cls.form_data = {
            "name": "V-CL-NEW",
            "closure_type": ClosureTypeChoices.DOME,
            "capacity_splices": 144,
            "status": OspStatusChoices.STATUS_PLANNED,
            "description": "View-test closure",
            "comments": "",
            "tags": [],
        }
        cls.bulk_edit_data = {
            "status": OspStatusChoices.STATUS_ACTIVE,
            "description": "Bulk-edited closure",
        }
        cls.csv_data = (
            "name,closure_type,capacity_splices,status",
            "V-CL-CSV-1,dome,288,planned",
            "V-CL-CSV-2,dome,288,planned",
            "V-CL-CSV-3,dome,288,planned",
        )
