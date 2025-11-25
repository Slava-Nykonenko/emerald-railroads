from rest_framework import serializers

from railway.models import (
    Station,
    Journey,
    Route,
    Crew,
    Train
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
    destination = serializers.SlugRelatedField(
        slug_field="name",
        many=False,
        read_only=True,
    )

    class Meta:
        model = Route
        fields = ("source", "destination")


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name", "position")


class CrewJourneySerializer(CrewSerializer):
    class Meta:
        model = Crew
        fields = ("first_name", "last_name", "position")


class TrainSerializer(serializers.ModelSerializer):
    train_type = serializers.SlugRelatedField(
        slug_field="name",
        many=False,
        read_only=True,
    )

    class Meta:
        model = Train
        fields = ("name", "train_type")


class JourneySerializer(serializers.ModelSerializer):
    route = serializers.PrimaryKeyRelatedField(
        many=False,
        read_only=False,
        queryset=Route.objects.all().select_related(
            "destination", "source"
        )
    )
    train = serializers.SlugRelatedField(
        many=False,
        read_only=False,
        slug_field="name",
        queryset=Train.objects.all().select_related("train_type")
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
