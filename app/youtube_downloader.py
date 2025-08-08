#!/usr/bin/env python3

import json
import logging
import os
import struct
import sys
import traceback
from typing import Dict, Optional, Any

from yt_dlp import YoutubeDL

# --------------------------------------------------------------------------- #
# Configuration constants
# --------------------------------------------------------------------------- #

HEADER_SIZE = 4  # 4‑byte length prefix
MAX_INCOMING = 64 * 1024 * 1024  # 64 MB
MAX_OUTGOING = 1 * 1024 * 1024   # 1 MB

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

logging.basicConfig(
    filename="/tmp/native_host.log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #

def _read_exact(n: int) -> bytes:
    """
    Read exactly *n* bytes from stdin.buffer.
    Raises EOFError if the stream ends prematurely.
    """
    data = bytearray()
    while len(data) < n:
        chunk = sys.stdin.buffer.read(n - len(data))
        if not chunk:
            raise EOFError("Unexpected EOF while reading message")
        data.extend(chunk)
    return bytes(data)


def read_message() -> Optional[Dict[str, Any]]:
    """
    Read a length‑prefixed JSON message from stdin.

    Returns:
        The decoded JSON object, or ``None`` if EOF is reached.
    """
    try:
        raw_len = _read_exact(HEADER_SIZE)
        length = struct.unpack("@I", raw_len)[0]
        logger.debug(f"Received message length: {length}")

        if length > MAX_INCOMING:
            raise ValueError(f"Message too large: {length} bytes")

        raw_msg = _read_exact(length)
        logger.debug(f"Received message bytes: {raw_msg[:50]!r}…")

        return json.loads(raw_msg.decode("utf-8"))
    except EOFError:
        logger.debug("EOF reached – no more messages")
        return None
    except (struct.error, json.JSONDecodeError, ValueError) as exc:
        logger.error(f"Failed to read message: {exc}")
        return None
    except Exception as exc:
        logger.exception(f"Unexpected error while reading message: {exc}")
        return None


def send_message(message: Dict[str, Any]) -> bool:
    """
    Send a JSON message to stdout following the protocol.

    Returns:
        ``True`` on success, ``False`` on failure.
    """
    try:
        message_json = json.dumps(message, ensure_ascii=False).encode("utf-8")
        logger.debug(f"Sending message: {message}")

        if len(message_json) > MAX_OUTGOING:
            raise ValueError(f"Response too large: {len(message_json)} bytes")

        sys.stdout.buffer.write(struct.pack("@I", len(message_json)))
        sys.stdout.buffer.write(message_json)
        sys.stdout.buffer.flush()
        logger.debug(f"Sent message of length {len(message_json)}")
        return True
    except Exception as exc:
        logger.exception(f"Send error: {exc}")
        return False


def log_error(message: str) -> None:
    """Log an error message."""
    logger.error(message)


def process_message(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single message from the extension.

    Parameters
    ----------
    input_data : dict
        Expected keys: ``url`` and ``action``.
    """
    try:
        url = input_data.get("url")
        action = input_data.get("action")
        logger.info(f"Processing message with URL: {url}, action: {action}")

        if not url:
            return {"status": "error", "message": "No URL provided"}

        # Build yt_dlp options based on the requested action
        if action == "high_quality":
            ydl_opts = {
                "format_sort": ["res:720", "+size"],
                "paths": {"home": "/home/an/Videos"},
            }
        elif action == "low_quality":
            ydl_opts = {
                "format_sort": ["+res:360", "+size"],
                "paths": {"home": "/home/an/Videos"},
            }
        elif action == "audio":
            ydl_opts = {
                "format": "ba",
                "format_sort": ["+size"],
                "paths": {"home": "/home/an/Music"},
            }
        else:
            return {"status": "error", "message": "Unknown action"}

        # Common options
        ydl_opts.update(
            {
                "outtmpl": {"default": "%(title)s.%(ext)s"},
                "quiet": True,
                "no_warnings": True,
                "verbose": False,
                "noprogress": True,
                "proxy": "socks://127.0.0.1:1080",
            }
        )

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            output_filename = ydl.prepare_filename(info_dict)
            # Send only the file name (basename) in the notification
            notify_message = f"Download completed: {os.path.basename(output_filename)}"
            os.system(f'notify-send "YouTube Downloader" "{notify_message}"')
        logger.info(f"Download completed: {output_filename}")
        return {"status": "success", "action": action, "url": url}
    except Exception as exc:
        logger.exception("Error during processing message")
        return {"status": "error", "message": str(exc)}


def main() -> None:
    """Main loop: read, process, and reply to messages."""
    logger.info("Starting main loop")
    while True:
        try:
            message = read_message()
            if message is None:
                logger.debug("No more messages, exiting loop")
                break

            logger.debug(f"Received message: {message}")
            response = process_message(message)
            if not send_message(response):
                logger.debug("Failed to send response, exiting loop")
                break
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received, exiting")
            break
        except Exception as exc:
            log_error(f"Main loop error: {exc}\n{traceback.format_exc()}")
            break


if __name__ == "__main__":
    main()
