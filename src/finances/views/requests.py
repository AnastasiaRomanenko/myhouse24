from ajax_datatable import AjaxDatatableView
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.text import Truncator
from django.views import View
from django.views.generic import DetailView, TemplateView

from src.core.mixins import RoleRequiredMixin
from src.finances.forms import RequestForm
from src.finances.models import Requests
from src.finances.views.meter_readings import parse_filter_date


def user_name(user):
    if not user:
        return "-"
    return user.get_full_name() or user.email


class RequestsListView(RoleRequiredMixin, TemplateView):
    permission_required = "has_requests"
    template_name = "requests/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Zgłoszenia serwisowe"
        context["breadcrumbs"] = [
            {
                "title": "Zgłoszenia serwisowe",
                "url": reverse_lazy("finances:requests_list"),
            },
        ]
        return context


class RequestsAjaxDatatableView(RoleRequiredMixin, AjaxDatatableView):
    permission_required = "has_requests"
    model = Requests
    title = "Zgłoszenia serwisowe"
    initial_order = [["pk", "desc"]]
    length_menu = [[10, 25, 50], [10, 25, 50]]
    disable_queryset_optimization = True

    column_defs = [
        {"name": "pk", "title": "Nr zgłoszenia"},
        {"name": "date_time", "title": "Preferowany czas"},
        {"name": "description", "title": "Opis"},
        {"name": "flat", "title": "Mieszkanie"},
        {"name": "owner", "title": "Właściciel"},
        {"name": "phone", "title": "Telefon"},
        {"name": "worker", "title": "Specjalista"},
        {"name": "status", "title": "Status"},
        {"name": "actions", "title": ""},
    ]

    def get_initial_queryset(self, request=None):
        queryset = Requests.objects.select_related(
            "flat",
            "flat__house",
            "owner",
            "worker",
            "worker__role",
        )

        if request is None:
            return queryset

        request_id = request.GET.get("request_id", "").strip()
        date_time = parse_filter_date(request.GET.get("date_time"))
        description = request.GET.get("description", "").strip()
        flat = request.GET.get("flat", "").strip()
        owner = request.GET.get("owner", "").strip()
        phone = request.GET.get("phone", "").strip()
        worker = request.GET.get("worker", "").strip()
        status = request.GET.get("status", "").strip()

        if request_id:
            if request_id.isdigit():
                queryset = queryset.filter(pk=int(request_id))
            else:
                queryset = queryset.none()
        if date_time:
            queryset = queryset.filter(date_time__date=date_time)
        if description:
            queryset = queryset.filter(description__icontains=description)
        if flat:
            if flat.isdigit():
                queryset = queryset.filter(flat__number=int(flat))
            else:
                queryset = queryset.filter(flat__house__title__icontains=flat)
        if owner:
            queryset = queryset.filter(
                Q(owner__first_name__icontains=owner)
                | Q(owner__last_name__icontains=owner)
                | Q(owner__email__icontains=owner)
            )
        if phone:
            queryset = queryset.filter(owner__phone_number__icontains=phone)
        if worker:
            queryset = queryset.filter(
                Q(worker__first_name__icontains=worker)
                | Q(worker__last_name__icontains=worker)
                | Q(worker__email__icontains=worker)
                | Q(worker__role__role__icontains=worker)
            )
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def render_column(self, row, column):
        if column == "date_time":
            if not row.date_time:
                return "-"
            return timezone.localtime(row.date_time).strftime(
                "%d.%m.%Y - %H:%M"
            )

        if column == "description":
            return Truncator(row.description).chars(80)

        if column == "flat":
            return str(row.flat) if row.flat_id else "-"

        if column == "owner":
            return user_name(row.owner)

        if column == "phone":
            return (
                row.owner.phone_number
                if row.owner_id and row.owner.phone_number
                else "-"
            )

        if column == "worker":
            if not row.worker_id:
                return "-"
            role = row.worker.role.role if row.worker.role else ""
            name = user_name(row.worker)
            return f"{role} - {name}" if role else name

        if column == "status":
            return f'<small class="label label-default">{row.get_status_display()}</small>'

        if column == "actions":
            update_url = reverse("finances:requests_update", args=[row.pk])
            delete_url = reverse("finances:requests_delete", args=[row.pk])
            csrf = self.request.COOKIES.get("csrftoken", "")
            return f"""
                <div class="btn-group pull-right">
                    <a class="btn btn-default btn-sm" href="{update_url}" title="Edytuj" data-toggle="tooltip">
                        <i class="fa fa-pencil"></i>
                    </a>
                    <form method="post" action="{delete_url}" style="display: inline;">
                        <input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">
                        <button type="submit" class="btn btn-default btn-sm" title="Usuń" data-toggle="tooltip"
                                onclick="return confirm('Usunąć zgłoszenie?');">
                            <i class="fa fa-trash"></i>
                        </button>
                    </form>
                </div>
            """

        return super().render_column(row, column)

    def customize_row(self, row, obj):
        row["row_href"] = reverse("finances:requests_detail", args=[obj.pk])
        return row


