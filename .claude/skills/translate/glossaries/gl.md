# Galician (gl) Translation Glossary

Agreed-upon translations and style rules for the Vorta project. These terms and rules are **mandatory** — use them consistently in all Galician translations.

## Style Rules

- **Orthography:** Follow official RAG (*Real Academia Galega*) norms.
- **Strict anti-Castilianism rules:**
  - Never use `elexir`, `elexido`, `elixe`, or `elixer` — use `escoller` or `seleccionar`.
  - Never use `ventá` — use `xanela`.
  - Never use `archivo` — use `arquivo`.
  - Never use `interrumpir` — use `interromper`.
  - Never use `recibeu` — use `recibiu`.
  - Never put a written accent on `-mente` adverbs (e.g., `automaticamente`, never `automáticamente`).
- **Register:** Use formal **"vostede"** (`Introduza`, `Escolla`, `Seleccione`, `Engada`, `Consulte`, `súa`) consistently throughout all translations. Never use informal `ti`.
- **Capitalization:** Use sentence case for buttons, menu items, tabs, column headers, and dialog titles. Always capitalize `Borg` in prose even if the English source writes lowercase `borg`.
- **Verbs in UI controls:** Use the infinitive for buttons and checkboxes (e.g., `Sobrescribir…`, `Comprobar…`, `Podar`).
- **Punctuation:** Use angular quotation marks `«…»` in prose and the Unicode ellipsis `…` (U+2026) instead of three ASCII periods `...`.

## Terminology

| English | Galician | Notes |
|---------|----------|-------|
| Repository | Repositorio | Never abbreviate as `repo` in prose |
| Archive | Arquivo | Distinct from File (`Ficheiro`); never `archivo` |
| File | Ficheiro | Distinct from Archive (`Arquivo`) |
| Folder / Directory | Cartafol / Directorio | |
| Backup (noun) | Copia de seguridade | |
| Backup (verb) | Facer copia de seguridade | |
| Encryption | Cifrado | Never `Cifraxe` |
| Deduplicated | Deduplicado | Never `Desduplicado` |
| Prune | Poda / Podar | Noun / verb |
| Mount / Unmount | Montar / Desmontar | 3-way distinction with Unlink and Detach |
| Unlink | Desvincular | 3-way distinction: Unmount (`Desmontar`) / Unlink (`Desvincular`) / Detach (`Separar`) |
| Detach | Separar | 3-way distinction: Unmount (`Desmontar`) / Unlink (`Desvincular`) / Detach (`Separar`) |
| Extract | Extraer | |
| Password / Passphrase | Contrasinal / Frase de paso | |
| Keyring | Chaveiro | Never `anel de chaves` |
| Keychain / Password manager | Chaveiro do sistema / Xestor de contrasinais | |
| System tray | Bandexa do sistema | |
| Full Disk Access | Acceso total ao disco | |
| Profile | Perfil | |
| Schedule / Scheduled | Planeamento / Planeada | Align with `Planeamento`; never `Programada` / `programacións` |
| Source | Orixe | |
| Exclude | Excluír | |
| Toggle | Alternar | |
| Settings (tab) | Axustes | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Rexistros | Link form: `rexistros` |
| Compact / Compaction | Compactar / Compactación | Distinct from Compression (`Compresión`) |
| Pattern | Patrón | Plural: `Patróns` |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Backup | Copia de seguridade | Established term across `vorta.gl.ts` |
| 2026-04-19 | Prune | Poda / Podar | Matches existing `ArchiveTab` Galician translations |
| 2026-04-19 | Schedule | Planeamento | Matches existing `MainWindow` and `ScheduleTab` in `vorta.gl.ts` |
| 2026-04-19 | Settings vs Misc | Axustes | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Compactar / Compactación | Distinct from data compression (`Compresión`) |
| 2026-11-24 | Encryption | Cifrado | Standard RAG Galician term; avoids `Cifraxe` |
| 2026-11-24 | Deduplicated | Deduplicado | Consistent with `BorgJob` and technical usage; avoids `Desduplicado` |
| 2026-11-24 | File vs Archive | Ficheiro / Arquivo | Keeps filesystem files clearly distinct from Borg archives |
| 2026-11-24 | Folder / Directory | Cartafol / Directorio | Consistent UI/filesystem terminology |
| 2026-11-24 | Keyring | Chaveiro | Aligns with `Chaveiro do sistema`; avoids `anel de chaves` |
| 2026-11-24 | Scheduled | Planeada | Aligns with `Planeamento`; avoids `Programada` / `programacións` |
| 2026-11-24 | Unmount / Unlink / Detach | Desmontar / Desvincular / Separar | Clear 3-way distinction across archive mounting and repository detachment |
| 2026-11-24 | Full Disk Access | Acceso total ao disco | Consistent macOS permission label across `VortaApp` and `settings` |
| 2026-11-24 | Toggle | Alternar | Accurate verb for toggling exclusion items; avoids ambiguous `Cambiar` |
