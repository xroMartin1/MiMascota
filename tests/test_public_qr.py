from datetime import datetime, timedelta, timezone
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from services.public_qr import PublicChapas, write_public_png
from services.cloud import CloudError


class PublicQrTests(unittest.TestCase):
    def test_opening_unissued_tag_does_not_start_trial(self):
        cloud = Mock()
        cloud.request.return_value = []
        self.assertIsNone(PublicChapas(cloud, "https://mascota.example").existing("pet-a"))
        self.assertEqual(cloud.request.call_count, 1)
        self.assertEqual(cloud.request.call_args.args[0], "GET")

    def test_existing_tag_uses_server_status_without_reissuing(self):
        cloud = Mock()
        cloud.request.side_effect = [[{"pet_id": "pet-a"}], dict(self.tag(), status="expired")]
        result = PublicChapas(cloud, "https://mascota.example").existing("pet-a")
        self.assertEqual(result['status'], 'expired')
        self.assertEqual(cloud.request.call_args.args[2], {"pet_id": "pet-a", "action": "sync"})

    def test_existing_response_must_match_requested_pet(self):
        cloud = Mock()
        for rows in ({}, [None], [{"pet_id": "pet-b"}]):
            cloud.request.return_value = rows
            with self.assertRaises(CloudError):
                PublicChapas(cloud, "https://mascota.example").existing("pet-a")

    def tag(self):
        now = datetime.now(timezone.utc)
        return dict(scan_code="00000000-0000-4000-8000-000000000000", created_at=now.isoformat(),
                    expires_at=(now+timedelta(days=14)).isoformat(), status="active")

    def test_uses_authenticated_api_without_dates_or_owner(self):
        cloud = Mock()
        cloud.request.return_value = self.tag()
        result = PublicChapas(cloud,"https://mascota.example").manage("pet-a")
        cloud.request.assert_called_once_with("POST","/functions/v1/manage-tag",{"pet_id":"pet-a","action":"issue"},authorized=True)
        self.assertEqual(result['url'],"https://mascota.example/q/00000000-0000-4000-8000-000000000000")

    def test_requires_domain_and_rejects_privileged_operations(self):
        cloud=Mock()
        for base in ("", "http://localhost:3000", "https://user:password@example.com", "https://example.com/?token=x"):
            with self.assertRaises(ValueError): PublicChapas(cloud,base)
        client=PublicChapas(cloud,"https://mascota.example")
        with self.assertRaises(ValueError): client.manage("pet-a","physical")
        cloud.request.assert_not_called()

    def test_rejects_invalid_server_result_and_inactive_qr(self):
        cloud=Mock()
        cloud.request.return_value=dict(self.tag(),scan_code="not-a-token")
        with self.assertRaises(CloudError): PublicChapas(cloud,"https://mascota.example").manage("pet-a")
        with self.assertRaises(ValueError): write_public_png({"status":"expired"},"unused.png")

    @patch("services.public_qr.segno.make")
    def test_qr_contains_only_stable_url(self, make):
        cloud=Mock()
        cloud.request.return_value=self.tag()
        tag=PublicChapas(cloud,"https://mascota.example").manage("pet-a")
        with TemporaryDirectory() as directory: write_public_png(tag,Path(directory)/"qr.png")
        make.assert_called_once_with(tag["url"],error="m")


if __name__ == "__main__": unittest.main()
