import os
import socket
import subprocess
import threading
import time
import webbrowser

from src.api_server import main


HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def is_server_running():
    try:
        with socket.create_connection((HOST, PORT), timeout=0.5):
            return True
    except OSError:
        return False


def is_wsl():
    try:
        return "microsoft" in os.uname().release.lower()
    except AttributeError:
        return False


def open_browser(delay=0):
    if delay:
        time.sleep(delay)

    if is_wsl():
        subprocess.Popen(
            ["cmd.exe", "/c", "start", "", URL],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    webbrowser.open(URL)


def run():
    if is_server_running():
        open_browser()
        return

    browser_thread = threading.Thread(
        target=open_browser,
        kwargs={"delay": 1.5},
        daemon=True,
    )
    browser_thread.start()

    main()


if __name__ == "__main__":
    run()
