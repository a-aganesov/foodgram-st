from django.db.models import Sum
from django.http import HttpResponse
from django.urls import reverse
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import get_user_model
from kitchen.models import (
    Recipe,
    Favorite,
    ShoppingCart,
    RecipeIngredient,
    Ingredient,
)
from users.models import Follow
from api.serializers import (
    RecipeReadSerializer,
    RecipeWriteSerializer,
    IngredientSerializer,
    RecipeActionSerializer,
    SubscriptionSerializer,
    SetPasswordSerializer,
    UserSerializer,
    UserCreateSerializer,
    FollowCreateSerializer,
)
from api.permissions import IsAuthorOrReadOnly
from api.filters import RecipeFilter
from api.pagination import PageNumberPagination
from http import HTTPStatus


User = get_user_model()


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
                return Response(
                    {"detail": "Уже добавлено"}, status=HTTPStatus.BAD_REQUEST
                )

            serializer = RecipeActionSerializer(
                recipe, context={"request": self.request}
            )
            return Response(serializer.data, status=HTTPStatus.CREATED)

        deleted_count, _ = model.objects.filter(
            user=user, recipe=recipe
        ).delete()
        if deleted_count == 0:
            return Response(
                {"detail": "Не найдено"}, status=HTTPStatus.BAD_REQUEST
            )

        return Response(status=HTTPStatus.NO_CONTENT)

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
            f"{item['ingredient__name']} ({item['ingredient__measurement_unit']}) — {item['total']}"
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
    url = reverse("recipes-detail", args=[recipe.id])
    return redirect(url)


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


# class SubscribeViewSet(viewsets.ViewSet):
#     permission_classes = [permissions.IsAuthenticated]

#     @action(detail=False, methods=["get"])
#     def subscriptions(self, request):
#         user = request.user
#         follows = user.follower.select_related("author")
#         authors = [follow.author for follow in follows]
#         page = self.paginate_queryset(authors)
#         serializer = SubscriptionSerializer(
#             page, many=True, context={"request": request}
#         )
#         return self.get_paginated_response(serializer.data)

#     @action(detail=True, methods=["post"], url_path="subscribe")
#     def subscribe(self, request, pk=None):
#         author = get_object_or_404(User, pk=pk)
#         data = {
#             "user": request.user.id,
#             "author": author.id,
#         }
#         serializer = FollowCreateSerializer(
#             data=data, context={"request": request}
#         )
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         response_serializer = SubscriptionSerializer(
#             author, context={"request": request}
#         )
#         return Response(response_serializer.data, status=HTTPStatus.CREATED)

#     @subscribe.mapping.delete
#     def unsubscribe(self, request, pk=None):
#         user = request.user
#         try:
#             author = User.objects.get(pk=pk)
#         except User.DoesNotExist:
#             return Response(
#                 {"detail": "Пользователь не найден"},
#                 status=HTTPStatus.NOT_FOUND,
#             )

#         follow = user.follower.filter(author=author).first()
#         if not follow:
#             return Response(
#                 {"detail": "Нет подписки"}, status=HTTPStatus.BAD_REQUEST
#             )

#         follow.delete()
#         return Response(status=HTTPStatus.NO_CONTENT)

#     def paginate_queryset(self, queryset):

#         paginator = PageNumberPagination()
#         paginator.page_size = 6
#         return paginator.paginate_queryset(queryset, self.request, view=self)

#     def get_paginated_response(self, data):

#         paginator = PageNumberPagination()
#         return paginator.get_paginated_response(data)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    @action(
        detail=False,
        methods=["get", "put"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def me(self, request):
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["put", "delete"],
        url_path="me/avatar",
        permission_classes=[permissions.IsAuthenticated],
    )
    def set_avatar(self, request):
        user = request.user

        if request.method == "PUT":
            if "avatar" not in request.data or not request.data["avatar"]:
                return Response(
                    {"avatar": "Это поле обязательно."},
                    status=HTTPStatus.BAD_REQUEST,
                )
            serializer = UserSerializer(
                user,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {"avatar": request.build_absolute_uri(user.avatar.url)}
            )

        if request.method == "DELETE":
            user.avatar = None
            user.save()
            return Response(
                {"detail": "Аватар удалён."}, status=HTTPStatus.NO_CONTENT
            )

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def set_password(self, request):
        serializer = SetPasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response(status=HTTPStatus.NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscriptions(self, request):
        author_ids = Follow.objects.filter(user=request.user).values_list(
            "author", flat=True
        )
        authors_qs = User.objects.filter(pk__in=author_ids)
        page = self.paginate_queryset(authors_qs)
        if page is not None:
            serializer = SubscriptionSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = SubscriptionSerializer(
            authors_qs, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="subscribe",
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        data = {
            "user": request.user.id,
            "author": author.id,
        }
        serializer = FollowCreateSerializer(
            data=data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response_serializer = SubscriptionSerializer(
            author, context={"request": request}
        )
        return Response(response_serializer.data, status=HTTPStatus.CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, pk=None):
        author = author = get_object_or_404(User, pk=pk)
        user = request.user
        follow = user.follower.filter(author=author).first()
        if not follow:
            return Response(
                {"detail": "Вы не подписаны"}, status=HTTPStatus.BAD_REQUEST
            )
        follow.delete()
        return Response(status=HTTPStatus.NO_CONTENT)
