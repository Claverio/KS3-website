from wagtail.snippets.views.snippets import (
    CreateView,
    EditView,
    IndexView,
    SnippetViewSet,
    reverse,
)
from django.shortcuts import redirect


class SingletonEditView(EditView):
    """Langsung redirect ke edit instance pertama / buat kalau belum ada."""

    def dispatch(self, request, *args, **kwargs):
        instance, _ = self.model.objects.get_or_create(pk=1)
        self.kwargs["pk"] = instance.pk
        return super().dispatch(request, *args, **kwargs)


class SingletonIndexView(IndexView):
    def dispatch(self, request, *args, **kwargs):
        instance, _ = self.model.objects.get_or_create(pk=1)
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        url = reverse(
            f"wagtailsnippets_{app_label}_{model_name}:edit", args=[instance.pk]
        )
        return redirect(url)


class SingletonSnippetViewSet(SnippetViewSet):
    index_view_class = SingletonIndexView

    def get_queryset(self, request):
        self.model.objects.get_or_create(pk=1)
        return super().get_queryset(request)
