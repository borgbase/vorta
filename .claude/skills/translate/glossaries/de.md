# German (de) Translation Glossary

Agreed-upon translations and style rules for the Vorta project. These terms and rules are **mandatory** — use them consistently in all German translations.

## Register

Use informal **"du"** (lowercase) consistently throughout all translations. Do not use formal "Sie/Ihr/Ihnen".

## German Style Rules

- **Capitalization:** Use sentence case with standard German noun capitalization. Never copy English Title Case into buttons, tabs, headers, or dialog titles. Keep parenthetical qualifiers lowercase when they are adjectives/participles — `(empfohlen)`, `(veraltet)`, `(automatisch, veraltet)` — and capitalize them when they are nouns — `(Standard)`, `(Standardeinstellung)`.
- **Compounds & Durchkopplung (Duden):**
  - Write native German compounds closed without unnecessary hyphens: `Schlüsselformat`, `Schlüssellänge`, `Ausgabedatei`, `Schlüsseldatei`, `Vorabversionen`, `Exportdatei`.
  - Write separate verb phrases according to Duden: `neu berechnen` (not `neuberechnen`), `mit einbeziehen` (not `miteinbeziehen`).
  - Use hyphens (Durchkopplung) for compounds with English loanwords, abbreviations, or proper nouns: `Repository-Daten`, `Repository-URL`, `Repository-Ordner`, `Vorta-Version`, `Borg-Version`, `Borg-Passwort`, `SSH-Schlüssel`, `Shell-Befehle`, `Schema-Upgrade-Fehler`, `Profil-Exportdatei`, `profile_export-Exportdatei`.
- **Repository inflection (Duden):** Always use `Repository` (singular), `Repositorys` (genitive singular and plural). Never abbreviate to `Repo` and never use English plural `Repositories`.
- **Quotation marks:** Use German typographic quotes `„…“` in prose and UI strings. Exception: keep ASCII double quotes `"..."` inside literal shell command examples (e.g. `echo "..."`) so shell syntax and variable expansion remain valid.
- **Ellipsis:** Always use the Unicode ellipsis `…` (U+2026) on dialog-opening actions and progress messages, never three ASCII periods `...` (except when `<source>` is a literal `...` browse button label).
- **Verb forms:** Use the infinitive for buttons, menu items, checkboxes, and settings labels (e.g. `Beim Start auf Updates prüfen`, `Nicht mehr anzeigen`, `Ausschlussmuster hinzufügen`). Use the `du`-imperative for direct dialog prompts and instructions (e.g. `Bitte gib eine gültige Repository-URL oder einen lokalen Pfad an.`).
- **Abbreviations & spacing:** Use a space in German abbreviations such as `z. B.`. Keep proper nouns in canonical casing (`GitHub`, `Borg`, `Vorta`, `macFUSE`, `ZStd`).

## Terminology

| English | German | Notes |
|---------|--------|-------|
| Password / Passphrase | Passwort | Use consistently; avoid "Kennwort" |
| Password manager / Keychain | Schlüsselbund | Use for both concepts |
| System keychain | Schlüsselbund des Systems | |
| System tray | System-Tray | English loan word with hyphen; avoid "Infobereich" |
| Repository | Repository | Keep English; plural/genitive `Repositorys` (never `Repo` or `Repositories`) |
| Repository URL | Repository-URL | Never `Repository-Adresse` or `Repo-Adresse` |
| Archive | Archiv | |
| Backup (noun) | Backup | Keep English; avoid "Datensicherung" |
| Backup (verb) | sichern | German verb form |
| Prune | Ausdünnen | |
| Mount | Einhängen | Avoid "einbinden" |
| Extract | Extrahieren | Avoid "Entpacken" |
| Compression | Kompression | Avoid "Komprimierung" (adjective/participle `komprimiert` / `Komprimierte Größe` is fine) |
| Profile | Profil | |
| Schedule | Zeitplan | |
| Source | Quelle | Avoid "Datenquelle" or "Ausgangs-" |
| Exclude | Ausschließen | |
| Pattern | Muster | Avoid "Schema" (`Ausschlussmuster`, not `Ausschlussschema`) |
| Shell Commands | Shell-Befehle | Avoid "Shell-Kommandos" |
| Tab | Reiter | Avoid "Tab" |
| Updates | Updates | Use consistently; avoid mixing with "Aktualisierungen" |
| Full Disk Access | Festplattenvollzugriff | Official macOS German term; avoid "vollständiger Festplattenzugriff" / "Vollzugriff auf die Festplatte" |
| Return code / Exit code | Rückgabecode | Avoid "Return Code" / "Return-Code" |
| Settings (tab) | Einstellungen | UI label is "Settings / About"; code uses "misc" internally — always match UI |
| Logs | Protokolle | Link form in dative (`in den %1`): `Protokollen` |
| Compact / Compaction | Optimieren / Optimierung | Distinct from Compression (`Kompression`) |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-02-06 | Passwort vs Kennwort | Passwort | Matches existing majority usage in file; more commonly understood |
| 2026-02-06 | System-Tray vs Infobereich | System-Tray | Widely understood German tech term; "Infobereich" is uncommon |
| 2026-02-06 | Schlüsselbund vs Passwortmanager/Kennwortverwaltung | Schlüsselbund | OS-neutral term for keychain/password manager; already used in existing translations |
| 2026-02-06 | Backup vs Datensicherung | Backup | Shorter, more international; consistent with English loan word conventions |
| 2026-02-06 | Einstellungen vs Verschiedenes | Einstellungen | UI tab is labeled "Settings / About", not "Misc"; previous "Verschiedenes" was a literal translation of the code-internal name |
| 2026-11-12 | Compact / Compaction | Optimieren / Optimierung | Consistent across ArchiveTab, SchedulePage, and BorgCompactJob; distinct from `Kompression` |
| 2026-11-24 | Extract: Extrahieren vs Entpacken | Extrahieren | Consistent across `ExtractDialog`, `ArchiveTab`, and `ArchiveExtract`; Borg archives are extracted rather than unpacked |
| 2026-11-24 | Mount: Einhängen vs einbinden | Einhängen | Standard German filesystem term; matches `Einhängepunkt` and `Aushängen` |
| 2026-11-24 | Compression: Kompression vs Komprimierung | Kompression | Matches `Kompression:` and `Keine Kompression` in `RepoTab` |
| 2026-11-24 | Shell Commands: Shell-Befehle vs Shell-Kommandos | Shell-Befehle | Matches `ShellCommandsPage` and `Befehl vor dem Backup` |
| 2026-11-24 | Tab: Reiter vs Tab | Reiter | Consistent German UI terminology across dialogs and help texts |
| 2026-11-24 | Updates: Updates vs Aktualisierungen | Updates | Matches the `Updates` settings section and Sparkle update descriptions |
| 2026-11-24 | Full Disk Access | Festplattenvollzugriff | Official macOS German system setting label; avoids inconsistent paraphrases |
| 2026-11-24 | Pattern: Muster vs Schema | Muster | Consistent across `ExcludeDialog` help texts and labels |
| 2026-11-24 | Return code / Exit code | Rückgabecode | Native German term replacing mixed English `Return Code` / `Return-Code` |
| 2026-11-24 | Repository URL | Repository-URL | Consistent with `AddRepository` and avoids `Repository-Adresse` / `Repo-Adresse` |
