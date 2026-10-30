"""Offline routing regressions. No real Telegram token or network is used."""
import asyncio
import importlib.util
import json
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

from telegram import Update
from telegram.ext import Application
from telegram.request import BaseRequest

BOT_PATH = Path(__file__).resolve().parents[1] / "zovteam_app_business_connected_notice_v8_fixed.py"
SPEC = importlib.util.spec_from_file_location("offer_bot_under_test", BOT_PATH)
bot_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bot_module
SPEC.loader.exec_module(bot_module)

BOT_USER = {"id": 999, "is_bot": True, "first_name": "Bot", "username": "offline_bot"}


def user(uid):
    return {"id": uid, "is_bot": False, "first_name": f"User{uid}", "username": f"user_{uid}"}


def message(uid=101, text=None, business_id=None, message_id=10, outgoing=False, **extra):
    data = {"message_id": message_id, "date": 1760000000,
            "chat": {"id": uid, "type": "private", "first_name": "User"},
            "from": BOT_USER if outgoing else user(uid)}
    if business_id:
        data["business_connection_id"] = business_id
    if text is not None:
        data["text"] = text
        if text.startswith("/"):
            data["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
    data.update(extra)
    return data


class OfflineRequest(BaseRequest):
    """Implement Telegram's transport entirely in memory."""
    def __init__(self):
        self.calls = []
        self.subscribed = True
        self.next_message_id = 100

    @property
    def read_timeout(self):
        return 5

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    async def do_request(self, url, method, request_data=None, **kwargs):
        endpoint = url.rsplit("/", 1)[1]
        params = request_data.parameters if request_data else {}
        self.calls.append((endpoint, params))
        if endpoint == "getMe":
            result = BOT_USER
        elif endpoint == "getChatMember":
            result = {"status": "member" if self.subscribed else "left", "user": user(params["user_id"])}
        elif endpoint == "getBusinessConnection":
            result = {"id": params["business_connection_id"], "user": user(101),
                      "user_chat_id": 101, "date": 1760000000, "is_enabled": True,
                      "rights": {"can_reply": True}}
        elif endpoint == "getChat":
            result = {"id": params["chat_id"], "type": "private", "first_name": "User", "username": "recipient",
                      "accent_color_id": 0, "max_reaction_count": 11}
        elif endpoint == "getCustomEmojiStickers":
            result = [{"file_id": "star", "file_unique_id": "star_unique", "type": "custom_emoji",
                       "width": 100, "height": 100, "is_animated": False, "is_video": False, "emoji": "⭐"}]
        elif endpoint in {"sendMessage", "sendPhoto", "editMessageText", "editMessageCaption"}:
            self.next_message_id += 1
            result = message(uid=params["chat_id"], outgoing=True,
                             message_id=params.get("message_id", self.next_message_id),
                             business_id=params.get("business_connection_id"), text=params.get("text"))
        elif endpoint in {"answerCallbackQuery", "deleteMessage"}:
            result = True
        else:
            raise AssertionError(f"Unexpected Telegram operation: {endpoint}")
        return 200, json.dumps({"ok": True, "result": result}).encode()


class RoutingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.enterContext(patch.object(socket.socket, "connect", side_effect=AssertionError("Network disabled")))
        self.enterContext(patch.object(socket, "create_connection", side_effect=AssertionError("Network disabled")))
        self.enterContext(patch.object(bot_module.Config, "OWNER_IDS", {101}))
        self.enterContext(patch.object(bot_module.Config, "LEADER_IDS", {101}))
        self.enterContext(patch.object(bot_module.Config, "BOT_TOKEN", "123:offline"))
        self.enterContext(patch.object(bot_module.Config, "USE_RANDOM_DELAYS", False))
        self.enterContext(patch.object(bot_module.Config, "MIN_MESSAGE_DELAY", 0))
        with patch.object(bot_module, "__file__", str(Path(self.temp.name) / "bot.py")):
            self.db = bot_module.Database()
        self.enterContext(patch.object(bot_module, "db", self.db))
        self.request = OfflineRequest()
        self.app = (Application.builder().token("123:offline").request(self.request)
                    .get_updates_request(OfflineRequest()).updater(None).build())
        self.handler = bot_module.MainHandler()
        self.handler.app = self.app
        self.handler._business_state_file = lambda: str(Path(self.temp.name) / "states.json")
        self.handler._register_handlers()
        self.errors = []

        async def capture_error(update, context):
            self.errors.append(context.error)

        self.app.add_error_handler(capture_error)
        await self.app.initialize()
        self.request.calls.clear()
        self.sequence = 0

    async def asyncTearDown(self):
        await self.app.shutdown()
        self.assertEqual(self.errors, [], repr(self.errors))

    async def dispatch(self, **payload):
        self.sequence += 1
        await self.app.process_update(Update.de_json({"update_id": self.sequence, **payload}, self.app.bot))

    async def callback(self, data, msg, actor=202):
        await self.dispatch(callback_query={"id": str(self.sequence + 1), "from": user(actor),
                                           "chat_instance": "test", "data": data, "message": msg})

    def writes(self):
        return [(name, params) for name, params in self.request.calls
                if name.startswith(("send", "forward", "copy", "edit", "delete", "answer"))]

    def create_offer(self, business_id="connection", message_id=77):
        now = bot_module.datetime.now()
        offer = self.db.create_offer(sender_id=101, sender_username="Sender", recipient_id=202,
                                     recipient_username="Recipient", gift_name="Gift", gift_id="1",
                                     gift_link="https://t.me/nft/Gift-1", price=10, created_at=now,
                                     expires_at=now + bot_module.timedelta(hours=1))
        offer.message_id = message_id
        offer.business_connection_id = business_id
        return offer

    async def test_business_messages_never_reach_control_or_media_handlers(self):
        self.app.user_data[202]["awaiting_holder_username"] = True
        content = [{"photo": [{"file_id": "photo", "file_unique_id": "p", "width": 10, "height": 10}]},
                   {"document": {"file_id": "image", "file_unique_id": "i", "mime_type": "image/png"}},
                   {"text": "⭐", "entities": [{"type": "custom_emoji", "offset": 0, "length": 1,
                                                 "custom_emoji_id": "1234"}]},
                   {"text": "@holder_name"}, {"text": "ordinary conversation"}]
        content += [{"text": text, "entities": [{"type": "bot_command", "offset": 0,
                                                 "length": len(text.split()[0])}]}
                    for text in ("/start", "/send 303 https://t.me/nft/Gift-1 10", "/test https://t.me/nft/Gift-1 10")]
        for kind in ("business_message", "edited_business_message"):
            for extra in content:
                with self.subTest(kind=kind, content=extra):
                    self.request.calls.clear()
                    await self.dispatch(**{kind: message(202, business_id="connection", **extra)})
                    self.assertEqual(self.writes(), [])
                    self.assertNotIn("getChatMember", [name for name, _ in self.request.calls])
        self.assertTrue(self.app.user_data[202]["awaiting_holder_username"])
        self.assertIsNone(self.db.get_user(202).nft_recipient_username)

    async def test_direct_screenshots_are_not_forwarded_or_acknowledged(self):
        self.request.subscribed = False
        for extra in ({"photo": [{"file_id": "photo", "file_unique_id": "p", "width": 10, "height": 10}]},
                      {"document": {"file_id": "image", "file_unique_id": "i", "mime_type": "image/png"}}):
            await self.dispatch(message=message(202, **extra))
        self.assertEqual(self.request.calls, [])

    async def test_start_and_subscription_prompts_remain_in_direct_chat(self):
        await self.dispatch(message=message(101, "/start"))
        self.assertEqual([name for name, _ in self.writes()], ["sendPhoto"])
        self.assertEqual(self.writes()[0][1]["chat_id"], 101)
        self.request.calls.clear()
        self.request.subscribed = False
        await self.dispatch(message=message(202, "/start"))
        self.assertEqual([name for name, _ in self.writes()], ["sendMessage"])
        self.assertEqual(self.writes()[0][1]["chat_id"], 202)

    async def test_direct_settings_roundtrip_still_works(self):
        await self.callback("settings_holder", message(101, "Settings", outgoing=True), actor=101)
        await self.dispatch(message=message(101, "@new_holder"))
        self.assertEqual(self.db.get_user(101).nft_recipient_username, "@new_holder")
        self.assertTrue(all(params.get("chat_id", 101) == 101 for _, params in self.writes()))

    async def test_business_and_unrelated_menu_callbacks_are_ignored(self):
        for data in ("settings_holder", "check_subscription", "home", "buy_access"):
            await self.callback(data, message(202, "unrelated", business_id="connection", outgoing=True))
            await self.callback(data, message(202, "unrelated", outgoing=False))
        self.assertEqual(self.request.calls, [])

    async def test_group_and_edited_commands_are_ignored(self):
        group = message(101, "/start")
        group["chat"] = {"id": -1001, "type": "supergroup", "title": "Group"}
        await self.dispatch(message=group)
        await self.dispatch(edited_message=message(101, "/start"))
        self.assertEqual(self.request.calls, [])

    async def test_explicit_send_creates_offer_and_only_edits_that_offer(self):
        self.db.set_business_connection(101, "connection")
        with patch.object(self.handler, "_offer_timer", new=AsyncMock()):
            await self.dispatch(message=message(101, "/send 202 https://t.me/nft/Gift-1 10"))
            await asyncio.sleep(0)
        outgoing = self.writes()
        self.assertEqual([name for name, _ in outgoing], ["sendMessage", "sendMessage"])
        self.assertEqual([params["chat_id"] for _, params in outgoing], [202, 101])
        offer = next(iter(self.db.offers.values()))
        self.assertEqual(offer.business_connection_id, "connection")
        original = message(202, "Offer", outgoing=True, business_id="connection", message_id=offer.message_id)
        self.request.calls.clear()
        await self.callback(f"accept_{offer.offer_id}", original)
        self.assertEqual(offer.status, "accepted")
        edits = [(name, params) for name, params in self.writes() if name.startswith("edit")]
        self.assertEqual(len(edits), 1)
        self.assertEqual((edits[0][1]["chat_id"], edits[0][1]["message_id"], edits[0][1]["business_connection_id"]),
                         (202, offer.message_id, "connection"))
        self.assertFalse(any(name.startswith("send") for name, _ in self.writes()))
        self.request.calls.clear()
        await self.callback(f"check_{offer.offer_id}", original)
        self.assertEqual([name for name, _ in self.writes()], ["answerCallbackQuery"])

    async def test_offer_buttons_reject_wrong_message_chat_actor_or_connection(self):
        offer = self.create_offer()
        variations = [(message(202, business_id="connection", message_id=78, outgoing=True), 202),
                      (message(303, business_id="connection", message_id=77, outgoing=True), 303),
                      (message(202, business_id="other", message_id=77, outgoing=True), 202),
                      (message(202, message_id=77, outgoing=True), 202),
                      (message(202, business_id="connection", message_id=77, outgoing=True), 303)]
        for action in ("accept", "decline", "transfer", "check"):
            for msg, actor in variations:
                await self.callback(f"{action}_{offer.offer_id}", msg, actor)
        await self.callback("accept_offer_missing", message(202, message_id=77, outgoing=True))
        self.assertEqual(self.writes(), [])
        self.assertEqual(offer.status, "pending")

    async def test_decline_and_expiry_only_edit_the_tracked_message(self):
        offer = self.create_offer()
        original = message(202, outgoing=True, business_id="connection", message_id=77)
        await self.callback(f"decline_{offer.offer_id}", original)
        self.assertEqual(offer.status, "declined")
        offer = self.create_offer(message_id=78)
        offer.expires_at = bot_module.datetime.now() - bot_module.timedelta(seconds=1)
        await self.handler.check_expired_offers(type("Context", (), {"bot": self.app.bot})())
        self.assertEqual(offer.status, "expired")
        for name, params in self.writes():
            self.assertFalse(name.startswith("send"))
            if name.startswith("edit"):
                self.assertEqual(params["chat_id"], 202)
                self.assertEqual(params["business_connection_id"], "connection")

    async def test_role_grants_reply_only_to_the_requesting_admin(self):
        for command in ("/giveleader 303", "/giverole 404"):
            self.request.calls.clear()
            await self.dispatch(message=message(101, command))
            self.assertEqual([params["chat_id"] for name, params in self.writes() if name == "sendMessage"], [101])
        self.assertTrue(self.db.is_admin(303))
        self.assertTrue(self.db.get_user(404).has_access)

    async def test_connection_events_are_silent(self):
        connection = {"id": "connection", "user": user(101), "user_chat_id": 101,
                      "date": 1760000000, "is_enabled": True, "rights": {"can_reply": True}}
        await self.dispatch(business_connection=connection)
        self.assertEqual(self.db.get_user(101).business_connection_id, "connection")
        connection["is_enabled"] = False
        await self.dispatch(business_connection=connection)
        self.assertIsNone(self.db.get_user(101).business_connection_id)
        self.assertEqual(self.request.calls, [])

    async def test_connection_watcher_never_sends_notifications(self):
        self.db.set_business_connection(101, "connection")
        session = Mock()
        session.get.return_value.json.return_value = {"ok": True, "result": {
            "id": "connection", "is_enabled": True, "date": 1760000000,
            "user": user(101), "user_chat_id": 101}}
        with patch("requests.Session", return_value=session), patch.object(
                bot_module.asyncio, "sleep", new=AsyncMock(side_effect=asyncio.CancelledError)):
            with self.assertRaises(asyncio.CancelledError):
                await self.handler._watch_saved_business_connections()
        session.post.assert_not_called()
        self.assertEqual(self.writes(), [])

    async def test_raw_connection_polling_never_sends_notifications(self):
        app = Mock()
        for name in ("initialize", "start", "stop", "shutdown"):
            setattr(app, name, AsyncMock())
        self.handler.app = app
        session = Mock()
        response = Mock()
        response.json.return_value = {"ok": True, "result": [{"update_id": 1, "business_connection": {
            "id": "connection", "user": user(101), "user_chat_id": 101,
            "date": 1760000000, "is_enabled": True}}]}
        session.get.side_effect = [response, asyncio.CancelledError()]
        with patch("requests.Session", return_value=session), patch.object(
                self.handler, "_watch_saved_business_connections", new=AsyncMock()):
            with self.assertRaises(asyncio.CancelledError):
                await self.handler._raw_botapi_polling(["business_connection"])
        session.post.assert_not_called()
        self.assertEqual(self.db.get_user(101).business_connection_id, "connection")


if __name__ == "__main__":
    unittest.main()
