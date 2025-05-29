import django_filters
from kitchen.models import Recipe


class RecipeFilter(django_filters.FilterSet):
    author = django_filters.NumberFilter(field_name="author__id")
    is_favorited = django_filters.CharFilter(method="filter_is_favorited")
    is_in_shopping_cart = django_filters.CharFilter(method="filter_in_cart")

    class Meta:
        model = Recipe
        fields = ["author", "is_favorited", "is_in_shopping_cart"]

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if user.is_anonymous:
            return queryset.none()

        if value in ("1", "true", "yes"):
            return queryset.filter(favorited_by__user=user).distinct()

        return queryset

    def filter_in_cart(self, queryset, name, value):
        user = self.request.user
        if user.is_anonymous:
            return queryset.none()

        if value in ("1", "true", "yes"):
            qs = queryset.filter(in_shopping_carts__user=user).distinct()
            return qs

        return queryset
