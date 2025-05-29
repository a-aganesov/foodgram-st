from users.models import User, Follow
from djoser.serializers import UserSerializer as BaseUserSerializer
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from core.fields import Base64ImageField
from rest_framework import serializers


class UserSerializer(BaseUserSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "avatar",
            "is_subscribed",
        )

    def get_is_subscribed(self, obj):
        user = self.context.get("request").user
        return (
            user.is_authenticated
            and Follow.objects.filter(user=user, author=obj).exists()
        )


class UserCreateSerializer(BaseUserCreateSerializer):
    first_name = serializers.CharField(
        required=True, max_length=150, allow_blank=False
    )
    last_name = serializers.CharField(
        required=True, max_length=150, allow_blank=False
    )

    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "password",
        )
