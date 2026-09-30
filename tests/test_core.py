import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch, Mock

from services.store import LocalStore, empty_data, normalize, pet_values, complete_task, pending, import_guest
from services.cloud import Supabase, CloudError


def pet():
    return dict(id="pet-a", **pet_values(dict(name="Nube", kind="Gato", weight="4,2")))


def task():
    return dict(id="task-a", title="Gotas", detail="Según receta", time="2026-09-27 08:00", due_at="2026-09-27 08:00",
                pet="pet-a", kind="Medicamento", repeat="Diaria", icon="paw", done=False)


class StorageTests(unittest.TestCase):
    def test_empty_guest_and_roundtrip(self):
        with TemporaryDirectory() as tmp:
            store = LocalStore(Path(tmp) / "guest.json")
            self.assertEqual(store.data["pets"], [])
            data = empty_data()
            data["pets"].append(pet())
            store.save(data)
            self.assertEqual(LocalStore(store.path).data, data)
            data["pets"][0]["name"] = "Nube nueva"
            store.save(data)
            self.assertEqual(json.loads(store.path.with_suffix(".bak").read_text(encoding="utf-8"))["pets"][0]["name"], "Nube")

    def test_corrupt_file_never_overwritten(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "guest.json"
            path.write_text("{broken", encoding="utf-8")
            store = LocalStore(path)
            with self.assertRaises(ValueError):
                store.save(empty_data())
            self.assertEqual(path.read_text(encoding="utf-8"), "{broken")

    def test_failed_write_preserves_memory_and_disk(self):
        with TemporaryDirectory() as tmp:
            store = LocalStore(Path(tmp) / "guest.json")
            store.save(empty_data())
            changed = empty_data()
            changed["pets"].append(pet())
            with patch("services.store.shutil.copy2", side_effect=OSError("disk")):
                with self.assertRaises(OSError):
                    store.save(changed)
            self.assertEqual(store.data["pets"], [])
            self.assertEqual(LocalStore(store.path).data["pets"], [])

    def test_weight_validation(self):
        self.assertEqual(pet()["weight"], "4.2")
        for value in ("nan", "inf", "-1", "0", "abc"):
            with self.assertRaises(ValueError):
                pet_values(dict(name="Nube", kind="Gato", weight=value))

    def test_recurrence_skips_past_and_records_history(self):
        data = empty_data()
        item = task()
        complete_task(data, item, datetime(2026, 9, 30, 9))
        self.assertEqual(item["due_at"], "2026-10-01 08:00")
        self.assertFalse(item["done"])
        self.assertEqual(data["events"][0]["pet"], "pet-a")
        self.assertEqual(data["events"][0]["kind"], "Medicamento")

    def test_single_completion_and_pending(self):
        data = empty_data()
        item = task()
        item["repeat"] = "No"
        data["routines"].append(item)
        self.assertEqual(pending(data, datetime(2026, 9, 28), True), [item])
        complete_task(data, item)
        self.assertEqual(pending(data), [])
        complete_task(data, item)
        self.assertFalse(item["done"])
        self.assertEqual(len(data["events"]), 1)

    def test_import_does_not_duplicate_or_change_guest(self):
        guest = empty_data()
        guest["pets"].append(pet())
        original = deepcopy(guest)
        imported = import_guest(empty_data(), guest)
        self.assertEqual(import_guest(imported, guest), imported)
        self.assertEqual(guest, original)

    def test_legacy_migration_preserves_data(self):
        old = dict(pets=[pet()], routines=[dict(id="old", title="Paseo", detail="Parque", time="Sábado", icon="walk", done=False)],
                   events=[dict(title="Control", detail="Todo bien", pet="pet-a")])
        new = normalize(old)
        self.assertEqual(new["routines"][0]["time"], "Sábado")
        self.assertTrue(new["events"][0]["id"])
        self.assertEqual(new["pets"], old["pets"])
        self.assertEqual(normalize(old), new)

    def test_account_files_are_separate(self):
        with TemporaryDirectory() as tmp:
            guest, first, second = [LocalStore(Path(tmp) / name) for name in ("guest.json", "accounts/a.json", "accounts/b.json")]
            data = empty_data()
            data["pets"].append(pet())
            first.save(data)
            self.assertEqual(guest.data["pets"], [])
            self.assertEqual(second.data["pets"], [])


class CloudTests(unittest.TestCase):
    def client(self):
        client = Supabase(config_path="no-config.json")
        client.url, client.key = "https://test.supabase.co", "sb_publishable_test"
        return client

    @patch("services.cloud.requests.request")
    def test_confirmed_and_pending_signup(self, request):
        client = self.client()
        request.return_value = Mock(ok=True, content=b"{}", json=lambda: {"user": {"id": "abc"}})
        self.assertFalse(client.authenticate("test@example.com", "password", True))
        self.assertIsNone(client.session)
        request.return_value.json = lambda: dict(access_token="token", refresh_token="refresh", user={"id": "abc"})
        self.assertTrue(client.authenticate("test@example.com", "password"))
        self.assertEqual(client.user["id"], "abc")

    @patch("services.cloud.requests.request")
    def test_cloud_requires_auth_and_sends_user_jwt(self, request):
        client = self.client()
        with self.assertRaises(CloudError):
            client.upload(empty_data())
        request.assert_not_called()
        client.set_session(dict(access_token="jwt", refresh_token="r", user={"id": "abc"}))
        request.return_value = Mock(ok=True, content=b"{}", json=lambda: {"revision": 1})
        self.assertEqual(client.upload(empty_data()), {"revision": 1})
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer jwt")
        self.assertEqual(kwargs["json"]["expected_revision"], 0)
        self.assertFalse(kwargs["allow_redirects"])

    @patch("services.cloud.requests.request")
    def test_conflict_is_not_retried_as_overwrite(self, request):
        client = self.client()
        client.set_session(dict(access_token="jwt", refresh_token="r", user={"id": "abc"}))
        request.return_value = Mock(ok=False, status_code=400, text="revision_conflict")
        with self.assertRaisesRegex(CloudError, "otra versión"):
            client.upload(empty_data())
        self.assertEqual(request.call_count, 1)

    def test_no_secret_key_or_http_allowed(self):
        client = self.client()
        client.key = "sb_secret_private"
        self.assertFalse(client.configured)
        client.key, client.url = "sb_publishable_test", "http://test.supabase.co"
        self.assertFalse(client.configured)

    @patch("services.cloud.requests.request")
    def test_refresh_and_logout(self, request):
        client = self.client()
        client.set_session(dict(access_token="old", refresh_token="r", user={"id": "abc"}))
        client.session["expires_at"] = 0
        request.side_effect = [Mock(ok=True, content=b"{}", json=lambda: dict(access_token="new", refresh_token="r2", user={"id": "abc"})),
                               Mock(ok=True, content=b"[]", json=lambda: []), Mock(ok=True, content=b"")]
        self.assertIsNone(client.download())
        self.assertEqual(client.session["access_token"], "new")
        client.logout()
        self.assertIsNone(client.session)


if __name__ == "__main__":
    unittest.main()
