from ajax_datatable import AjaxDatatableView
from django.contrib import messages
from django.db.models import Case, F, FloatField, Sum, Value, When
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, TemplateView

from src.buildings.forms import FlatForm
from src.buildings.models import Flats, Floors, Houses, Sections
from src.core.mixins import RoleRequiredMixin
from src.core.select2 import request_page, request_term, select2_response
from src.finances.enums import AccountingType
from src.settings.models import Tariffs
from src.users.models import Users

SELECT2_PAGE_SIZE = 10


def owner_label(owner):
    parts = [owner.last_name, owner.first_name, owner.patronimic_name]
    full_name = " ".join(part for part in parts if part)
    return full_name or owner.email


def selected_object(model, value):
    if not value:
        return None
    try:
        return model.objects.get(pk=value)
    except (model.DoesNotExist, TypeError, ValueError):
        return None


def selected_pk(value):
    value = str(value or "").strip()
    return value if value.isdigit() else None


def with_balance(queryset):
    return queryset.annotate(
        balance=Coalesce(
            Sum(
                Case(
                    When(
                        bank_book__accounting_bank_book_rows__type=AccountingType.INCOME,
                        then=F("bank_book__accounting_bank_book_rows__amount"),
                    ),
                    When(
                        bank_book__accounting_bank_book_rows__type=AccountingType.EXPENSE,
                        then=-F(
                            "bank_book__accounting_bank_book_rows__amount"
                        ),
                    ),
                    default=Value(0.0),
                    output_field=FloatField(),
                ),
            ),
            Value(0.0),
            output_field=FloatField(),
        ),
    )


class FlatListView(RoleRequiredMixin, TemplateView):
    permission_required = "has_flats"
    template_name = "flats/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Mieszkania"
        context["breadcrumbs"] = [
            {
                "title": "Mieszkania",
                "url": reverse_lazy("buildings:flat_list"),
            },
        ]
        return context


