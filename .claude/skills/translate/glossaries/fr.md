# French (fr) Translation Glossary

Agreed-upon translations and style rules for the Vorta project. These terms and rules are **mandatory** — use them consistently in all French translations.

## Register & Style Rules

- **Register & verb forms:** Use formal **"vous"** (`Veuillez`, `Votre`) with the imperative (`Saisissez`, `Utilisez-la`) for direct user prompts, and the **infinitive** (`Stocker`, `Ajouter`, `Enregistrer`, `Révéler`) for action labels, tooltips, and settings checkboxes.
- **Punctuation spacing:** Always place a non-breaking space (`\u00a0`) before `:`, `?`, `!`, and `;` everywhere in French prose and UI labels (never omit the space or use a regular ASCII space; exclude URLs, CLI/code tokens, `{now:...}`, and `;;` file-dialog filters).
- **Capitalization:** Use French **sentence case** for buttons, menus, tabs, dialog titles, labels, and parenthetical qualifiers (`Renommer le profil`, `Zstandard niveau 3 (moderne)`). Never copy English Title Case.
- **Accented capitals:** Always keep accents on uppercase letters (`Échec`, `Élaguer`, `À propos`, `Êtes-vous`).
- **Quotation marks:** Use French guillemets with non-breaking spaces (`«\u00a0…\u00a0»`) in prose. Keep ASCII double quotes (`"..."`) inside shell `echo` command examples.
- **Ellipsis:** Always use the Unicode ellipsis character `…` (U+2026) whenever `<source>` uses `…` (never ASCII `...`).
- **Pronoun hyphenation:** Always hyphenate inverted subject pronouns and post-verbal imperative pronouns (`Êtes-vous`, `Utilisez-la`, `doit-il`).
- **Gender:** Use the standard masculine generic consistently (e.g., `Êtes-vous sûr` — avoid mixing inclusive-writing forms like `sûr·e` with `sûr`).

## Terminology

| English | French | Notes |
|---------|--------|-------|
| Repository | Dépôt | |
| Archive | Archive | |
| Backup (noun) | Sauvegarde | |
| Backup (verb) | Sauvegarder | |
| Save | Enregistrer | Never `Sauvegarder` or `Sauver` |
| Quit | Quitter | Never `Fermer` |
| Prune | Élaguer | |
| Mount / Unmount | Monter / Démonter | |
| Extract | Extraire | |
| Password | Mot de passe | Distinct from `Passphrase` |
| Passphrase | Phrase secrète | Distinct from `Password`; never `phrase de passe` |
| Keychain | Trousseau de clés du système | |
| Password manager | Gestionnaire de mots de passe | Always plural `mots` |
| Key | Clé | Never `clef` |
| Clipboard | Presse-papiers | Always plural `papiers` |
| System tray | Zone de notification | |
| Profile | Profil | |
| Schedule | Planification | |
| Source | Source | |
| Exclude | Exclure | |
| Settings (tab) | Paramètres | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Journaux | Link form: `journaux` |
| Compact / Compaction | Compacter / Compactage | Distinct from Compression (`Compression`) |
| Metered network / connection | Réseau limité / Connexion limitée | Never `réseau mesuré` |
| Break lock | Forcer le déverrouillage | Never `Cassage du verrou` |
| Bug | Bogue | |
| Shell Commands | Commandes shell | |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Repository | Dépôt | Standard French BorgBackup term used throughout `vorta.fr.ts` |
| 2026-04-19 | Prune | Élaguer | Matches existing `ArchiveTab` French strings |
| 2026-04-19 | System tray | Zone de notification | Standard French desktop environment term in `vorta.fr.ts` |
| 2026-04-19 | Settings vs Misc | Paramètres | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Compacter / Compactage | Avoids collision with data compression (`Compresser` / `Compression`) |
| 2026-11-24 | Passphrase vs Password | Phrase secrète / Mot de passe | Standardizes terminology across dialogs and messages; forbids anglicism `phrase de passe` |
| 2026-11-24 | Password manager | Gestionnaire de mots de passe | Enforces standard French plural `mots` |
| 2026-11-24 | Save | Enregistrer | Avoids ambiguity with Backup (`Sauvegarder`) and informal `Sauver` |
| 2026-11-24 | Quit | Quitter | Standard French application exit label (distinct from `Fermer` for windows) |
| 2026-11-24 | Key | Clé | Modern standard French orthography; forbids archaic `clef` |
| 2026-11-24 | Clipboard | Presse-papiers | Standard French invariable plural spelling |
| 2026-11-24 | Metered network / connection | Réseau limité / Connexion limitée | Idiomatic French networking term; avoids literal calque `réseau mesuré` |
| 2026-11-24 | Break lock | Forcer le déverrouillage | Idiomatic French action phrase; avoids literal calque `Cassage du verrou` |
| 2026-11-24 | Bug | Bogue | Standard French software localization term |
| 2026-11-24 | Shell Commands | Commandes shell | Consistent French UI label keeping technical term `shell` lowercase |
