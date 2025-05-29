from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
import uuid


class Ingredient(models.Model):
    name = models.CharField(max_length=128, verbose_name="Название")
    measurement_unit = models.CharField(
        max_length=64, verbose_name="Единица измерения"
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "measurement_unit"], name="unique_ingredient"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор",
    )
    name = models.CharField(max_length=256, verbose_name="Название рецепта")
    image = models.ImageField(
        upload_to="recipes/images/", verbose_name="Картинка"
    )
    text = models.TextField(verbose_name="Описание")
    cooking_time = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1, message="Минимальное время — 1 минута")
        ],
        verbose_name="Время приготовления (мин)",
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through="RecipeIngredient",
        related_name="recipes",
        verbose_name="Ингредиенты",
    )
    pub_date = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата публикации"
    )
    short_uuid = models.CharField(max_length=8, unique=True, editable=False)

    class Meta:
        ordering = ["-pub_date"]
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.short_uuid:
            self.short_uuid = uuid.uuid4().hex[:3]
        super().save(*args, **kwargs)


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name="recipe_ingredients"
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, related_name="ingredient_recipes"
    )
    amount = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1, message="Минимальное количество — 1")
        ],
        verbose_name="Количество",
    )

    class Meta:
        verbose_name = "Ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецептах"
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "ingredient"],
                name="unique_recipe_ingredient",
            )
        ]

    def __str__(self):
        return f"{self.ingredient.name} — {self.amount}"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="Рецепт",
    )

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="unique_favorite"
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.recipe}"


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="shopping_cart",
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="in_shopping_carts",
        verbose_name="Рецепт",
    )

    class Meta:
        verbose_name = "Список покупок"
        verbose_name_plural = "Списки покупок"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"], name="unique_shopping_cart"
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.recipe}"
