from netbox.search import SearchIndex, register_search

from .models import OspCable, SpliceClosure, FibreLink


@register_search
class OspCableIndex(SearchIndex):
    model = OspCable
    fields = (
        ("cid", 100),
        ("description", 500),
        ("part_number", 500),
        ("comments", 1000),
    )


@register_search
class SpliceClosureIndex(SearchIndex):
    model = SpliceClosure
    fields = (
        ("name", 100),
        ("model", 500),
        ("description", 500),
        ("comments", 1000),
    )


@register_search
class FibreLinkIndex(SearchIndex):
    model = FibreLink
    fields = (
        ("name", 100),
        ("description", 500),
        ("comments", 1000),
    )
