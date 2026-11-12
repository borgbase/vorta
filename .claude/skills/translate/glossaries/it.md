# Italian (it) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Italian translations.

## Register

Use informal 2nd person singular **"tu"** / imperative (`Inserisci`, `Seleziona`, `Mostra`, `Avvia`, `Memorizza`) consistently for prompts, action labels, and settings checkboxes throughout the catalog.

## Terminology

| English | Italian | Notes |
|---------|---------|-------|
| Repository | Repository | Keep English |
| Archive | Archivio | |
| Backup (noun) | Backup | Keep English |
| Backup (verb) | Eseguire il backup | |
| Prune | Pulisci / Pulizia | Verb / noun |
| Mount / Unmount | Monta / Smonta | |
| Extract | Estrai | |
| Password / Passphrase | Password / Frase segreta | |
| Keychain / Password manager | Portachiavi di sistema / Gestore delle password | |
| System tray | Area di notifica | Or `System tray` where already used |
| Profile | Profilo | |
| Schedule | Pianificazione | |
| Source | Sorgente | |
| Exclude | Escludi | |
| Settings (tab) | Impostazioni | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Log / Registri | Link form: `log` |
| Compact / Compaction | Compatta / Compattazione | Distinct from Compression (`Compressione`) |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Repository & Backup | Repository / Backup | Kept in English throughout existing `vorta.it.ts` |
| 2026-04-19 | Prune | Pulisci / Pulizia | Matches existing `ArchiveTab` Italian translations |
| 2026-04-19 | Schedule | Pianificazione | Matches existing `MainWindow` and `ScheduleTab` in `vorta.it.ts` |
| 2026-04-19 | Settings vs Misc | Impostazioni | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Compatta / Compattazione | Distinct from data compression (`Compressione`) |
| 2026-11-12 | Settings checkboxes register | 2nd person singular imperative (`Mostra`, `Memorizza`, `Abilita`) | Matches 100% of existing checkboxes across `settings`, `SchedulePage`, `NetworksPage`, and `VortaFileDialog` |
