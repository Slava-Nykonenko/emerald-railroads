from datetime import datetime

from django.db import transaction
from django.db.models import Count, F
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from railway.models import (
    Station,
    Journey,
    Route,
    Crew,
    Train,
    Order,
    Ticket,
    TrainType
)


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ("id", "name", "latitude", "longitude")


class StationListSerializer(StationSerializer):
    class Meta:
        model = Station
        fields = ("id", "name")


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class RouteListSerializer(RouteSerializer):
    source = serializers.CharField(
        source="source.name",
        read_only=True,
    )
    destination = serializers.CharField(
        read_only=True,
        source="destination.name",
    )


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name", "position")


class CrewJourneySerializer(CrewSerializer):
    class Meta:
        model = Crew
        fields = ("first_name", "last_name", "position")


class TrainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Train
        fields = ("id", "name", "train_type", "cargo_num", "places_in_cargo")


class TrainListSerializer(TrainSerializer):
    train_type = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field="name"
    )


class TrainImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Train
        fields = ("id", "image")


class TrainRetrieveSerializer(TrainSerializer):
    class Meta:
        model = Train
        fields = TrainSerializer.Meta.fields + ("image",)


class TrainJourneySerializer(TrainSerializer):
    class Meta:
        model = Train
        fields = ("id", "name", "cargo_num", "places_in_cargo")


class JourneySerializer(serializers.ModelSerializer):
    route = serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=Route.objects.select_related("source", "destination"),
        read_only=False,
    )

    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "train",
            "departure_time",
            "arrival_time",
            "crew"
        )


class JourneyUpcomingSerializer(JourneySerializer):
    available_tickets = serializers.IntegerField()

    class Meta:
        model = Journey
        fields = ("id", "departure_time", "arrival_time", "available_tickets")

class JourneyListSerializer(serializers.ModelSerializer):
    route = serializers.StringRelatedField(many=False, read_only=False)
    train = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field="name"
    )
    available_tickets = serializers.IntegerField()

    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "train",
            "departure_time",
            "arrival_time",
            "available_tickets",
        )


class JourneyRetrieveSerializer(JourneyListSerializer):
    train = TrainJourneySerializer(many=False, read_only=True)
    crew = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Journey
        fields = JourneyListSerializer.Meta.fields + ("crew",)


class RouteRetrieveSerializer(RouteSerializer):
    upcoming_journeys = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Route
        fields = RouteListSerializer.Meta.fields + ("upcoming_journeys",)

    @staticmethod
    @extend_schema_field(JourneyUpcomingSerializer(many=True))
    def get_upcoming_journeys(obj):
        journeys = (
            Journey.objects.filter(
                departure_time__gte=datetime.now(),
                route_id=obj.id
            ).order_by("departure_time")
            .select_related("train")
            .annotate(
                available_tickets=(
                    F("train__cargo_num") * F("train__places_in_cargo")
                    - Count("tickets")
                )
            )
        )
        return JourneyUpcomingSerializer(journeys, many=True).data


class TicketSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super(TicketSerializer, self).validate(attrs)
        Ticket.validate_seat(
            attrs["seat"],
            attrs["cargo"],
            attrs["journey"].train.places_in_cargo,
            attrs["journey"].train.cargo_num,
            serializers.ValidationError,
        )
        return data

    class Meta:
        model = Ticket
        fields = ("cargo", "seat", "journey")


class TicketListSerializer(TicketSerializer):
    journey = serializers.StringRelatedField(
        many=False,
        read_only=True,
        source="journey.route",
    )


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False)

    class Meta:
        model = Order
        fields = ("id", "created_at", "tickets")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)


class JourneyOutStationSerializer(JourneySerializer):
    destination = serializers.CharField(
        read_only=True,
        source="route.destination.name"
    )
    available_tickets = serializers.IntegerField()

    class Meta:
        model = Journey
        fields = ("id", "destination", "departure_time", "available_tickets")


class JourneyInStationSerializer(JourneySerializer):
    source = serializers.CharField(read_only=True, source="route.source.name")
    available_tickets = serializers.IntegerField()

    class Meta:
        model = Journey
        fields = ("id", "source", "arrival_time", "available_tickets")


class StationRetrieveSerializer(StationListSerializer):
    outgoing_journeys = serializers.SerializerMethodField(read_only=True)
    incoming_journeys = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Station
        fields = StationSerializer.Meta.fields + (
            "outgoing_journeys",
            "incoming_journeys",
        )

    @staticmethod
    @extend_schema_field(JourneyOutStationSerializer(many=True))
    def get_outgoing_journeys(obj):
        journeys = (
            Journey.objects.filter(
                arrival_time__gte=datetime.now(), route__source__name=obj
            )
            .select_related("route", "route__destination")
            .order_by("departure_time")
            .annotate(
                available_tickets=(
                    F("train__cargo_num") * F("train__places_in_cargo")
                    - Count("tickets")
                )
            )
        )
        return JourneyOutStationSerializer(journeys, many=True).data

    @staticmethod
    @extend_schema_field(JourneyInStationSerializer(many=True))
    def get_incoming_journeys(obj):
        journeys = (
            Journey.objects.filter(
                departure_time__gte=datetime.now(),
                route__destination__name=obj
            )
            .select_related("route", "route__source")
            .order_by("arrival_time")
            .annotate(
                available_tickets=(
                    F("train__cargo_num") * F("train__places_in_cargo")
                    - Count("tickets")
                )
            )
        )
        return JourneyInStationSerializer(journeys, many=True).data


class TrainTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainType
        fields = ("id", "name")


class TrainTypeRetrieveSerializer(TrainTypeSerializer):
    trains = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )

    class Meta:
        model = TrainType
        fields = TrainTypeSerializer.Meta.fields + ("trains",)
