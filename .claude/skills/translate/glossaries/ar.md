# Arabic (ar) Translation Glossary

Agreed-upon translations for the Vorta project. These terms are **mandatory** — use them consistently in all Arabic translations.

## Register

Use Modern Standard Arabic imperative/second-person (`أدخل`, `أكّد`, `حدد`) consistently throughout all translations, and use standard indefinite defective participle `جارٍ` (never `جاري`) for ongoing status messages. Arabic is right-to-left (RTL); keep English proper nouns (`Vorta`, `Borg`, `BorgBackup`, `Git`, `SSH`), placeholders, and shell variables intact in Latin script.

## Terminology

| English | Arabic | Notes |
|---------|--------|-------|
| Repository | مستودع | |
| Archive | أرشيف | Plural: `أرشيفات` |
| Backup (noun) | نسخة احتياطية / النسخ الاحتياطي | Context-dependent (single backup vs. process) |
| Backup (verb) | نسخ احتياطي | |
| Prune | تقليم | |
| Mount / Unmount | ضمّ / إلغاء الضمّ | Consistent with `نقطة الضمّ` (Mount Point); avoid `تحميل` (download/load) |
| Extract | استخراج | |
| Password / Passphrase | كلمة المرور / عبارة المرور | |
| Keychain / Keyring / Password manager | سلسلة مفاتيح النظام / سلسلة المفاتيح / مدير كلمات المرور | Forbid `حلقة المفاتيح` for Keyring |
| System tray | علبة النظام | |
| Profile | ملف تعريف | Plural: `ملفات التعريف` (forbid `ملف شخصي` and `ملفات التعريفات`) |
| Schedule | جدولة | |
| Source | المصدر | |
| Exclude | استبعاد | |
| Settings (tab) | الإعدادات | UI label is "Settings / About"; code uses "misc" internally |
| Logs | السجلات | |
| Compact / Compaction | تحرير المساحة / تحرير المساحة غير المستخدمة | Reclaims unused repository space; distinct from Compression (`ضغط`) and merging (`دمج`) |
| Deduplicated | دون تكرار | Forbid `مكررة` / `المكرر` (which mean "duplicated") |
| Pre-backup / Post-backup | ما قبل النسخ الاحتياطي / ما بعد النسخ الاحتياطي | Forbid `النسخ الاحتياطي المسبق` |
| Arguments (CLI) | وسيطات | Forbid `الحجج` |
| Validation / Check | التحقق من الصحة / فحص | Forbid `تصديق` |
| Directory / Folder | دليل / مجلد | Keep distinct; forbid `مسار` for Directory |
| Unlink / Detach / Unmount | إلغاء الربط / فصل / إلغاء الضمّ | Keep all three distinct: `Unlink` = `إلغاء الربط`, `Detach` = `فصل`, `Unmount` = `إلغاء الضمّ` (avoid `إلغاء التحميل`) |
| Notifications | إشعارات | Forbid `إخطارات` |
| Recommended | موصى به | Forbid `مستحسن` |
| Shell | شل | Use Arabic transliteration consistently in prose and UI labels |
| Diff | الفروق | |
| Block / Character device / special file | ملف جهاز كتلي / محرفي (ملف كتلي / محرفي خاص) | Forbid verb `حظر` (mistranslation of "block") |
| Trigger | المُحفّز / سبب التشغيل | Forbid `مشغل` |

## Arabic Style Rules

