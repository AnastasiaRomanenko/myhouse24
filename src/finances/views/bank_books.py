from ajax_datatable import AjaxDatatableView
from django.contrib import messages
from django.db.models import Case, F, FloatField, Q, Sum, Value, When
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, TemplateView

from src.buildings.models import Floors, Houses, Sections
from src.core.mixins import RoleRequiredMixin
from src.core.select2 import (
    request_page,
    request_term,
    select2_response,
    selected_object,
)
from src.finances.enums import AccountingType
from src.finances.forms import BankBookForm
from src.finances.models import BankBooks


def bank_book_balance(bank_book):
    rows = bank_book.accounting_bank_book_rows.all()
    income = sum(r.amount for r in rows if r.type == AccountingType.INCOME)
    expense = sum(r.amount for r in rows if r.type == AccountingType.EXPENSE)
    return income - expense


def with_balance(queryset):
    return queryset.annotate(
        balance=Coalesce(
            Sum(
                Case(
                    When(
                        accounting_bank_book_rows__type=AccountingType.INCOME,
                        then=F("accounting_bank_book_rows__amount"),
                    ),
                    When(
                        accounting_bank_book_rows__type=AccountingType.EXPENSE,
                        then=-F("accounting_bank_book_rows__amount"),
                    ),
                    default=Value(0.0),
                    output_field=FloatField(),
                ),
            ),
            Value(0.0),
            output_field=FloatField(),
        ),
    )


class BankBooksListView(RoleRequiredMixin, TemplateView):
    permission_required = "has_bank_books"
    template_name = "bank_books/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Konta osobiste"
        context["breadcrumbs"] = [
            {
                "title": "Konta osobiste",
                "url": reverse_lazy("finances:bank_books_list"),
            },
        ]
        context["accounts_count"] = BankBooks.objects.count()
        return context


