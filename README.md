# Telegram Offer Bot

A Python Telegram bot with offer delivery, direct-chat settings, subscription checks, and administration controls. It runs as a background worker using Telegram long polling.

Messages in connected Telegram Business private chats do not trigger command handlers, subscription prompts, screenshot forwarding, or debug replies. Direct messages to the bot retain their controls. The explicit `/send` command delivers an offer; its buttons and expiration updates operate on that offer's stored message.

## Deploy to a hosting service

Connect or upload this repository to your host and select a **background worker** with Python 3.12. Use:

| Setting | Value |
| --- | --- |
| Build command | `python -m pip install -r requirements.txt` |
| Start command | `python -u main.py` |
| Worker instances | `1` |

The repository includes a `Procfile` for platforms that support worker process files and a `Dockerfile` for container hosting. The bot does not listen for HTTP requests, so select a worker service or a persistent Python process rather than a web service requiring a port.

Set these environment variables in the hosting dashboard:

| Variable | Required | Purpose |
| --- | --- | --- |
| `BOT_TOKEN` | Yes | Your Telegram BotFather token |
| `OWNER_IDS` | Yes | Your numeric Telegram user ID, or comma-separated owner IDs |
| `REQUIRED_CHANNEL` | Yes | Your required channel, such as `@your_actual_channel` |
| `DEFAULT_RECIPIENT_USERNAME` | Yes | Default gift recipient, such as `@your_actual_username` |
| `REQUIRED_CHANNEL_URL` | Optional | Channel subscription link; derived from `REQUIRED_CHANNEL` by default |
| `LEADER_IDS` | Optional | Comma-separated leader IDs |
| `ADMIN_IDS` | Optional | Comma-separated admin IDs |
| `TON_WALLET` | For paid access | Wallet shown in the access-payment instructions |
| `BOT_DATA_DIR` | For persistent storage | Directory on your host's mounted persistent disk |

Replace all example values before starting. Make the bot an administrator of the required channel so subscription checks work. Connect it through Telegram's Business chatbot settings for business offer delivery.

`.env.example` lists the settings to copy into the host's environment panel. The bot reads operating-system environment variables; it does not automatically load `.env` files. Tokens and live account settings belong in the hosting dashboard, not in GitHub.

Check configuration without contacting Telegram:

```text
python main.py --check-config
```

This verifies required settings and rejects missing/example values. It does not verify the token with Telegram. Normal startup checks the token online. Stop any locally running copy before starting the hosted worker; one token must have one active polling worker.

### Persistent storage

Mount your host's persistent disk and set `BOT_DATA_DIR` to its mount path, for example `/data`. Access permissions, settings, administrators, statistics, business connections, and the worker lock are stored there. Copy your existing runtime JSON files into that directory if migrating an existing installation.

Without `BOT_DATA_DIR`, data remains beside the Python script, preserving existing local installations. A host with an ephemeral filesystem will lose that data when the filesystem is replaced. Offers remain in memory and are not restored after a process restart.

### Docker

```text
docker build -t telegram-offer-bot .
docker run --env-file /path/to/your/private/hosting.env --mount type=volume,src=telegram-offer-bot-data,dst=/data telegram-offer-bot
```

Create the private environment file using the keys in `.env.example`, or configure the same environment variables through your container host. The image uses `/data` for runtime data; attach a persistent volume there. The Docker build copies only the requirements and the two application Python files.

## Run locally

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
.\.venv\Scripts\python.exe main.py --check-config
.\.venv\Scripts\python.exe -u main.py
```

On other platforms, set the same environment variables in your shell and run `python -u main.py`.

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

When updating an existing installation, retain its JSON files beside the script or move them into the directory configured by `BOT_DATA_DIR`. Git ignores runtime data files and the local `data/` directory.

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The offline tests cover direct-chat controls, silent Business messages, no screenshot forwarding, silent connection events, offer-message validation, configuration checks, persistent storage, and the single-worker lock. Routing tests use an in-memory Telegram transport and disable network connections.
