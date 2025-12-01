from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db.models import Count, F
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import (
    APIClient,
    APITestCase
)

from railway.models import (
    Station,
    Crew,
    Train,
    TrainType,
    Route,
    Journey
)
from railway.serializers import JourneyListSerializer


def sample_station(name="Station", **params) -> Station:
    defaults = {
        "name": f"{name}_{uuid4()}",
        "latitude": "0.00000",
        "longitude": "0.00000",
    }
    defaults.update(params)
    return Station.objects.create(**defaults)

def sample_train(name="Train", **params) -> Train:
    defaults = {
        "name": f"{name}_{uuid4()}",
        "cargo_num": 10,
        "places_in_cargo": 10,
        "train_type": TrainType.objects.create(name="TestType"),
    }
    defaults.update(params)
    return Train.objects.create(**defaults)

def sample_route(**params) -> Route:
    defaults = {
        "source": sample_station(name="Source"),
        "destination": sample_station(name="Destination"),
        "distance": 10,
    }
    defaults.update(params)
    return Route.objects.create(**defaults)

def sample_journey(route=None, train=None, **params):
    if not route:
        route = sample_route()
    if not train:
        train = sample_train()
    defaults = {
        "route": route,
        "train": train,
        "departure_time": timezone.now(),
        "arrival_time": timezone.now() + timedelta(hours=1),
    }
    defaults.update(params)
    return Journey.objects.create(**defaults)

def detail_url(instance_type: str, instance_id: int) -> str:
    return reverse(
        f"railway:{instance_type}-detail",
        args=(instance_id,)
    )


class UnauthorizedRailwayTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.station = sample_station()
        self.route = sample_route()
        self.train = sample_train()
        self.crew = Crew.objects.create(
            first_name="Test",
            last_name="Test",
            position="Tester"
        )
        self.traintype = TrainType.objects.create(name="TestType")

    def test_lists_unauthorized(self):
        for endpoint in ["station", "train", "route", "journey"]:
            res = self.client.get(reverse(f"railway:{endpoint}-list"))
            self.assertEqual(res.status_code, status.HTTP_200_OK)
        for endpoint in ["crew", "traintype", "order"]:
            res = self.client.get(reverse(f"railway:{endpoint}-list"))
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_retrieve_denied(self):
        for key, value in {
            "station": self.station,
            "route": self.route,
            "train": self.train,
            "crew": self.crew,
            "traintype": self.traintype,
        }.items():
            url = detail_url(key, value.id)
            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        journey = sample_journey()
        url = detail_url("journey", journey.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthorizedRailwayTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test.user@example.ie",
            password="password.test.user",
        )
        self.client.force_authenticate(user=self.user)
        self.station = sample_station()
        self.route = sample_route()
        self.train = sample_train()
        self.crew = Crew.objects.create(
            first_name="Test",
            last_name="Test",
            position="Tester"
        )
        self.traintype = TrainType.objects.create(name="TestType")

    def test_lists_authorized(self):
        for endpoint in ["crew", "traintype"]:
            res = self.client.get(reverse(f"railway:{endpoint}-list"))
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        res = self.client.get(reverse(f"railway:order-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_authorized_station_create_forbidden(self):
        payload = {
            "name": "Test",
            "latitude": "1.00000",
            "longitude": "1.00000",
        }
        res = self.client.post(reverse("railway:station-list"), payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized_route_create_forbidden(self):
        payload = {
            "source": self.station.id,
            "destination": sample_station(name="Destination").id,
            "distance": 10,
        }
        res = self.client.post(
            reverse("railway:route-list"),
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized_crew_create_forbidden(self):
        payload = {
            "first_name": "Test",
            "last_name": "Test",
            "position": "Tester"
        }
        res = self.client.post(reverse("railway:crew-list"), payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized_traintype_create_forbidden(self):
        payload = {
            "name": "Test",
        }
        res = self.client.post(reverse("railway:traintype-list"), payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized_train_create_forbidden(self):
        payload = {
            "name": "Test",
            "train_type": self.traintype.id,
            "cargo_num": 10,
            "places_in_cargo": 10
        }
        res = self.client.post(
            reverse("railway:train-list"),
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized_journey_create_forbidden(self):
        payload = {
            "route": self.route.id,
            "train": self.train.id,
            "departure_time": timezone.now(),
            "arrival_time": timezone.now() + timedelta(hours=1),
        }
        res = self.client.post(
            reverse("railway:journey-list"),
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_authorized_order_create_success(self):
        payload = {
            "tickets": [
                {
                    "cargo": 7,
                    "seat": 5,
                    "journey": sample_journey().id
                }
            ]
        }
        res = self.client.post(
            reverse("railway:order-list"),
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_journey_list(self):
        in_an_hour = timezone.now() + timedelta(hours=1)
        journey_1 = sample_journey(
            departure_time=in_an_hour,
            arrival_time=in_an_hour + timedelta(hours=2),
        )
        tomorrow = timezone.now() + timedelta(days=1)
        journey_2 = sample_journey(
            route=self.route,
            train=self.train,
            departure_time=tomorrow,
            arrival_time=tomorrow + timedelta(hours=1),
        )
        train = sample_train(name="Test")
        route = sample_route()
        next_week = timezone.now() + timedelta(days=7)
        journey_3 = sample_journey(
            train=train,
            route=route,
            departure_time=next_week,
            arrival_time=next_week + timedelta(hours=1),
        )
        yesterday = timezone.now() - timedelta(days=1)
        journey_expired = sample_journey(
            train=sample_train(),
            route=sample_route(),
            departure_time=yesterday,
            arrival_time=yesterday + timedelta(hours=1),
        )
        journeys = Journey.objects.all().annotate(
            available_tickets=(
                F("train__cargo_num") * F("train__places_in_cargo")
                - Count("tickets")
            )
        )

        serializer = JourneyListSerializer(journeys, many=True)
        res = self.client.get(reverse("railway:journey-list"))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in res.data["results"]]
        self.assertIn(journey_1.id, ids)
        self.assertIn(journey_2.id, ids)
        self.assertIn(journey_3.id, ids)
        self.assertNotIn(journey_expired, ids)
        self.assertIn(serializer.data[0], res.data["results"])

        res = self.client.get(
            reverse("railway:journey-list"),
            {
                "date": str(tomorrow.date())
            }
        )
        ids = [item["id"] for item in res.data["results"]]
        self.assertIn(journey_2.id, ids)
        self.assertIn(journey_3.id, ids)
        self.assertNotIn(journey_1, ids)

        res = self.client.get(
            reverse("railway:journey-list"),
            {
                "destination": route.destination.name
            }
        )
        ids = [item["id"] for item in res.data["results"]]
        self.assertIn(journey_3.id, ids)
        self.assertNotIn(journey_1.id, ids)

        res = self.client.get(
            reverse("railway:journey-list"),
            {
                "source": self.route.source.name
            }
        )
        ids = [item["id"] for item in res.data["results"]]
        self.assertIn(journey_2.id, ids)
        self.assertNotIn(journey_3.id, ids)

    def test_authorized_only_users_orders(self):
        user_1 = get_user_model().objects.create_user(
            email="test_1.user@example.ie",
            password="password.test_1.user",
        )
        client_1 = APIClient()
        client_1.force_authenticate(user=user_1)
        payload_1 = {
            "tickets": [
                {
                    "cargo": 3,
                    "seat": 2,
                    "journey": sample_journey().id
                }
            ]
        }
        payload_2 = {
            "tickets": [
                {
                    "cargo": 3,
                    "seat": 2,
                    "journey": sample_journey().id
                }
            ]
        }
        res_1 = client_1.post(
            reverse("railway:order-list"),
            payload_1,
            format="json"
        )
        res_2 = self.client.post(
            reverse("railway:order-list"),
            payload_2,
            format="json"
        )
        self.assertEqual(res_1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(payload_1["tickets"], res_1.data["tickets"])
        self.assertNotEqual(payload_2["tickets"], res_1.data["tickets"])


class AdminRailwayTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test.user@example.ie",
            password="password.test.user",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)
        self.station = sample_station()
        self.route = sample_route()
        self.train = sample_train()
        self.crew = Crew.objects.create(
            first_name="Test",
            last_name="Test",
            position="Tester"
        )
        self.traintype = TrainType.objects.create(name="TestType")

    def test_admin_station_create_success(self):
        payload = {
            "name": "Test",
            "latitude": "1.00000",
            "longitude": "1.00000",
        }
        res = self.client.post(reverse("railway:station-list"), payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_admin_route_create_success(self):
        payload = {
            "source": self.station.id,
            "destination": sample_station(name="Destination").id,
            "distance": 10,
        }
        res = self.client.post(
            reverse("railway:route-list"),
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_admin_crew_create_success(self):
        payload = {
            "first_name": "Test",
            "last_name": "Test",
            "position": "Tester"
        }
        res = self.client.post(reverse("railway:crew-list"), payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_admin_traintype_create_success(self):
        payload = {
            "name": "Test",
        }
        res = self.client.post(reverse("railway:traintype-list"), payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_admin_train_create_success(self):
        payload = {
            "name": "Test",
            "train_type": self.traintype.id,
            "cargo_num": 10,
            "places_in_cargo": 10
        }
        res = self.client.post(
            reverse("railway:train-list"),
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_admin_journey_create_success(self):
        payload = {
            "route": self.route.id,
            "train": self.train.id,
            "departure_time": timezone.now(),
            "arrival_time": timezone.now() + timedelta(hours=1),
        }
        res = self.client.post(
            reverse("railway:journey-list"),
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
