from rest_framework import viewsets, generics, mixins
from rest_framework.generics import GenericAPIView
from rest_framework.viewsets import GenericViewSet

from railway.models import Station, Journey
from railway.serializers import StationSerializer, JourneySerializer, \
    JourneyListSerializer, JourneyRetrieveSerializer


# Create your views here.
class StationViewSet(viewsets.ModelViewSet):
    queryset = Station.objects.all()
    serializer_class = StationSerializer


class JourneyViewSet(viewsets.ModelViewSet):
    queryset = Journey.objects.all()
    serializer_class = JourneySerializer

    def get_queryset(self):
        queryset = self.queryset
        if self.action in ("list", "retrieve"):
            queryset = queryset.select_related(
                "route",
                "route__source",
                "route__destination",
                "train",
                "train__train_type"
            )
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return JourneyListSerializer
        elif self.action == "retrieve":
            return JourneyRetrieveSerializer
        return JourneySerializer
