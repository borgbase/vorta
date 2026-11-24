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
| Keychain / Password manager | سلسلة مفاتيح النظام / مدير كلمات المرور | |
| System tray | علبة النظام | |
| Profile | ملف تعريف | |
| Schedule | جدولة | |
| Source | المصدر | |
| Exclude | استبعاد | |
| Settings (tab) | الإعدادات | UI label is "Settings / About"; code uses "misc" internally |
| Logs | السجلات | |
| Compact / Compaction | تحرير المساحة / تحرير المساحة غير المستخدمة | Reclaims unused repository space; distinct from Compression (`ضغط`) and merging (`دمج`) |

## Decision Log

| Date | Term | Decision | Rationale |
|------|------|----------|-----------|
| 2026-04-19 | Repository | مستودع | Matches established usage across existing Arabic catalog |
| 2026-04-19 | Prune | تقليم | Consistent with existing `ArchiveTab` Arabic strings |
| 2026-11-12 | Mount / Unmount | ضمّ / إلغاء الضمّ | Matches `نقطة الضمّ` (Mount Point) and avoids confusion with `تحميل` (download/load) |
| 2026-04-19 | Settings vs Misc | الإعدادات | Matches UI tab label rather than code-internal name |
| 2026-11-12 | Compact / Compaction | تحرير المساحة / تحرير المساحة غير المستخدمة | Communicates freeing unused repository segment space rather than merging (`دمج`) or compression (`ضغط`) |
