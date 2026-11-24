# Italian (it) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Italian translations.

## Register

Use informal 2nd person singular **"tu"** / imperative (`Inserisci`, `Seleziona`, `Mostra`, `Avvia`, `Memorizza`) consistently for prompts, action labels, and settings checkboxes throughout the catalog.

## Style Rules

- **Capitalization:** Use sentence case for buttons, menu items, tabs, column headers, dialog titles, and labels (e.g. `Aggiungi repository`, `Genera chiave SSH`, `Seleziona la destinazione di backup`). Use lowercase inside parenthetical qualifiers (e.g. `(consigliata)`, `(predefinita)`, `(obsoleta)`).
- **Progress and status messages:** Use impersonal nominal phrasing (`… in corso…`, `Avvio di…`, `Backup non eseguito…`, `Salvataggio della password…`). Never use 1st-person progressive (`Sto + gerundio`) and never use imperative/infinitive commands (`Non eseguire…`, `Salvare…`) for status messages.
- **Grammatical gender of Repository:** Always masculine (`il repository`, `un repository`, `del repository`); never feminine or abbreviated (`la repo`).
- **Proper nouns:** Always capitalize `Borg` in prose, even when `<source>` writes lowercase `borg`.
- **Ellipsis:** Use the Unicode ellipsis `…` (U+2026) whenever `<source>` uses `…` (never ASCII `...`).
- **No stray English words:** Always translate `Key` (`Chiave`), `Default` (`Predefinito/a`), `Level` (`Livello`), and `kill signal` (`segnale di terminazione`).

## Terminology

| English | Italian | Notes |
|---------|---------|-------|
| Repository | Repository | Keep English; always masculine (`il repository`, never `la repo`) |
| Archive | Archivio | |
| Backup (noun) | Backup | Keep English |
| Backup (verb) | Eseguire il backup | |
| Prune | Pulisci / Pulizia | Verb / noun |
| Mount / Unmount | Monta / Smonta | Filesystem mount/unmount (distinct from Unlink and Detach) |
| Unlink | Scollega | Remove repository from Vorta (distinct from Unmount and Detach) |
| Detach | Dissocia | Detach repository from current profile while keeping it for other profiles |
| Extract | Estrai | |
| Encryption | Cifratura | Consistent across all UI labels and messages (not `Crittografia`) |
| Consistency | Coerenza | Never `consistenza` |
| Diff | Differenze / Confronta | Noun / verb |
| Password / Passphrase | Password / Frase segreta | Never leave `passphrase` untranslated |
| Key | Chiave | Never leave `Key` untranslated (e.g. `Chiave SSH`) |
| Default | Predefinito / Predefinita | Never leave `default` untranslated |
| Level | Livello | Never leave `Level` untranslated (e.g. `livello 3`) |
| Keychain / Password manager | Portachiavi di sistema / Gestore delle password | |
| System tray | Area di notifica | Always `Area di notifica` |
| Profile | Profilo | |
| Schedule | Pianificazione | |
| Source | Fonte / Fonti | Matches live catalog (`Fonti`, `Aggiungi fonti`, etc.) |
| Exclude | Escludi | |
| Settings (tab) | Impostazioni | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Log | Link form: `log`; use `Registrazione` only for the `Logging` activity |
| Compact / Compaction | Compatta / Compattazione | Distinct from Compression (`Compressione`) |
| Trigger | Avvio | Not `Innesco` |
| Balance | Bilancio | Net size delta in diff view (not `Saldo`) |
| Task | Operazione | |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Repository & Backup | Repository / Backup | Kept in English throughout existing `vorta.it.ts` |
| 2026-04-19 | Prune | Pulisci / Pulizia | Matches existing `ArchiveTab` Italian translations |
| 2026-04-19 | Schedule | Pianificazione | Matches existing `MainWindow` and `ScheduleTab` in `vorta.it.ts` |
| 2026-04-19 | Settings vs Misc | Impostazioni | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Compatta / Compattazione | Distinct from data compression (`Compressione`) |
| 2026-11-12 | Settings checkboxes register | 2nd person singular imperative (`Mostra`, `Memorizza`, `Abilita`) | Matches 100% of existing checkboxes across `settings`, `SchedulePage`, `NetworksPage`, and `VortaFileDialog` |
| 2026-11-24 | Source | Fonte / Fonti | Resolved conflict with live catalog (`Fonti` tab, `Aggiungi fonti`, `Rimuovi la fonte selezionata`) |
| 2026-11-24 | Logs vs Logging | `Log` / `Registrazione` | `Log` for log entries/files (`Visualizza i log`, `i log`); `Registrazione` reserved for the `Logging` activity |
| 2026-11-24 | System tray | Area di notifica | Standardized across `settings` without English fallback |
| 2026-11-24 | Encryption | Cifratura | Standardized on `Cifratura` across all labels and messages instead of mixing `Cifratura` and `Crittografia` |
| 2026-11-24 | Consistency | Coerenza | Standard Italian technical term; avoids false friend `consistenza` |
| 2026-11-24 | Unmount / Unlink / Detach | Smonta / Scollega / Dissocia | Clear 3-way distinction between filesystem unmount, repo unlink, and profile detach |
| 2026-11-24 | Diff | Differenze / Confronta | Idiomatic Italian for archive comparison |
| 2026-11-24 | Key / Default / Level | Chiave / Predefinito(a) / Livello | Eliminates stray untranslated English words in Italian UI strings |
| 2026-11-24 | Trigger | Avvio | Natural UI column header instead of literal `Innesco` |
| 2026-11-24 | Balance | Bilancio | Size difference/net change in `DiffTree`, avoiding financial term `Saldo` |
| 2026-11-24 | Task | Operazione | Matches `Operazione avviata`, `Operazione annullata`, `Operazione in corso`, `Operazione non riuscita` |
