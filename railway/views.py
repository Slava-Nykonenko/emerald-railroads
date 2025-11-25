from django.db.models import F, Count
from rest_framework import viewsets, mixins
from rest_framework.generics import GenericAPIView
from rest_framework.viewsets import GenericViewSet

from railway.models import (
    Station,
    Journey
)
from railway.serializers import (
    StationSerializer,
    JourneySerializer,
    JourneyListSerializer,
    JourneyRetrieveSerializer
)


# Create your views here.
class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer


class JourneyViewSet(viewsets.ModelViewSet):
    queryset = Journey.objects.all()
    serializer_class = JourneySerializer

    def get_queryset(self):
        queryset = self.queryset.select_related(
            "train__train_type",
            "route__destination",
            "route__source",
        ).prefetch_related("crew")
        if self.action in ("list", "retrieve"):
            queryset = queryset.annotate(
                available_tickets=(
                    F("train__cargo_num") * F("train__places_in_cargo")
                    - Count("tickets")
                )
            )
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return JourneyListSerializer
        elif self.action == "retrieve":
            return JourneyRetrieveSerializer
        return JourneySerializer
