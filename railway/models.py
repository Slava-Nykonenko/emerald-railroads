import pathlib
from uuid import uuid4

from django.db import models
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError

from railroads import settings


# Create your models here.
class Station(models.Model):
    name = models.CharField(max_length=100, unique=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    def __str__(self):
        return self.name


class TrainType(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Crew(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    position = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.position})"


def train_image_path(instance: "Train", filename: str) -> pathlib.Path:
    filename = (
        f"{slugify(instance.name)}-{uuid4()}"
        + pathlib.Path(filename).suffix
    )
    return pathlib.Path("upload-image/trains/") / pathlib.Path(filename)


class Train(models.Model):
    name = models.CharField(max_length=100)
    cargo_num = models.IntegerField()
    places_in_cargo = models.IntegerField()
    train_type = models.ForeignKey(
        TrainType,
        on_delete=models.PROTECT,
        related_name="trains"
    )
    image = models.ImageField(
        null=True,
        blank=True,
        upload_to=train_image_path
    )

    def __str__(self):
        return f"{self.name} ({self.train_type.name})"


class Route(models.Model):
    source = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="outgoing_routes"
    )
    destination = models.ForeignKey(
        Station,
        on_delete=models.CASCADE,
        related_name="incoming_routes"
    )
    distance = models.IntegerField()

    class Meta:
        indexes = [
            models.Index(fields=["source", "destination"])
        ]

    def __str__(self):
        return (f"{self.source.name} -> {self.destination.name} "
                f"({self.distance} km)")


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    class Meta:
        ordering = ["-created_at"]


class Journey(models.Model):
    route = models.ForeignKey(
        Route,
        on_delete=models.CASCADE,
        related_name="journeys"
    )
    train = models.ForeignKey(
        Train,
        on_delete=models.CASCADE,
        related_name="journeys"
    )
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    crew = models.ManyToManyField(Crew, blank=True)

    class Meta:
        ordering = ("departure_time",)
        indexes = [models.Index(fields=["departure_time"])]

    def __str__(self):
        return f"{self.route.source.name} -> {self.route.destination.name}"


class Ticket(models.Model):
    cargo = models.IntegerField()
    seat = models.IntegerField()
    journey = models.ForeignKey(
        Journey,
        on_delete=models.CASCADE,
        related_name="tickets"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    class Meta:
        unique_together = ("cargo", "seat", "journey")

    def __str__(self):
        return f"{self.journey.train.name} ({self.seat})"

    @staticmethod
    def validate_seat(
            seat: int,
            cargo: int,
            places_in_cargo: int,
            cargo_num: int,
            error_to_raise
    ):
        if not (1 <= seat <= places_in_cargo):
            raise error_to_raise(
                {
                    "seat":
                        f"seat must be in the range [1, {places_in_cargo}]",
                }
            )
        elif not (1 <= cargo <= cargo_num):
            raise error_to_raise(
                {
                    "cargo": f"cargo must be in the range [1, {cargo_num}]",
                }
            )

    def clean(self):
        Ticket.validate_seat(
            self.seat,
            self.cargo,
            self.journey.train.places_in_cargo,
            self.journey.train.cargo_num,
            ValidationError
        )

    def save(
        self,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        self.clean()
        return super(Ticket, self).save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
