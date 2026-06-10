from ajax_datatable import AjaxDatatableView
from django.contrib import messages
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, TemplateView

from src.core.mixins import RoleRequiredMixin
from src.core.select2 import request_page, request_term, select2_response
from src.finances.enums import AccountingType
from src.finances.forms import AccountingExpenseForm, AccountingIncomeForm
from src.finances.models import Accounting, BankBooks
from src.finances.views.bank_books import with_balance
from src.finances.views.meter_readings import parse_filter_date
from src.settings.models import PaymentItems
from src.users.models import Users


def user_name(user):
    if not user:
        return "-"
    return user.get_full_name() or user.email


def cashbox_totals():
    income = (
        Accounting.objects.filter(
            type=AccountingType.INCOME, completed=True
        ).aggregate(total=Sum("amount"))["total"]
        or 0.0
    )
    expense = (
        Accounting.objects.filter(
            type=AccountingType.EXPENSE, completed=True
        ).aggregate(total=Sum("amount"))["total"]
        or 0.0
    )
    return income, expense


class AccountingListView(RoleRequiredMixin, TemplateView):
    permission_required = "has_cash_register"
    template_name = "accounting/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        income, expense = cashbox_totals()
        context["page_title"] = "Kasa"
        context["breadcrumbs"] = [
            {"title": "Kasa", "url": reverse_lazy("finances:accounting_list")},
        ]
        context["total_income"] = f"{income:.2f}"
        context["total_expense"] = f"{expense:.2f}"
        context["cashbox_state"] = f"{income - expense:.2f}"
        balances = with_balance(BankBooks.objects.all())
        context["accounts_balance"] = (
            f"{sum(b.balance for b in balances if b.balance > 0):.2f}"
        )
        context["accounts_debt"] = (
            f"{-sum(b.balance for b in balances if b.balance < 0):.2f}"
        )
        return context


