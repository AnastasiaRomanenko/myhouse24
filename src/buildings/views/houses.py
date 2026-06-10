from ajax_datatable import AjaxDatatableView
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from src.buildings.forms import FloorFormSet, HouseForm, SectionFormSet
from src.buildings.models import Floors, Houses, Sections
from src.core.mixins import RoleRequiredMixin
from src.core.select2 import request_page, request_term, select2_response
from src.users.enums import Status
from src.users.models import Users


class HouseListView(RoleRequiredMixin, TemplateView):
    permission_required = "has_houses"
    template_name = "houses/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Budynki"
        context["breadcrumbs"] = [
            {"title": "Budynki", "url": reverse_lazy("buildings:house_list")},
        ]
        return context


class HouseAjaxDatatableView(RoleRequiredMixin, AjaxDatatableView):
    permission_required = "has_houses"
    model = Houses
    title = "Budynki"
    initial_order = [["id", "asc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]

    column_defs = [
        {"name": "pk", "title": "#"},
        {"name": "title", "title": "Nazwa"},
        {"name": "address", "title": "Adres"},
        {"name": "actions", "title": ""},
    ]

    def get_initial_queryset(self, request=None):
        queryset = Houses.objects.all()

        if request is None:
            return queryset

        title = request.GET.get("title", "").strip()
        address = request.GET.get("address", "").strip()

        if title:
            queryset = queryset.filter(title__icontains=title)
        if address:
            queryset = queryset.filter(address__icontains=address)

        return queryset

    def render_column(self, row, column):
        if column == "actions":
            update_url = reverse("buildings:house_update", args=[row.pk])
            delete_url = reverse("buildings:house_delete", args=[row.pk])
            csrf = self.request.COOKIES.get("csrftoken", "")

            return f"""
                <div class="btn-group pull-right">
                    <a class="btn btn-default btn-sm" href="{update_url}" title="Edytuj" data-toggle="tooltip">
                        <i class="fa fa-pencil"></i>
                    </a>
                    <form method="POST" action="{delete_url}" style="display: inline;">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                        <button type="submit" class="btn btn-default btn-sm" title="Usuń" data-toggle="tooltip"
                                onclick="return confirm('Czy na pewno chcesz usunąć ten element?');">
                            <i class="fa fa-trash"></i>
                        </button>
                    </form>
                </div>
            """

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        row["row_href"] = reverse("buildings:house_detail", args=[obj.pk])
        return row


class HouseDetailView(RoleRequiredMixin, TemplateView):
    permission_required = "has_houses"
    template_name = "houses/detail.html"

    @staticmethod
    def _workers_json():
        users = Users.objects.select_related("role").filter(
            is_active=True, is_staff=True, status=Status.ACTIVE
        )
        return [
            {
                "id": u.pk,
                "email": u.email,
                "role": u.role.role if u.role else "",
            }
            for u in users
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        house = get_object_or_404(Houses, pk=self.kwargs["pk"])
        context["house"] = house
        context["page_title"] = house.title
        context["breadcrumbs"] = [
            {"title": "Budynki", "url": reverse_lazy("buildings:house_list")},
            {
                "title": house.title,
                "url": reverse_lazy(
                    "buildings:house_detail", kwargs={"pk": house.pk}
                ),
            },
        ]
        context["workers"] = self._workers_json()
        context["floors_count"] = Floors.objects.filter(house=house).count()
        context["sections_count"] = Sections.objects.filter(
            house=house
        ).count()
        return context


class HouseCreateView(RoleRequiredMixin, CreateView):
    permission_required = "has_houses"
    model = Houses
    form_class = HouseForm
    template_name = "houses/form.html"
    success_url = reverse_lazy("buildings:house_list")

    @staticmethod
    def _workers_json():
        users = Users.objects.select_related("role").filter(
            is_active=True,
            is_staff=True,
            status=Status.ACTIVE,
        )
        return [
            {
                "id": u.pk,
                "email": u.email,
                "role": u.role.role if u.role else "",
            }
            for u in users
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.POST:
            context["section_formset"] = SectionFormSet(
                self.request.POST,
                prefix="sections",
            )
            context["floor_formset"] = FloorFormSet(
                self.request.POST,
                prefix="floors",
            )
            context["selected_worker_ids"] = self.request.POST.getlist(
                "workers"
            )
        else:
            context["section_formset"] = SectionFormSet(prefix="sections")
            context["floor_formset"] = FloorFormSet(prefix="floors")
            context["selected_worker_ids"] = []

        context["house"] = None
        context["workers_json"] = self._workers_json()
        context["page_title"] = "Nowy budynek"
        context["breadcrumbs"] = [
            {"title": "Budynki", "url": reverse_lazy("buildings:house_list")},
            {
                "title": "Nowy budynek",
                "url": reverse_lazy("buildings:house_create"),
            },
        ]
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        section_formset = context["section_formset"]
        floor_formset = context["floor_formset"]

        if not section_formset.is_valid() or not floor_formset.is_valid():
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()

            section_formset.instance = self.object
            floor_formset.instance = self.object

            section_formset.save()
            floor_formset.save()

        messages.success(self.request, "Budynek utworzono.")
        return redirect(self.get_success_url())


class HouseUpdateView(RoleRequiredMixin, UpdateView):
    permission_required = "has_houses"
    model = Houses
    form_class = HouseForm
    template_name = "houses/form.html"
    context_object_name = "house"
    pk_url_kwarg = "pk"
    success_url = reverse_lazy("buildings:house_list")

    @staticmethod
    def _workers_json():
        users = Users.objects.select_related("role").filter(
            is_active=True,
            is_staff=True,
            status=Status.ACTIVE,
        )
        return [
            {
                "id": u.pk,
                "email": u.email,
                "role": u.role.role if u.role else "",
            }
            for u in users
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        house = self.object

        if self.request.POST:
            context["section_formset"] = SectionFormSet(
                self.request.POST,
                instance=house,
                prefix="sections",
            )
            context["floor_formset"] = FloorFormSet(
                self.request.POST,
                instance=house,
                prefix="floors",
            )
            context["selected_worker_ids"] = self.request.POST.getlist(
                "workers"
            )
        else:
            context["section_formset"] = SectionFormSet(
                instance=house,
                prefix="sections",
            )
            context["floor_formset"] = FloorFormSet(
                instance=house,
                prefix="floors",
            )
            if self.object and self.object.pk:
                context["selected_worker_ids"] = [
                    str(worker.pk) for worker in self.object.workers.all()
                ]
            else:
                context["selected_worker_ids"] = []

        context["workers_json"] = self._workers_json()
        context["page_title"] = f"Edytuj: {house.title}"
        context["breadcrumbs"] = [
            {"title": "Budynki", "url": reverse_lazy("buildings:house_list")},
            {
                "title": house.title,
                "url": reverse_lazy(
                    "buildings:house_detail", kwargs={"pk": house.pk}
                ),
            },
            {
                "title": "Edytuj",
                "url": reverse_lazy(
                    "buildings:house_update", kwargs={"pk": house.pk}
                ),
            },
        ]
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        section_formset = context["section_formset"]
        floor_formset = context["floor_formset"]

        if not section_formset.is_valid() or not floor_formset.is_valid():
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()

            section_formset.instance = self.object
            floor_formset.instance = self.object

            section_formset.save()
            floor_formset.save()

        messages.success(self.request, "Budynek zaktualizowano.")
        return redirect(self.get_success_url())


class HouseDeleteView(RoleRequiredMixin, View):
    permission_required = "has_houses"

    def post(self, request, pk):
        house = get_object_or_404(Houses, pk=pk)
        title = house.title
        house.delete()
        messages.success(request, f"Budynek «{title}» usunięto.")
        return redirect(reverse_lazy("buildings:house_list"))


class HouseSelect2View(RoleRequiredMixin, View):
    def get(self, request):
        term = request_term(request)
        queryset = Houses.objects.order_by("title", "address")

        if term:
            queryset = queryset.filter(
                Q(title__icontains=term) | Q(address__icontains=term)
            )

        return JsonResponse(
            select2_response(
                queryset,
                request_page(request),
                lambda house: (
                    f"{house.title} ({house.address})"
                    if house.address
                    else house.title
                ),
            )
        )
