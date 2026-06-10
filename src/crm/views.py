from ajax_datatable import AjaxDatatableView
from django.contrib import messages as django_messages
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.text import Truncator
from django.views import View
from django.views.generic import DetailView, TemplateView

from src.buildings.models import Flats
from src.core.mixins import OwnerRequiredMixin
from src.crm.forms import MASTER_TYPE_CHOICES, MasterRequestForm, ProfileForm
from src.finances.enums import PaymentReceiptStatus, RequestStatus
from src.finances.models import Messages, PaymentReceipts, Requests
from src.finances.receipt_pdf import generate_receipt_xlsx
from src.finances.views.bank_books import bank_book_balance
from src.settings.models import PaymentDetails, ServiceTariffs


def owner_flats(user):
    return Flats.objects.select_related(
        "house", "section", "floor", "tariff", "bank_book"
    ).filter(owner=user)


def receipt_total(receipt):
    return sum(line.price * line.amount for line in receipt.lines.all())


class CabinetBaseMixin(OwnerRequiredMixin):
    def get_apartment_or_404(self, pk):
        return get_object_or_404(owner_flats(self.request.user), pk=pk)

    def get_context_data(self, **kwargs):
        parent = getattr(super(), "get_context_data", None)
        context = parent(**kwargs) if parent else dict(kwargs)
        flats = list(
            owner_flats(self.request.user).order_by("house__title", "number")
        )
        context["sidebar_apartments"] = flats
        owner_messages = Messages.objects.filter(
            flat__owner=self.request.user
        ).order_by("-id")
        context["unread_messages"] = owner_messages[:5]
        context["unread_messages_count"] = owner_messages.count()
        return context


class ProfileView(CabinetBaseMixin, TemplateView):
    template_name = "profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_flats"] = context["sidebar_apartments"]
        return context


