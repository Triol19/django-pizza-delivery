from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from operator import attrgetter


from models import PizzaSizeTypes, PizzaTypes, Customer, DeliveryOrder, Pizza,
    PizzaLink

__all__ = [
    'DeliveryOrderReadSerializer', 'DeliveryOrderSaveSerializer',
    'DeliveryOrderEditSerializer'
]


class PizzaReadSerializer(serializers.Serializer):
    name = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    amount = serializers.IntegerField()

    def to_representation(self, instance):
        data = super(PizzaReadSerializer, self).to_representation(instance)
        data['price'] = instance.pizza.price * instance.amount
        return data

    def get_name(self, obj):
        return PizzaTypes(obj.pizza.type).verbose_name

    def get_size(self, obj):
        return PizzaSizeTypes(obj.pizza.size).verbose_name


class DeliveryOrderReadSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    customer = serializers.CharField(source='customer.name')
    pizzas = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(
        decimal_places=2,
        max_digits=12,
        source='total'
    )

    def to_representation(self, instance):
        data = super(DeliveryOrderReadSerializer, self).to_representation(instance)
        data['estimated_total_price'] = sum(
            i['price'] for i in data['pizzas']
        )
        return data

    def get_pizzas(self, order):
        return PizzaReadSerializer(
            order.pizza_links.all(),
            many=True
        ).data


class PizzaSerializer(serializers.Serializer):
    number = serializers.IntegerField()
    type = serializers.IntegerField()
    size = serializers.IntegerField()

    def validate_type(self, value):
        try:
            PizzaTypes(int(value))
            return value
        except ValueError:
            raise serializers.ValidationError('Invalid pizza type')

    def validate_size(self, value):
        try:
            PizzaSizeTypes(int(value))
            return value
        except ValueError:
            raise serializers.ValidationError('Invalid pizza size')


class DeliveryOrderMixin:
    @staticmethod
    def get_pizza_type_size_key(type, size):
        return '{}__{}'.format(type, size)

    @classmethod
    def build_pizza_type_size_to_instance_mapping(
        cls, data, type_attr_name='type', size_attr_name='size',
        instance_attr_name=None, mapping_for_update=None
    ):
        if not mapping_for_update:
            mapping_for_update = {}
        mapping_for_update.update(
            {
                cls.get_pizza_type_size_key(
                    i.get(type_attr_name) if isinstance(i, dict) else attrgetter(
                        type_attr_name
                    )(i),
                    i.get(size_attr_name) if isinstance(i, dict) else attrgetter(
                        size_attr_name
                    )(i)
                ):
                i if not instance_attr_name else (
                    i.get(instance_attr_name) if isinstance(i, dict) else attrgetter(
                        instance_attr_name
                    )(i)
                )
                for i in data
            }
        )
        return mapping_for_update


class DeliveryOrderBaseSerializer(serializers.Serializer, DeliveryOrderMixin):
    pizzas = serializers.ListField(
        child=PizzaSerializer(),
        min_length=1
    )


class DeliveryOrderSaveSerializer(DeliveryOrderBaseSerializer):
    customer_id = serializers.IntegerField()

    def create(self, validated_data):
        customer, _ = Customer.objects.get_or_create(
            id=validated_data['customer_id']
        )

        pizza_type_size_to_instance = self.build_pizza_type_size_to_instance_mapping(
            data=Pizza.objects.filter(
                type__in=list(set(i['type'] for i in validated_data['pizzas']))
            ).intersection(
                Pizza.objects.filter(
                    size__in=list(set(i['size'] for i in validated_data['pizzas']))
                )
            )
        )

        with transaction.atomic():
            order = DeliveryOrder.objects.create(
                customer_id=customer.pk,
                total=sum(
                    pizza_data['number'] * pizza_type_size_to_instance[
                        self.get_pizza_type_size_key(
                            pizza_data['type'],
                            pizza_data['size']
                        )
                    ].price
                    for pizza_data in validated_data['pizzas']
                )
            )

            pizza_links = []
            for pizza_data in validated_data['pizzas']:
                pizza_links.append(
                    PizzaLink(
                        delivery_order_id=order.id,
                        pizza_id=pizza_type_size_to_instance[
                            self.get_pizza_type_size_key(
                                pizza_data['type'],
                                pizza_data['size']
                            )
                        ].pk,
                        amount=pizza_data['number']
                    )
                )
            PizzaLink.objects.bulk_create(pizza_links)
        return order


class DeliveryOrderEditSerializer(DeliveryOrderBaseSerializer):

    def update(self, instance, validated_data):

        pizza_type_size_to_instance = self.build_pizza_type_size_to_instance_mapping(
            data=instance.pizza_links.all(),
            type_attr_name='pizza.type',
            size_attr_name='pizza.size',
            instance_attr_name='pizza'
        )

        old_order_pizzas_type_size = pizza_type_size_to_instance.keys()
        new_order_pizzas_type_size = [
            self.get_pizza_type_size_key(i['type'], i['size'])
            for i in validated_data['pizzas']
        ]

        absent_type_size_keys = set(new_order_pizzas_type_size).difference(
            old_order_pizzas_type_size
        )

        if absent_type_size_keys:
            self.build_pizza_type_size_to_instance_mapping(
                data=Pizza.objects.filter(
                    type__in=list(set(i.split('__')[0] for i in absent_type_size_keys))
                ).intersection(
                    Pizza.objects.filter(
                        size__in=list(set(i.split('__')[1] for i in absent_type_size_keys))
                    )
                ),
                mapping_for_update=pizza_type_size_to_instance
            )

        with transaction.atomic():
            # edit/remove
            for link in instance.pizza_links.all():
                exist_link = next(
                    (
                        i for i in validated_data['pizzas']
                        if i['type'] == link.pizza.type and i['size'] == link.pizza.size
                    ),
                    None
                )
                if exist_link:
                    link.amount = exist_link['number']
                    link.save()
                else:
                    link.delete()
            # add
            new_pizza_links = []
            new_pizza_prices = []
            for type_size_key in absent_type_size_keys:
                new_type, new_size = type_size_key.split('__')
                new_pizza = pizza_type_size_to_instance[type_size_key]
                amount = next(
                    (
                        i for i in validated_data['pizzas']
                        if str(i['type']) == new_type and str(i['size']) == new_size
                    )
                )['number']

                new_pizza_links.append(
                    PizzaLink(
                        delivery_order_id=instance.id,
                        pizza_id=new_pizza.pk,
                        amount=amount
                    )
                )
                new_pizza_prices.append(new_pizza.price * amount)
            PizzaLink.objects.bulk_create(new_pizza_links)
            instance.total = sum(
                link.amount * link.pizza.price
                for link in instance.pizza_links.all()
            ) + sum(new_pizza_prices)
            instance.updated = timezone.now()
            instance.save()
        return instance
