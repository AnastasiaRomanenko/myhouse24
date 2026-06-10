import json
from datetime import date

from django.db.models import Sum
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from src.buildings.models import Flats, Houses
from src.core.mixins import RoleRequiredMixin
from src.finances.enums import AccountingType, RequestStatus
from src.finances.models import (
    Accounting,
    BankBooks,
    PaymentReceipts,
    Requests,
)
from src.finances.views.accounting import cashbox_totals
from src.finances.views.bank_books import with_balance
from src.users.enums import Status
from src.users.models import Users


def _monthly_accounting(year):
    income = [0.0] * 12
    expense = [0.0] * 12
    rows = (
        Accounting.objects.filter(completed=True, created_at__year=year)
        .values("created_at__month", "type")
        .annotate(total=Sum("amount"))
    )
    for row in rows:
        m = row["created_at__month"] - 1
        if row["type"] == AccountingType.INCOME:
            income[m] += row["total"] or 0.0
        else:
            expense[m] += row["total"] or 0.0
    return income, expense


def _monthly_receipts(year):
    debt = [0.0] * 12
    repayment = [0.0] * 12
    receipts = PaymentReceipts.objects.filter(
        date_from__year=year
    ).prefetch_related("lines")
    for receipt in receipts:
        m = receipt.date_from.month - 1
        total = sum(line.price * line.amount for line in receipt.lines.all())
        debt[m] += total
        if receipt.completed:
            repayment[m] += total
    return debt, repayment


class StatisticsDetailView(RoleRequiredMixin, TemplateView):
    permission_required = "has_statistics"
    template_name = "statistics/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        income, expense = cashbox_totals()
        balances = list(with_balance(BankBooks.objects.all()))
        year = date.today().year

        context["page_title"] = "Statystyki"
        context["breadcrumbs"] = [
            {
                "title": "Statystyki",
                "url": reverse_lazy("finances:statistics"),
            },
        ]
        context["houses_count"] = Houses.objects.count()
        context["flats_count"] = Flats.objects.count()
        context["accounts_count"] = BankBooks.objects.count()
        context["active_users_count"] = Users.objects.filter(
            is_staff=False, status=Status.ACTIVE
        ).count()
        context["master_requests_in_progress"] = Requests.objects.filter(
            status=RequestStatus.IN_PROGRESS
        ).count()
        context["new_master_requests"] = Requests.objects.filter(
            status=RequestStatus.NEW
        ).count()

        total_balance = sum(b.balance for b in balances if b.balance > 0)
        total_debt = -sum(b.balance for b in balances if b.balance < 0)
        context["total_balance"] = f"{total_balance:.2f}"
        context["total_debt"] = f"{total_debt:.2f}"
        context["cashbox_state"] = f"{income - expense:.2f}"

        monthly_income, monthly_expense = _monthly_accounting(year)
        receipt_debt, receipt_repayment = _monthly_receipts(year)

        context["chart1_debt_data"] = json.dumps(
            [round(v, 2) for v in receipt_debt]
        )
        context["chart1_repayment_data"] = json.dumps(
            [round(v, 2) for v in receipt_repayment]
        )
        context["chart2_income_data"] = json.dumps(
            [round(v, 2) for v in monthly_income]
        )
        context["chart2_expense_data"] = json.dumps(
            [round(v, 2) for v in monthly_expense]
        )
        return context
