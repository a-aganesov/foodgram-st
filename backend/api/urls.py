from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import UserViewSet
from api.views import RecipeViewSet, IngredientViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("recipes", RecipeViewSet, basename="recipes")
router.register("ingredients", IngredientViewSet, basename="ingredients")

urlpatterns = [
    path("", include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
