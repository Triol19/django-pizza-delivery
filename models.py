from django.db import models
from enum import Enum

__all__ = [
    'Customer', 'DeliveryOrder', 'PizzaSizeTypes', 'PizzaTypes', 'Pizza',
    'PizzaLink'
]


class BaseEnum(Enum):
    def __init__(self, *args):
        self.verbose_name, self._value_ = args[:2]

    @classmethod
    def get_choices(cls):
        return tuple((i._value_, i.verbose_name) for i in cls)


class PizzaTypes(BaseEnum):
    MARGARITA = 'Margarita', 1
    PEPPERONI = 'Pepperoni', 2
    BBQ = 'BBQ', 3


class PizzaSizeTypes(BaseEnum):
    SMALL = '30cm', 1
    BIG = '50cm', 2


class Customer(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)


class Pizza(models.Model):
    type = models.PositiveSmallIntegerField(
        choices=PizzaTypes.get_choices(),
        default=PizzaTypes.PEPPERONI.value
    )
    size = models.PositiveSmallIntegerField(
        choices=PizzaSizeTypes.get_choices(),
        default=PizzaSizeTypes.SMALL.value
    )
    price = models.DecimalField(max_digits=4, decimal_places=2)


    class Meta:
        unique_together = [['type', 'size']]


class DeliveryOrder(models.Model):
    customer = models.ForeignKey(Customer)
    ordered = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(null=True)
    made = models.DateTimeField(null=True)
    delivered = models.DateTimeField(null=True)
    pizzas = models.ManyToManyField(
        Pizza,
        through='PizzaLink',
        related_name='orders'
    )
    total = models.DecimalField(
        decimal_places=2,
        max_digits=12
    )


class PizzaLink(models.Model):
    delivery_order = models.ForeignKey(
        DeliveryOrder,
        null=False,
        related_name='pizza_links'
    )
    pizza = models.ForeignKey(
        Pizza,
        null=False,
        related_name='pizza_links'
    )
    amount = models.PositiveIntegerField(default=1)
