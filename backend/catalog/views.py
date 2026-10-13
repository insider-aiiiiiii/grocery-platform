from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from users.permissions import IsSuperAdmin

from .models import MasterProduct
from .serializers import MasterProductSerializer


class MasterProductViewSet(viewsets.ModelViewSet):
    """
    CRUD API for platform-level Master Catalog products.

    Only platform-authorized Super Admin operations are allowed.
    Master Catalog records remain strictly independent of Shop Products:
    - Master Products do not belong to any Shop.
    - Creating, updating, or deleting Master Products does not alter or impair
      existing Shop Products.
    """

    queryset = MasterProduct.objects.all().select_related("category").order_by("name", "id")
    serializer_class = MasterProductSerializer
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            if is_active.lower() in ("true", "1"):
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() in ("false", "0"):
                queryset = queryset.filter(is_active=False)

        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset
