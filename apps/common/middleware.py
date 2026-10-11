"""Let Django parse form data for HTMX PUT/PATCH/DELETE requests.

Django only populates ``request.POST`` for the POST method. HTMX issues real
PUT/PATCH/DELETE verbs, so we normalise the method to POST for parsing while
preserving the original verb in a private attribute.
"""
from django.http import QueryDict


class HtmxMethodMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in {"PUT", "PATCH", "DELETE"}:
            request.real_method = request.method
            # Allow request.POST / request.FILES to be populated.
            if request.content_type in (
                "application/x-www-form-urlencoded",
                "multipart/form-data",
            ):
                request.POST = QueryDict(request.body)
            request.method = "POST"
        else:
            request.real_method = request.method
        return self.get_response(request)


def get_real_method(request) -> str:
    return getattr(request, "real_method", request.method)
