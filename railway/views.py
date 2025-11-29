from datetime import datetime
from typing import Type

from django.db.models import F, Count, QuerySet
from django.http import (
    HttpResponse,
    HttpRequest
)
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter
)
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated,
    IsAdminUser
)
from rest_framework.response import Response

from railway.models import (
    Station,
    Journey,
    Route,
    Order,
    Train,
    Crew,
    TrainType
)
from railway.pagination import (
    OrdersAndJourneysPagination,
    ListsPagination
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
    TrainImageSerializer,
    RouteRetrieveSerializer,
    CrewSerializer,
    TrainTypeSerializer,
    TrainTypeRetrieveSerializer,
)


# Create your views here.
class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer
    pagination_class = ListsPagination

    def get_serializer_class(self) -> Type[
        StationListSerializer | StationRetrieveSerializer | StationSerializer
    ]:
        if self.action == "list":
            return StationListSerializer
        elif self.action == "retrieve":
            return StationRetrieveSerializer
        return StationSerializer


class JourneyViewSet(viewsets.ModelViewSet):
    queryset = Journey.objects.all()
    serializer_class = JourneySerializer
    ordering_fields = ("departure_time",)
    pagination_class = OrdersAndJourneysPagination

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset.select_related(
            "train", "route", "route__destination", "route__source"
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
            queryset = queryset.filter(route__source__name__icontains=source)
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

    def get_serializer_class(self) -> Type[
        JourneyListSerializer | JourneyRetrieveSerializer | JourneySerializer
    ]:
        if self.action == "list":
            return JourneyListSerializer
        elif self.action == "retrieve":
            return JourneyRetrieveSerializer
        return JourneySerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "source",
                type=OpenApiTypes.STR,
                description="Filtering journeys by source "
                            "(ex. '?source=Dublin')",
                required=False,
            ),
            OpenApiParameter(
                "destination",
                type=OpenApiTypes.STR,
                description="Filtering journeys by destination "
                "(ex. '?destination=Kilkenny')",
                required=False,
            ),
            OpenApiParameter(
                "date",
                type=OpenApiTypes.DATE,
                description="Filtering journeys by date "
                            "(ex. '?date=2025-11-28')",
                required=False,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    pagination_class = ListsPagination

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset
        if self.action in ("list", "retrieve"):
            queryset = queryset.select_related("source", "destination")
        return queryset

    def get_serializer_class(self) -> Type[
        RouteListSerializer | RouteSerializer | RouteRetrieveSerializer
    ]:
        if self.action == "list":
            return RouteListSerializer
        elif self.action == "retrieve":
            return RouteRetrieveSerializer
        return RouteSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = OrdersAndJourneysPagination

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset.filter(user=self.request.user)
        if self.action in ("list", "retrieve"):
            queryset = queryset.prefetch_related(
                "tickets",
                "tickets__journey",
                "tickets__journey__route__source",
                "tickets__journey__route__destination",
            )
        return queryset

    def get_serializer_class(self) -> Type[
        OrderListSerializer | OrderSerializer
    ]:
        if self.action in ("list", "retrieve"):
            return OrderListSerializer
        return OrderSerializer

    def perform_create(
        self,
        serializer: Type[OrderSerializer | OrderListSerializer]
    ) -> None:
        serializer.save(user=self.request.user)


class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.all()
    serializer_class = TrainSerializer

    def get_serializer_class(
        self,
    ) -> Type[
        TrainListSerializer
        | TrainRetrieveSerializer
        | TrainSerializer
        | TrainImageSerializer
    ]:
        if self.action == "list":
            return TrainListSerializer
        elif self.action == "retrieve":
            return TrainRetrieveSerializer
        elif self.action == "upload_image":
            return TrainImageSerializer
        return TrainSerializer

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset
        if self.action in ("list", "retrieve"):
            queryset = queryset.select_related("train_type")
        return queryset

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
    )
    def upload_image(self, request: HttpRequest, pk: int) -> HttpResponse:
        train = Train.objects.get(pk=pk)
        serializer = self.get_serializer(train, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.all()
    serializer_class = CrewSerializer
    permission_classes = (IsAdminUser,)
    pagination_class = ListsPagination


class TrainTypeViewSet(viewsets.ModelViewSet):
    queryset = TrainType.objects.all()
    serializer_class = TrainTypeSerializer
    permission_classes = (IsAdminUser,)
    pagination_class = ListsPagination

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TrainTypeRetrieveSerializer
        return TrainTypeSerializer
