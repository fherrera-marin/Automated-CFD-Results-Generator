from rest_framework.routers import DefaultRouter

from .views import RunViewSet

router = DefaultRouter()
router.register("", RunViewSet, basename="run")

urlpatterns = router.urls
