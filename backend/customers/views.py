from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.models import Cart
from shops.models import Shop
from shops.permissions import IsActiveMerchant
from .models import Customer
from .serializers import (
    MerchantCustomerSerializer,
    PublicCustomerInputSerializer,
    PublicCustomerProfileSerializer,
)
from .services import create_or_recognize_customer, recognize_customer


def get_authenticated_merchant_shop(request):
    """
    Resolve and validate the Shop owned by the authenticated Merchant.
    Returns (shop, error_response). If valid, error_response is None.
    """
    user = request.user
    merchant = getattr(user, "merchant", None)
    if merchant is None:
        return None, Response(
            {"detail": "Only active merchants can perform this action.", "code": "NOT_A_MERCHANT"},
            status=status.HTTP_403_FORBIDDEN,
        )
    shop = Shop.objects.filter(merchant_id=merchant.pk, merchant__user_id=user.pk).first()
    if not shop:
        return None, Response(
            {"detail": "Merchant does not have a shop.", "code": "SHOP_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if shop.status in (Shop.Status.DEACTIVATED, Shop.Status.SUSPENDED):
        return None, Response(
            {"detail": "Shop is deactivated or suspended.", "code": "SHOP_INACTIVE"},
            status=status.HTTP_403_FORBIDDEN,
        )
    return shop, None


def get_public_active_shop(public_slug: str):
    """
    Resolve and validate an active Shop by its public_slug for customer-facing requests.
    Returns (shop, error_response).
    """
    shop = Shop.objects.filter(public_slug=public_slug).first()
    if not shop:
        return None, Response(
            {"detail": "Shop not found.", "code": "SHOP_NOT_FOUND"},
            status=status.HTTP_404_NOT_FOUND,
        )
    if shop.status != Shop.Status.ACTIVE:
        return None, Response(
            {"detail": "Shop is unavailable.", "code": "SHOP_UNAVAILABLE"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return shop, None


class PublicCustomerCreateOrRecognizeView(APIView):
    """
    Public customer endpoint to create or recognize a Shop-specific Customer profile.

    Accessible unauthenticated to allow shoppers to provide their WhatsApp contact
    during catalog browsing or checkout, including before an Order is created.
    Never exposes private Merchant or platform credentials, and never creates a User account.
    """

    permission_classes = [AllowAny]

    def post(self, request, public_slug: str):
        shop, error_res = get_public_active_shop(public_slug)
        if error_res:
            return error_res

        serializer = PublicCustomerInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        whatsapp_number = validated_data["whatsapp_number"]
        name = validated_data.get("name", "")
        cart_id = validated_data.get("cart_id")

        cart = None
        if cart_id is not None:
            cart = Cart.objects.filter(pk=cart_id, shop=shop).first()
            if not cart:
                return Response(
                    {"detail": "Cart not found in this shop.", "code": "CART_NOT_FOUND"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            customer, created = create_or_recognize_customer(
                shop=shop,
                whatsapp_number=whatsapp_number,
                name=name,
                cart=cart,
            )
        except DjangoValidationError as err:
            detail = err.message_dict if hasattr(err, "message_dict") else err.messages
            return Response(
                {"detail": detail, "code": "INVALID_CUSTOMER_DATA"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resp_data = {
            "created": created,
            "customer": PublicCustomerProfileSerializer(customer).data,
        }
        res_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(resp_data, status=res_status)


class PublicCustomerRecognizeView(APIView):
    """
    Public customer endpoint to recognize a returning customer within a Shop.

    Uses WhatsApp number to check if a Customer profile exists strictly for this Shop.
    Prefills customer profile name if recognized; never leaks profiles from other shops.
    """

    permission_classes = [AllowAny]

    def get(self, request, public_slug: str):
        return self._recognize(request, public_slug)

    def post(self, request, public_slug: str):
        return self._recognize(request, public_slug)

    def _recognize(self, request, public_slug: str):
        shop, error_res = get_public_active_shop(public_slug)
        if error_res:
            return error_res

        whatsapp_number = (
            request.query_params.get("whatsapp_number")
            or request.data.get("whatsapp_number")
        )
        if not whatsapp_number:
            return Response(
                {"detail": "WhatsApp number is required.", "code": "WHATSAPP_NUMBER_REQUIRED"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        customer = recognize_customer(shop=shop, whatsapp_number=str(whatsapp_number))
        if not customer:
            return Response(
                {
                    "recognized": False,
                    "detail": "Customer not found in this shop.",
                    "code": "CUSTOMER_NOT_FOUND",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "recognized": True,
                "customer": PublicCustomerProfileSerializer(customer).data,
            },
            status=status.HTTP_200_OK,
        )


class MerchantCustomerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnly ViewSet for Merchant retrieval of Shop-specific Customer profiles for ERP use.

    - Authorization: Derived strictly on the server from the authenticated user's active merchant shop.
    - Tenant Isolation: Merchant can only retrieve profiles belonging to their own Shop.
    - Global Identity Boundary: A global contact identity does not make another Shop's profile or history accessible.
    - ERP Search & Filtering: Supports filtering by search keyword, customer name, and WhatsApp number.
    """

    serializer_class = MerchantCustomerSerializer
    permission_classes = [IsAuthenticated, IsActiveMerchant]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        shop, error_res = get_authenticated_merchant_shop(request)
        self._shop = shop
        self._shop_error = error_res

    def get_queryset(self):
        if getattr(self, "_shop_error", None):
            return Customer.objects.none()
        shop = getattr(self, "_shop", None)
        if not shop:
            return Customer.objects.none()

        # Reject or return none if client attempts to pass an unmatching shop parameter
        client_shop_id = self.request.query_params.get("shop_id") or self.request.query_params.get("shop")
        if client_shop_id and str(client_shop_id) != str(shop.pk):
            return Customer.objects.none()

        queryset = Customer.objects.filter(shop=shop).order_by("-created_at", "id")

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(whatsapp_number__icontains=search)
            )

        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)

        whatsapp_number = self.request.query_params.get("whatsapp_number")
        if whatsapp_number:
            cleaned = str(whatsapp_number).strip().replace(" ", "").replace("-", "")
            queryset = queryset.filter(
                Q(whatsapp_number=whatsapp_number)
                | Q(whatsapp_number=f"+91{cleaned}")
                | Q(whatsapp_number__endswith=cleaned)
            )

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["shop"] = getattr(self, "_shop", None)
        return context

    def list(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        if getattr(self, "_shop_error", None):
            return self._shop_error
        return super().retrieve(request, *args, **kwargs)

