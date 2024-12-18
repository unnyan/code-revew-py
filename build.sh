#!/bin/bash

set -e

echo "\nЗапуск сборки проекта...\n"

echo "Запускаем docker-compose..."
docker-compose down --remove-orphans
docker-compose up --build -d

echo "\nОжидание запуска базы данных...\n"
sleep 10

echo "\nВыполняем подготовительные скрипты...\n"
docker exec -it recipe-diet-bot-app-1 python site_parser.py

echo "\nЗапуск Telegram-бота...\n"
docker exec -it recipe-diet-bot-app-1 python bot.py

echo "\nПроект успешно собран и запущен!\n"
