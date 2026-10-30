# Telegram Offer Bot

A Python Telegram bot with offer delivery, direct-chat settings, subscription checks, and administration controls.

Messages in connected Telegram Business private chats do not trigger command handlers, subscription prompts, screenshot forwarding, or debug replies. Direct messages to the bot retain their controls. The explicit `/send` command delivers an offer; its buttons and expiration updates operate on that offer's stored message.

## Setup

Requires Python 3.12 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item config.example.ps1 config.ps1
```

Edit `config.ps1` with your Telegram bot token, owner ID, required channel, wallet, and default recipient username. `OWNER_IDS`, `LEADER_IDS`, and `ADMIN_IDS` accept comma-separated numeric Telegram user IDs. Make the bot an administrator of your required channel so it can check subscriptions.

Load the settings and start the bot:

```powershell
. .\config.ps1
.\.venv\Scripts\python.exe zovteam_app_business_connected_notice_v8_fixed.py
```

On other platforms, set the same environment variables in your shell or hosting service and run the Python file. The script reads environment variables directly.

Connect the bot through Telegram's Business chatbot settings to enable business offer delivery. Send commands directly to the bot:

```text
/start
/send USER_ID https://t.me/nft/Gift-1 100
/test https://t.me/nft/Gift-1 100
```

## Message behavior

- Commands, menus, settings, and admin controls operate in direct bot chats.
- Incoming messages and edits in connected Business conversations are handled silently for connection bookkeeping.
- Screenshots and image documents are not forwarded to other users or administrators.
- Payment verification requires contacting a leader directly; access-grant commands remain available.
- Connection events and role grants do not send unsolicited notifications to other users. Admin commands confirm results to the requesting admin.
- Offer buttons validate the recipient, chat ID, message ID, and business connection before acting. Follow-ups edit the original offer or display a callback status.

## Configuration and saved data

The repository contains no bot token, saved account IDs, wallet address, or runtime JSON files from the original project. Configure your own values using `config.ps1` or environment variables. Keep `config.ps1` private; Git ignores it.

When updating an existing installation, retain its JSON files beside the script. Access permissions, settings, administrators, statistics, and business connections are loaded from those files. Git ignores runtime data files. Offers remain in memory and are not restored after a restart.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The 13 regression tests use an in-memory Telegram transport and disable network connections. They cover direct-chat controls, silent Business messages, no screenshot forwarding, silent connection events, and offer-message validation.