class RequestFormContextMixin:
    template_name = "requests/form.html"

    def get_form_context(self, form, request_obj=None):
        if request_obj:
            page_title = "Edytuj zgłoszenie"
            form_url = reverse_lazy(
                "finances:requests_update", kwargs={"pk": request_obj.pk}
            )
            breadcrumbs = [
                {
                    "title": "Zgłoszenia serwisowe",
                    "url": reverse_lazy("finances:requests_list"),
                },
                {
                    "title": f"Zgłoszenie nr{request_obj.pk}",
                    "url": reverse_lazy(
                        "finances:requests_detail",
                        kwargs={"pk": request_obj.pk},
                    ),
                },
                {"title": "Edytuj", "url": form_url},
            ]
        else:
            page_title = "Nowe zgłoszenie"
            form_url = reverse_lazy("finances:requests_create")
            breadcrumbs = [
                {
                    "title": "Zgłoszenia serwisowe",
                    "url": reverse_lazy("finances:requests_list"),
                },
                {"title": "Nowe zgłoszenie", "url": form_url},
            ]

        return {
            "form": form,
            "request_obj": request_obj,
            "form_url": form_url,
            "page_title": page_title,
            "breadcrumbs": breadcrumbs,
        }


class RequestsCreateView(RoleRequiredMixin, RequestFormContextMixin, View):
    permission_required = "has_requests"

    def get(self, request):
        form = RequestForm()
        return render(request, self.template_name, self.get_form_context(form))

    def post(self, request):
        form = RequestForm(request.POST)
        if form.is_valid():
            request_obj = form.save()
            messages.success(request, "Zgłoszenie zapisano.")
            return redirect(
                reverse_lazy(
                    "finances:requests_detail", kwargs={"pk": request_obj.pk}
                )
            )

        return render(request, self.template_name, self.get_form_context(form))


class RequestsUpdateView(RoleRequiredMixin, RequestFormContextMixin, View):
    permission_required = "has_requests"

    def get_object(self, pk):
        return get_object_or_404(Requests, pk=pk)

    def get(self, request, pk):
        request_obj = self.get_object(pk)
        form = RequestForm(instance=request_obj)
        return render(
            request,
            self.template_name,
            self.get_form_context(form, request_obj),
        )

    def post(self, request, pk):
        request_obj = self.get_object(pk)
        form = RequestForm(request.POST, instance=request_obj)
        if form.is_valid():
            request_obj = form.save()
            messages.success(request, "Zgłoszenie zapisano.")
            return redirect(
                reverse_lazy(
                    "finances:requests_detail", kwargs={"pk": request_obj.pk}
                )
            )

        return render(
            request,
            self.template_name,
            self.get_form_context(form, request_obj),
        )


class RequestsDetailView(RoleRequiredMixin, DetailView):
    permission_required = "has_requests"
    model = Requests
    template_name = "requests/detail.html"
    context_object_name = "request_obj"

    def get_queryset(self):
        return Requests.objects.select_related(
            "flat",
            "flat__house",
            "flat__section",
            "flat__floor",
            "owner",
            "worker",
            "worker__role",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Zgłoszenie nr{self.object.pk}"
        context["breadcrumbs"] = [
            {
                "title": "Zgłoszenia serwisowe",
                "url": reverse_lazy("finances:requests_list"),
            },
            {
                "title": f"Zgłoszenie nr{self.object.pk}",
                "url": reverse_lazy(
                    "finances:requests_detail", kwargs={"pk": self.object.pk}
                ),
            },
        ]
        return context


class RequestsDeleteView(RoleRequiredMixin, View):
    permission_required = "has_requests"
    success_url = reverse_lazy("finances:requests_list")

    def post(self, request, pk):
        request_obj = get_object_or_404(Requests, pk=pk)
        number = request_obj.pk
        request_obj.delete()
        messages.success(request, f"Zgłoszenie nr{number} usunięto.")
        return redirect(self.success_url)