class AccountingAjaxDatatableView(RoleRequiredMixin, AjaxDatatableView):
    permission_required = "has_cash_register"
    model = Accounting
    title = "Kasa"
    initial_order = [["created_at", "desc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    disable_queryset_optimization = True

    column_defs = [
        {"name": "random_number", "title": "№"},
        {"name": "created_at", "title": "Data"},
        {"name": "completed", "title": "Status"},
        {"name": "payment_item", "title": "Typ płatności"},
        {"name": "owner", "title": "Właściciel"},
        {"name": "bank_book", "title": "Konto osobiste"},
        {"name": "type", "title": "Przychód/Wydatek"},
        {"name": "amount", "title": "Kwota (zł)"},
        {"name": "actions", "title": ""},
    ]

    def get_initial_queryset(self, request=None):
        queryset = Accounting.objects.select_related(
            "payment_item",
            "owner",
            "bank_book",
            "manager",
        )

        if request is None:
            return queryset

        uid = request.GET.get("uid", "").strip()
        date = parse_filter_date(request.GET.get("date"))
        status = request.GET.get("status", "").strip()
        purpose = request.GET.get("purpose", "").strip()
        owner_id = request.GET.get("user_id", "").strip()
        account_uid = request.GET.get("account_uid", "").strip()
        type_ = request.GET.get("type", "").strip()

        if uid:
            queryset = queryset.filter(random_number__icontains=uid)
        if date:
            queryset = queryset.filter(created_at=date)
        if status == "completed":
            queryset = queryset.filter(completed=True)
        elif status == "pending":
            queryset = queryset.filter(completed=False)
        if purpose.isdigit():
            queryset = queryset.filter(payment_item_id=int(purpose))
        if owner_id.isdigit():
            queryset = queryset.filter(owner_id=int(owner_id))
        if account_uid:
            queryset = queryset.filter(
                bank_book__random_number__icontains=account_uid
            )
        if type_ in (AccountingType.INCOME, AccountingType.EXPENSE):
            queryset = queryset.filter(type=type_)

        return queryset

    def render_column(self, row, column):
        if column == "created_at":
            return (
                row.created_at.strftime("%d.%m.%Y") if row.created_at else "-"
            )

        if column == "completed":
            if row.completed:
                return (
                    '<small class="label label-success">Zaksięgowano</small>'
                )
            return (
                '<small class="label label-default">Nie zaksięgowano</small>'
            )

        if column == "payment_item":
            return row.payment_item.name if row.payment_item_id else "-"

        if column == "owner":
            return user_name(row.owner) if row.owner_id else "-"

        if column == "bank_book":
            return row.bank_book.random_number if row.bank_book_id else "-"

        if column == "type":
            return row.get_type_display()

        if column == "amount":
            if row.type == AccountingType.EXPENSE:
                return f'<span class="text-red">-{row.amount:.2f}</span>'
            return f'<span class="text-green">{row.amount:.2f}</span>'

        if column == "actions":
            update_url = reverse("finances:accounting_update", args=[row.pk])
            delete_url = reverse("finances:accounting_delete", args=[row.pk])
            csrf = self.request.COOKIES.get("csrftoken", "")
            return f"""
                <div class="btn-group pull-right">
                    <a class="btn btn-default btn-sm" href="{update_url}" title="Edytuj" data-toggle="tooltip">
                        <i class="fa fa-pencil"></i>
                    </a>
                    <form method="post" action="{delete_url}" style="display: inline;">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                        <button type="submit" class="btn btn-default btn-sm" title="Usuń" data-toggle="tooltip"
                                onclick="return confirm('Usunąć dokument?');">
                            <i class="fa fa-trash"></i>
                        </button>
                    </form>
                </div>
            """

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        row["row_href"] = reverse("finances:accounting_detail", args=[obj.pk])
        return row


class AccountingFormContextMixin:
    def get_form_context(self, form, kind, accounting=None):
        if kind == AccountingType.EXPENSE:
            template_name = "accounting/form_expense.html"
            list_title = "Dokument rozchodowy"
            create_url = reverse_lazy("finances:accounting_expense")
        else:
            template_name = "accounting/form_income.html"
            list_title = "Dokument przychodowy"
            create_url = reverse_lazy("finances:accounting_income")

        if accounting:
            page_title = f"Edytuj: {list_title}"
            form_url = reverse_lazy(
                "finances:accounting_update", kwargs={"pk": accounting.pk}
            )
            breadcrumbs = [
                {
                    "title": "Kasa",
                    "url": reverse_lazy("finances:accounting_list"),
                },
                {
                    "title": accounting.random_number,
                    "url": reverse_lazy(
                        "finances:accounting_detail",
                        kwargs={"pk": accounting.pk},
                    ),
                },
                {"title": "Edytuj", "url": form_url},
            ]
        else:
            page_title = list_title
            form_url = create_url
            breadcrumbs = [
                {
                    "title": "Kasa",
                    "url": reverse_lazy("finances:accounting_list"),
                },
                {"title": page_title, "url": form_url},
            ]

        return template_name, {
            "form": form,
            "accounting": accounting,
            "form_url": form_url,
            "page_title": page_title,
            "breadcrumbs": breadcrumbs,
        }


class AccountingIncomeCreateView(
    RoleRequiredMixin, AccountingFormContextMixin, View
):
    permission_required = "has_cash_register"

    def get(self, request, bank_book_pk=None):
        initial = {}
        if bank_book_pk:
            book = get_object_or_404(BankBooks, pk=bank_book_pk)
            initial["bank_book"] = book.pk
            if book.flat_id:
                initial["owner"] = book.flat.owner_id
        form = AccountingIncomeForm(initial=initial)
        template, ctx = self.get_form_context(form, AccountingType.INCOME)
        return render(request, template, ctx)

    def post(self, request, bank_book_pk=None):
        form = AccountingIncomeForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Dokument przychodowy zapisano.")
            return redirect(
                reverse_lazy(
                    "finances:accounting_detail", kwargs={"pk": obj.pk}
                )
            )
        template, ctx = self.get_form_context(form, AccountingType.INCOME)
        return render(request, template, ctx)


class AccountingExpenseCreateView(
    RoleRequiredMixin, AccountingFormContextMixin, View
):
    permission_required = "has_cash_register"

    def get(self, request):
        form = AccountingExpenseForm()
        template, ctx = self.get_form_context(form, AccountingType.EXPENSE)
        return render(request, template, ctx)

    def post(self, request):
        form = AccountingExpenseForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Dokument rozchodowy zapisano.")
            return redirect(
                reverse_lazy(
                    "finances:accounting_detail", kwargs={"pk": obj.pk}
                )
            )
        template, ctx = self.get_form_context(form, AccountingType.EXPENSE)
        return render(request, template, ctx)


class AccountingUpdateView(
    RoleRequiredMixin, AccountingFormContextMixin, View
):
    permission_required = "has_cash_register"

    def get_object(self, pk):
        return get_object_or_404(Accounting, pk=pk)

    def _form_class(self, accounting):
        if accounting.type == AccountingType.EXPENSE:
            return AccountingExpenseForm, AccountingType.EXPENSE
        return AccountingIncomeForm, AccountingType.INCOME

    def get(self, request, pk):
        accounting = self.get_object(pk)
        form_class, kind = self._form_class(accounting)
        form = form_class(instance=accounting)
        template, ctx = self.get_form_context(form, kind, accounting)
        return render(request, template, ctx)

    def post(self, request, pk):
        accounting = self.get_object(pk)
        form_class, kind = self._form_class(accounting)
        form = form_class(request.POST, instance=accounting)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Dokument zapisano.")
            return redirect(
                reverse_lazy(
                    "finances:accounting_detail", kwargs={"pk": obj.pk}
                )
            )
        template, ctx = self.get_form_context(form, kind, accounting)
        return render(request, template, ctx)


class AccountingDetailView(RoleRequiredMixin, DetailView):
    permission_required = "has_cash_register"
    model = Accounting
    template_name = "accounting/detail.html"
    context_object_name = "accounting"

    def get_queryset(self):
        return Accounting.objects.select_related(
            "payment_item",
            "owner",
            "bank_book",
            "bank_book__flat",
            "manager",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object
        context["page_title"] = f"Dokument {obj.random_number}"
        context["breadcrumbs"] = [
            {"title": "Kasa", "url": reverse_lazy("finances:accounting_list")},
            {
                "title": obj.random_number,
                "url": reverse_lazy(
                    "finances:accounting_detail", kwargs={"pk": obj.pk}
                ),
            },
        ]
        context["transaction"] = obj
        return context


class AccountingExportView(RoleRequiredMixin, View):
    permission_required = "has_cash_register"

    def get(self, request):
        from io import BytesIO

        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Kasa"
        ws.append(
            [
                "№",
                "Data",
                "Status",
                "Typ płatności",
                "Właściciel",
                "Konto osobiste",
                "Przychód/Wydatek",
                "Kwota (zł)",
            ]
        )
        for obj in Accounting.objects.select_related(
            "payment_item", "owner", "bank_book"
        ).order_by("-created_at"):
            ws.append(
                [
                    obj.random_number,
                    (
                        obj.created_at.strftime("%d.%m.%Y")
                        if obj.created_at
                        else ""
                    ),
                    "Zaksięgowano" if obj.completed else "Nie zaksięgowano",
                    obj.payment_item.name if obj.payment_item_id else "",
                    user_name(obj.owner) if obj.owner_id else "",
                    obj.bank_book.random_number if obj.bank_book_id else "",
                    obj.get_type_display(),
                    round(obj.amount, 2),
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
            "attachment; filename=accounting.xlsx"
        )
        return response


class AccountingDeleteView(RoleRequiredMixin, View):
    permission_required = "has_cash_register"
    success_url = reverse_lazy("finances:accounting_list")

    def post(self, request, pk):
        obj = get_object_or_404(Accounting, pk=pk)
        number = obj.random_number
        obj.delete()
        messages.success(request, f"Dokument {number} usunięto.")
        return redirect(self.success_url)


class PaymentItemSelect2View(RoleRequiredMixin, View):
    permission_required = "has_cash_register"

    def get(self, request):
        term = request_term(request)
        queryset = PaymentItems.objects.order_by("name")
        kind = request.GET.get("type", "").strip()
        if kind in (AccountingType.INCOME, AccountingType.EXPENSE):
            queryset = queryset.filter(type=kind)
        if term:
            queryset = queryset.filter(name__icontains=term)
        return JsonResponse(
            select2_response(
                queryset, request_page(request), lambda item: item.name
            )
        )


class ManagerSelect2View(RoleRequiredMixin, View):
    permission_required = "has_cash_register"

    def get(self, request):
        term = request_term(request)
        queryset = Users.objects.filter(is_staff=True).order_by(
            "last_name", "first_name", "email"
        )
        if term:
            queryset = queryset.filter(
                Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(email__icontains=term)
            )
        return JsonResponse(
            select2_response(queryset, request_page(request), user_name)
        )