- **Verbal nouns vs. imperative:** Use verbal nouns (`مصدر`) for buttons, menu items, and action labels (e.g., `حفظ`, `إلغاء`, `نسخ احتياطي الآن`, `استخراج`), and use the imperative (`فعل الأمر`) for direct user prompts and instructions (e.g., `أدخل عبارة المرور`, `نفّذ نسخة احتياطية يدوية أولاً`, `اختر الملفات لاستخراجها`).
- **`الـ` definiteness consistency:** Keep definiteness consistent across sibling items in lists, table headers, and form labels (e.g., indefinite nouns for file types: `ملف`, `دليل`, `رابط`).
- **Digits:** Always use Western Arabic digits (`0–9`), never Eastern Arabic-Indic digits (`٠–٩`).
- **Punctuation:** Use Arabic punctuation (`،`, `؟`) in prose, but preserve ASCII syntax tokens (`;;`, `"..."`, `,`, `;`) inside `QFileDialog` filters, CLI/shell examples, and code literals.
- **Orthography (tanwīn & defective nouns):** Place tanwīn al-fatḥ consistently on the letter before the alif (`تلقائيًا`, `يدويًا`, `مسبقًا`, `فارغًا`), and use standard indefinite defective noun forms with tanwīn al-kasr (`جارٍ`, `عالٍ`) instead of `جاري` / `عالي`.
- **Spacing with Latin & colons:** Insert a space after Arabic single-letter prefixes (`لـ`) before Latin tokens (`لـ Ed25519`, `لـ Borg`). Never place a space before a colon (`مفتاح SSH:`).
- **Qt 6-form plural slot order (`numerus="yes"`):** Provide all 6 `<numerusform>` elements in exact Qt Arabic order: `[0]` `n == 0`, `[1]` `n == 1`, `[2]` `n == 2`, `[3]` `3–10`, `[4]` `11–99`, `[5]` `100+`.

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Repository | مستودع | Matches established usage across existing Arabic catalog |
| 2026-04-19 | Prune | تقليم | Consistent with existing `ArchiveTab` Arabic strings |
| 2026-11-12 | Mount / Unmount | ضمّ / إلغاء الضمّ | Matches `نقطة الضمّ` (Mount Point) and avoids confusion with `تحميل` (download/load) |
| 2026-04-19 | Settings vs Misc | الإعدادات | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | تحرير المساحة / تحرير المساحة غير المستخدمة | Communicates freeing unused repository segment space rather than merging (`دمج`) or compression (`ضغط`) |
| 2026-11-24 | Deduplicated | دون تكرار | Avoids `مكررة` / `المكرر` which mean the opposite ("duplicated") |
| 2026-11-24 | Profile (plural) | ملفات التعريف | Consistent with singular `ملف تعريف`; forbids `ملف شخصي` and ungrammatical `ملفات التعريفات` |
| 2026-11-24 | Pre-backup / Post-backup | ما قبل النسخ الاحتياطي / ما بعد النسخ الاحتياطي | Accurate temporal phrasing; avoids misleading `النسخ الاحتياطي المسبق` |
| 2026-11-24 | Arguments (CLI) | وسيطات | Standard Arabic computing term; avoids literal mistranslation `الحجج` |
| 2026-11-24 | Validation / Check | التحقق من الصحة / فحص | Standard technical terms; avoids `تصديق` (authentication/attestation) |
| 2026-11-24 | Directory vs Folder | دليل / مجلد | Distinguishes filesystem `Directory` from UI `Folder`; avoids `مسار` (Path) |
| 2026-11-24 | Unlink / Detach / Unmount | إلغاء الربط / فصل / إلغاء الضمّ | Keeps the three distinct repository/archive operations unambiguous |
| 2026-11-24 | Keyring | سلسلة المفاتيح | Consistent with `سلسلة مفاتيح النظام`; avoids literal `حلقة المفاتيح` |
| 2026-11-24 | Notifications | إشعارات | Standard modern Arabic UI term; avoids `إخطارات` |
| 2026-11-24 | Recommended | موصى به | Consistent across dialogs; avoids `مستحسن` |
| 2026-11-24 | Shell | شل | Standard Arabic transliteration matching `أوامر شل` |
| 2026-11-24 | Diff | الفروق | Consistent across `Diff` buttons and dialog headers |
| 2026-11-24 | Block/Character device/special file | ملف جهاز كتلي/محرفي (ملف كتلي/محرفي خاص) | Standard Unix terminology; avoids mistranslating "Block" as verb `حظر` |
| 2026-11-24 | Trigger | المُحفّز / سبب التشغيل | Avoids `مشغل` (player/operator) |
