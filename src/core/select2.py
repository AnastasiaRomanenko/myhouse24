SELECT2_PAGE_SIZE = 10


def select2_response(queryset, page, label_callback):
    page = max(page, 1)
    start = (page - 1) * SELECT2_PAGE_SIZE
    end = start + SELECT2_PAGE_SIZE
    total = queryset.count()

    return {
        "results": [
            {"id": obj.pk, "text": label_callback(obj)}
            for obj in queryset[start:end]
        ],
        "pagination": {
            "more": end < total,
        },
    }


def request_page(request):
    try:
        return int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        return 1


def request_term(request):
    return (request.GET.get("term") or request.GET.get("q") or "").strip()


def selected_object(model, value):
    if not value:
        return None
    try:
        return model.objects.get(pk=value)
    except (model.DoesNotExist, TypeError, ValueError):
        return None


def selected_pk(value):
    value = str(value or "").strip()
    return value if value.isdigit() else None
