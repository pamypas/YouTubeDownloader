#!/usr/bin/env python3
import sys
import json
import struct
import traceback
import os
import logging
from typing import Optional, Dict, Any
from yt_dlp import YoutubeDL

# Configure logging
logging.basicConfig(
    filename="/tmp/native_host.log",
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

def read_message() -> Optional[Dict[str, Any]]:
    """Чтение сообщения из stdin с соблюдением протокола"""
    try:
        # Читаем 4 байта длины сообщения (big-endian)
        raw_length = sys.stdin.buffer.read(4)
        if len(raw_length) < 4:
            return None

        # Распаковываем длину (I = unsigned 32-bit integer)
        length = struct.unpack('<I', raw_length)[0]
        logger.debug(f"Received message length: {length}")

        # Проверяем максимальный размер (64 MB для входящих сообщений)
        if length > 64 * 1024 * 1024:
            raise ValueError("Message too large")

        # Читаем само сообщение
        message_bytes = sys.stdin.buffer.read(length)
        if len(message_bytes) < length:
            return None

        logger.debug(f"Received message bytes: {message_bytes[:50]}...")

        return json.loads(message_bytes.decode('utf-8'))

    except Exception as e:
        log_error(f"Read error: {str(e)}\n{traceback.format_exc()}")
        return None

def send_message(message: Dict[str, Any]) -> bool:
    """Отправка сообщения в stdout с соблюдением протокола"""
    try:
        message_json = json.dumps(message).encode('utf-8')
        logger.debug(f"Sending message: {message}")

        # Проверяем максимальный размер (1 MB для исходящих сообщений)
        if len(message_json) > 1024 * 1024:
            raise ValueError("Response too large")

        # Записываем длину сообщения (big-endian) и само сообщение
        sys.stdout.buffer.write(struct.pack('@I', len(message_json)))
        sys.stdout.buffer.write(message_json)
        sys.stdout.buffer.flush()
        logger.debug(f"Sent message of length {len(message_json)}")
        return True

    except Exception as e:
        log_error(f"Send error: {str(e)}\n{traceback.format_exc()}")
        return False

def log_error(message: str):
    """Логирование ошибок в файл"""
    logger.error(message)

def process_message(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Обработка полученного сообщения"""
    try:
        url = input_data.get("url")
        action = input_data.get("action")
        logger.info(f"Processing message with URL: {url}, action: {action}")

        if not url:
            return {"status": "error", "message": "No URL provided"}
        if action == "high_quality":
            ydl_opts = {'format_sort': ['res:720', '+size'], 'paths': {'home': '/home/an/Videos'}}
        elif action == "low_quality":
            ydl_opts = {'format_sort': ['+res:360', '+size'], 'paths': {'home': '/home/an/Videos'}}
        elif action == "audio":
            ydl_opts = {'format': 'ba', 'format_sort': ['+size'],'paths': {'home': '/home/an/Music'}}
        else:
            return {"status": "error", "message": "Unknown action"}

        ydl_opts.update({
            'outtmpl': {'default': '%(title)s.%(ext)s'},
            'quiet': True,
            'no_warnings': True,
            'verbose': False,
            'noprogress': True,
            'proxy': 'socks://127.0.0.1:1080'
        })

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            output_filename = ydl.prepare_filename(info_dict)
            notify_message = f"Download completed: {output_filename}"
            os.system(f'notify-send "YouTube Downloader" "{notify_message}"')
        logger.info(f"Download completed: {output_filename}")
        return {"status": "success", "action": action, "url": url}
    except Exception as e:
        logger.exception("Error during processing message")
        return {"status": "error", "message": str(e)}

def main():
    """Основной цикл обработки сообщений"""
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
        except Exception as e:
            log_error(f"Main loop error: {str(e)}\n{traceback.format_exc()}")
            break

if __name__ == "__main__":
    main()
