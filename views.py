from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from models import Customer, DeliveryOrder
from serializers import DeliveryOrderReadSerializer, \
    DeliveryOrderEditSerializer, DeliveryOrderSaveSerializer

__all__ = [
    'CustomerOrdersView', 'PizzaOrdersView'
]


class CustomerOrdersView(APIView):

    def get(self, request, customer_id):
        customer = get_object_or_404(
            Customer,
            id=customer_id
        )

        return Response(
            data={
                'object_list': DeliveryOrderReadSerializer(
                    DeliveryOrder.objects.filter(
                        customer_id=customer.pk
                    ),
                    many=True
                ).data
            }
        )


class PizzaOrdersView(APIView):

    def post(self, request, order_id=None):
        serializer = DeliveryOrderSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(DeliveryOrderReadSerializer(order).data)

    def put(self, request, order_id):
        pizza_order = get_object_or_404(
            DeliveryOrder.objects.prefetch_related('pizza_links__pizza'),
            id=order_id
        )
        serializer = DeliveryOrderEditSerializer(
            instance=pizza_order, data=request.data
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            DeliveryOrderReadSerializer(
                DeliveryOrder.objects.get(
                    id=order_id
                )
            ).data
        )

    def delete(self, request, order_id):
        pizza_order = get_object_or_404(
            DeliveryOrder,
            id=order_id
        )
        pizza_order.delete()
        return Response(status=200)
