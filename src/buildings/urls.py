from django.urls import path

from src.buildings.views import flats, houses

app_name = "buildings"

urlpatterns = [
    path("", houses.HouseListView.as_view(), name="house_list"),
    path(
        "houses/ajax/",
        houses.HouseAjaxDatatableView.as_view(),
        name="house_ajax_list",
    ),
    path(
        "houses/create/", houses.HouseCreateView.as_view(), name="house_create"
    ),
    path(
        "houses/<int:pk>/info/",
        houses.HouseDetailView.as_view(),
        name="house_detail",
    ),
    path(
        "houses/<int:pk>/update/",
        houses.HouseUpdateView.as_view(),
        name="house_update",
    ),
    path(
        "houses/<int:pk>/delete/",
        houses.HouseDeleteView.as_view(),
        name="house_delete",
    ),
    path("flats/", flats.FlatListView.as_view(), name="flat_list"),
    path(
        "flats/ajax/",
        flats.FlatAjaxDatatableView.as_view(),
        name="flat_ajax_list",
    ),
    path("flats/create/", flats.FlatCreateView.as_view(), name="flat_create"),
    path(
        "flats/<int:pk>/detail/",
        flats.FlatDetailView.as_view(),
        name="flat_detail",
    ),
    path(
        "flats/<int:pk>/update/",
        flats.FlatUpdateView.as_view(),
        name="flat_update",
    ),
    path(
        "flats/<int:pk>/delete/",
        flats.FlatDeleteView.as_view(),
        name="flat_delete",
    ),
    path(
        "ajax/houses/select2/",
        houses.HouseSelect2View.as_view(),
        name="house_select2",
    ),
    path(
        "ajax/houses/children/",
        flats.HouseChildrenView.as_view(),
        name="house_children",
    ),
    path(
        "ajax/sections/select2/",
        flats.SectionSelect2View.as_view(),
        name="section_select2",
    ),
    path(
        "ajax/floors/select2/",
        flats.FloorSelect2View.as_view(),
        name="floor_select2",
    ),
    path(
        "ajax/flats/select2/",
        flats.FlatSelect2View.as_view(),
        name="flat_select2",
    ),
]
