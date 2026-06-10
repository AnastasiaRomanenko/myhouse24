from ajax_datatable import AjaxDatatableView
from django.contrib import messages
from django.core.mail import EmailMessage
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, TemplateView

from src.core.mixins import RoleRequiredMixin
from src.finances.enums import PaymentReceiptStatus
from src.finances.forms import PaymentReceiptForm, PaymentReceiptServiceFormSet
from src.finances.models import BankBooks, MeterReadings, PaymentReceipts
from src.finances.receipt_pdf import (
    generate_receipt_pdf,
    generate_receipt_xlsx,
)
from src.finances.views.accounting import cashbox_totals
from src.finances.views.bank_books import with_balance
from src.finances.views.meter_readings import parse_filter_date
from src.settings.models import ReceiptTemplate, ServiceTariffs


class PaymentReceiptsListView(RoleRequiredMixin, TemplateView):
    permission_required = "has_payment_receipts"
    template_name = "payment_receipts/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        income, expense = cashbox_totals()
        context["page_title"] = "Rachunki do zapłaty"
        context["breadcrumbs"] = [
            {
                "title": "Rachunki do zapłaty",
                "url": reverse_lazy("finances:payment_receipts_list"),
            },
        ]
        context["cashbox_state"] = f"{income - expense:.2f}"
        balances = with_balance(BankBooks.objects.all())
        context["accounts_balance"] = (
            f"{sum(b.balance for b in balances if b.balance > 0):.2f}"
        )
        context["accounts_debt"] = (
            f"{-sum(b.balance for b in balances if b.balance < 0):.2f}"
        )
        return context


