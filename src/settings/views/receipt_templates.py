import os

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from src.core.mixins import RoleRequiredMixin
from src.settings.models import ReceiptTemplate


class ReceiptTemplatesView(RoleRequiredMixin, TemplateView):
    permission_required = "has_payment_details"
    template_name = "receipt_templates/settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Konfiguracja szablonów"
        context["breadcrumbs"] = [
            {
                "title": "Rachunki do zapłaty",
                "url": reverse_lazy("finances:payment_receipts_list"),
            },
            {
                "title": "Konfiguracja szablonów",
                "url": reverse_lazy("settings:receipt_templates"),
            },
        ]
        context["templates"] = ReceiptTemplate.objects.order_by("created_at")
        return context

    def post(self, request):
        name = request.POST.get("name", "").strip()
        file = request.FILES.get("file")
        if not name:
            messages.error(request, "Podaj nazwę szablonu.")
            return redirect(reverse_lazy("settings:receipt_templates"))
        if not file:
            messages.error(request, "Wybierz plik szablonu.")
            return redirect(reverse_lazy("settings:receipt_templates"))
        is_first = not ReceiptTemplate.objects.exists()
        ReceiptTemplate.objects.create(
            name=name, file=file, is_default=is_first
        )
        messages.success(request, f'Szablon "{name}" wgrany.')
        return redirect(reverse_lazy("settings:receipt_templates"))


class ReceiptTemplateSetDefaultView(RoleRequiredMixin, View):
    permission_required = "has_payment_details"

    def post(self, request, pk):
        tpl = get_object_or_404(ReceiptTemplate, pk=pk)
        ReceiptTemplate.objects.exclude(pk=pk).update(is_default=False)
        tpl.is_default = True
        tpl.save()
        messages.success(
            request, f'Szablon "{tpl.name}" ustawiony jako domyślny.'
        )
        return redirect(reverse_lazy("settings:receipt_templates"))


class ReceiptTemplateDownloadView(RoleRequiredMixin, View):
    permission_required = "has_payment_details"

    def get(self, request, pk):
        tpl = get_object_or_404(ReceiptTemplate, pk=pk)
        if not tpl.file or not os.path.exists(tpl.file.path):
            raise Http404
        response = FileResponse(open(tpl.file.path, "rb"), as_attachment=True)
        response["Content-Disposition"] = (
            f'attachment; filename="{os.path.basename(tpl.file.name)}"'
        )
        return response


class ReceiptTemplateDeleteView(RoleRequiredMixin, View):
    permission_required = "has_payment_details"

    def post(self, request, pk):
        tpl = get_object_or_404(ReceiptTemplate, pk=pk)
        name = tpl.name
        if tpl.file and os.path.exists(tpl.file.path):
            os.remove(tpl.file.path)
        was_default = tpl.is_default
        tpl.delete()
        if was_default:
            first = ReceiptTemplate.objects.order_by("created_at").first()
            if first:
                first.is_default = True
                first.save()
        messages.success(request, f'Szablon "{name}" usunięto.')
        return redirect(reverse_lazy("settings:receipt_templates"))
