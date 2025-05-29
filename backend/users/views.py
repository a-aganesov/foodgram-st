from rest_framework import permissions, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from users.models import Follow
from users.serializers import SubscriptionSerializer, SetPasswordSerializer
from core.serializers import UserSerializer, UserCreateSerializer

User = get_user_model()


class SubscribeViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def subscriptions(self, request):
        user = request.user
        follows = Follow.objects.filter(user=user).select_related("author")
        authors = [follow.author for follow in follows]
        page = self.paginate_queryset(authors)
        serializer = SubscriptionSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=["post"], url_path="subscribe")
    def subscribe(self, request, pk=None):
        user = request.user
        try:
            author = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "Пользователь не найден"}, status=404)

        if user == author:
            return Response(
                {"detail": "Нельзя подписаться на себя"}, status=400
            )

        if Follow.objects.filter(user=user, author=author).exists():
            return Response({"detail": "Уже подписан"}, status=400)

        Follow.objects.create(user=user, author=author)
        serializer = SubscriptionSerializer(
            author, context={"request": request}
        )
        return Response(serializer.data, status=201)

    @subscribe.mapping.delete
    def unsubscribe(self, request, pk=None):
        user = request.user
        try:
            author = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "Пользователь не найден"}, status=404)

        follow = Follow.objects.filter(user=user, author=author).first()
        if not follow:
            return Response({"detail": "Нет подписки"}, status=400)

        follow.delete()
        return Response(status=204)

    def paginate_queryset(self, queryset):

        paginator = PageNumberPagination()
        paginator.page_size = 6
        return paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):

        paginator = PageNumberPagination()
        return paginator.get_paginated_response(data)


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
                    status=status.HTTP_400_BAD_REQUEST,
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
                {"detail": "Аватар удалён."}, status=status.HTTP_204_NO_CONTENT
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
        return Response(status=status.HTTP_204_NO_CONTENT)

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
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscribe(self, request, pk=None):
        author = self.get_object()
        user = request.user
        if user == author:
            return Response(
                {"detail": "Нельзя подписаться на самого себя"}, status=400
            )
        if Follow.objects.filter(user=user, author=author).exists():
            return Response({"detail": "Вы уже подписаны"}, status=400)
        Follow.objects.create(user=user, author=author)
        serializer = SubscriptionSerializer(
            author, context={"request": request}
        )
        return Response(serializer.data, status=201)

    @subscribe.mapping.delete
    def unsubscribe(self, request, pk=None):
        author = self.get_object()
        user = request.user
        follow = Follow.objects.filter(user=user, author=author).first()
        if not follow:
            return Response({"detail": "Вы не подписаны"}, status=400)
        follow.delete()
        return Response(status=204)
