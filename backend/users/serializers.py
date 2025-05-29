from rest_framework import serializers
from django.contrib.auth import password_validation
from users.models import Follow, User
from kitchen.serializers import SubscriptionRecipeSerializer


class SetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    current_password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.context["request"].user
        if not user.check_password(data["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "Неверный пароль"}
            )
        password_validation.validate_password(data["new_password"], user)
        return data


class SubscriptionSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "recipes",
            "recipes_count",
            "avatar",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if not request or request.user.is_anonymous:
            return False
        return Follow.objects.filter(user=request.user, author=obj).exists()

    def get_recipes(self, obj):
        request = self.context.get("request")
        recipes = obj.recipes.all()
        if request:
            limit = request.query_params.get("recipes_limit")
            if limit:
                try:
                    recipes = recipes[: int(limit)]
                except (ValueError, TypeError):
                    pass
        return SubscriptionRecipeSerializer(
            recipes, many=True, context={"request": request}
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_avatar(self, obj):
        request = self.context.get("request")
        if obj.avatar and hasattr(obj.avatar, "url"):
            return request.build_absolute_uri(obj.avatar.url)
        return None
