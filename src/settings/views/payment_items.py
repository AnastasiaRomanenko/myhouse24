from ajax_datatable import AjaxDatatableView
from django.contrib import messages
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView

from src.finances.models import Accounting
from src.settings.enums import Type
from src.settings.forms import PaymentItemsForm
from src.settings.models import PaymentItems


class PaymentItemsListView(TemplateView):
    template_name = "payment_items/list.html"
    permission_required = "has_payment_items"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Pozycje płatności"
        return context


class PaymentItemsAjaxDatatableView(AjaxDatatableView):
    model = PaymentItems
    title = "Pozycje płatności"
    initial_order = [["name", "asc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    permission_required = "has_payment_items"

    column_defs = [
        {"name": "name", "title": "Nazwa"},
        {"name": "type", "title": "Przychód/Wydatek"},
        {"name": "actions", "title": ""},
    ]

    def get_initial_queryset(self, request=None):
        queryset = PaymentItems.objects.annotate(
            is_used_flag=Exists(
                Accounting.objects.filter(payment_item_id=OuterRef("pk")),
            ),
        )

        if request is None:
            return queryset

        name = request.GET.get("name", "").strip()
        item_type = request.GET.get("type", "").strip()

        if name:
            queryset = queryset.filter(name__icontains=name)
        if item_type:
            queryset = queryset.filter(type=item_type)

        return queryset

    def render_column(self, row, column):
        if column == "type":
            if row.type == Type.INCOME:
                return '<span class="text text-green">Przychód</span>'
            return '<span class="text text-red">Wydatek</span>'

        if column == "actions":
            update_url = reverse(
                "settings:payment_items_update", args=[row.pk]
            )
            delete_url = reverse(
                "settings:payment_items_delete", args=[row.pk]
            )
            csrf = self.request.COOKIES.get("csrftoken", "")
            is_used = getattr(row, "is_used_flag", None)
            if is_used is None:
                is_used = row.is_used

            delete_control = """
                <button type="button" class="btn btn-default btn-sm disabled" title="Usuń" data-toggle="tooltip"
                        onclick="alert('Ten element jest używany w systemie i nie może zostać usunięty.');">
                    <i class="fa fa-trash"></i>
                </button>
            """
            if not is_used:
                delete_control = f"""
                    <form method="post" action="{delete_url}" style="display: inline;">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                        <button type="submit" class="btn btn-default btn-sm" title="Usuń" data-toggle="tooltip"
                                onclick="return confirm('Czy na pewno chcesz usunąć ten element?');">
                            <i class="fa fa-trash"></i>
                        </button>
                    </form>
                """

            return f"""
                <div class="btn-group pull-right">
                    <a class="btn btn-default btn-sm" href="{update_url}" title="Edytuj" data-toggle="tooltip">
                        <i class="fa fa-pencil"></i>
                    </a>
                    {delete_control}
                </div>
            """

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        row["row_href"] = reverse(
            "settings:payment_items_update", args=[obj.pk]
        )
        return row


class PaymentItemsCreateView(View):
    template_name = "payment_items/form.html"
    success_url = reverse_lazy("settings:payment_items_list")

    def get(self, request):
        form = PaymentItemsForm()
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "purpose": None,
                "page_title": "Nowa pozycja",
            },
        )

    def post(self, request):
        form = PaymentItemsForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Pozycja utworzona.")
            return redirect(self.success_url)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "purpose": None,
                "page_title": "Nowa pozycja",
            },
        )


class PaymentItemsUpdateView(View):
    template_name = "payment_items/form.html"
    success_url = reverse_lazy("settings:payment_items_list")

    def get_object(self, pk):
        return get_object_or_404(PaymentItems, pk=pk)

    def get(self, request, pk):
        purpose = self.get_object(pk)
        form = PaymentItemsForm(instance=purpose)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "purpose": purpose,
                "page_title": "Edytuj pozycję",
            },
        )

    def post(self, request, pk):
        purpose = self.get_object(pk)
        form = PaymentItemsForm(request.POST, instance=purpose)
        if form.is_valid():
            form.save()
            messages.success(request, "Pozycja zapisana.")
            return redirect(self.success_url)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "purpose": purpose,
                "page_title": "Edytuj pozycję",
            },
        )


class PaymentItemsDeleteView(View):
    model = PaymentItems
    success_url = reverse_lazy("settings:payment_items_list")

    def post(self, request, pk, *args, **kwargs):
        obj = get_object_or_404(self.model, pk=pk)
        if obj.is_used:
            messages.error(
                request,
                "Ten element jest używany w systemie i nie może zostać usunięty.",
            )
            return redirect(self.success_url)
        name = obj.name
        obj.delete()
        messages.success(request, f"Pozycja «{name}» usunięto.")
        return redirect(self.success_url)