class PaymentReceiptsAjaxDatatableView(RoleRequiredMixin, AjaxDatatableView):
    permission_required = "has_payment_receipts"
    model = PaymentReceipts
    title = "Rachunki do zapłaty"
    initial_order = [["date_from", "desc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    disable_queryset_optimization = True

    column_defs = [
        {"name": "random_number", "title": "Nr rachunku"},
        {"name": "status", "title": "Status"},
        {"name": "date_from", "title": "Data"},
        {"name": "period", "title": "Miesiąc"},
        {"name": "flat", "title": "Mieszkanie"},
        {"name": "owner", "title": "Właściciel"},
        {"name": "completed", "title": "Zaksięgowano"},
        {"name": "amount", "title": "Kwota (zł)"},
        {"name": "actions", "title": ""},
    ]

    def get_initial_queryset(self, request=None):
        queryset = PaymentReceipts.objects.select_related(
            "flat",
            "flat__house",
            "flat__owner",
            "tariff",
            "bank_book",
        ).prefetch_related("lines")

        if request is None:
            return queryset

        uid = request.GET.get("uid", "").strip()
        status = request.GET.get("status", "").strip()
        date = parse_filter_date(request.GET.get("date"))
        flat = request.GET.get("flat", "").strip()
        owner_id = request.GET.get("owner", "").strip()
        is_checked = request.GET.get("is_checked", "").strip()
        bank_book_id = request.GET.get("bank_book_id", "").strip()

        if uid:
            queryset = queryset.filter(random_number__icontains=uid)
        if status in dict(PaymentReceiptStatus.choices):
            queryset = queryset.filter(status=status)
        if date:
            queryset = queryset.filter(date_from=date)
        if bank_book_id.isdigit():
            queryset = queryset.filter(bank_book_id=int(bank_book_id))
        elif flat:
            if flat.isdigit():
                queryset = queryset.filter(flat__number=int(flat))
            else:
                queryset = queryset.none()
        if owner_id.isdigit():
            queryset = queryset.filter(flat__owner_id=int(owner_id))
        if is_checked == "1":
            queryset = queryset.filter(completed=True)
        elif is_checked == "0":
            queryset = queryset.filter(completed=False)

        return queryset

    def render_column(self, row, column):
        if column == "status":
            label = {
                PaymentReceiptStatus.PAID: "label-success",
                PaymentReceiptStatus.PARTIALLY_PAID: "label-warning",
                PaymentReceiptStatus.NOT_PAID: "label-danger",
            }.get(row.status, "label-default")
            return f'<small class="label {label}">{row.get_status_display()}</small>'

        if column == "date_from":
            return row.date_from.strftime("%d.%m.%Y") if row.date_from else "-"

        if column == "period":
            if row.period_from:
                return row.period_from.strftime("%m.%Y")
            return "-"

        if column == "flat":
            return row.flat.number if row.flat_id else "-"

        if column == "owner":
            if not row.flat_id or not row.flat.owner_id:
                return "-"
            owner = row.flat.owner
            return owner.get_full_name() or owner.email

        if column == "completed":
            if row.completed:
                return (
                    '<small class="label label-success">Zaksięgowano</small>'
                )
            return (
                '<small class="label label-default">Nie zaksięgowano</small>'
            )

        if column == "amount":
            total = sum(line.price * line.amount for line in row.lines.all())
            return f"{total:.2f}"

        if column == "actions":
            update_url = reverse(
                "finances:payment_receipts_update", args=[row.pk]
            )
            delete_url = reverse(
                "finances:payment_receipts_delete", args=[row.pk]
            )
            csrf = self.request.COOKIES.get("csrftoken", "")
            return f"""
                <div class="btn-group pull-right">
                    <a class="btn btn-default btn-sm" href="{update_url}" title="Edytuj" data-toggle="tooltip">
                        <i class="fa fa-pencil"></i>
                    </a>
                    <form method="post" action="{delete_url}" style="display: inline;">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                        <button type="submit" class="btn btn-default btn-sm" title="Usuń" data-toggle="tooltip"
                                onclick="return confirm('Usunąć rachunek?');">
                            <i class="fa fa-trash"></i>
                        </button>
                    </form>
                </div>
            """

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        row["row_href"] = reverse(
            "finances:payment_receipts_detail", args=[obj.pk]
        )
        return row


class BankBookOwnerInfoView(RoleRequiredMixin, View):
    permission_required = "has_payment_receipts"

    def get(self, request, pk):
        try:
            book = BankBooks.objects.select_related("flat", "flat__owner").get(
                pk=pk
            )
        except BankBooks.DoesNotExist:
            return JsonResponse(
                {"owner": "nie wybrano", "phone": "nie wybrano"}
            )
        owner = book.flat.owner if book.flat_id else None
        if owner:
            name = owner.get_full_name() or owner.email
            phone = (
                str(owner.phone_number)
                if hasattr(owner, "phone_number") and owner.phone_number
                else "nie wybrano"
            )
        else:
            name = "nie wybrano"
            phone = "nie wybrano"
        return JsonResponse({"owner": name, "phone": phone})


class TariffServicesView(RoleRequiredMixin, View):
    permission_required = "has_payment_receipts"

    def get(self, request):
        tariff_id = request.GET.get("tariff_id", "").strip()
        if not tariff_id.isdigit():
            return JsonResponse({"services": []})
        rows = ServiceTariffs.objects.filter(
            tariff_id=int(tariff_id)
        ).select_related("service", "service__unit_of_measurement")
        return JsonResponse(
            {
                "services": [
                    {
                        "id": row.service.pk,
                        "title": row.service.title,
                        "price": row.price,
                        "unit": (
                            row.service.unit_of_measurement.title
                            if row.service.unit_of_measurement_id
                            else ""
                        ),
                    }
                    for row in rows
                ]
            }
        )


class FlatMeterReadingsView(RoleRequiredMixin, View):
    permission_required = "has_payment_receipts"

    def get(self, request):
        flat_id = request.GET.get("flat_id", "").strip()
        if not flat_id.isdigit():
            return JsonResponse({"readings": []})
        readings = (
            MeterReadings.objects.filter(flat_id=int(flat_id))
            .select_related(
                "flat",
                "flat__house",
                "flat__section",
                "meter_type",
                "meter_type__unit_of_measurement",
            )
            .order_by("-created_at")
        )
        return JsonResponse(
            {
                "readings": [
                    {
                        "random_number": r.random_number,
                        "status": r.get_status_display(),
                        "created_at": (
                            r.created_at.strftime("%d.%m.%Y")
                            if r.created_at
                            else ""
                        ),
                        "month": (
                            r.created_at.strftime("%m.%Y")
                            if r.created_at
                            else ""
                        ),
                        "house": (
                            r.flat.house.title
                            if r.flat_id and r.flat.house_id
                            else ""
                        ),
                        "section": (
                            r.flat.section.title
                            if r.flat_id and r.flat.section_id
                            else ""
                        ),
                        "flat_number": r.flat.number if r.flat_id else "",
                        "meter_type_id": r.meter_type_id,
                        "meter_type": (
                            r.meter_type.title if r.meter_type_id else ""
                        ),
                        "current_data": r.current_data,
                        "unit": (
                            r.meter_type.unit_of_measurement.title
                            if r.meter_type_id
                            and r.meter_type.unit_of_measurement_id
                            else ""
                        ),
                    }
                    for r in readings
                ]
            }
        )


class ServiceUnitView(RoleRequiredMixin, View):
    permission_required = "has_payment_receipts"

    def get(self, request):
        service_id = request.GET.get("service_id", "").strip()
        if not service_id.isdigit():
            return JsonResponse({"unit": ""})
        from src.settings.models import Services

        try:
            svc = Services.objects.select_related("unit_of_measurement").get(
                pk=int(service_id)
            )
            unit = (
                svc.unit_of_measurement.title
                if svc.unit_of_measurement_id
                else ""
            )
        except Services.DoesNotExist:
            unit = ""
        return JsonResponse({"unit": unit})


class PaymentReceiptFormContextMixin:
    template_name = "payment_receipts/form.html"

    def get_form_context(self, form, formset, receipt=None):
        from src.buildings.models import Flats, Floors, Sections
        from src.core.select2 import selected_object as sel_obj

        if receipt:
            page_title = "Edytuj rachunek"
            form_url = reverse_lazy(
                "finances:payment_receipts_update", kwargs={"pk": receipt.pk}
            )
            breadcrumbs = [
                {
                    "title": "Rachunki do zapłaty",
                    "url": reverse_lazy("finances:payment_receipts_list"),
                },
                {
                    "title": receipt.random_number,
                    "url": reverse_lazy(
                        "finances:payment_receipts_detail",
                        kwargs={"pk": receipt.pk},
                    ),
                },
                {"title": "Edytuj", "url": form_url},
            ]
        else:
            page_title = "Nowy rachunek"
            form_url = reverse_lazy("finances:payment_receipts_create")
            breadcrumbs = [
                {
                    "title": "Rachunki do zapłaty",
                    "url": reverse_lazy("finances:payment_receipts_list"),
                },
                {"title": "Nowy rachunek", "url": form_url},
            ]

        flat_id = form["flat"].value() if "flat" in form.fields else None
        selected_flat = sel_obj(Flats, flat_id)
        selected_house = None
        selected_section = None
        selected_floor = None
        sections = Sections.objects.none()
        floors = Floors.objects.none()
        if selected_flat:
            # Re-fetch with all related objects in one query to avoid lazy hits
            selected_flat = Flats.objects.select_related(
                "house", "section", "floor", "owner"
            ).get(pk=selected_flat.pk)
            selected_house = (
                selected_flat.house if selected_flat.house_id else None
            )
            selected_section = (
                selected_flat.section if selected_flat.section_id else None
            )
            selected_floor = (
                selected_flat.floor if selected_flat.floor_id else None
            )
        if selected_house:
            sections = Sections.objects.filter(house=selected_house).order_by(
                "title"
            )
            floors = Floors.objects.filter(house=selected_house).order_by(
                "title"
            )

        bank_book_id = (
            form["bank_book"].value() if "bank_book" in form.fields else None
        )
        owner_name = "nie wybrano"
        owner_phone = "nie wybrano"
        if bank_book_id:
            try:
                book = BankBooks.objects.select_related(
                    "flat", "flat__owner"
                ).get(pk=bank_book_id)
                owner = book.flat.owner if book.flat_id else None
                if owner:
                    owner_name = owner.get_full_name() or owner.email
                    owner_phone = (
                        str(owner.phone_number)
                        if hasattr(owner, "phone_number")
                        and owner.phone_number
                        else "nie wybrano"
                    )
            except BankBooks.DoesNotExist:
                pass

        meter_readings = []
        if selected_flat:
            meter_readings = list(
                MeterReadings.objects.filter(flat=selected_flat)
                .select_related(
                    "meter_type",
                    "meter_type__unit_of_measurement",
                    "flat",
                    "flat__house",
                    "flat__section",
                )
                .order_by("-created_at")
            )

        return {
            "form": form,
            "formset": formset,
            "receipt": receipt,
            "form_url": form_url,
            "page_title": page_title,
            "breadcrumbs": breadcrumbs,
            "selected_house": selected_house,
            "selected_section": selected_section,
            "selected_floor": selected_floor,
            "sections": sections,
            "floors": floors,
            "selected_flat": selected_flat,
            "owner_name": owner_name,
            "owner_phone": owner_phone,
            "meter_readings": meter_readings,
        }


class PaymentReceiptsCreateView(
    RoleRequiredMixin, PaymentReceiptFormContextMixin, View
):
    permission_required = "has_payment_receipts"

    def get(self, request, bank_book_id=None):
        initial = {}
        if bank_book_id:
            try:
                book = BankBooks.objects.select_related(
                    "flat", "flat__house", "flat__section", "flat__floor"
                ).get(pk=bank_book_id)
                initial["bank_book"] = book.pk
                if book.flat_id:
                    flat = book.flat
                    initial["flat"] = flat.pk
                    if flat.house_id:
                        initial["house"] = flat.house_id
                    if flat.section_id:
                        initial["section"] = flat.section_id
                    if flat.floor_id:
                        initial["floor"] = flat.floor_id
            except BankBooks.DoesNotExist:
                pass
        form = PaymentReceiptForm(initial=initial)
        formset = PaymentReceiptServiceFormSet()
        return render(
            request, self.template_name, self.get_form_context(form, formset)
        )

    def post(self, request):
        form = PaymentReceiptForm(request.POST)
        formset = PaymentReceiptServiceFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                receipt = form.save()
                formset.instance = receipt
                formset.save()
            messages.success(request, "Rachunek zapisano.")
            return redirect(
                reverse_lazy(
                    "finances:payment_receipts_detail",
                    kwargs={"pk": receipt.pk},
                )
            )
        return render(
            request, self.template_name, self.get_form_context(form, formset)
        )


class PaymentReceiptsUpdateView(
    RoleRequiredMixin, PaymentReceiptFormContextMixin, View
):
    permission_required = "has_payment_receipts"

    def get_object(self, pk):
        return get_object_or_404(PaymentReceipts, pk=pk)

    def get(self, request, pk):
        receipt = self.get_object(pk)
        form = PaymentReceiptForm(instance=receipt)
        formset = PaymentReceiptServiceFormSet(instance=receipt)
        return render(
            request,
            self.template_name,
            self.get_form_context(form, formset, receipt),
        )

    def post(self, request, pk):
        receipt = self.get_object(pk)
        form = PaymentReceiptForm(request.POST, instance=receipt)
        formset = PaymentReceiptServiceFormSet(request.POST, instance=receipt)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                receipt = form.save()
                formset.save()
            messages.success(request, "Rachunek zapisano.")
            return redirect(
                reverse_lazy(
                    "finances:payment_receipts_detail",
                    kwargs={"pk": receipt.pk},
                )
            )
        else:
            print(form.errors)
            print(formset.errors)
            return render(
                request,
                self.template_name,
                self.get_form_context(form, formset, receipt),
            )


class PaymentReceiptsDetailView(RoleRequiredMixin, DetailView):
    permission_required = "has_payment_receipts"
    model = PaymentReceipts
    template_name = "payment_receipts/detail.html"
    context_object_name = "invoice"

    def get_queryset(self):
        return PaymentReceipts.objects.select_related(
            "flat",
            "flat__house",
            "flat__section",
            "flat__owner",
            "tariff",
            "bank_book",
        ).prefetch_related(
            "lines", "lines__service", "lines__service__unit_of_measurement"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object
        context["page_title"] = f"Rachunek {obj.random_number}"
        context["breadcrumbs"] = [
            {
                "title": "Rachunki do zapłaty",
                "url": reverse_lazy("finances:payment_receipts_list"),
            },
            {
                "title": obj.random_number,
                "url": reverse_lazy(
                    "finances:payment_receipts_detail", kwargs={"pk": obj.pk}
                ),
            },
        ]
        context["lines"] = obj.lines.all()
        context["total_amount"] = (
            f"{sum(l.price * l.amount for l in obj.lines.all()):.2f}"
        )
        return context


class PaymentReceiptsDeleteView(RoleRequiredMixin, View):
    permission_required = "has_payment_receipts"
    success_url = reverse_lazy("finances:payment_receipts_list")

    def post(self, request, pk):
        receipt = get_object_or_404(PaymentReceipts, pk=pk)
        number = receipt.random_number
        receipt.delete()
        messages.success(request, f"Rachunek {number} usunięto.")
        return redirect(self.success_url)


def _get_receipt_with_relations(pk):
    return get_object_or_404(
        PaymentReceipts.objects.select_related(
            "flat",
            "flat__house",
            "flat__section",
            "flat__owner",
            "tariff",
            "bank_book",
        ).prefetch_related(
            "lines", "lines__service", "lines__service__unit_of_measurement"
        ),
        pk=pk,
    )


class PaymentReceiptPrintView(RoleRequiredMixin, View):
    permission_required = "has_payment_receipts"
    template_name = "payment_receipts/print.html"

    def get(self, request, pk):
        receipt = _get_receipt_with_relations(pk)
        templates = ReceiptTemplate.objects.order_by("created_at")
        default = (
            templates.filter(is_default=True).first() or templates.first()
        )
        return render(
            request,
            self.template_name,
            {
                "invoice": receipt,
                "templates": templates,
                "default_template": default,
                "page_title": "Wydruk dokumentu",
                "breadcrumbs": [
                    {
                        "title": "Rachunki do zapłaty",
                        "url": reverse_lazy("finances:payment_receipts_list"),
                    },
                    {
                        "title": receipt.random_number,
                        "url": reverse(
                            "finances:payment_receipts_detail", args=[pk]
                        ),
                    },
                    {
                        "title": "Wydruk",
                        "url": reverse(
                            "finances:payment_receipts_print", args=[pk]
                        ),
                    },
                ],
            },
        )


class PaymentReceiptDownloadView(RoleRequiredMixin, View):
    permission_required = "has_payment_receipts"

    def get(self, request, pk):
        receipt = _get_receipt_with_relations(pk)
        template_id = request.GET.get("template_id", "").strip()
        xlsx = generate_receipt_xlsx(receipt, template_id=template_id or None)
        if xlsx is None:
            messages.error(
                request,
                "Szablon rachunku nie jest wgrany. Wgraj szablon w sekcji «Szablony rachunków».",
            )
            return redirect(
                reverse("finances:payment_receipts_print", args=[pk])
            )
        filename = f"receipt_{receipt.random_number}.xlsx"
        response = HttpResponse(
            xlsx,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class PaymentReceiptEmailView(RoleRequiredMixin, View):
    permission_required = "has_payment_receipts"

    def post(self, request, pk):
        receipt = _get_receipt_with_relations(pk)
        owner = (
            receipt.flat.owner
            if receipt.flat_id and receipt.flat.owner_id
            else None
        )
        if not owner or not owner.email:
            messages.error(
                request, "Właściciel mieszkania nie ma podanego adresu e-mail."
            )
            return redirect(
                reverse("finances:payment_receipts_print", args=[pk])
            )

        template_id = request.POST.get("template_id", "").strip()
        pdf = generate_receipt_pdf(receipt, template_id=template_id or None)
        if pdf is None:
            messages.error(
                request,
                "Szablon rachunku nie jest wgrany. Wgraj szablon w sekcji «Szablony rachunków».",
            )
            return redirect(
                reverse("finances:payment_receipts_print", args=[pk])
            )

        filename = f"receipt_{receipt.random_number}.pdf"
        email = EmailMessage(
            subject=f"Rachunek do zapłaty nr{receipt.random_number}",
            body=(
                f"Dzień dobry, {owner.get_full_name() or owner.email}!\n\n"
                f"W załączniku — rachunek do zapłaty nr{receipt.random_number}.\n\n"
                "Z poważaniem, administracja."
            ),
            to=[owner.email],
        )
        email.attach(filename, pdf, "application/pdf")
        email.send(fail_silently=False)
        messages.success(request, f"Rachunek wysłano na {owner.email}.")
        return redirect(reverse("finances:payment_receipts_print", args=[pk]))
