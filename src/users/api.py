from ninja import NinjaAPI, Schema

from .models import Roles

api = NinjaAPI()


class Select2Item(Schema):
    id: int
    text: str


class Select2Pagination(Schema):
    more: bool


class Select2Response(Schema):
    results: list[Select2Item]
    pagination: Select2Pagination


@api.get("/roles/select2", response=Select2Response)
def roles_select2(request, term: str = "", page: int = 1):
    page_size = 10
    qs = Roles.objects.all().order_by("role")

    if term:
        qs = qs.filter(role__icontains=term)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size

    items = [{"id": obj.id, "text": obj.role} for obj in qs[start:end]]

    return {"results": items, "pagination": {"more": end < total}}
