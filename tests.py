from models import DeliveryOrder
from rest_framework import status
from rest_framework.test import APITestCase


class DeliveryOrderTests(APITestCase):

    def test_create_new_order(self):
        data = {
            "customer_id": 1,
            "pizzas": [
                {
                    "number": 5,
                    "type": 2,
                    "size": 2
                }
            ]
        }
        response = self.client.post('api/admin/pizza-orders', data, format='json')
        self.assertEqual(
            response.data, {
                "id": 1,
                "pizzas": [
                    {
                        "name": "Pepperoni",
                        "size": "50cm",
                        "amount": 5,
                        "price": 100
                    }
                ],
                "total_price": "100.00",
                "estimated_total_price": 100
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(DeliveryOrder.objects.count(), 1)
