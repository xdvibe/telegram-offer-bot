"""Hosting entry point: python -u main.py."""
import argparse

import zovteam_app_business_connected_notice_v8_fixed as bot


def main():
    parser = argparse.ArgumentParser(description="Run the Telegram offer bot.")
    parser.add_argument(
        "--check-config", action="store_true",
        help="Check required configuration locally without contacting Telegram.",
    )
    args = parser.parse_args()
    if args.check_config:
        errors = bot.configuration_errors()
        if errors:
            parser.exit(1, "Configuration needed: " + ", ".join(errors) + "\n")
        print("Configuration is present. Telegram credentials have not been verified online.")
        return
    bot.main()


if __name__ == "__main__":
    main()
