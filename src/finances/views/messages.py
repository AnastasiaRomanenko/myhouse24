from ajax_datatable import AjaxDatatableView
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.text import Truncator
from django.views import View
from django.views.generic import DetailView, TemplateView

from src.core.mixins import RoleRequiredMixin
from src.finances.forms import MessagesForm
from src.finances.models import Messages


class MessagesListView(RoleRequiredMixin, TemplateView):
    permission_required = "has_messages"
    template_name = "messages/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Wiadomości"
        context["breadcrumbs"] = [
            {
                "title": "Wiadomości",
                "url": reverse_lazy("finances:messages_list"),
            },
        ]
        return context


class MessagesAjaxDatatableView(RoleRequiredMixin, AjaxDatatableView):
    permission_required = "has_messages"
    model = Messages
    title = "Wiadomości"
    initial_order = [["pk", "desc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    disable_queryset_optimization = True

    column_defs = [
        {"name": "selection", "title": ""},
        {"name": "recipient", "title": "Odbiorcy"},
        {"name": "title", "title": "Temat"},
        {"name": "description", "title": "Treść"},
        {"name": "actions", "title": ""},
    ]

    def get_initial_queryset(self, request=None):
        queryset = Messages.objects.select_related(
            "flat",
            "flat__house",
            "flat__owner",
        )

        if request is None:
            return queryset

        search = request.GET.get("search", "").strip()
        if search:
            message_filter = (
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(flat__house__title__icontains=search)
            )
            if search.isdigit():
                message_filter |= Q(flat__number=int(search))
            queryset = queryset.filter(message_filter)

        return queryset

    def render_column(self, row, column):
        if column == "selection":
            return (
                f'<input type="checkbox" name="selection[]" value="{row.pk}">'
            )

        if column == "recipient":
            if row.to_debtors:
                return "Właścicielom z zadłużeniami"
            return str(row.flat) if row.flat_id else "Wszystkim"

        if column == "description":
            return Truncator(row.description).chars(120)

        if column == "actions":
            update_url = reverse("finances:messages_update", args=[row.pk])
            delete_url = reverse("finances:messages_delete", args=[row.pk])
            csrf = self.request.COOKIES.get("csrftoken", "")
            return f"""
                <div class="btn-group pull-right">
                    <a class="btn btn-default btn-sm" href="{update_url}" title="Edytuj" data-toggle="tooltip">
                        <i class="fa fa-pencil"></i>
                    </a>
                    <form method="post" action="{delete_url}" style="display: inline;">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                        <button type="submit" class="btn btn-default btn-sm" title="Usuń" data-toggle="tooltip"
                                onclick="return confirm('Usunąć wiadomość?');">
                            <i class="fa fa-trash-o"></i>
                        </button>
                    </form>
                </div>
            """

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        row["row_href"] = reverse("finances:messages_detail", args=[obj.pk])
        return row


class MessageFormContextMixin:
    template_name = "messages/form.html"

    def get_form_context(self, form, message=None):
        if message:
            page_title = "Edytuj wiadomość"
            form_url = reverse_lazy(
                "finances:messages_update", kwargs={"pk": message.pk}
            )
            breadcrumbs = [
                {
                    "title": "Wiadomości",
                    "url": reverse_lazy("finances:messages_list"),
                },
                {
                    "title": message.title,
                    "url": reverse_lazy(
                        "finances:messages_detail", kwargs={"pk": message.pk}
                    ),
                },
                {"title": "Edytuj", "url": form_url},
            ]
        else:
            page_title = "Nowa wiadomość"
            form_url = reverse_lazy("finances:messages_create")
            breadcrumbs = [
                {
                    "title": "Wiadomości",
                    "url": reverse_lazy("finances:messages_list"),
                },
                {"title": "Nowa wiadomość", "url": form_url},
            ]

        return {
            "form": form,
            "message": message,
            "form_url": form_url,
            "page_title": page_title,
            "breadcrumbs": breadcrumbs,
        }


class MessagesCreateView(RoleRequiredMixin, MessageFormContextMixin, View):
    permission_required = "has_messages"

    def get(self, request):
        form = MessagesForm()
        return render(request, self.template_name, self.get_form_context(form))

    def post(self, request):
        form = MessagesForm(request.POST)
        if form.is_valid():
            message = form.save()
            messages.success(request, "Wiadomość zapisano.")
            return redirect(
                reverse_lazy(
                    "finances:messages_detail", kwargs={"pk": message.pk}
                )
            )

        return render(request, self.template_name, self.get_form_context(form))


class MessagesUpdateView(RoleRequiredMixin, MessageFormContextMixin, View):
    permission_required = "has_messages"

    def get_object(self, pk):
        return get_object_or_404(Messages, pk=pk)

    def get(self, request, pk):
        message = self.get_object(pk)
        form = MessagesForm(instance=message)
        return render(
            request, self.template_name, self.get_form_context(form, message)
        )

    def post(self, request, pk):
        message = self.get_object(pk)
        form = MessagesForm(request.POST, instance=message)
        if form.is_valid():
            message = form.save()
            messages.success(request, "Wiadomość zapisano.")
            return redirect(
                reverse_lazy(
                    "finances:messages_detail", kwargs={"pk": message.pk}
                )
            )

        return render(
            request, self.template_name, self.get_form_context(form, message)
        )


class MessagesDetailView(RoleRequiredMixin, DetailView):
    permission_required = "has_messages"
    model = Messages
    template_name = "messages/detail.html"
    context_object_name = "message"

    def get_queryset(self):
        return Messages.objects.select_related(
            "flat", "flat__house", "flat__owner"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = self.object.title
        context["breadcrumbs"] = [
            {
                "title": "Wiadomości",
                "url": reverse_lazy("finances:messages_list"),
            },
            {
                "title": self.object.title,
                "url": reverse_lazy(
                    "finances:messages_detail", kwargs={"pk": self.object.pk}
                ),
            },
        ]
        return context


class MessagesDeleteView(RoleRequiredMixin, View):
    permission_required = "has_messages"
    success_url = reverse_lazy("finances:messages_list")

    def post(self, request, pk):
        message = get_object_or_404(Messages, pk=pk)
        title = message.title
        message.delete()
        messages.success(request, f"Wiadomość «{title}» usunięto.")
        return redirect(self.success_url)
