"""Environment configuration. Contains no credentials."""
import logging
import os
from pathlib import Path
import re
import sys

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent
load_dotenv(PROJECT_DIR / '.env', override=False)


def path_setting(name, default):
    path = Path(os.getenv(name, default)).expanduser()
    return path if path.is_absolute() else PROJECT_DIR / path


DATA_DIR = path_setting('DATA_DIR', 'data')
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = path_setting('DATABASE_PATH', str(DATA_DIR / 'bot.sqlite3'))
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


def ids(name):
    return {int(value.strip()) for value in os.getenv(name, '').split(',') if value.strip()}


class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
    OFFER_EXPIRY_HOURS = int(os.getenv('OFFER_EXPIRY_HOURS', '24'))
    MAX_PRICE = int(os.getenv('MAX_PRICE', '999999'))
    PREMIUM_STAR_ID = os.getenv('PREMIUM_STAR_ID', '6028338546736107668')
    ACCESS_PRICE_TON = float(os.getenv('ACCESS_PRICE_TON', '3'))
    TON_WALLET = os.getenv('TON_WALLET', '')
    REQUIRED_CHANNEL = os.getenv('REQUIRED_CHANNEL', '@offerfake')
    REQUIRED_CHANNEL_URL = os.getenv('REQUIRED_CHANNEL_URL', 'https://t.me/offerfake')
    ADMIN_IDS = ids('ADMIN_IDS')
    LEADER_IDS = ids('LEADER_IDS')
    OWNER_IDS = ids('OWNER_IDS')
    MENU_BANNER = os.getenv('MENU_BANNER', 'zov_team_banner.png')
    DEFAULT_RECIPIENT_ID = int(os.environ['DEFAULT_RECIPIENT_ID']) if os.getenv('DEFAULT_RECIPIENT_ID') else None
    DEFAULT_RECIPIENT_USERNAME = os.getenv('DEFAULT_RECIPIENT_USERNAME', '')
    MIN_MESSAGE_DELAY = float(os.getenv('MIN_MESSAGE_DELAY', '5'))
    RANDOM_DELAY_MIN = float(os.getenv('RANDOM_DELAY_MIN', '3'))
    RANDOM_DELAY_MAX = float(os.getenv('RANDOM_DELAY_MAX', '8'))
    USE_RANDOM_DELAYS = os.getenv('USE_RANDOM_DELAYS', 'true').lower() in {'1', 'true', 'yes'}
    RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '3600'))
    TEST_NAMES = ['Stellar Rocket', 'Instant Ramen', 'Jingle Bells', 'Snoop Dogg',
                  'Golden Star', 'Birthday Cake', 'Delicious Cake']


def redact(value):
    text = str(value)
    if Config.BOT_TOKEN:
        text = text.replace(Config.BOT_TOKEN, '<BOT_TOKEN>')
    return re.sub(r'\b\d{8,}:[A-Za-z0-9_-]{20,}\b', '<BOT_TOKEN>', text)


class RedactedStream:
    def __init__(self, stream):
        self.stream = stream

    def write(self, text):
        return self.stream.write(redact(text))

    def __getattr__(self, name):
        return getattr(self.stream, name)


_record_factory = logging.getLogRecordFactory()


def _safe_record(*args, **kwargs):
    record = _record_factory(*args, **kwargs)
    record.msg = redact(record.getMessage())
    record.args = ()
    return record


logging.setLogRecordFactory(_safe_record)
sys.stdout = RedactedStream(sys.stdout)
sys.stderr = RedactedStream(sys.stderr)
