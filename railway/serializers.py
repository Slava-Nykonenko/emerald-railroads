from django.db import transaction
from rest_framework import serializers

from railway.models import (
    Station,
    Journey,
    Route,
    Crew,
    Train,
    Order,
    Ticket
)


class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ("id", "name", "latitude", "longitude")


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class RouteListSerializer(RouteSerializer):
    source = serializers.SlugRelatedField(
        slug_field="name",
        many=False,
        read_only=True,
    )
    destination = serializers.PrimaryKeyRelatedField(
        many=False,
        read_only=True,
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
        fields = ("id", "name", "train_type")


class TrainListSerializer(TrainSerializer):
    train_type = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="name"
    )


class JourneySerializer(serializers.ModelSerializer):
    route = serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=Route.objects.select_related("source", "destination"),
        read_only=False,
    )

    class Meta:
        model = Journey
        fields = (
            "id", "route", "train", "departure_time", "arrival_time", "crew"
        )


class JourneyListSerializer(serializers.ModelSerializer):
    route = serializers.StringRelatedField(many=False, read_only=False)
    train = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="name"
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
            "available_tickets"
        )


class JourneyRetrieveSerializer(JourneyListSerializer):
    crew = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Journey
        fields = JourneyListSerializer.Meta.fields + ("crew",)


class TicketSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        data = super(TicketSerializer, self).validate(attrs)
        Ticket.validate_seat(
            attrs["seat"],
            attrs["cargo"],
            attrs["journey"].train.places_in_cargo,
            attrs["journey"].train.cargo_num,
            serializers.ValidationError
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