class BankBooksAjaxDatatableView(RoleRequiredMixin, AjaxDatatableView):
    permission_required = "has_bank_books"
    model = BankBooks
    title = "Konta osobiste"
    initial_order = [["random_number", "desc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    disable_queryset_optimization = True

    column_defs = [
        {"name": "random_number", "title": "№"},
        {"name": "status", "title": "Status"},
        {"name": "flat", "title": "Mieszkanie"},
        {"name": "house", "title": "Budynek"},
        {"name": "section", "title": "Sekcja"},
        {"name": "owner", "title": "Właściciel"},
        {"name": "balance", "title": "Saldo (zł)"},
        {"name": "actions", "title": ""},
    ]

    def get_initial_queryset(self, request=None):
        queryset = with_balance(
            BankBooks.objects.select_related(
                "flat",
                "flat__house",
                "flat__section",
                "flat__owner",
            )
        )

        if request is None:
            return queryset

        uid = request.GET.get("uid", "").strip()
        status = request.GET.get("status", "").strip()
        flat = request.GET.get("flat", "").strip()
        house_id = request.GET.get("house", "").strip()
        section_id = request.GET.get("section", "").strip()
        owner_id = request.GET.get("owner", "").strip()
        has_debt = request.GET.get("has_debt", "").strip()

        if uid:
            queryset = queryset.filter(random_number__icontains=uid)
        if status == "active":
            queryset = queryset.filter(status=True)
        elif status == "inactive":
            queryset = queryset.filter(status=False)
        if flat:
            if flat.isdigit():
                queryset = queryset.filter(flat__number=int(flat))
            else:
                queryset = queryset.none()
        if house_id.isdigit():
            queryset = queryset.filter(flat__house_id=int(house_id))
        if section_id.isdigit():
            queryset = queryset.filter(flat__section_id=int(section_id))
        if owner_id.isdigit():
            queryset = queryset.filter(flat__owner_id=int(owner_id))
        if has_debt == "1":
            queryset = queryset.filter(balance__lt=0)
        elif has_debt == "0":
            queryset = queryset.filter(balance__gte=0)

        return queryset

    def render_column(self, row, column):
        if column == "status":
            if row.status:
                return '<small class="label label-success">Aktywny</small>'
            return '<small class="label label-default">Nieaktywny</small>'

        if column == "flat":
            return row.flat.number if row.flat_id else "-"

        if column == "house":
            return (
                row.flat.house.title
                if row.flat_id and row.flat.house_id
                else "-"
            )

        if column == "section":
            return (
                row.flat.section.title
                if row.flat_id and row.flat.section_id
                else "-"
            )

        if column == "owner":
            if not row.flat_id or not row.flat.owner_id:
                return "-"
            owner = row.flat.owner
            return owner.get_full_name() or owner.email

        if column == "balance":
            css = "text-default"
            if row.balance < 0:
                css = "text-red"
            elif row.balance > 0:
                css = "text-green"
            return f'<span class="{css}">{row.balance:.2f}</span>'

        if column == "actions":
            update_url = reverse("finances:bank_books_update", args=[row.pk])
            delete_url = reverse("finances:bank_books_delete", args=[row.pk])
            csrf = self.request.COOKIES.get("csrftoken", "")
            return f"""
                <div class="btn-group pull-right">
                    <a class="btn btn-default btn-sm" href="{update_url}" title="Edytuj" data-toggle="tooltip">
                        <i class="fa fa-pencil"></i>
                    </a>
                    <form method="post" action="{delete_url}" style="display: inline;">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                        <button type="submit" class="btn btn-default btn-sm" title="Usuń" data-toggle="tooltip"
                                onclick="return confirm('Usunąć konto osobiste?');">
                            <i class="fa fa-trash"></i>
                        </button>
                    </form>
                </div>
            """

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        row["row_href"] = reverse("finances:bank_books_detail", args=[obj.pk])
        return row


class BankBookFormContextMixin:
    template_name = "bank_books/form.html"

    def get_form_context(self, form, bank_book=None):
        house_value = form["house"].value()
        section_value = form["section"].value()
        floor_value = form["floor"].value()

        selected_house = selected_object(Houses, house_value)
        sections = Sections.objects.none()
        floors = Floors.objects.none()
        if selected_house:
            sections = Sections.objects.filter(house=selected_house).order_by(
                "title"
            )
            floors = Floors.objects.filter(house=selected_house).order_by(
                "title"
            )

        if bank_book:
            page_title = "Edytuj konto osobiste"
            form_url = reverse_lazy(
                "finances:bank_books_update", kwargs={"pk": bank_book.pk}
            )
            breadcrumbs = [
                {
                    "title": "Konta osobiste",
                    "url": reverse_lazy("finances:bank_books_list"),
                },
                {
                    "title": bank_book.random_number,
                    "url": reverse_lazy(
                        "finances:bank_books_detail",
                        kwargs={"pk": bank_book.pk},
                    ),
                },
                {"title": "Edytuj", "url": form_url},
            ]
        else:
            page_title = "Nowe konto osobiste"
            form_url = reverse_lazy("finances:bank_books_create")
            breadcrumbs = [
                {
                    "title": "Konta osobiste",
                    "url": reverse_lazy("finances:bank_books_list"),
                },
                {"title": "Nowe konto osobiste", "url": form_url},
            ]

        return {
            "form": form,
            "bank_book": bank_book,
            "form_url": form_url,
            "page_title": page_title,
            "breadcrumbs": breadcrumbs,
            "sections": sections,
            "floors": floors,
            "selected_house": selected_house,
            "selected_section": selected_object(Sections, section_value),
            "selected_floor": selected_object(Floors, floor_value),
        }


class BankBooksCreateView(RoleRequiredMixin, BankBookFormContextMixin, View):
    permission_required = "has_bank_books"

    def get(self, request):
        form = BankBookForm()
        return render(request, self.template_name, self.get_form_context(form))

    def post(self, request):
        form = BankBookForm(request.POST)
        if form.is_valid():
            bank_book = form.save()
            messages.success(request, "Konto osobiste zapisano.")
            return redirect(
                reverse_lazy(
                    "finances:bank_books_detail", kwargs={"pk": bank_book.pk}
                )
            )
        return render(request, self.template_name, self.get_form_context(form))


class BankBooksUpdateView(RoleRequiredMixin, BankBookFormContextMixin, View):
    permission_required = "has_bank_books"

    def get_object(self, pk):
        return get_object_or_404(BankBooks, pk=pk)

    def get(self, request, pk):
        bank_book = self.get_object(pk)
        form = BankBookForm(instance=bank_book)
        return render(
            request, self.template_name, self.get_form_context(form, bank_book)
        )

    def post(self, request, pk):
        bank_book = self.get_object(pk)
        form = BankBookForm(request.POST, instance=bank_book)
        if form.is_valid():
            bank_book = form.save()
            messages.success(request, "Konto osobiste zapisano.")
            return redirect(
                reverse_lazy(
                    "finances:bank_books_detail", kwargs={"pk": bank_book.pk}
                )
            )
        return render(
            request, self.template_name, self.get_form_context(form, bank_book)
        )


class BankBooksDetailView(RoleRequiredMixin, DetailView):
    permission_required = "has_bank_books"
    model = BankBooks
    template_name = "bank_books/detail.html"
    context_object_name = "bank_book"

    def get_queryset(self):
        return BankBooks.objects.select_related(
            "flat",
            "flat__house",
            "flat__section",
            "flat__floor",
            "flat__owner",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Konto osobiste {self.object.random_number}"
        context["breadcrumbs"] = [
            {
                "title": "Konta osobiste",
                "url": reverse_lazy("finances:bank_books_list"),
            },
            {
                "title": self.object.random_number,
                "url": reverse_lazy(
                    "finances:bank_books_detail", kwargs={"pk": self.object.pk}
                ),
            },
        ]
        context["reminder"] = f"{bank_book_balance(self.object):.2f}"
        return context


class BankBooksDeleteView(RoleRequiredMixin, View):
    permission_required = "has_bank_books"
    success_url = reverse_lazy("finances:bank_books_list")

    def post(self, request, pk):
        bank_book = get_object_or_404(BankBooks, pk=pk)
        number = bank_book.random_number
        try:
            bank_book.delete()
        except ProtectedError:
            messages.error(
                request, "Konto osobiste jest używane i nie może być usunięte."
            )
            return redirect(self.success_url)
        messages.success(request, f"Konto osobiste {number} usunięto.")
        return redirect(self.success_url)


class BankBooksExportView(RoleRequiredMixin, View):
    permission_required = "has_bank_books"

    def get(self, request):
        from io import BytesIO

        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Konta osobiste"
        ws.append(
            ["№", "Status", "Mieszkanie", "Budynek", "Właściciel", "Saldo"]
        )
        for book in with_balance(
            BankBooks.objects.select_related(
                "flat", "flat__house", "flat__owner"
            )
        ):
            owner = book.flat.owner if book.flat_id else None
            ws.append(
                [
                    book.random_number,
                    "Aktywny" if book.status else "Nieaktywny",
                    book.flat.number if book.flat_id else "",
                    (
                        book.flat.house.title
                        if book.flat_id and book.flat.house_id
                        else ""
                    ),
                    (owner.get_full_name() or owner.email) if owner else "",
                    round(book.balance, 2),
                ]
            )

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            "attachment; filename=bank_books.xlsx"
        )
        return response


class BankBookSelect2View(RoleRequiredMixin, View):
    permission_required = "has_bank_books"

    def get(self, request):
        term = request_term(request)
        queryset = BankBooks.objects.select_related("flat").order_by(
            "random_number"
        )
        if term:
            queryset = queryset.filter(
                Q(random_number__icontains=term)
                | Q(flat__number__icontains=term)
            )
        return JsonResponse(
            select2_response(
                queryset,
                request_page(request),
                lambda book: str(book.random_number),
            )
        )
