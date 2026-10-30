"""Offline checks for hosting startup and persistent state."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from telegram.ext import Application
from test_bot_routing import BOT_PATH, bot_module


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.enterContext(patch.dict(os.environ, {"BOT_DATA_DIR": self.temp.name}))
        self.enterContext(patch.object(bot_module.Config, "OWNER_IDS", {101}))
        self.enterContext(patch.object(bot_module.Config, "ADMIN_IDS", set()))
        self.enterContext(patch.object(bot_module.Config, "LEADER_IDS", set()))

    def test_missing_configuration_stops_before_any_telegram_request(self):
        with patch.object(bot_module.Config, "BOT_TOKEN", ""), patch(
                "requests.get", side_effect=AssertionError("Network must not run")) as request:
            with self.assertRaises(SystemExit) as stopped:
                bot_module.main()
        self.assertIn("BOT_TOKEN", str(stopped.exception))
        request.assert_not_called()

    def test_check_config_entrypoint_never_starts_the_bot(self):
        spec = importlib.util.spec_from_file_location("hosting_entrypoint", BOT_PATH.parent / "main.py")
        entrypoint = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"zovteam_app_business_connected_notice_v8_fixed": bot_module}):
            spec.loader.exec_module(entrypoint)
        with patch.object(bot_module.Config, "BOT_TOKEN", "123:offline"), patch.object(
                bot_module.Config, "REQUIRED_CHANNEL", "@test_channel"), patch.object(
                bot_module.Config, "DEFAULT_RECIPIENT_USERNAME", "@test_holder"), patch.object(
                bot_module.MainHandler, "run", side_effect=AssertionError("Bot must not start")) as start, patch.object(
                sys, "argv", ["main.py", "--check-config"]):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                entrypoint.main()
            self.assertIn("Configuration is present", output.getvalue())
            with patch.object(bot_module.Config, "BOT_TOKEN", ""), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as stopped:
                    entrypoint.main()
            self.assertEqual(stopped.exception.code, 1)
            start.assert_not_called()

    def test_persistent_directory_restores_permissions_settings_and_connections(self):
        first = bot_module.Database()
        first.grant_access(202)
        first.get_user(202).display_name = "Saved user"
        first.save_preferences(202)
        first.add_admin(303)
        first.set_business_connection(101, "saved_connection")
        first.record_stat("offers_sent")
        second = bot_module.Database()
        self.assertTrue(second.get_user(202).has_access)
        self.assertEqual(second.get_user(202).display_name, "Saved user")
        self.assertTrue(second.is_admin(303))
        self.assertEqual(second.get_user(101).business_connection_id, "saved_connection")
        self.assertEqual(second.get_statistics()["offers_sent"], 1)
        paths = [second.access_file, second.admins_file, second.business_connections_file,
                 second.statistics_file, bot_module.MainHandler()._business_state_file()]
        self.assertTrue(all(Path(path).parent == Path(self.temp.name) for path in paths))

    def test_default_data_directory_preserves_existing_local_installations(self):
        with patch.dict(os.environ, {"BOT_DATA_DIR": ""}), patch.object(
                bot_module, "__file__", str(Path(self.temp.name) / "bot.py")):
            self.assertEqual(bot_module.data_file_path("access_users.json"),
                             str(Path(self.temp.name) / "access_users.json"))

    def test_only_one_worker_can_hold_the_persistent_lock(self):
        first = bot_module.acquire_single_instance_lock()
        try:
            with self.assertRaises(RuntimeError):
                bot_module.acquire_single_instance_lock()
        finally:
            first.close()
        second = bot_module.acquire_single_instance_lock()
        second.close()
        self.assertTrue((Path(self.temp.name) / "bot.lock").exists())

    def test_scheduler_dependency_is_available(self):
        app = Application.builder().token("123:offline").updater(None).build()
        self.assertIsNotNone(app.job_queue)

    def test_invalid_token_response_stops_with_a_clear_error(self):
        response = Mock()
        response.json.return_value = {"ok": False, "description": "Unauthorized"}
        with patch("requests.get", return_value=response) as request:
            with self.assertRaises(SystemExit) as stopped:
                bot_module.MainHandler().run()
        self.assertIn("BOT_TOKEN", str(stopped.exception))
        self.assertEqual(request.call_args.kwargs["timeout"], 30)


if __name__ == "__main__":
    unittest.main()
