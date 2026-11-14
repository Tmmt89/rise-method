# Чтение методической базы

Все команды выполняются с фактическим путём папки skill. Примеры ниже предполагают рабочую папку skill; из другой папки укажи полный путь к `scripts/query.py`. Нужен только Python 3, без внешних библиотек. Скрипт читает единую базу и не меняет проект, платформу или настройки.

```sh
python3 scripts/query.py status
python3 scripts/query.py catalog profiles
python3 scripts/query.py get PR-FUNCTIONAL CTX-ONE-TO-ONE
python3 scripts/query.py selector frameworks
python3 scripts/query.py get FW-CONTEXT-PRACTICE
python3 scripts/query.py selector activities
python3 scripts/query.py get ACT-002 ACT-017 ACT-020
python3 scripts/query.py bindings ACT-017 ACT-020
python3 scripts/query.py get PLAT-021
python3 scripts/query.py platform-check PLAT-021
python3 scripts/query.py checks --gate authoring
python3 scripts/query.py get QC-008 QC-012
python3 scripts/query.py source LANG-020 PRACTICE-014
python3 scripts/query.py text blueprint
```

## Что читать в какой момент

| Команда | Выход и условие использования |
|---|---|
| `status` | Путь базы, версии, размеры каталогов, документы, состояние последней структурной проверки. Это не новая проверка и не runtime. |
| `catalog profiles / contexts / frameworks / activities / rules / checks / platform` | Короткий список ID с назначением; позволяет выбрать нужное без загрузки всех контрактов. |
| `selector profiles / frameworks / activities` | Процедура/условия выбора из спецификации. Для курса profile включает отдельную логику курса и занятия. |
| `get ID ...` | Полная запись выбранных PR/CTX/FW/ACT/CORE/QC/PLAT. До восьми ID за вызов; для нескольких больших профилей читай по одному. Возвращает происхождение каталога и SHA-256. |
| `bindings ACT-...` | До восьми ACT за вызов. Условные форматы/компоненты, точные PLAT, ограничения, manual fallback и будущие runtime-сценарии. Прочитай также global/conditional requirements. |
| `checks --gate authoring/runtime/post_pilot` | Все проверки нужного этапа с условиями применимости и существенностью; полное правило читается через `get QC-...`. Для полного урока явно учти каждую authoring-проверку. Для малого задания указывай N/A по масштабу. |
| `source CARD-ID ...` | Точная исходная карточка из заметки, строка и вводный контекст; до трёх карточек. Это текстовый доступ к карточке, не новая сверка оригинального PDF/аудио. |
| `platform-check PLAT-...` | До восьми PLAT за вызов; большие списки разбей на группы. Сравнение файлов кода/документов с хешами исследованного checkout. `unchanged` сохраняет силу локального основания; `changed/missing` требует адресной проверки. Даже unchanged не подтверждает production. |
| `text blueprint / decisions / glossary / platform / workflow / scenarios / framework-selection` | Полный выбранный документ и путь. Blueprint нужен для структуры пакета; decisions — при споре; platform — для настоящего цифрового выхода; остальные по условию. |

Пример другого расположения базы:

```sh
python3 scripts/query.py --workspace "/path/to/Teaching skills" get PR-WRITING
python3 scripts/query.py --platform-repo "/path/to/Speaking_livekit" platform-check PLAT-006
```

Приоритет пути базы: `--workspace` → `RISE_MATERIALS_WORKSPACE` → непустой путь в `references/workspace.json` → встроенная `references/basis`. Для платформы: `--platform-repo` → `RISE_MATERIALS_PLATFORM_REPO` → настройка; без пути возвращается `not_configured`, а не успешная проверка. Если явный путь ошибочен, скрипт завершает чтение с ошибкой, не подставляет другую базу молча. Публичный пакет переносим целиком: все методические каталоги и карточки включены. Оригинальные 73 файла и код Speaking_livekit не распространяются с ним.

## Основания и свежесть

CORE — синтезированные правила; PR/CTX — профили/контексты; FW — маршруты; ACT — семейства; QC — качество материала; PLAT — основание в локальном коде/документах. `source_cards` ведут к карточкам INT/LANG/BOOK/PROMPT/BANK/VIDEO/PRACTICE, где сохраняется статус и точный первичный локатор. Полезная ссылка на карантинную карточку может задавать исключение, а не принятие спорного тезиса.

Чтение через скрипт содержит текущий хеш выбранного каталога. Сохраняй используемые ID/версию в плане или QA. Для обновления самой спецификации по отдельному запросу доступен её `methodology/scripts/build_specification.py`; обычное создание урока не требует заново хешировать все оригиналы и пересобирать исследование.

При необходимости оригинального медиа используй локатор карточки и доступный оригинал, если он предоставлен. Во встроенной базе есть авторские карточки и каталог исходных типов материалов, а не сами медиа; отсутствие оригинала остаётся зависимостью. Допустима явно авторская замена с новой проверкой задания/ключа. Для фонетики прослушай нужный фрагмент: ASR не удостоверяет интонацию. Применяй skill PDF/DOCX/презентаций только при соответствующем формате работы.
