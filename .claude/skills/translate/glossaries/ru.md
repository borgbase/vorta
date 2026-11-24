# Russian (ru) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Russian translations.

## Register

Use formal **«вы»** in **lowercase** mid-sentence (`вы`, `вас`, `вам`, `ваш` — never capitalized `Вы`/`Ваш` mid-sentence; capitalize only at the start of a sentence). Use imperative (`Введите`, `Выберите`) for direct prompts and imperfective infinitive (`Хранить`, `Добавлять`, `Очищать`, `Проверять`, `Уплотнять`) for recurring settings and schedule checkboxes.

## Style Rules

- **Capitalization:** Use sentence case for buttons, menu items, tabs, column headers, dialog titles, and parenthetical qualifiers (`(рекомендуется)`, `(устарело)`). Never copy English Title Case.
- **Orthography (`ё`):** Use `ё` consistently (`удалённый`, `обновлён`, `путём`, `сохранён`, `отключён`).
- **Quotation marks:** Use Russian guillemets `«…»` in UI prose. Keep ASCII double quotes `"..."` inside shell command examples (`echo "..."`) so shell syntax and variable expansion remain valid.
- **Ellipsis:** Use the Unicode ellipsis `…` (U+2026) wherever `<source>` uses `…` (dialog-opening actions and progress messages); never substitute ASCII `...`.
- **Qt plural forms (`numerus="yes"`):** Russian uses 3 `<numerusform>` slots:
  - `[0]` `1, 21, 31…` (`%n файл`)
  - `[1]` `2–4, 22–24…` (`%n файла`)
  - `[2]` `0, 5–20, 25–30…` (`%n файлов`)
- **Verb aspect for recurring checkboxes:** Use imperfective infinitives for recurring schedule/settings actions (`Очищать`, `Проверять`, `Уплотнять`, `Выполнять`), reserving perfective infinitives (`Очистить`, `Проверить`, `Уплотнить`) for one-shot action buttons.

## Terminology

| English | Russian | Notes |
|---------|---------|-------|
| Repository | Репозиторий | |
| Archive | Архив | |
| Backup (process) | Архивация | Forbid `резервирование` |
| Backup (artifact) | Резервная копия | |
| Backup (verb) | Архивировать | |
| Prune | Очистить / Очищать | Imperfective (`Очищать`) for recurring schedule checkboxes |
| Mount / Unmount | Смонтировать / Отмонтировать | Distinct from `Unlink` (`Отвязать`) and `Detach` (`Отключить от профиля`) |
| Unlink | Отвязать | Disconnect repository from Vorta; distinct from `Unmount` and `Detach` |
| Detach | Отключить от профиля | Remove repository from current profile while keeping it for other profiles |
| Extract | Извлечь | |
| Password | Пароль | Distinct from `Passphrase` (`Ключевая фраза`) |
| Passphrase | Ключевая фраза | Distinct from `Password` (`Пароль`) |
| Keychain / Password manager | Системное хранилище ключей / Менеджер паролей | |
| System tray | Системный трей / Область уведомлений | |
| Profile | Профиль | |
| Schedule | Расписание | |
| Source | Источник | |
| Exclude | Исключить | |
| Patterns | Шаблоны | Distinct from `Presets` (`Наборы`) |
| Presets | Наборы | Distinct from `Patterns` (`Шаблоны`) |
| Metered network / connection | Лимитная сеть / Лимитное подключение | Forbid `платное соединение` |
| Full Disk Access | Полный доступ к диску | Sentence case in prose (`полный доступ к диску`) |
| Exit code / Returncode | Код возврата | Avoid `код ошибки` when `<source>` says `exit code` / `returncode` |
| Shell Commands | Команды оболочки | |
| Settings (tab) | Настройки | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Журналы | Link form in prepositional (`в %1`): `журналах` |
| Compact / Compaction | Уплотнить / Уплотнять / Уплотнение | Distinct from Compression (`Сжатие`); avoid `Дефрагментация` |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Repository | Репозиторий | Established term across `vorta.ru.ts` |
| 2026-04-19 | Mount / Unmount | Смонтировать / Размонтировать | Matches existing `ArchiveTab` Russian translations (superseded for Unmount below) |
| 2026-04-19 | Logs (link) | журналах | Prepositional plural matching `Подробности смотрите в %1.` |
| 2026-04-19 | Settings vs Misc | Настройки | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Уплотнить / Уплотнение | Borg compaction reclaims unused segment space rather than defragmenting files |
| 2026-11-24 | Formal `вы` | Lowercase `вы`/`ваш` mid-sentence | Modern Russian UI standard (Apple, GNOME, KDE, Yandex) |
| 2026-11-24 | Passphrase vs Password | Ключевая фраза vs Пароль | Keeps Borg encryption passphrases distinct from generic passwords |
| 2026-11-24 | Backup (process vs artifact) | Архивация / Резервная копия | Avoids `резервирование`; matches existing Vorta Russian usage |
| 2026-11-24 | Presets vs Patterns | Наборы vs Шаблоны | Prevents collision between the Presets tab and exclusion patterns |
| 2026-11-24 | Unmount / Unlink / Detach | Отмонтировать / Отвязать / Отключить от профиля | Clear 3-way distinction between filesystem unmount, Vorta unlink, and profile detach |
| 2026-11-24 | Metered network / connection | Лимитная сеть / Лимитное подключение | Standard Russian OS terminology; forbids `платное соединение` |
| 2026-11-24 | Full Disk Access | Полный доступ к диску | Matches macOS Russian localization |
| 2026-11-24 | Exit code / Returncode | Код возврата | Accurate technical term; distinct from `код ошибки` |
| 2026-11-24 | Shell Commands | Команды оболочки | Consistent with existing `ShellCommandsPage` and `schedule_tab.ui` |
