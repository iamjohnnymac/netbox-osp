from django.urls import path
from netbox.views.generic import ObjectChangeLogView, ObjectJournalView

from . import models, views


urlpatterns = [
    # ----- Network Map (full-screen) -----
    path("map/", views.NetworkMapView.as_view(), name="network_map"),
    path("map/data/", views.NetworkMapDataView.as_view(), name="network_map_data"),

    # ----- Tile proxy (offline MBTiles) -----
    path("tiles/<int:z>/<int:x>/<int:y>.<str:ext>", views.TileProxyView.as_view(), name="tile_proxy"),

    # ----- OspCable -----
    path("cables/", views.OspCableListView.as_view(), name="ospcable_list"),
    path("cables/add/", views.OspCableEditView.as_view(), name="ospcable_add"),
    path("cables/edit/", views.OspCableBulkEditView.as_view(), name="ospcable_bulk_edit"),
    path("cables/delete/", views.OspCableBulkDeleteView.as_view(), name="ospcable_bulk_delete"),
    path("cables/import/", views.OspCableBulkImportView.as_view(), name="ospcable_import"),
    path("cables/<int:pk>/", views.OspCableView.as_view(), name="ospcable"),
    path("cables/<int:pk>/edit/", views.OspCableEditView.as_view(), name="ospcable_edit"),
    path("cables/<int:pk>/delete/", views.OspCableDeleteView.as_view(), name="ospcable_delete"),
    path("cables/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="ospcable_changelog", kwargs={"model": models.OspCable}),
    path("cables/<int:pk>/journal/", ObjectJournalView.as_view(),
         name="ospcable_journal", kwargs={"model": models.OspCable}),

    # ----- Tube -----
    path("tubes/", views.TubeListView.as_view(), name="tube_list"),
    path("tubes/add/", views.TubeEditView.as_view(), name="tube_add"),
    path("tubes/<int:pk>/", views.TubeView.as_view(), name="tube"),
    path("tubes/<int:pk>/edit/", views.TubeEditView.as_view(), name="tube_edit"),
    path("tubes/<int:pk>/delete/", views.TubeDeleteView.as_view(), name="tube_delete"),
    path("tubes/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="tube_changelog", kwargs={"model": models.Tube}),

    # ----- Strand -----
    path("strands/", views.StrandListView.as_view(), name="strand_list"),
    path("strands/add/", views.StrandEditView.as_view(), name="strand_add"),
    path("strands/<int:pk>/", views.StrandView.as_view(), name="strand"),
    path("strands/<int:pk>/edit/", views.StrandEditView.as_view(), name="strand_edit"),
    path("strands/<int:pk>/delete/", views.StrandDeleteView.as_view(), name="strand_delete"),
    path("strands/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="strand_changelog", kwargs={"model": models.Strand}),

    # ----- SpliceClosure -----
    path("closures/", views.SpliceClosureListView.as_view(), name="spliceclosure_list"),
    path("closures/add/", views.SpliceClosureEditView.as_view(), name="spliceclosure_add"),
    path("closures/<int:pk>/", views.SpliceClosureView.as_view(), name="spliceclosure"),
    path("closures/<int:pk>/edit/", views.SpliceClosureEditView.as_view(), name="spliceclosure_edit"),
    path("closures/<int:pk>/delete/", views.SpliceClosureDeleteView.as_view(), name="spliceclosure_delete"),
    path("closures/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="spliceclosure_changelog", kwargs={"model": models.SpliceClosure}),

    # ----- SpliceTray -----
    path("trays/", views.SpliceTrayListView.as_view(), name="splicetray_list"),
    path("trays/add/", views.SpliceTrayEditView.as_view(), name="splicetray_add"),
    path("trays/<int:pk>/", views.SpliceTrayView.as_view(), name="splicetray"),
    path("trays/<int:pk>/edit/", views.SpliceTrayEditView.as_view(), name="splicetray_edit"),
    path("trays/<int:pk>/delete/", views.SpliceTrayDeleteView.as_view(), name="splicetray_delete"),
    path("trays/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="splicetray_changelog", kwargs={"model": models.SpliceTray}),

    # ----- Splice -----
    path("splices/", views.SpliceListView.as_view(), name="splice_list"),
    path("splices/add/", views.SpliceEditView.as_view(), name="splice_add"),
    path("splices/<int:pk>/", views.SpliceView.as_view(), name="splice"),
    path("splices/<int:pk>/edit/", views.SpliceEditView.as_view(), name="splice_edit"),
    path("splices/<int:pk>/delete/", views.SpliceDeleteView.as_view(), name="splice_delete"),
    path("splices/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="splice_changelog", kwargs={"model": models.Splice}),

    # ----- FibreLink -----
    path("links/", views.FibreLinkListView.as_view(), name="fibrelink_list"),
    path("links/add/", views.FibreLinkEditView.as_view(), name="fibrelink_add"),
    path("links/<int:pk>/", views.FibreLinkView.as_view(), name="fibrelink"),
    path("links/<int:pk>/edit/", views.FibreLinkEditView.as_view(), name="fibrelink_edit"),
    path("links/<int:pk>/delete/", views.FibreLinkDeleteView.as_view(), name="fibrelink_delete"),
    path("links/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="fibrelink_changelog", kwargs={"model": models.FibreLink}),
]
