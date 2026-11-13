"""GP-QA-3: saving settings / products with a large photo must not crash.

Django keeps uploads over FILE_UPLOAD_MAX_MEMORY_SIZE (2.5 MB) as an open temp file, which cannot be
deep-copied. QueryDict.copy() deep-copies, so any photo over 2.5 MB made the whole save return 500.
"""

import shutil
import tempfile
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import QueryDict
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from config.request_data import shallow_mutable_copy
from orders.test_lifecycle import OrderLifecycleAPITests

PNG_HEADER = b"\x89PNG\r\n\x1a\n"
BIG = PNG_HEADER + b"\x00" * (3 * 1024 * 1024)  # 3 MB, above the 2.5 MB in-memory limit
MEDIA = tempfile.mkdtemp()


class ShallowMutableCopyTests(SimpleTestCase):
    def test_querydict_copy_is_mutable_and_keeps_all_values(self):
        original = QueryDict("a=1&a=2&b=3")
        copy = shallow_mutable_copy(original)
        copy["c"] = "4"
        self.assertEqual(copy.getlist("a"), ["1", "2"])
        self.assertEqual(copy["b"], "3")
        self.assertNotIn("c", original)

    def test_does_not_deepcopy_values(self):
        class NoDeepCopy:
            def __deepcopy__(self, memo):
                raise AssertionError("uploaded files must not be deep-copied")

        marker = NoDeepCopy()
        original = QueryDict(mutable=True)
        original.setlist("logo", [marker])
        self.assertIs(shallow_mutable_copy(original)["logo"], marker)

    def test_plain_dict_is_copied(self):
        source = {"a": 1}
        copy = shallow_mutable_copy(source)
        copy["b"] = 2
        self.assertEqual(source, {"a": 1})


@override_settings(MEDIA_ROOT=MEDIA)
class LargeUploadTests(TestCase):
    setUp = OrderLifecycleAPITests.setUp

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def _client(self):
        client = APIClient()
        client.force_authenticate(user=self.merchant_user)
        return client

    def test_shop_settings_save_with_a_3mb_logo(self):
        response = self._client().patch(
            "/api/v1/shops/me/",
            {
                "name": "Saved With Big Photo",
                "pending_order_timeout_minutes": "20",
                "logo": SimpleUploadedFile("big.png", BIG, content_type="image/png"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.name, "Saved With Big Photo")
        self.assertEqual(self.shop.pending_order_timeout_minutes, 20)
        self.assertTrue(self.shop.logo)

    def test_shop_settings_save_can_clear_optional_fields_together_with_a_photo(self):
        self.shop.description = "old description"
        self.shop.google_maps_url = "https://maps.google.com/?q=old"
        self.shop.save()

        response = self._client().patch(
            "/api/v1/shops/me/",
            {
                "name": self.shop.name,
                "description": "",
                "google_maps_url": "",
                "logo": SimpleUploadedFile("small.png", PNG_HEADER + b"\x00" * 100, content_type="image/png"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.description, "")
        self.assertEqual(self.shop.google_maps_url, "")

    def test_shop_product_create_with_a_3mb_image(self):
        response = self._client().post(
            "/api/v1/shops/me/products/",
            {
                "name": "Big Image Product",
                "price": "12.50",
                "image": SimpleUploadedFile("big.png", BIG, content_type="image/png"),
            },
            format="multipart",
        )

        self.assertIn(response.status_code, (200, 201), getattr(response, "data", None))