class ProfileUpdateView(CabinetBaseMixin, View):
    template_name = "profile_form.html"

    def get(self, request):
        form = ProfileForm(instance=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            django_messages.success(request, "Profil zaktualizowano.")
            return redirect(reverse_lazy("crm:profile"))
        return render(request, self.template_name, {"form": form})


class ApartmentSummaryView(CabinetBaseMixin, TemplateView):
    template_name = "summary.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        flat = self.get_apartment_or_404(kwargs["pk"])
        bank_book = getattr(flat, "bank_book", None)
        balance = bank_book_balance(bank_book) if bank_book else 0.0

        receipts = PaymentReceipts.objects.filter(flat=flat).prefetch_related(
            "lines"
        )
        totals = [receipt_total(r) for r in receipts]
        months = len(totals) or 1

        context["flat"] = {
            "balance": f"{balance:.2f}",
            "account_number": (
                bank_book.random_number if bank_book else "Nie przypisano"
            ),
        }
        context["average_expense"] = (
            f"{(sum(totals) / months):.2f}" if totals else "0.00"
        )
        context["has_pie_data"] = False
        context["has_bar_data"] = False
        context["page_title"] = f"{flat.house.title}, m. {flat.number}"
        return context


class InvoiceListView(CabinetBaseMixin, TemplateView):
    template_name = "receipt.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        flat_pk = kwargs.get("pk")
        context["flat_pk"] = flat_pk
        if flat_pk:
            flat = self.get_apartment_or_404(flat_pk)
            context["page_title"] = (
                f"Rachunki — {flat.house.title}, m. {flat.number}"
            )
        else:
            context["page_title"] = "Wszystkie rachunki"
        return context


class InvoiceAjaxDatatableView(OwnerRequiredMixin, AjaxDatatableView):
    model = PaymentReceipts
    title = "Rachunki"
    initial_order = [["date_from", "desc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    disable_queryset_optimization = True

    column_defs = [
        {"name": "random_number", "title": "№"},
        {"name": "date_from", "title": "Data"},
        {
            "name": "status",
            "title": "Status",
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "amount",
            "title": "Kwota",
            "searchable": False,
            "orderable": False,
        },
    ]

    def get_initial_queryset(self, request=None):
        queryset = (
            PaymentReceipts.objects.select_related("flat")
            .prefetch_related("lines")
            .filter(flat__owner=self.request.user)
            .order_by("-date_from", "-id")
        )

        if request is None:
            return queryset

        flat_id = request.GET.get("flat_id", "").strip()
        date = request.GET.get("date", "").strip()
        status = request.GET.get("status", "").strip()

        if flat_id.isdigit():
            queryset = queryset.filter(flat_id=int(flat_id))
        if date:
            from datetime import datetime

            for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
                try:
                    queryset = queryset.filter(
                        date_from=datetime.strptime(date, fmt).date()
                    )
                    break
                except ValueError:
                    continue
        status_map = {
            "paid": PaymentReceiptStatus.PAID,
            "partially_paid": PaymentReceiptStatus.PARTIALLY_PAID,
            "unpaid": PaymentReceiptStatus.NOT_PAID,
        }
        if status in status_map:
            queryset = queryset.filter(status=status_map[status])

        return queryset

    def render_column(self, row, column):
        if column == "date_from":
            return row.date_from.strftime("%d.%m.%Y") if row.date_from else "-"

        if column == "status":
            label = {
                PaymentReceiptStatus.PAID: "label-success",
                PaymentReceiptStatus.PARTIALLY_PAID: "label-warning",
                PaymentReceiptStatus.NOT_PAID: "label-danger",
            }.get(row.status, "label-default")
            return f'<small class="label {label}">{row.get_status_display()}</small>'

        if column == "amount":
            return f"{receipt_total(row):.2f}"

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        row["row_href"] = reverse("crm:invoice_detail", args=[obj.pk])
        return row


class InvoiceDetailView(CabinetBaseMixin, DetailView):
    model = PaymentReceipts
    template_name = "invoice_detail.html"
    context_object_name = "invoice"

    def get_queryset(self):
        return (
            PaymentReceipts.objects.select_related(
                "flat", "flat__house", "tariff", "bank_book"
            )
            .prefetch_related(
                "lines",
                "lines__service",
                "lines__service__unit_of_measurement",
            )
            .filter(flat__owner=self.request.user)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["lines"] = self.object.lines.all()
        context["total_amount"] = f"{receipt_total(self.object):.2f}"
        context["page_title"] = f"Rachunek {self.object.random_number}"
        return context


class ApartmentTariffView(CabinetBaseMixin, TemplateView):
    template_name = "tariffs.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        flat = self.get_apartment_or_404(kwargs["pk"])
        if flat.tariff_id:
            context["tariff_services"] = (
                ServiceTariffs.objects.select_related(
                    "service", "service__unit_of_measurement"
                )
                .filter(tariff=flat.tariff)
                .order_by("service__title")
            )
        else:
            context["tariff_services"] = []
        context["page_title"] = (
            f"Taryfa — {flat.house.title}, m. {flat.number}"
        )
        return context


class MessageListView(CabinetBaseMixin, TemplateView):
    template_name = "messages.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Wiadomości"
        return context


class MessageAjaxDatatableView(OwnerRequiredMixin, AjaxDatatableView):
    model = Messages
    title = "Wiadomości"
    initial_order = [["id", "desc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    disable_queryset_optimization = True

    column_defs = [
        {
            "name": "selection",
            "title": "",
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "sender",
            "title": "Od kogo",
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "text",
            "title": "Treść",
            "searchable": False,
            "orderable": False,
        },
        {"name": "id", "title": "№"},
    ]

    def get_initial_queryset(self, request=None):
        queryset = (
            Messages.objects.select_related("flat", "flat__house")
            .filter(flat__owner=self.request.user)
            .order_by("-id")
        )
        if request is None:
            return queryset
        search = request.GET.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        return queryset

    def render_column(self, row, column):
        if column == "selection":
            return (
                f'<input type="checkbox" name="selection[]" value="{row.pk}">'
            )
        if column == "sender":
            return "Administracja"
        if column == "text":
            text = Truncator(row.description).chars(100)
            return f"<strong>{row.title}</strong> - {text}"
        return super().render_column(row, column)

    def customize_row(self, row, obj):
        row["row_href"] = reverse("crm:message_detail", args=[obj.pk])
        return row


class MessageDetailView(CabinetBaseMixin, DetailView):
    model = Messages
    template_name = "message_detail.html"
    context_object_name = "message"

    def get_queryset(self):
        return Messages.objects.select_related("flat", "flat__house").filter(
            flat__owner=self.request.user
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.object.title
        return context


class MessageDeleteAjaxView(OwnerRequiredMixin, View):
    def post(self, request):
        ids = request.POST.getlist("ids[]")
        Messages.objects.filter(
            flat__owner=request.user,
            pk__in=[i for i in ids if i.isdigit()],
        ).delete()
        return JsonResponse({"status": "ok"})


class RequestListView(CabinetBaseMixin, TemplateView):
    template_name = "master_call_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Zgłoszenia serwisowe"
        return context


class RequestAjaxDatatableView(OwnerRequiredMixin, AjaxDatatableView):
    model = Requests
    title = "Zgłoszenia serwisowe"
    initial_order = [["id", "desc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    disable_queryset_optimization = True

    column_defs = [
        {"name": "id", "title": "Nr zgłoszenia"},
        {
            "name": "master_type",
            "title": "Typ specjalisty",
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "description",
            "title": "Opis",
            "searchable": False,
            "orderable": False,
        },
        {"name": "date_time", "title": "Preferowany czas"},
        {
            "name": "status",
            "title": "Status",
            "searchable": False,
            "orderable": False,
        },
        {
            "name": "actions",
            "title": "",
            "searchable": False,
            "orderable": False,
        },
    ]

    def get_initial_queryset(self, request=None):
        return Requests.objects.filter(owner=self.request.user).order_by("-id")

    def render_column(self, row, column):
        if column == "master_type":
            for _, label in MASTER_TYPE_CHOICES:
                if row.description and row.description.startswith(
                    f"[{label}]"
                ):
                    return label
            return "Dowolny specjalista"

        if column == "description":
            return Truncator(row.description).chars(50)

        if column == "date_time":
            return (
                row.date_time.strftime("%d.%m.%Y - %H:%M")
                if row.date_time
                else "-"
            )

        if column == "status":
            mapping = {
                RequestStatus.NEW: ("label-warning", "Nowe"),
                RequestStatus.IN_PROGRESS: ("label-primary", "W trakcie"),
                RequestStatus.DONE: ("label-success", "Zakończono"),
            }
            css, label = mapping.get(row.status, ("label-default", row.status))
            return f'<small class="label {css}">{label}</small>'

        if column == "actions":
            delete_url = reverse("crm:request_delete", args=[row.pk])
            csrf = self.request.COOKIES.get("csrftoken", "")
            return f"""
                <form method="post" action="{delete_url}" style="display:inline;">
                    <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                    <button type="submit" class="btn btn-default btn-sm" title="Usuń"
                            onclick="return confirm('Czy na pewno chcesz usunąć to zgłoszenie?');">
                        <i class="fa fa-trash"></i>
                    </button>
                </form>
            """

        return super().render_column(row, column)


class RequestCreateView(CabinetBaseMixin, View):
    template_name = "master_call.html"

    def get(self, request):
        form = MasterRequestForm(owner=request.user)
        context = self.get_context_data()
        context["form"] = form
        context["user_flats"] = context["sidebar_apartments"]
        return render(request, self.template_name, context)

    def post(self, request):
        form = MasterRequestForm(request.POST, owner=request.user)
        if form.is_valid():
            form.save()
            django_messages.success(request, "Zgłoszenie wysłano.")
            return redirect(reverse_lazy("crm:request_list"))
        context = self.get_context_data()
        context["form"] = form
        context["user_flats"] = context["sidebar_apartments"]
        return render(request, self.template_name, context)


class RequestDeleteView(CabinetBaseMixin, View):
    def post(self, request, pk):
        req = get_object_or_404(Requests, pk=pk, owner=request.user)
        req.delete()
        django_messages.success(request, "Zgłoszenie usunięto.")
        return redirect(reverse_lazy("crm:request_list"))


def _get_invoice_for_owner(user, pk):
    return get_object_or_404(
        PaymentReceipts.objects.select_related(
            "flat", "flat__house", "bank_book"
        ),
        pk=pk,
        flat__owner=user,
    )


class InvoiceDownloadView(OwnerRequiredMixin, View):
    def get(self, request, pk):
        invoice = _get_invoice_for_owner(request.user, pk)
        data = generate_receipt_xlsx(invoice)
        if not data:
            django_messages.error(
                request,
                "Szablon rachunku nie znaleziono. Wgraj szablon w ustawieniach.",
            )
            return redirect(reverse("crm:invoice_detail", args=[pk]))
        filename = f"receipt_{invoice.random_number}.xlsx"
        response = HttpResponse(
            data,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class InvoicePayStep1View(CabinetBaseMixin, View):
    template_name = "payment_step1.html"

    def _get_invoice(self, pk):
        return _get_invoice_for_owner(self.request.user, pk)

    def get(self, request, pk):
        invoice = self._get_invoice(pk)
        bank_book = invoice.bank_book
        saved_account = request.session.get("saved_account_number", "")
        account_number = saved_account or (
            bank_book.random_number if bank_book else ""
        )
        details = PaymentDetails.objects.first()
        context = self.get_context_data()
        context.update(
            {
                "invoice": invoice,
                "account_number": account_number,
                "company_name": details.company_name if details else "",
                "total_amount": f"{receipt_total(invoice):.2f}",
                "page_title": "Opłata rachunku",
            }
        )
        return render(request, self.template_name, context)

    def post(self, request, pk):
        self._get_invoice(pk)  # validate ownership
        account_number = request.POST.get("account_number", "").strip()
        remember = request.POST.get("remember")
        if remember:
            request.session["saved_account_number"] = account_number
        else:
            request.session.pop("saved_account_number", None)
        request.session[f"pay_account_{pk}"] = account_number
        return redirect(reverse("crm:invoice_pay_step2", args=[pk]))


class InvoicePayStep2View(CabinetBaseMixin, View):
    template_name = "payment_step2.html"

    def _get_invoice(self, pk):
        return _get_invoice_for_owner(self.request.user, pk)

    def get(self, request, pk):
        invoice = self._get_invoice(pk)
        context = self.get_context_data()
        context.update(
            {
                "invoice": invoice,
                "page_title": "Wybór metody płatności",
            }
        )
        return render(request, self.template_name, context)

    def post(self, request, pk):
        method = request.POST.get("payment_method", "card")
        request.session[f"pay_method_{pk}"] = method
        return redirect(reverse("crm:invoice_pay_card", args=[pk]))


class InvoicePayCardView(CabinetBaseMixin, View):
    template_name = "payment_card.html"

    def _get_invoice(self, pk):
        return _get_invoice_for_owner(self.request.user, pk)

    def get(self, request, pk):
        invoice = self._get_invoice(pk)
        method = request.session.get(f"pay_method_{pk}", "card")
        context = self.get_context_data()
        context.update(
            {
                "invoice": invoice,
                "method": method,
                "page_title": "Podaj dane karty",
            }
        )
        return render(request, self.template_name, context)

    def post(self, request, pk):
        invoice = self._get_invoice(pk)
        card_number = request.POST.get("card_number", "").replace(" ", "")
        cvv = request.POST.get("cvv", "").strip()
        expiry = request.POST.get("expiry", "").strip()
        errors = []
        if not card_number or not card_number.isdigit():
            errors.append("Podaj prawidłowy numer karty.")
        if not cvv or not cvv.isdigit():
            errors.append("Podaj prawidłowy CVV.")
        if not expiry:
            errors.append("Podaj datę ważności karty.")
        if errors:
            method = request.session.get(f"pay_method_{pk}", "card")
            context = self.get_context_data()
            context.update(
                {
                    "invoice": invoice,
                    "method": method,
                    "errors": errors,
                    "page_title": "Podaj dane karty",
                }
            )
            return render(request, self.template_name, context)
        invoice.status = PaymentReceiptStatus.PAID
        invoice.save(update_fields=["status"])
        for key in (f"pay_account_{pk}", f"pay_method_{pk}"):
            request.session.pop(key, None)
        return redirect(reverse("crm:invoice_pay_success", args=[pk]))


class InvoicePaySuccessView(CabinetBaseMixin, View):
    template_name = "payment_success.html"

    def get(self, request, pk):
        invoice = _get_invoice_for_owner(request.user, pk)
        context = self.get_context_data()
        context.update(
            {
                "invoice": invoice,
                "page_title": "Płatność zakończona sukcesem",
            }
        )
        return render(request, self.template_name, context)
