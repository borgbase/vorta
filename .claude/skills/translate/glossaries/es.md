# Spanish (es) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Spanish translations.

## Register

Use formal **"usted"** (`Introduzca`, `Seleccione`, `Añada`) consistently throughout all translations.

## Terminology

| English | Spanish | Notes |
|---------|---------|-------|
| Repository | Repositorio | |
| Archive | Instantánea | Plural: `Instantáneas`, matching existing `ArchiveTab` |
| Backup (noun) | Respaldo | |
| Backup (verb) | Respaldar | |
| Prune | Limpiar | |
| Mount / Unmount | Montar / Desmontar | |
| Extract | Extraer | |
| Password / Passphrase | Contraseña / Frase de contraseña | |
| Keychain / Password manager | Llavero del sistema / Gestor de contraseñas | |
| System tray | Bandeja del sistema | |
| Profile | Perfil | |
| Schedule | Calendarización | |
| Source | Origen | |
| Exclude | Excluir | |
| Settings (tab) | Configuración | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Registros | Link form: `registros` |
| Compact / Compaction | Compactar / Compactación | Distinct from Compression (`Compresión`) |
| Preset | Preajuste | Plural: `Preajustes`, matching exclusion dialog tab |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Archive | Instantánea | Established convention across `ArchiveTab` in `vorta.es.ts` |
| 2026-04-19 | Backup | Respaldo / Respaldar | Matches existing Spanish catalog terminology |
| 2026-04-19 | Schedule | Calendarización | Matches existing `ScheduleTab` and `MainWindow` translations |
| 2026-04-19 | Settings vs Misc | Configuración | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Compactar / Compactación | Distinct from data compression (`Compresión`) |
