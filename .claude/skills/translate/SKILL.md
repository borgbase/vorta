---
name: translate
description: Manage Vorta translations using AI. Commands - /translate missing (report status), /translate translate <lang> (generate translations), /translate review <lang> (quality check), /translate compile (build .qm files).
---

# Vorta Translation Skill

Manage translations for the Vorta backup application. This skill replaces the previous Transifex-based workflow with AI-powered translations.

## Commands

### `/translate missing`
Report the count of untranslated strings for each language.

### `/translate translate <lang>`
Generate translations for untranslated strings in a specific language (e.g., `de`, `es`, `fr`).

### `/translate review <lang>`
Review existing translations for quality, consistency, and glossary compliance. Does not generate new translations.

### `/translate compile`
Compile all .ts files to binary .qm format.

---

## File Locations

- **Source .ts files:** `src/vorta/i18n/ts/vorta.<lang>.ts`
- **Compiled .qm files:** `src/vorta/i18n/qm/vorta.<lang>.qm`

## Supported Languages

| Code | Language |
|------|----------|
| ar | Arabic (RTL) |
| cs | Czech |
| de | German |
| es | Spanish |
| fi | Finnish |
| fr | French |
| gl | Galician |
| it | Italian |
| nl | Dutch |
| ru | Russian |
| sk | Slovak |
| sv | Swedish |

---

## Command: `/translate missing`

1. Read each .ts file in `src/vorta/i18n/ts/`
2. Count strings with `<translation type="unfinished"/>` (untranslated)
3. Count total `<message>` elements
4. Display a summary table:

```
Language    Untranslated    Total    Completion
de          12              450      97.3%
es          45              450      90.0%
...
```

---

## Command: `/translate translate <lang>`

Generate translations for a specific language.

### Step 1: Parse the .ts file

Read `src/vorta/i18n/ts/vorta.<lang>.ts` and identify:
- Untranslated strings: `<translation type="unfinished"/>`
- Existing translations for context

### Step 2: Load glossary and scan for consistency

**2a. Load glossary:** Read `.claude/skills/translate/glossaries/<lang>.md` if it exists. All terms in the glossary are mandatory — use them consistently.

**2b. Scan existing translations:** Before translating new strings, grep for key domain terms in already-translated strings to identify established conventions. Flag any conflicts with the glossary (e.g., a glossary says "Passwort" but existing translations use "Kennwort").

**2c. Resolve unknown terms:** If a source string contains a term not covered by the glossary, and the term is ambiguous or has multiple valid translations, ask the user which translation to use (via `AskUserQuestion`). Add the decision to the glossary file and its Decision Log.

### Step 3: Understand the .ts file format

```xml
<context>
    <name>AddProfileWindow</name>          <!-- UI component name -->
    <message>
        <location filename="views/profile.py" line="25"/>  <!-- Source location -->
        <source>Save</source>              <!-- English text to translate -->
        <translation>Speichern</translation>  <!-- Translated text -->
    </message>
</context>
```

**Special case - comment-based strings:**
```xml
<message>
    <source>messages</source>
    <comment>Please unlock your system password manager</comment>  <!-- THIS is the text to translate -->
    <translation type="unfinished"/>
</message>
```
When `<source>` is `messages`, `settings`, or `app`, the actual translatable text is in `<comment>`.

### Step 4: Generate translations with context

For each untranslated string, consider:

1. **UI Context** (`<name>` element):
   - `RepoTab`, `ArchiveTab`, `SourceTab` = main tabs
   - `AddRepoWindow`, `AddProfileWindow` = dialog windows
   - `MainWindow` = main application window

2. **Source Location** (`<location>` element):
   - Files in `views/` = UI text
   - Files in `borg/` = backup operation messages
   - Files in `store/` = settings descriptions

3. **Application Domain:**
   - Vorta is a backup GUI for BorgBackup
   - Key terms: repository, archive, backup, prune, mount, extract, passphrase

4. **Style Guide:**
   - **Buttons:** Title Case in English (Save, Cancel, Add Repository)
   - **Labels with colons:** Keep the colon (Repository:, Password:)
   - **Menu items:** Title Case
   - **Descriptions/tooltips:** Sentence case
   - **Technical terms:** Keep English for: Borg, BorgBackup, SSH, repository (or use locale-appropriate term)
   - **Placeholders:** Preserve `{variable}` and `%s` patterns exactly

### Step 5: Terminology check

Before writing translations, cross-check all generated translations against the glossary. Verify that no inconsistent terms slipped through (e.g., using "Kennwort" when the glossary specifies "Passwort"). Fix any violations before proceeding.

### Step 6: Update the .ts file

Replace `<translation type="unfinished"/>` with `<translation>Translated text</translation>`

