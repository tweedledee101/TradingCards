import os
import unittest
from unittest import mock

from acquisition.facebook_marketplace import novaact_intake


class TestNovaActIntake(unittest.TestCase):
    def test_load_config_requires_api_key(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                novaact_intake.load_config()

    def test_parse_args_defaults(self) -> None:
        args = novaact_intake.parse_args([])
        self.assertEqual(args.query, "trading cards")
        self.assertFalse(args.dry_run)

    def test_dry_run_client_methods_do_not_raise(self) -> None:
        config = novaact_intake.NovaActConfig(api_key="test-key")
        client = novaact_intake.NovaActClient(config, dry_run=True)
        client.start_session()
        client.login_facebook()
        client.search_marketplace("football cards")

    def test_ensure_novaact_available_missing(self) -> None:
        with mock.patch(
            "importlib.util.find_spec",
            return_value=None,
        ):
            with self.assertRaises(RuntimeError):
                novaact_intake.ensure_novaact_available()

    def test_main_dry_run(self) -> None:
        with mock.patch.dict(os.environ, {"NOVAACT_API_KEY": "test-key"}):
            novaact_intake.main(["--dry-run", "--query", "basketball cards"])


if __name__ == "__main__":
    unittest.main()
