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
    # Order matters: edit/, delete/, import/ MUST precede the greedy <int:pk>/.
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
    path("tubes/edit/", views.TubeBulkEditView.as_view(), name="tube_bulk_edit"),
    path("tubes/delete/", views.TubeBulkDeleteView.as_view(), name="tube_bulk_delete"),
    path("tubes/import/", views.TubeBulkImportView.as_view(), name="tube_import"),
    path("tubes/<int:pk>/", views.TubeView.as_view(), name="tube"),
    path("tubes/<int:pk>/edit/", views.TubeEditView.as_view(), name="tube_edit"),
    path("tubes/<int:pk>/delete/", views.TubeDeleteView.as_view(), name="tube_delete"),
    path("tubes/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="tube_changelog", kwargs={"model": models.Tube}),

    # ----- Strand -----
    path("strands/", views.StrandListView.as_view(), name="strand_list"),
    path("strands/add/", views.StrandEditView.as_view(), name="strand_add"),
    path("strands/edit/", views.StrandBulkEditView.as_view(), name="strand_bulk_edit"),
    path("strands/delete/", views.StrandBulkDeleteView.as_view(), name="strand_bulk_delete"),
    path("strands/import/", views.StrandBulkImportView.as_view(), name="strand_import"),
    path("strands/<int:pk>/", views.StrandView.as_view(), name="strand"),
    path("strands/<int:pk>/edit/", views.StrandEditView.as_view(), name="strand_edit"),
    path("strands/<int:pk>/delete/", views.StrandDeleteView.as_view(), name="strand_delete"),
    path("strands/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="strand_changelog", kwargs={"model": models.Strand}),
    # PR E — visual core tracer.
    path("strands/<int:pk>/trace/", views.StrandTraceView.as_view(), name="strand_trace"),
    path("ports/<int:pk>/trace/", views.FrontPortTraceRedirectView.as_view(),
         name="frontport_trace"),
    path("interfaces/<int:pk>/trace/", views.InterfaceTraceRedirectView.as_view(),
         name="interface_trace"),

    # ----- SpliceClosure -----
    path("closures/", views.SpliceClosureListView.as_view(), name="spliceclosure_list"),
    path("closures/add/", views.SpliceClosureEditView.as_view(), name="spliceclosure_add"),
    path("closures/edit/", views.SpliceClosureBulkEditView.as_view(), name="spliceclosure_bulk_edit"),
    path("closures/delete/", views.SpliceClosureBulkDeleteView.as_view(), name="spliceclosure_bulk_delete"),
    path("closures/import/", views.SpliceClosureBulkImportView.as_view(), name="spliceclosure_import"),
    path("closures/<int:pk>/", views.SpliceClosureView.as_view(), name="spliceclosure"),
    path("closures/<int:pk>/edit/", views.SpliceClosureEditView.as_view(), name="spliceclosure_edit"),
    path("closures/<int:pk>/delete/", views.SpliceClosureDeleteView.as_view(), name="spliceclosure_delete"),
    path("closures/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="spliceclosure_changelog", kwargs={"model": models.SpliceClosure}),

    # ----- SpliceTray -----
    path("trays/", views.SpliceTrayListView.as_view(), name="splicetray_list"),
    path("trays/add/", views.SpliceTrayEditView.as_view(), name="splicetray_add"),
    path("trays/edit/", views.SpliceTrayBulkEditView.as_view(), name="splicetray_bulk_edit"),
    path("trays/delete/", views.SpliceTrayBulkDeleteView.as_view(), name="splicetray_bulk_delete"),
    path("trays/import/", views.SpliceTrayBulkImportView.as_view(), name="splicetray_import"),
    path("trays/<int:pk>/", views.SpliceTrayView.as_view(), name="splicetray"),
    path("trays/<int:pk>/edit/", views.SpliceTrayEditView.as_view(), name="splicetray_edit"),
    path("trays/<int:pk>/delete/", views.SpliceTrayDeleteView.as_view(), name="splicetray_delete"),
    path("trays/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="splicetray_changelog", kwargs={"model": models.SpliceTray}),

    # ----- Splice -----
    path("splices/", views.SpliceListView.as_view(), name="splice_list"),
    path("splices/add/", views.SpliceEditView.as_view(), name="splice_add"),
    path("splices/edit/", views.SpliceBulkEditView.as_view(), name="splice_bulk_edit"),
    path("splices/delete/", views.SpliceBulkDeleteView.as_view(), name="splice_bulk_delete"),
    path("splices/import/", views.SpliceBulkImportView.as_view(), name="splice_import"),
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

    # ----- LocationGeo -----
    path("location-geos/", views.LocationGeoListView.as_view(), name="locationgeo_list"),
    path("location-geos/add/", views.LocationGeoEditView.as_view(), name="locationgeo_add"),
    path("location-geos/edit/", views.LocationGeoBulkEditView.as_view(), name="locationgeo_bulk_edit"),
    path("location-geos/delete/", views.LocationGeoBulkDeleteView.as_view(), name="locationgeo_bulk_delete"),
    path("location-geos/import/", views.LocationGeoBulkImportView.as_view(), name="locationgeo_import"),
    path("location-geos/<int:pk>/", views.LocationGeoView.as_view(), name="locationgeo"),
    path("location-geos/<int:pk>/edit/", views.LocationGeoEditView.as_view(), name="locationgeo_edit"),
    path("location-geos/<int:pk>/delete/", views.LocationGeoDeleteView.as_view(), name="locationgeo_delete"),
    path("location-geos/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="locationgeo_changelog", kwargs={"model": models.LocationGeo}),

    # ----- FibreTrunk -----
    path("trunks/", views.FibreTrunkListView.as_view(), name="fibretrunk_list"),
    path("trunks/add/", views.FibreTrunkEditView.as_view(), name="fibretrunk_add"),
    path("trunks/edit/", views.FibreTrunkBulkEditView.as_view(), name="fibretrunk_bulk_edit"),
    path("trunks/delete/", views.FibreTrunkBulkDeleteView.as_view(), name="fibretrunk_bulk_delete"),
    path("trunks/import/", views.FibreTrunkBulkImportView.as_view(), name="fibretrunk_import"),
    path("trunks/<int:pk>/", views.FibreTrunkView.as_view(), name="fibretrunk"),
    path("trunks/<int:pk>/edit/", views.FibreTrunkEditView.as_view(), name="fibretrunk_edit"),
    path("trunks/<int:pk>/delete/", views.FibreTrunkDeleteView.as_view(), name="fibretrunk_delete"),
    path("trunks/<int:pk>/import-cables/",
         views.TrunkImportFromCablesView.as_view(), name="fibretrunk_import_cables"),
    path("trunks/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="fibretrunk_changelog", kwargs={"model": models.FibreTrunk}),

    # ----- TrunkBreakout -----
    path("trunk-breakouts/", views.TrunkBreakoutListView.as_view(), name="trunkbreakout_list"),
    path("trunk-breakouts/add/", views.TrunkBreakoutEditView.as_view(), name="trunkbreakout_add"),
    path("trunk-breakouts/edit/", views.TrunkBreakoutBulkEditView.as_view(), name="trunkbreakout_bulk_edit"),
    path("trunk-breakouts/delete/", views.TrunkBreakoutBulkDeleteView.as_view(), name="trunkbreakout_bulk_delete"),
    path("trunk-breakouts/import/", views.TrunkBreakoutBulkImportView.as_view(), name="trunkbreakout_import"),
    path("trunk-breakouts/<int:pk>/", views.TrunkBreakoutView.as_view(), name="trunkbreakout"),
    path("trunk-breakouts/<int:pk>/edit/", views.TrunkBreakoutEditView.as_view(), name="trunkbreakout_edit"),
    path("trunk-breakouts/<int:pk>/delete/", views.TrunkBreakoutDeleteView.as_view(), name="trunkbreakout_delete"),
    path("trunk-breakouts/<int:pk>/changelog/", ObjectChangeLogView.as_view(),
         name="trunkbreakout_changelog", kwargs={"model": models.TrunkBreakout}),
]
