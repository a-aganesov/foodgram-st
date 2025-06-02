from rest_framework import serializers
from django.contrib.auth import password_validation
from django.core.validators import MinValueValidator, MaxValueValidator
from users.models import Follow, User
from api.fields import Base64ImageField
from kitchen.models import Ingredient, Recipe, RecipeIngredient
from djoser.serializers import UserSerializer as BaseUserSerializer
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from core.constants import MIN_INGREDIENT_AMOUNT, MAX_INGREDIENT_AMOUNT, MIN_COOKING_TIME, MAX_COOKING_TIME


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
        request = self.context["request"]
        user = request.user
        if not user.is_authenticated:
            return False
        return obj.following.filter(user=user).exists()


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


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")


class IngredientAmountSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), source="ingredient"
    )
    name = serializers.ReadOnlyField(source="ingredient.name")
    measurement_unit = serializers.ReadOnlyField(
        source="ingredient.measurement_unit"
    )
    amount = serializers.IntegerField(
        validators=[
            MinValueValidator(
                MIN_INGREDIENT_AMOUNT,
                message=f"Минимальное количество — {MIN_INGREDIENT_AMOUNT}",
            ),
            MaxValueValidator(
                MAX_INGREDIENT_AMOUNT,
                message=f"Максимальное количество — {MAX_INGREDIENT_AMOUNT}",
            ),
        ],
        help_text=f"Количество (от {MIN_INGREDIENT_AMOUNT} до {MAX_INGREDIENT_AMOUNT})",
    )

    class Meta:
        model = RecipeIngredient
        fields = ("id", "name", "measurement_unit", "amount")


class RecipeReadSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = IngredientAmountSerializer(
        source="recipe_ingredients", many=True, read_only=True
    )
    image = Base64ImageField(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "author",
            "name",
            "image",
            "text",
            "ingredients",
            "cooking_time",
            "is_favorited",
            "is_in_shopping_cart",
        )

    def get_is_favorited(self, obj):
        request = self.context.get("request")
        if not request or request.user.is_anonymous:
            return False
        return obj.favorited_by.filter(user=request.user).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get("request")
        if not request or request.user.is_anonymous:
            return False
        return obj.in_shopping_carts.filter(user=request.user).exists()


class RecipeWriteSerializer(serializers.ModelSerializer):
    ingredients = IngredientAmountSerializer(many=True)
    image = Base64ImageField()
    cooking_time = serializers.IntegerField(
        validators=[
            MinValueValidator(
                MIN_INGREDIENT_AMOUNT,
                message=f"Минимальное время — {MIN_COOKING_TIME}",
            ),
            MaxValueValidator(
                MAX_INGREDIENT_AMOUNT,
                message=f"Максимальное время — {MAX_COOKING_TIME}",
            ),
        ],
        help_text=f"Время (от {MIN_COOKING_TIME} до {MAX_COOKING_TIME})",
    )

    class Meta:
        model = Recipe
        fields = (
            "id",
            "name",
            "image",
            "text",
            "ingredients",
            "cooking_time",
        )

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Нужен хотя бы один ингредиент.")
        seen = set()
        for item in value:
            ingredient = item["ingredient"]
            if ingredient.id in seen:
                raise serializers.ValidationError(
                    "Ингредиенты не должны повторяться."
                )
            seen.add(ingredient.id)
        return value

    def create_ingredients(self, ingredients, recipe):
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    recipe=recipe,
                    ingredient=item["ingredient"],
                    amount=item["amount"],
                )
                for item in ingredients
            ]
        )

    def create(self, validated_data):
        ingredients = validated_data.pop("ingredients")
        recipe = Recipe.objects.create(**validated_data)
        self.create_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop("ingredients", None)
        if ingredients is None:
            raise serializers.ValidationError(
                {"ingredients": "Это поле обязательно."}
            )
        if not ingredients:
            raise serializers.ValidationError(
                {"ingredients": "Нужен хотя бы один ингредиент."}
            )
        instance = super().update(instance, validated_data)
        instance.recipe_ingredients.all().delete()
        self.create_ingredients(ingredients, instance)
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class SubscriptionRecipeSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "name",
            "image",
            "cooking_time",
        )

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image and hasattr(obj.image, "url"):
            return request.build_absolute_uri(obj.image.url)
        return None


class RecipeActionSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "name",
            "image",
            "cooking_time",
        )

    def get_image(self, obj):
        request = self.context.get("request")
        if obj.image and hasattr(obj.image, "url"):
            return request.build_absolute_uri(obj.image.url)
        return None


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
        return request.user.follower.filter(author=obj).exists()

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


class FollowCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Follow
        fields = ("user", "author")

    def validate(self, data):
        request_user = self.context["request"].user
        author = data["author"]

        if request_user.id != data["user"].id:
            raise serializers.ValidationError(
                "Неверный пользователь в запросе"
            )

        if request_user == author:
            raise serializers.ValidationError("Нельзя подписаться на себя")

        if request_user.follower.filter(author=author).exists():
            raise serializers.ValidationError("Уже подписан")

        return data

    def create(self, validated_data):
        return Follow.objects.create(**validated_data)
