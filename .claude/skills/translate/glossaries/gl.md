# Galician (gl) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Galician translations.

## Register

Use formal **"vostede"** (`Introduza`, `Escolla`, `Engada`, `súa`) consistently throughout all translations.

## Terminology

| English | Galician | Notes |
|---------|----------|-------|
| Repository | Repositorio | |
| Archive | Arquivo | |
| Backup (noun) | Copia de seguridade | |
| Backup (verb) | Facer copia de seguridade | |
| Prune | Poda / Podar | Noun / verb |
| Mount / Unmount | Montar / Desmontar | |
| Extract | Extraer | |
| Password / Passphrase | Contrasinal / Frase de paso | |
| Keychain / Password manager | Chaveiro do sistema / Xestor de contrasinais | |
| System tray | Bandexa do sistema | |
| Profile | Perfil | |
| Schedule | Planeamento | |
| Source | Orixe | |
| Exclude | Excluír | |
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
