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
        "latitude": "0.000000",
        "longitude": "0.000000",
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
    route = route or sample_route()
    train = train or sample_train()
    defaults = {
        "route": route,
        "train": train,
        "departure_time": timezone.now() + timedelta(minutes=1),
        "arrival_time": timezone.now() + timedelta(hours=1),
    }
    defaults.update(params)
    return Journey.objects.create(**defaults)

def detail_url(instance_type: str, instance_id: int) -> str:
    return reverse(
        f"railway:{instance_type}-detail",
        args=(instance_id,)
    )


class BaseRailwayTest(APITestCase):
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


class UnauthorizedRailwayTests(BaseRailwayTest):
    def test_lists_unauthorized(self):
        for endpoint in ["station", "train", "route", "journey"]:
            res = self.client.get(reverse(f"railway:{endpoint}-list"))
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        for endpoint in ["crew", "traintype", "order"]:
            res = self.client.get(reverse(f"railway:{endpoint}-list"))
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_retrieve_denied(self):
        objects_to_check = {
            "station": self.station,
            "route": self.route,
            "train": self.train,
            "crew": self.crew,
            "traintype": self.traintype,
            "journey": sample_journey(),
        }
        for key, instance in objects_to_check.items():
            url = detail_url(key, instance.id)
            res = self.client.get(url)
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_station_create_denied(self):
        payload = {"name": "AnonTest", "latitude": 1, "longitude": 1}
        res = self.client.post(reverse("railway:station-list"), payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthorizedRailwayTests(BaseRailwayTest):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user(
            email="test.user@example.ie",
            password="password.test.user",
        )
        self.client.force_authenticate(user=self.user)

    def test_lists_authorized(self):
        for endpoint in ["crew", "traintype"]:
            res = self.client.get(reverse(f"railway:{endpoint}-list"))
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        res = self.client.get(reverse(f"railway:order-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_authorized_station_create_forbidden(self):
        scenarios = [
            (
                "station",
                {
                    "name": "TStation",
                    "latitude": 1.555555,
                    "longitude": 1.333333
                }
            ),
            (
                "route",
                {
                    "source": self.station.id,
                    "destination": sample_station().id,
                    "distance": 10
                }
            ),
            (
                "crew",
                {
                    "first_name": "FirstTest",
                    "last_name": "LastTest",
                    "position": "TestPosition"
                }
            ),
            ("traintype", {"name": "T"}),
            (
                "train",
                {
                    "name": "TrainTest",
                    "train_type": self.traintype.id,
                    "cargo_num": 8,
                    "places_in_cargo": 15
                }
            ),
            (
                "journey",
                {
                    "route": self.route.id,
                    "train": self.train.id,
                    "departure_time": timezone.now() + timedelta(minutes=1),
                    "arrival_time": timezone.now() + timedelta(hours=1),
                }
            )
        ]

        for endpoint, payload in scenarios:
            res = self.client.post(
                reverse(
                    f"railway:{endpoint}-list"),
                    payload,
                    format="json"
            )
            self.assertEqual(
                res.status_code,
                status.HTTP_403_FORBIDDEN,
                f"Failed on {endpoint}"
            )

    def test_authorized_order_create_success(self):
        journey = sample_journey()
        payload = {
            "tickets": [
                {
                    "cargo": 7,
                    "seat": 5,
                    "journey": journey.id
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
        journey_1 = sample_journey()
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

    def test_authorized_retrieve_station(self):
        url = detail_url("station", self.station.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.station.id)
        self.assertEqual(res.data["name"], self.station.name)
        self.assertEqual(res.data["latitude"], self.station.latitude)
        self.assertEqual(res.data["longitude"], self.station.longitude)

    def test_authorized_retrieve_journey(self):
        journey = sample_journey()
        url = detail_url("journey", journey.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(journey.id, res.data["id"])

    def test_authorized_retrieve_route(self):
        url = detail_url("route", self.route.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.route.id, res.data["id"])

    def test_authorized_retrieve_train(self):
        url = detail_url("train", self.train.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.train.id, res.data["id"])

    def test_authorized_retrieve_station_route_out_in_journeys(self):
        route_outgoing = sample_route(
            source=self.station,
        )
        route_incoming = sample_route(
            destination=self.station,
        )
        journey_outgoing = sample_journey(
            route=route_outgoing,
        )
        journey_incoming = sample_journey(
            route=route_incoming
        )

        # Check Station detail
        # (must contain "outgoing_journeys" and "incoming_journeys" fields)
        url_station = detail_url("station", self.station.id)
        res_station = self.client.get(url_station)
        self.assertIsInstance(res_station.data["outgoing_journeys"], list)
        self.assertIsInstance(res_station.data["incoming_journeys"], list)
        outgoing_ids = [journey["id"] for journey in
                        res_station.data["outgoing_journeys"]]
        self.assertIn(journey_outgoing.id, outgoing_ids)
        incoming_ids = [journey["id"] for journey in
                        res_station.data["incoming_journeys"]]
        self.assertIn(journey_incoming.id, incoming_ids)

        outgoing = next(
            journey for journey in res_station.data["outgoing_journeys"]
            if journey["id"] == journey_outgoing.id
        )
        self.assertEqual(
            outgoing["destination"],
            journey_outgoing.route.destination.name
        )
        incoming = next(
            journey for journey in res_station.data["incoming_journeys"]
            if journey["id"] == journey_incoming.id
        )
        self.assertEqual(
            incoming["source"],
            journey_incoming.route.source.name
        )

        # Check Route detail (must contain "incoming_journeys" field)
        url_route = detail_url("route", route_outgoing.id)
        res_route = self.client.get(url_route)
        self.assertIsInstance(res_station.data["outgoing_journeys"], list)
        self.assertIsInstance(res_station.data["incoming_journeys"], list)
        upcoming_ids = [journey["id"] for journey in
                        res_route.data["upcoming_journeys"]]
        self.assertIn(journey_outgoing.id, upcoming_ids)

    def test_authorized_update_delete_forbidden(self):
        test_dict = {
            "station": sample_station().id,
            "route": sample_route().id,
            "journey": sample_journey().id,
            "train": sample_train().id,
        }
        for key, instance_id in test_dict.items():
            url = detail_url(key, instance_id)
            res_put = self.client.put(url, {})
            res_patch = self.client.patch(url, {})
            res_del = self.client.delete(url)
            self.assertEqual(res_put.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(res_patch.status_code, status.HTTP_403_FORBIDDEN)
            self.assertEqual(res_del.status_code, status.HTTP_403_FORBIDDEN)


class AdminRailwayTests(BaseRailwayTest):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user(
            email="test.user@example.ie",
            password="password.test.user",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_admin_create_success(self):
        scenarious = [
            (
                "station",
                {"name": "Test", "latitude": 1.888888, "longitude": 1.777777}
            ),
            (
                "crew",
                {"first_name": "T", "last_name": "T", "position": "T"}
            ),
            ("traintype", {"name": "NewType"}),
        ]
        for endpoint, data in scenarious:
            res = self.client.post(reverse(f"railway:{endpoint}-list"), data)
            self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_admin_route_create_success(self):
        payload = {
            "source": self.station.id,
            "destination": sample_station().id,
            "distance": 10,
        }
        res = self.client.post(
            reverse("railway:route-list"),
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_admin_journey_create_success(self):
        payload = {
            "route": self.route.id,
            "train": self.train.id,
            "departure_time": timezone.now() + timedelta(minutes=1),
            "arrival_time": timezone.now() + timedelta(hours=1),
        }
        res = self.client.post(
            reverse("railway:journey-list"),
            payload,
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_admin_update_delete_success(self):
        scenarios = {
            "station":
                lambda: (
                    sample_station().id,
                    {
                        "name": "UpdateStation",
                        "latitude": 4.444444,
                        "longitude": 5.123456
                    },
                    {}
                ),
            "route":
                lambda: (
                    sample_route().id,
                    {"distance": 50}, {"distance": 500}
                ),
            "train":
                lambda: (
                    sample_train().id,
                    {"name": "UpdateTrain"},
                    {"name": "Patch Train"}
                ),
            "journey":
                lambda: (
                    sample_journey().id,
                    {"departure_time": timezone.now() + timedelta(seconds=1)},
                    {"departure_time": timezone.now() + timedelta(days=1)}
                ),
        }
        for key, data_factory in scenarios.items():
            instance_id, put_payload, patch_payload = data_factory()
            url = detail_url(key, instance_id)

            res_patch = self.client.patch(url, patch_payload, format="json")
            self.assertEqual(res_patch.status_code, status.HTTP_200_OK,
                             f"{key} PATCH error")

            res_del = self.client.delete(url)
            self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT,
                             f"{key} DELETE error")
