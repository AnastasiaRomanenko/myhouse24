from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.views.generic import ListView
from django.urls import reverse_lazy

Users = get_user_model()
# Create your views here.
class OwnersView(ListView):
    context_object_name = "data"
    queryset = Users.objects.filter(is_staff=False)
    template_name = "owners/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Владельцы квартир"
        context["breadcrumbs"] = [
            {"title": "Владельцы квартир", "url": reverse_lazy("users:owners")},
        ]
        return context
