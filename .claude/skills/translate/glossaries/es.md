# Spanish (es) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Spanish translations.

## Style Rules

- **Variant:** Use neutral international Spanish (avoid strongly regional idioms or terms).
- **Register & Mood:**
  - Use the **infinitive** for buttons, checkboxes, menu items, and tooltips (`Guardar`, `Añadir repositorio`, `Mostrar notificaciones cuando fallen las tareas en segundo plano`).
  - Use the formal **"usted"** imperative for direct user prompts and instructions (`Introduzca`, `Seleccione`, `Añada`, `Intente`).
  - Use impersonal or nominal/passive forms for status and progress messages (`Iniciando respaldo…`, `Instantánea eliminada.`).
- **Capitalization:** Use **sentence case** for buttons, labels, tabs, column headers, dialog titles, and lowercase inside parenthetical qualifiers (e.g., `(recomendado)`, `(predeterminado)`). Do not copy English Title Case. Always capitalize `Borg` in prose even when `<source>` writes `borg`.
- **Punctuation:**
  - Always use opening inverted question and exclamation marks (`¿…?, ¡…!`).
  - Preserve Unicode ellipses `…` (U+2026) wherever `<source>` uses `…` (never replace with ASCII `...`).
  - Match `<source>` trailing periods: do not add trailing periods to checkboxes, tooltips, titles, or labels that omit them in `<source>`, and preserve periods on full sentences that have them.
  - Use angular quotes `«…»` consistently in prose (except literal shell command examples such as `echo "..."`, which must keep ASCII double quotes).

## Terminology

| English | Spanish | Notes |
|---------|---------|-------|
| Repository | Repositorio | |
| Archive | Instantánea | Plural: `Instantáneas`, matching existing `ArchiveTab` |
| Backup (noun) | Respaldo | |
| Backup (verb) | Respaldar | |
| Prune | Limpiar | |
| Check | Comprobar / Comprobación | Consistency check; avoid `Verificar` / `Verificación` |
| Mount / Unmount | Montar / Desmontar | Filesystem mount operations (distinct from `Unlink` and `Detach`) |
| Unlink | Desvincular | Remove repository reference from Vorta (distinct from `Unmount` and `Detach`) |
| Detach | Desconectar | Detach repository from current profile while keeping it available for other profiles |
| Extract | Extraer | |
| Delete | Eliminar | Never use `Borrar` |
| Add | Añadir | Never use `Agregar` |
| Key | Llave | SSH/encryption key; never use `Clave` |
| Password / Passphrase | Contraseña / Frase de contraseña | Always distinguish `Passphrase` (`Frase de contraseña`) from `Password` (`Contraseña`) |
| Keychain / Password manager | Llavero del sistema / Gestor de contraseñas | Never use `Administrador de contraseñas` or `Gestor de claves` |
| System tray | Bandeja del sistema | |
| Profile | Perfil | |
| Schedule | Calendarización | Verb/participle: `Calendarizado` (avoid `Programado`) |
| Source | Fuente / Fuentes | Matches all live UI occurrences (`Fuentes`, `Añadir fuentes`, `Eliminar la fuente seleccionada`) |
| Exclude | Excluir | |
| Raw | Sin formato | Exclusion dialog tab (`«Sin formato»`) |
| Settings (tab) | Configuración | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Registros | Link form: `registros` |
| Command | Comando | For `Shell commands`: `Comandos de terminal` (avoid `Orden` / `Órdenes`) |
| Return code / Exit code | Código de retorno / Código de salida | Never translate as `Código de error` |
| Compact / Compaction | Compactar / Compactación | Distinct from Compression (`Compresión`) |
| Preset | Preajuste | Plural: `Preajustes`, matching exclusion dialog tab |
| Full Disk Access | Acceso total al disco | macOS system permission name |
| Metered network / connection | Red limitada / Conexión limitada | |
| Pre-release | Versión preliminar | Plural: `Versiones preliminares` (avoid `Versiones beta`) |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Archive | Instantánea | Established convention across `ArchiveTab` in `vorta.es.ts` |
| 2026-04-19 | Backup | Respaldo / Respaldar | Matches existing Spanish catalog terminology |
| 2026-04-19 | Schedule | Calendarización | Matches existing `ScheduleTab` and `MainWindow` translations |
| 2026-04-19 | Settings vs Misc | Configuración | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Compactar / Compactación | Distinct from data compression (`Compresión`) |
| 2026-11-24 | Source | Fuente / Fuentes | Resolved glossary conflict (`Origen`) to match all 5 live occurrences in `vorta.es.ts` |
| 2026-11-24 | Key | Llave | Standardize on `Llave` (forbid `Clave`) for SSH and repository keys |
| 2026-11-24 | Check | Comprobar / Comprobación | Unify consistency check terminology across `BorgCheckJob`, `RepoCheckJob`, `Form`, and `VortaApp` |
| 2026-11-24 | Delete | Eliminar | Standardize on `Eliminar` (forbid `Borrar`) across all UI actions and tooltips |
| 2026-11-24 | Add | Añadir | Standardize on `Añadir` (forbid `Agregar`) for neutral international Spanish |
| 2026-11-24 | Command / Shell commands | Comando / Comandos de terminal | Standardize on `Comando` (`Subcomando`, `Comandos de terminal`) instead of `Orden` / `Órdenes` |
| 2026-11-24 | Return code / Exit code | Código de retorno / Código de salida | Preserve semantic distinction from `Error code` (`Código de error`) |
| 2026-11-24 | Unmount / Unlink / Detach | Desmontar / Desvincular / Desconectar | Clear 3-way distinction between filesystem unmount, removing repo from Vorta, and detaching from a profile |
| 2026-11-24 | Full Disk Access | Acceso total al disco | Matches macOS Spanish localization (`Acceso total al disco`) consistently |
| 2026-11-24 | Metered network / connection | Red limitada / Conexión limitada | Consistent terminology across `NetworksPage` and `messages` |
| 2026-11-24 | Raw | Sin formato | Matches existing exclusion dialog tab and help text |
| 2026-11-24 | Pre-release | Versión preliminar | Accurate translation covering alphas, betas, and release candidates (avoid `versión beta`) |
