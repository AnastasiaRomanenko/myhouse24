from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View

from src.settings.forms import PaymentDetailsForm
from src.settings.models import PaymentDetails


class PaymentDetailsView(View):
    template_name = "payment_details/form.html"
    success_url = reverse_lazy("settings:payment_details")
    permission_required = "has_payment_details"

    def _get_instance(self):
        return PaymentDetails.objects.first()

    def _context(self, form):
        return {
            "form": form,
            "page_title": "Dane płatnicze",
            "breadcrumbs": [
                {
                    "title": "Dane płatnicze",
                    "url": reverse_lazy("settings:payment_details"),
                },
            ],
        }

    def get(self, request):
        instance = self._get_instance()
        form = PaymentDetailsForm(instance=instance)
        return render(request, self.template_name, self._context(form))

    def post(self, request):
        instance = self._get_instance()
        form = PaymentDetailsForm(request.POST, instance=instance)

        if form.is_valid():
            form.save()
            messages.success(request, "Dane płatnicze zapisano.")
            return redirect(self.success_url)

        return render(request, self.template_name, self._context(form))
