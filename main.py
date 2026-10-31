"""Hosting entry point with startup diagnostics."""
import asyncio
import faulthandler
import inspect
from pathlib import Path
import time
import traceback

diagnostic_path = Path(__file__).resolve().parent / "startup-diagnostic.log"
diagnostic = diagnostic_path.open("a", buffering=1)

def stage(message):
    diagnostic.write(time.strftime("%Y-%m-%d %H:%M:%S ") + message + "\n")
    diagnostic.flush()

if __name__ == "__main__":
    stage("Importing bot module")
    faulthandler.dump_traceback_later(30, repeat=True, file=diagnostic)
    try:
        from zovteam_app_business_connected_notice_v8_fixed import main
        stage("Bot module imported; calling main")
        result = main()
        if inspect.isawaitable(result):
            stage("Awaiting asynchronous main")
            asyncio.run(result)
        stage("Bot main returned")
    except BaseException:
        stage("Startup failed")
        traceback.print_exc(file=diagnostic)
        raise
    finally:
        faulthandler.cancel_dump_traceback_later()
