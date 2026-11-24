# Russian (ru) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Russian translations.

## Register

Use formal **"Вы"** (`Введите`, `Ваша`, `Пожалуйста, разблокируйте`) for user prompts and infinitive (`Хранить`, `Добавлять`) for settings checkboxes.

## Terminology

| English | Russian | Notes |
|---------|---------|-------|
| Repository | Репозиторий | |
| Archive | Архив | |
| Backup (noun) | Архивация / Резервная копия | Context-dependent matching existing `vorta.ru.ts` |
| Backup (verb) | Архивировать | |
| Prune | Очистить | |
| Mount / Unmount | Смонтировать / Размонтировать | |
| Extract | Извлечь | |
| Password / Passphrase | Пароль / Ключевая фраза | |
| Keychain / Password manager | Системное хранилище ключей / Менеджер паролей | |
| System tray | Системный трей / Область уведомлений | |
| Profile | Профиль | |
| Schedule | Расписание | |
| Source | Источник | |
| Exclude | Исключить | |
| Settings (tab) | Настройки | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Журналы | Link form in prepositional (`в %1`): `журналах` |
| Compact / Compaction | Уплотнить / Уплотнение | Distinct from Compression (`Сжатие`); avoid `Дефрагментация` |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Repository | Репозиторий | Established term across `vorta.ru.ts` |
| 2026-04-19 | Mount / Unmount | Смонтировать / Размонтировать | Matches existing `ArchiveTab` Russian translations |
| 2026-04-19 | Logs (link) | журналах | Prepositional plural matching `Подробности смотрите в %1.` |
| 2026-04-19 | Settings vs Misc | Настройки | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Уплотнить / Уплотнение | Borg compaction reclaims unused segment space rather than defragmenting files |
