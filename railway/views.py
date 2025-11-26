from datetime import datetime

from django.db.models import F, Count
from rest_framework import viewsets, mixins
from rest_framework.viewsets import GenericViewSet

from railway.models import (
    Station,
    Journey, Route, Order
)
from railway.serializers import (
    StationSerializer,
    JourneySerializer,
    JourneyListSerializer,
    JourneyRetrieveSerializer, RouteSerializer, RouteListSerializer,
    OrderSerializer, OrderListSerializer
)


# Create your views here.
class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer


class JourneyViewSet(
    # mixins.ListModelMixin,
    # mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.CreateModelMixin,
    GenericViewSet
    # viewsets.ModelViewSet
):
    queryset = Journey.objects.all()
    serializer_class = JourneySerializer
    ordering_fields = ('departure_time',)

    def get_queryset(self):
        queryset = self.queryset.select_related(
            "train",
            "route",
            "route__destination",
            "route__source"
        ).prefetch_related("crew")
        if self.action in ("list", "retrieve"):
            queryset = queryset.annotate(
                available_tickets=(
                    F("train__cargo_num") * F("train__places_in_cargo")
                    - Count("tickets")
                )
            )
        if self.action == "list":
            queryset = queryset.filter(departure_time__gte=datetime.now())

        return queryset.order_by("departure_time")

    def get_serializer_class(self):
        if self.action == "list":
            return JourneyListSerializer
        elif self.action == "retrieve":
            return JourneyRetrieveSerializer
        return JourneySerializer


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer

    def get_queryset(self):
        queryset = self.queryset.select_related("source", "destination")
        return queryset

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return RouteListSerializer
        return RouteSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    def get_queryset(self):
        queryset = self.queryset.filter(user=self.request.user)
        if self.action in ("list", "retrieve"):
            queryset = queryset.prefetch_related(
                "tickets",
                "tickets__journey",
                "tickets__journey__route__source",
                "tickets__journey__route__destination"
            )
        return queryset

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return OrderListSerializer
        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
