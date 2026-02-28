from rest_framework.routers import DefaultRouter
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView, TokenBlacklistView
)
from app.users.views import (
    RegisterAPI,
    ProfileAPI,
    TelegramLinkCodeView,
    CustomToken,
    ResetPasswordRequestView,
    VerifyCodeView,
    SetNewPasswordView
)

router = DefaultRouter()
router.register(r"register", RegisterAPI, basename='register')
router.register(r"profile", ProfileAPI, basename='profile')

urlpatterns = [
    path("token/", CustomToken.as_view()),
    path("token/refresh/", TokenRefreshView.as_view()),
    path("logout/", TokenBlacklistView.as_view()),
    path("telegram/", TelegramLinkCodeView.as_view()),

    path("reset-password/", ResetPasswordRequestView.as_view()),
    path("verify-code/", VerifyCodeView.as_view()),
    path("set-new-password/", SetNewPasswordView.as_view()),
]

urlpatterns += router.urls
