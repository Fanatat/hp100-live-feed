# hp100-live-feed

Публичный JSON-фид домашнего датчика воздуха HP100: CO₂, температура, влажность, пыль — обновляется каждые 5 минут.
*Public JSON feed of an HP100 air-quality sensor (CO₂, temperature, humidity, dust), refreshed every 5 minutes.*

## Что это

Репозиторий-фид. Скрипт на VPS опрашивает локальный сервер датчика (`localhost:8080`) и коммитит сюда два файла: `latest.json` — текущее показание с меткой времени UTC, `history.json` — последние 24 часа с усреднением по 15 минут (96 точек). Коммиты идут от отдельной бот-учётки, поэтому данные можно забирать со стабильного raw-URL GitHub, не обращаясь к самому VPS.

Поля: `co2` (ppm), `temperature` (°C), `humidity` (%), `dust` (PM2.5), `updated` / `timestamp`. Поле `dust` присутствует только когда датчик его отдаёт.

## Как читать

```
https://raw.githubusercontent.com/Fanatat/hp100-live-feed/master/latest.json
https://raw.githubusercontent.com/Fanatat/hp100-live-feed/master/history.json
```

## Как это работает

- `update_feed.py` — опрос датчика, сборка JSON, commit + push; интервал `UPDATE_INTERVAL_SECONDS = 300` (5 минут), при неизменившемся показании коммит пропускается. Разовый запуск без флагов — для ручной проверки, `--loop` — бесконечный цикл.
- `hp100-feed.service` — unit systemd, запускает скрипт с `--loop` от имени пользователя VPS; команды установки — в шапке файла.
- Зависимости: Python 3 (только стандартная библиотека) и настроенный push в этот репозиторий.

## Статус

Фид обновляется службой на VPS автора; данные читает виджет на сайте автора.
