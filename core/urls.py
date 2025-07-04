from django.urls import path
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.views.auth_views import register_view, login_view
from core.views.prediction_views import PredictAPIView, dashboard
from core.models import Prediction
from core.serializers import PredictionSerializer

from core.views.misc_views import healthz
from core.views.stripe_checkout import upgrade_to_pro, payment_success


from rest_framework.permissions import IsAuthenticated

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_predictions(request):
    predictions = Prediction.objects.filter(user=request.user)
    serializer = PredictionSerializer(predictions, many=True)
    return Response(serializer.data)

urlpatterns = [
    #  Auth (API + HTML)
    path('register/', register_view, name='register_html'),     # HTML form
    path('login/', login_view, name='login'),                        # HTML form

    #  JWT token endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    #  Prediction API + Dashboard
    path('predict/', PredictAPIView.as_view(), name='predict'),
    path('dashboard/', dashboard, name='dashboard'),

    #  Past predictions list API
    path('predictions/', get_user_predictions, name='predictions'),

    path('healthz/', healthz, name='healthz'),

    path("upgrade/", upgrade_to_pro, name = "upgrade"),
    path("payment-success/", payment_success, name="payment_success"),
]

