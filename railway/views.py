from datetime import datetime

from django.db.models import F, Count
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from railway.models import (
    Station,
    Journey,
    Route,
    Order,
    Train
)
from railway.serializers import (
    StationSerializer,
    JourneySerializer,
    JourneyListSerializer,
    JourneyRetrieveSerializer,
    RouteSerializer,
    RouteListSerializer,
    OrderSerializer,
    OrderListSerializer,
    TrainSerializer,
    TrainListSerializer,
    StationListSerializer,
    StationRetrieveSerializer,
    TrainRetrieveSerializer,
    TrainImageSerializer
)


# Create your views here.
class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return StationListSerializer
        elif self.action == "retrieve":
            return StationRetrieveSerializer
        return StationSerializer


class JourneyViewSet(viewsets.ModelViewSet):
    queryset = Journey.objects.all()
    serializer_class = JourneySerializer
    ordering_fields = ("departure_time",)

    def get_queryset(self):
        queryset = self.queryset.select_related(
            "train",
            "route",
            "route__destination",
            "route__source"
        ).prefetch_related("crew")
        source = self.request.query_params.get("source", None)
        destination = self.request.query_params.get("destination", None)
        date = self.request.query_params.get("date", None)
        if self.action in ("list", "retrieve"):
            queryset = queryset.annotate(
                available_tickets=(
                    F("train__cargo_num") * F("train__places_in_cargo")
                    - Count("tickets")
                )
            )
        if self.action == "list":
            queryset = queryset.filter(departure_time__gte=datetime.now())
        if source:
            queryset = queryset.filter(
                route__source__name__icontains=source
            )
        if destination:
            queryset = queryset.filter(
                route__destination__name__icontains=destination
            )
        if date:
            aware_date = timezone.make_aware(
                datetime.combine(parse_date(date), datetime.min.time())
            )
            queryset = queryset.filter(departure_time__gte=aware_date)

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
        queryset = self.queryset
        if self.action in ("list", "retrieve"):
            queryset = queryset.select_related("source", "destination")
        return queryset

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return RouteListSerializer
        return RouteSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)

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


class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.all()
    serializer_class = TrainSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return TrainListSerializer
        elif self.action == "retrieve":
            return TrainRetrieveSerializer
        elif self.action == "upload_image":
            return TrainImageSerializer
        return TrainSerializer

    def get_queryset(self):
        queryset = self.queryset
        if self.action in ("list", "retrieve"):
            queryset = queryset.select_related("train_type")
        return queryset

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
    )
    def upload_image(self, request, pk):
        train = Train.objects.get(pk=pk)
        serializer = self.get_serializer(train, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
