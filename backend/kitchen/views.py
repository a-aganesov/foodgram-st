from django.db.models import Sum
from django.http import HttpResponse
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import redirect, get_object_or_404
from kitchen.models import (
    Recipe,
    Favorite,
    ShoppingCart,
    RecipeIngredient,
    Ingredient,
)
from kitchen.serializers import (
    RecipeReadSerializer,
    RecipeWriteSerializer,
    IngredientSerializer,
    RecipeActionSerializer,
)
from kitchen.permissions import IsAuthorOrReadOnly
from kitchen.filters import RecipeFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly,
    ]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.request.method in ("GET",):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=["post", "delete"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        return self._add_or_remove(
            Favorite, request.user, pk, add=(request.method == "POST")
        )

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        return self._add_or_remove(ShoppingCart, request.user, pk, add=True)

    @shopping_cart.mapping.delete
    def remove_from_cart(self, request, pk=None):
        return self._add_or_remove(ShoppingCart, request.user, pk, add=False)

    def _add_or_remove(self, model, user, pk, add):
        recipe = get_object_or_404(self.get_queryset(), pk=pk)

        if add:
            obj, created = model.objects.get_or_create(
                user=user, recipe=recipe
            )
            if not created:
                return Response({"detail": "Уже добавлено"}, status=400)

            serializer = RecipeActionSerializer(
                recipe, context={"request": self.request}
            )
            return Response(serializer.data, status=201)

        deleted_count, _ = model.objects.filter(
            user=user, recipe=recipe
        ).delete()
        if deleted_count == 0:
            return Response({"detail": "Не найдено"}, status=400)

        return Response(status=204)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__in_shopping_carts__user=request.user
            )
            .values("ingredient__name", "ingredient__measurement_unit")
            .annotate(total=Sum("amount"))
            .order_by("ingredient__name")
        )

        lines = [
            f"{item['ingredient__name']} \
                ({item['ingredient__measurement_unit']}) — {item['total']}"
            for item in ingredients
        ]
        content = "\n".join(lines)
        filename = "shopping_list.txt"

        response = HttpResponse(content, content_type="text/plain")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_short_link(self, request, pk=None):
        recipe = self.get_object()
        base_url = request.build_absolute_uri("/")[:-1]
        return Response({"short-link": f"{base_url}/s/{recipe.short_uuid}"})


def redirect_short_link(request, slug):
    recipe = get_object_or_404(Recipe, short_uuid=slug)
    return redirect(f"/recipes/{recipe.id}/")


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        name = self.request.query_params.get("name")
        if name:
            return self.queryset.filter(name__istartswith=name)
        return self.queryset
