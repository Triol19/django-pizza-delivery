from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^pizza-orders/(?P<order_id>\w+)', views.PizzaOrdersView.as_view()),
    url(r'^pizza-orders', views.PizzaOrdersView.as_view()),
    url(r'^customers/(?P<customer_id>\w+)/orders', views.CustomerOrdersView.as_view())
]