**Important XML rules:**
- Preserve exact XML structure and indentation
- Escape XML entities: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`
- Preserve newlines in multi-line strings
- Keep `type="unfinished"` attribute only for strings you cannot confidently translate

### Step 7: Show summary

After making changes, display:
- Number of strings translated
- Any strings skipped (with reasons)
- Suggest running `/translate compile` to build .qm files

---

## Command: `/translate review <lang>`

Review existing translations for quality and consistency without generating new translations. This command performs a quality assurance pass over already-translated strings.

### Step 1: Parse the .ts file

Read `src/vorta/i18n/ts/vorta.<lang>.ts` and collect all existing translations (excluding `type="unfinished"` entries).

### Step 2: Load glossary

Read `.claude/skills/translate/glossaries/<lang>.md` if it exists. The glossary contains mandatory terminology that must be used consistently.

### Step 3: Quality checks

Perform the following checks on existing translations:

**3a. Glossary compliance:**
- For each term in the glossary, search all translated strings
- Flag any translation that uses a different term than specified in the glossary
- Example: If glossary says "Passwort" but translation uses "Kennwort", flag it

**3b. Consistency check:**
- Identify the same English source string appearing in multiple contexts
- Verify all instances have identical translations
- Flag inconsistencies

**3c. Style compliance:**
- Check button text follows Title Case conventions (if applicable to the language)
- Verify labels with colons in English preserve colons in translation
- Ensure placeholders (`{0}`, `%s`, `%d`) are preserved unchanged
- Check that proper nouns (Borg, BorgBackup, Vorta, SSH) remain untranslated

**3d. Technical validation:**
- Verify XML entities are properly escaped (`&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`)
- Check for mismatched quotes or brackets
- Ensure keyboard shortcuts (e.g., `&File`) are preserved

### Step 4: Report findings

Display a summary report:
```
Translation Review: German (de)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Total translations reviewed: 416

Issues found:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠ Glossary violations (3):
  - Line 145: Uses "Kennwort" instead of "Passwort"
  - Line 289: Uses "Sichern" instead of "Speichern"
  - Line 412: Uses "Repo" instead of "Repository"

⚠ Inconsistencies (2):
  - "Cancel" translated as both "Abbrechen" and "Beenden"
  - "Settings" translated as both "Einstellungen" and "Konfiguration"

⚠ Style issues (1):
  - Line 234: Missing colon in "Repository" (should be "Repository:")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Recommendation: Fix the 6 issues above before release.
```

### Step 5: Optional fixes

If issues are found, offer to fix them automatically:
- Ask user: "Would you like me to fix these issues automatically?"
- If yes, update the .ts file to correct the flagged problems
- If no, just provide the report

---

## Command: `/translate compile`

Compile .ts source files to binary .qm format:

```bash
make translations-to-qm
```

Or manually:
```bash
for f in src/vorta/i18n/ts/vorta.*.ts; do
    lrelease "$f" -qm "src/vorta/i18n/qm/$(basename "$f" .ts).qm"
done
```

---

## Translation Quality Guidelines

### DO:
- Maintain consistency with existing translations in the same file
- Use formal/informal tone based on the target language's conventions
- Preserve keyboard shortcuts (e.g., "&File" where & indicates Alt+F)
- Keep URLs unchanged
- Preserve formatting placeholders (`{0}`, `%s`, `%d`, etc.)

### DON'T:
- Translate proper nouns: Borg, BorgBackup, Vorta, SSH, URL
- Change technical identifiers or paths
- Add or remove punctuation unnecessarily
- Translate placeholder text that's clearly an example (e.g., email@example.com)
- Translate based on code-internal names instead of actual UI labels (e.g., code says "Misc" but UI shows "Settings / About" — translate as "Settings")

### RTL Languages (Arabic):
- Text direction is handled by Qt automatically
- Ensure no hardcoded LTR punctuation breaks the flow
- Test UI layout after translation

---

## Testing Translations

After updating translations:

1. Compile: `make translations-to-qm`
2. Run the app: `uv run vorta`
3. Go to **Settings** tab → **Language** dropdown
4. Select the language and restart the app
5. Verify translations appear correctly in the UI

---

## Workflow Example

```bash
# 1. Check translation status
/translate missing

# 2. Generate missing German translations
/translate translate de

# 3. Review translation quality
/translate review de

# 4. Compile translations
/translate compile

# 5. Test in app
uv run vorta
```

---

## Glossary of Common Terms

Maintain consistency with these translations:

| English | Context | Notes |
|---------|---------|-------|
| Repository | Borg repo | Often kept as "Repository" in many languages |
| Archive | Backup snapshot | Time-based backup point |
| Backup | Action/noun | The backup operation |
| Prune | Delete old archives | Technical term |
| Mount | Make archive browsable | Filesystem operation |
| Extract | Restore files | Copy files from archive |
| Passphrase | Password to unlock the borg key | Security credential |
| Profile | Backup configuration | Group of settings |
| Schedule | Backup timing | When to run backups |
| Source | Files to back up | Folders/files to include |
| Exclude | Files to skip | Patterns to ignore |

## Per-Language Glossaries

Per-language glossaries live in `.claude/skills/translate/glossaries/<lang>.md`. These document agreed-upon translations for domain-specific and ambiguous terms. The terms in a glossary are **mandatory** — they must be used consistently in all translations for that language.

Each glossary contains:
- A **Terminology** table mapping English terms to the agreed translation
- A **Decision Log** recording when and why each term was chosen

Create a new glossary when a language is first reviewed. Update it whenever a new term decision is made.

---

## Adding a New Language

1. Copy an existing .ts file as template:
   ```bash
   cp src/vorta/i18n/ts/vorta.de.ts src/vorta/i18n/ts/vorta.XX.ts
   ```

2. Update the language attribute in the new file:
   ```xml
   <TS version="2.1" language="XX">
   ```

3. Clear all translations (set to `type="unfinished"`)

4. Run `/translate translate XX` to generate translations

5. Run `/translate review XX` to check quality

6. Compile with `/translate compile`

7. Test in the application
