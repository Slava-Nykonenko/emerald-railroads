import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from railway.models import (
    TrainType,
    Train
)

TRAIN_URL = reverse("railway:train-list")

def image_upload_url(train_id):
    """Return URL for recipe image upload"""
    return reverse("railway:train-upload-image", args=[train_id])

def detail_url(train_id):
    return reverse("railway:train-detail", args=[train_id])


class TrainAnonImageUploadTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.train_type = TrainType.objects.create(name="Sample TrainType")
        self.train = Train.objects.create(
            name="Sample train",
            cargo_num=10,
            places_in_cargo=20,
            train_type=self.train_type
        )

    def tearDown(self):
        self.train.image.delete()

    def test_upload_image_to_train(self):
        url = image_upload_url(self.train.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {"image": ntf},
                format="multipart"
            )
        self.train.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class TrainAuthenticatedImageUploadTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@example.ie",
            password="user-password"
        )
        self.client.force_authenticate(user=self.user)
        self.train_type = TrainType.objects.create(name="Sample TrainType")
        self.train = Train.objects.create(
            name="Sample train",
            cargo_num=10,
            places_in_cargo=20,
            train_type=self.train_type
        )

    def tearDown(self):
        self.train.image.delete()

    def test_upload_image_to_train(self):
        url = image_upload_url(self.train.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {"image": ntf},
                format="multipart"
            )
        self.train.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class TrainImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.train_type = TrainType.objects.create(name="Sample TrainType")
        self.train = Train.objects.create(
            name="Sample train",
            cargo_num=10,
            places_in_cargo=20,
            train_type=self.train_type
        )

    def tearDown(self):
        self.train.image.delete()

    def test_upload_image_to_train(self):
        url = image_upload_url(self.train.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {"image": ntf},
                format="multipart"
            )
        self.train.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.train.image.path))

    def test_upload_image_bad_request(self):
        url = image_upload_url(self.train.id)
        res = self.client.post(
            url,
            {"image": "not image"},
            format="multipart"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_train_list(self):
        url = TRAIN_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "name": "Test",
                    "cargo_num": 10,
                    "places_in_cargo": 15,
                    "train_type": self.train_type.id,
                    "image": ntf,
                },
                format="multipart",
            )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        train = Train.objects.get(pk=res.data["id"])
        self.assertFalse(train.image)

    def test_image_url_is_shown_on_train_detail(self):
        url = image_upload_url(self.train.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.train.id))
        self.assertIn("image", res.data)