class FlatAjaxDatatableView(RoleRequiredMixin, AjaxDatatableView):
    permission_required = "has_flats"
    model = Flats
    title = "Mieszkania"
    initial_order = [["id", "asc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    disable_queryset_optimization = True

    column_defs = [
        {"name": "number", "title": "Nr mieszkania"},
        {"name": "house", "title": "Budynek"},
        {"name": "section", "title": "Sekcja"},
        {"name": "floor", "title": "Piętro"},
        {"name": "owner", "title": "Właściciel"},
        {"name": "balance", "title": "Saldo (zł)"},
        {"name": "actions", "title": ""},
    ]

    def get_initial_queryset(self, request=None):
        queryset = Flats.objects.select_related(
            "house",
            "section",
            "floor",
            "owner",
            "tariff",
        )
        queryset = with_balance(queryset)

        if request is None:
            return queryset

        number = request.GET.get("number", "").strip()
        house_id = selected_pk(request.GET.get("house_id", ""))
        section_id = selected_pk(request.GET.get("section_id", ""))
        floor_id = selected_pk(request.GET.get("floor_id", ""))
        owner_id = selected_pk(
            request.GET.get("owner_id", "") or request.GET.get("user_id", "")
        )
        has_debt = request.GET.get("has_debt", "").strip()

        if number:
            if number.isdigit():
                queryset = queryset.filter(number=number)
            else:
                queryset = queryset.none()

        if house_id:
            queryset = queryset.filter(house_id=house_id)

        if section_id:
            queryset = queryset.filter(section_id=section_id)

        if floor_id:
            queryset = queryset.filter(floor_id=floor_id)

        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)

        if has_debt == "1":
            queryset = queryset.filter(balance__lt=0)
        elif has_debt == "0":
            queryset = queryset.filter(balance__gte=0)

        return queryset

    def render_column(self, row, column):
        if column == "house":
            return (
                row.house.title
                if row.house
                else "<span class='not-set'>(nie ustawiono)</span>"
            )

        if column == "section":
            return (
                row.section.title
                if row.section
                else "<span class='not-set'>(nie ustawiono)</span>"
            )

        if column == "floor":
            return (
                row.floor.title
                if row.floor
                else "<span class='not-set'>(nie ustawiono)</span>"
            )

        if column == "owner":
            if not row.owner:
                return "<span class='not-set'>(nie ustawiono)</span>"
            owner_url = reverse("users:owner_profile", args=[row.owner_id])
            return f'<a href="{owner_url}">{row.owner}</a>'

        if column == "balance":
            css_class = "text-default"
            if row.balance < 0:
                css_class = "text-red"
            elif row.balance > 0:
                css_class = "text-green"
            return f'<span class="{css_class}">{row.balance:.2f}</span>'

        if column == "actions":
            update_url = reverse("buildings:flat_update", args=[row.pk])
            delete_url = reverse("buildings:flat_delete", args=[row.pk])
            csrf = self.request.COOKIES.get("csrftoken", "")
            return f"""
                <div class="btn-group pull-right">
                    <a class="btn btn-default btn-sm" href="{update_url}" title="Edytuj" data-toggle="tooltip">
                        <i class="fa fa-pencil"></i>
                    </a>
                    <form method="post" action="{delete_url}" style="display: inline;">
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
        row["row_href"] = reverse("buildings:flat_detail", args=[obj.pk])
        return row


class FlatDetailView(RoleRequiredMixin, DetailView):
    permission_required = "has_flats"
    model = Flats
    template_name = "flats/detail.html"
    context_object_name = "flat"

    def get_queryset(self):
        return Flats.objects.select_related(
            "house",
            "section",
            "floor",
            "owner",
            "tariff",
            "bank_book",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        flat = self.object
        context["page_title"] = f"Mieszkanie №{flat.number}"
        context["breadcrumbs"] = [
            {
                "title": "Mieszkania",
                "url": reverse_lazy("buildings:flat_list"),
            },
            {
                "title": f"Mieszkanie №{flat.number}",
                "url": reverse_lazy(
                    "buildings:flat_detail", kwargs={"pk": flat.pk}
                ),
            },
        ]
        context["bank_book"] = getattr(flat, "bank_book", None)
        context["balance"] = getattr(flat, "balance", None)
        if context["balance"] is None:
            context["balance"] = (
                with_balance(Flats.objects.filter(pk=flat.pk))
                .values_list("balance", flat=True)
                .first()
            )
        return context


class FlatFormContextMixin:
    template_name = "flats/form.html"

    def get_form_context(self, form, flat=None):
        house_value = form["house"].value()
        section_value = form["section"].value()
        floor_value = form["floor"].value()
        owner_value = form["owner"].value()

        selected_house = selected_object(Houses, house_value)

        if selected_house:
            sections = Sections.objects.filter(house=selected_house).order_by(
                "title"
            )
            floors = Floors.objects.filter(house=selected_house).order_by(
                "title"
            )
        else:
            sections = Sections.objects.none()
            floors = Floors.objects.none()

        if flat:
            page_title = "Edytuj mieszkanie"
            breadcrumbs = [
                {
                    "title": "Mieszkania",
                    "url": reverse_lazy("buildings:flat_list"),
                },
                {
                    "title": f"Mieszkanie №{flat.number}",
                    "url": reverse_lazy(
                        "buildings:flat_detail", kwargs={"pk": flat.pk}
                    ),
                },
                {
                    "title": "Edytuj",
                    "url": reverse_lazy(
                        "buildings:flat_update", kwargs={"pk": flat.pk}
                    ),
                },
            ]
            form_url = reverse_lazy(
                "buildings:flat_update", kwargs={"pk": flat.pk}
            )
        else:
            page_title = "Nowe mieszkanie"
            breadcrumbs = [
                {
                    "title": "Mieszkania",
                    "url": reverse_lazy("buildings:flat_list"),
                },
                {
                    "title": "Nowe mieszkanie",
                    "url": reverse_lazy("buildings:flat_create"),
                },
            ]
            form_url = reverse_lazy("buildings:flat_create")

        return {
            "form": form,
            "flat": flat,
            "form_url": form_url,
            "page_title": page_title,
            "breadcrumbs": breadcrumbs,
            "selected_house": selected_house,
            "selected_section": selected_object(Sections, section_value),
            "selected_floor": selected_object(Floors, floor_value),
            "selected_owner": selected_object(Users, owner_value),
            "sections": sections,
            "floors": floors,
            "tariffs": Tariffs.objects.order_by("title"),
        }


class FlatCreateView(RoleRequiredMixin, FlatFormContextMixin, View):
    permission_required = "has_flats"

    def get(self, request):
        form = FlatForm()
        return render(request, self.template_name, self.get_form_context(form))

    def post(self, request):
        form = FlatForm(request.POST)
        if form.is_valid():
            flat = form.save()
            messages.success(request, "Mieszkanie utworzono.")
            if "action_save_add" in request.POST:
                return redirect(reverse_lazy("buildings:flat_create"))
            return redirect(
                reverse_lazy("buildings:flat_detail", kwargs={"pk": flat.pk})
            )

        return render(request, self.template_name, self.get_form_context(form))


class FlatUpdateView(RoleRequiredMixin, FlatFormContextMixin, View):
    permission_required = "has_flats"

    def get_object(self, pk):
        return get_object_or_404(Flats, pk=pk)

    def get(self, request, pk):
        flat = self.get_object(pk)
        form = FlatForm(instance=flat)
        return render(
            request, self.template_name, self.get_form_context(form, flat)
        )

    def post(self, request, pk):
        flat = self.get_object(pk)
        form = FlatForm(request.POST, instance=flat)
        if form.is_valid():
            flat = form.save()
            messages.success(request, "Mieszkanie zapisano.")
            if "action_save_add" in request.POST:
                return redirect(reverse_lazy("buildings:flat_create"))
            return redirect(
                reverse_lazy("buildings:flat_detail", kwargs={"pk": flat.pk})
            )

        return render(
            request, self.template_name, self.get_form_context(form, flat)
        )


class FlatDeleteView(RoleRequiredMixin, View):
    permission_required = "has_flats"
    success_url = reverse_lazy("buildings:flat_list")

    def post(self, request, pk):
        flat = get_object_or_404(Flats, pk=pk)
        number = flat.number
        try:
            flat.delete()
        except ProtectedError:
            messages.error(
                request,
                "Mieszkanie jest używane w systemie i nie może zostać usunięte.",
            )
            return redirect(self.success_url)

        messages.success(request, f"Mieszkanie №{number} usunięto.")
        return redirect(self.success_url)


class HouseChildrenView(RoleRequiredMixin, View):
    def get(self, request):
        house_id = selected_pk(request.GET.get("house_id"))
        sections = Sections.objects.none()
        floors = Floors.objects.none()

        if house_id:
            sections = Sections.objects.filter(house_id=house_id).order_by(
                "title"
            )
            floors = Floors.objects.filter(house_id=house_id).order_by("title")

        return JsonResponse(
            {
                "sections": [
                    {"id": section.pk, "text": section.title}
                    for section in sections
                ],
                "floors": [
                    {"id": floor.pk, "text": floor.title} for floor in floors
                ],
            }
        )


class SectionSelect2View(RoleRequiredMixin, View):
    def get(self, request):
        term = request_term(request)
        house_id = selected_pk(request.GET.get("house_id"))
        queryset = Sections.objects.order_by("title")
        if house_id:
            queryset = queryset.filter(house_id=house_id)
        if term:
            queryset = queryset.filter(title__icontains=term)
        return JsonResponse(
            select2_response(
                queryset, request_page(request), lambda s: s.title
            )
        )


class FloorSelect2View(RoleRequiredMixin, View):
    def get(self, request):
        term = request_term(request)
        house_id = selected_pk(request.GET.get("house_id"))
        queryset = Floors.objects.order_by("title")
        if house_id:
            queryset = queryset.filter(house_id=house_id)
        if term:
            queryset = queryset.filter(title__icontains=term)
        return JsonResponse(
            select2_response(
                queryset, request_page(request), lambda f: f.title
            )
        )


class FlatSelect2View(RoleRequiredMixin, View):
    def get(self, request):
        term = request_term(request)
        house_id = selected_pk(request.GET.get("house_id"))
        section_id = selected_pk(request.GET.get("section_id"))
        floor_id = selected_pk(request.GET.get("floor_id"))
        queryset = Flats.objects.order_by("number")
        if house_id:
            queryset = queryset.filter(house_id=house_id)
        if section_id:
            queryset = queryset.filter(section_id=section_id)
        if floor_id:
            queryset = queryset.filter(floor_id=floor_id)
        if term:
            if term.isdigit():
                queryset = queryset.filter(number=int(term))
            else:
                queryset = queryset.none()
        return JsonResponse(
            select2_response(
                queryset, request_page(request), lambda f: str(f.number)
            )
        )
