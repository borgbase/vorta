# French (fr) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all French translations.

## Register

Use formal **"vous"** (`Veuillez`, `Votre`) for user prompts and infinitive (`Stocker`, `Ajouter`) for settings checkboxes and action labels. Preserve French spacing before `:` where established or standard French punctuation applies.

## Terminology

| English | French | Notes |
|---------|--------|-------|
| Repository | Dépôt | |
| Archive | Archive | |
| Backup (noun) | Sauvegarde | |
| Backup (verb) | Sauvegarder | |
| Prune | Élaguer | |
| Mount / Unmount | Monter / Démonter | |
| Extract | Extraire | |
| Password / Passphrase | Mot de passe / Phrase secrète | Or `Mot de passe` where already established |
| Keychain / Password manager | Trousseau de clés du système / Gestionnaire de mots de passe | |
| System tray | Zone de notification | |
| Profile | Profil | |
| Schedule | Planification | |
| Source | Source | |
| Exclude | Exclure | |
| Settings (tab) | Paramètres | UI label is "Settings / About"; code uses "misc" internally |
| Logs | Journaux | Link form: `journaux` |
| Compact / Compaction | Compacter / Compactage | Distinct from Compression (`Compression`) |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Repository | Dépôt | Standard French BorgBackup term used throughout `vorta.fr.ts` |
| 2026-04-19 | Prune | Élaguer | Matches existing `ArchiveTab` French strings |
| 2026-04-19 | System tray | Zone de notification | Standard French desktop environment term in `vorta.fr.ts` |
| 2026-04-19 | Settings vs Misc | Paramètres | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | Compacter / Compactage | Avoids collision with data compression (`Compresser` / `Compression`) |
