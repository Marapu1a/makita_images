# Project Context

Короткая актуальная сводка для быстрого старта в новом чате.

## Что это за проект

Это рабочий пайплайн по закрытию отсутствующих изображений для товаров из Bitrix-экспортов.

Основные блоки работы:
- `Makita tools`
- `Makita accessories`
- `Elitech + TEH`
- ручная доборка части placeholder-хвоста в папке `макитаапрель`
- новый блок из папки `Результат скриптов` / поставка `new_items_delivery_2026-05-09`

## Что считать истиной

Главное правило проекта:
- истина — это не старые optimistic-отчёты парсеров
- истина — это финальные папки и финальные Excel-файлы

Если есть сомнение:
1. смотрим финальную папку поставки
2. смотрим `final_report.xlsx`
3. смотрим импортный Excel

## Проверенная стартовая сверка

Состояние по финальным импортным Excel и `.webp` в товарных папках:

| Блок | Строк импорта | Реальные картинки | Placeholder | Импортных `.webp` |
| --- | ---: | ---: | ---: | ---: |
| Инструменты | `165` | `124` | `41` | `261` |
| Аксессуары | `2882` | `2603` | `279` | `4718` |
| Elitech + TEH | `234` | `234` | `0` | `1048` |
| Итого по трём финальным поставкам | `3281` | `2961` | `320` | `6027` |
| Ручная доборка `макитаапрель` | `292` | `292` | `0` | `347` |

В файловых подсчётах считаются только импортные `.webp`. Технические `.gitkeep` и служебные placeholder-файлы в корне поставок не считаются товарными изображениями.

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
- импортных `.webp`: `261`

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
- импортных `.webp`: `4718`

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
- импортных `.webp`: `1048`

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
- импортных `.webp`: `347`

Проверочный файл:
- [makitaapril_placeholder_check_2026-05-07.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\makitaapril_placeholder_check_2026-05-07.xlsx)

### 5. Новый блок из `Результат скриптов`

Текущая рабочая поставка:
- [new_items_delivery_2026-05-09](C:\Users\Valentine\Desktop\makita\py_makita\upload\new_items_delivery_2026-05-09)

Что важно:
- это отдельный поздний блок, он не входит в старые финальные цифры по инструментам / аксессуарам / Elitech+TEH
- в нём смешаны `Elitech` и `Makita`
- `Elitech` в этом блоке уже закрыт полностью
- текущий хвост остался только по `Makita`

Актуальная сводка:
- всего товаров: `585`
- реальные картинки: `577`
- placeholder: `8`

Разбивка:
- `elitech`: `496 / 496` закрыто
- `makita_tools`: `38` real, `0` placeholder
- `makita_accessories`: `32` real, `0` placeholder
- `makita_spare_parts`: `11` real, `8` placeholder

Последний честный точечный добор:
- [iterations/new_items_2026-05-09/makita_exact_tail_2026-05-10](C:\Users\Valentine\Desktop\makita\py_makita\upload\iterations\new_items_2026-05-09\makita_exact_tail_2026-05-10)
- добрал хвост до `15`, после ручной доборки `by_hands` и финализации осталось `8`

Текущий честный хвост:
- [remaining_placeholders.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\new_items_delivery_2026-05-09\remaining_placeholders.xlsx)

Дополнительный служебный экспорт по Bitrix-разделу `Запасные части`:
- [spare_parts_placeholder_import_2026-05-10.xlsx](C:\Users\Valentine\Desktop\makita\py_makita\upload\spare_parts_placeholder_import_2026-05-10.xlsx)
- лист `spare_parts_import`: `47454` строк с placeholder для импорта
- лист `other_missing_all`: `2900` прочих товаров без анонс-картинки
- лист `other_missing_with_article`: `1916` прочих товаров без анонс-картинки и с непустым артикулом

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
