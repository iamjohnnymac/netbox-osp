from netbox.api.viewsets import NetBoxModelViewSet

from .. import filtersets, models
from . import serializers


class OspCableViewSet(NetBoxModelViewSet):
    queryset = models.OspCable.objects.prefetch_related("tags").all()
    serializer_class = serializers.OspCableSerializer
    filterset_class = filtersets.OspCableFilterSet


class TubeViewSet(NetBoxModelViewSet):
    queryset = models.Tube.objects.prefetch_related("tags").all()
    serializer_class = serializers.TubeSerializer
    filterset_class = filtersets.TubeFilterSet


class StrandViewSet(NetBoxModelViewSet):
    queryset = models.Strand.objects.prefetch_related("tags").all()
    serializer_class = serializers.StrandSerializer
    filterset_class = filtersets.StrandFilterSet


class SpliceClosureViewSet(NetBoxModelViewSet):
    queryset = models.SpliceClosure.objects.prefetch_related("tags").all()
    serializer_class = serializers.SpliceClosureSerializer
    filterset_class = filtersets.SpliceClosureFilterSet


class SpliceTrayViewSet(NetBoxModelViewSet):
    queryset = models.SpliceTray.objects.prefetch_related("tags").all()
    serializer_class = serializers.SpliceTraySerializer
    filterset_class = filtersets.SpliceTrayFilterSet


class SpliceViewSet(NetBoxModelViewSet):
    queryset = models.Splice.objects.prefetch_related("tags").all()
    serializer_class = serializers.SpliceSerializer
    filterset_class = filtersets.SpliceFilterSet


class FibreLinkViewSet(NetBoxModelViewSet):
    queryset = models.FibreLink.objects.prefetch_related("tags").all()
    serializer_class = serializers.FibreLinkSerializer
    filterset_class = filtersets.FibreLinkFilterSet
