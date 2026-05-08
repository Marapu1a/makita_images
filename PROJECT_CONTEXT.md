# Project Context

Короткая актуальная сводка для быстрого старта в новом чате.

## Что это за проект

Это рабочий пайплайн по закрытию отсутствующих изображений для товаров из Bitrix-экспортов.

Основные блоки работы:
- `Makita tools`
- `Makita accessories`
- `Elitech + TEH`
- ручная доборка части placeholder-хвоста в папке `макитаапрель`

## Что считать истиной

Главное правило проекта:
- истина — это не старые optimistic-отчёты парсеров
- истина — это финальные папки и финальные Excel-файлы

Если есть сомнение:
1. смотрим финальную папку поставки
2. смотрим `final_report.xlsx`
3. смотрим импортный Excel

## Главные файлы, которые надо открыть в новом чате

Сначала:
- [README.md](C:\Users\Valentine\Desktop\makita\py_makita\upload\README.md)
- [NEXT_CHAT_HANDOFF.md](C:\Users\Valentine\Desktop\makita\py_makita\upload\NEXT_CHAT_HANDOFF.md)

Потом по ситуации:
- [CLIENT_FINAL_REPORT_2026-04-27.md](C:\Users\Valentine\Desktop\makita\py_makita\upload\CLIENT_FINAL_REPORT_2026-04-27.md)
- [placeholder_items_2026-04-27.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\placeholder_items_2026-04-27.xlsx)
- [makitaapril_placeholder_check_2026-05-07.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\makitaapril_placeholder_check_2026-05-07.xlsx)

## Финальные поставки

### 1. Инструменты

Готовая поставка:
- [final_delivery_2026-04-09](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_delivery_2026-04-09)

Содержит:
- `import_images`
- `final_report.xlsx`
- `pictures_for_import.xlsx`
- `pictures_for_bitrix_import.xlsx`

Сводка:
- всего товаров: `165`
- реальные картинки: `124`
- placeholder: `41`

### 2. Аксессуары

Готовая поставка:
- [final_accessories_delivery_2026-04-18](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_accessories_delivery_2026-04-18)

Содержит:
- `import_images`
- `final_report.xlsx`
- `pictures_for_import.xlsx`
- `pictures_for_bitrix_import.xlsx`

Сводка:
- всего товаров: `2882`
- реальные картинки: `2603`
- placeholder: `279`

### 3. Elitech + TEH

Готовая поставка:
- [final_elitech_and_teh_delivery_2026-04-27](C:\Users\Valentine\Desktop\makita\py_makita\upload\final_elitech_and_teh_delivery_2026-04-27)

Содержит:
- `import_images`
- `final_report.xlsx`
- `sources_summary.xlsx`
- `pictures_for_import.xlsx`
- `pictures_for_bitrix_import.xlsx`

Сводка:
- всего товаров: `234`
- закрыто: `234`
- placeholder: `0`

### 4. Ручная доборка placeholder-хвоста

Нормализованная поставка:
- [makitaapril_delivery_2026-05-07](C:\Users\Valentine\Desktop\makita\py_makita\upload\makitaapril_delivery_2026-05-07)

Содержит:
- `import_images`
- `final_report.xlsx`
- `pictures_for_import.xlsx`
- `pictures_for_bitrix_import.xlsx`

Сводка:
- в `placeholder_items_2026-04-27.xlsx` было `320` placeholder-позиций
- вручную найдено по папке `макитаапрель`: `291`
- из них нормализовано в поставку: `291`
- потом вручную был добавлен ещё `CP100DZ`
- итоговая поставка `makitaapril_delivery_2026-05-07`: `292` строк в импортном Excel

Проверочный файл:
- [makitaapril_placeholder_check_2026-05-07.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\makitaapril_placeholder_check_2026-05-07.xlsx)

## Placeholder-файл

Общий список placeholder-позиций:
- [placeholder_items_2026-04-27.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\placeholder_items_2026-04-27.xlsx)

Сводка:
- всего placeholder: `320`
- инструменты: `41`
- аксессуары: `279`
- Elitech + TEH: `0`

## Важные рабочие правила

- главный ключ сопоставления — `Артикул [ARTIKUL]`
- одна итерация = один источник
- после ручной чистки честный остаток всегда строится по реально существующим папкам
- если артикул содержит недопустимые для имени папки символы, имя папки санитизируется

Пример:
- артикул: `D-31669/1`
- имя папки: `D-31669_1`

## Что уже удалено и не надо возвращать

Удалены как мусор/неудачные попытки:
- `iterations\tools_tail_2026-04-27`
- `iterations\accessories\makitapro_tail_2026-04-27`
- старая recovery-папка из GitHub
- разные временные `tmp_*`, тестовые HTML и одноразовые файлы

То есть если в новом чате всплывёт идея “может там ещё был хвостовой прогон”:
- нет, последние две попытки сознательно удалены как хлам

## Если продолжать работу дальше

Рабочая логика остаётся прежней:
1. берём Excel / хвост
2. проверяем источник на качество
3. делаем отдельную итерацию под источник
4. после ручной проверки пересобираем честный остаток
5. в финал тащим только подтверждённое

Если задача будет не про новый парсинг, а про импорт / пересборку:
- сначала смотрим существующие финальные поставки
- потом смотрим `makitaapril_delivery_2026-05-07`

## Что важно помнить

- у проекта длинная история, но текущее состояние уже стабилизировано
- основные поставки готовы
- ручная доборка тоже нормализована
- новый чат должен отталкиваться не от старых промежуточных итераций, а от финальных директорий и этого контекста
