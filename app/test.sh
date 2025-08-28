# Создаём тестовое сообщение
TEST_MSG='{"url":"https://youtube.com/watch?v=dQw4w9WgXcQ", "action": "audio"}'
LEN=$(printf "%08x" ${#TEST_MSG})

# Отправляем в скрипт (длина + сообщение)
echo -n -e "\\x${LEN:0:2}\\x${LEN:2:2}\\x${LEN:4:2}\\x${LEN:6:2}${TEST_MSG}" | python3 youtube_downloader.py
