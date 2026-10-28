# تیکت‌های لایهٔ کنترل رویداد مالی

مرجع طراحی: `docs/financial-event-control-layer.md` و ADRهای `0001` تا `0027`.

| تیکت | وضعیت | blocker |
|---|---|---|
| [001](001-evidence-discovery-and-derived-workbook.md) | در حال اجرا | — |
| [002](002-versioned-pre-accounting-control-module.md) | در حال اجرا | — |
| [003](003-rtl-pre-accounting-package-ui.md) | در حال اجرا | — |
| [004](004-authoritative-table-import-and-profile-release.md) | مسدود | جدول آقای خداپرست + 002 |
| [005](005-end-to-end-qa-and-accounting-inbox-contract.md) | آماده پس از 001–003 | 001، 002، 003 |

تیکت 004 هیچ master-data یا رابطهٔ production را تا دریافت و تأیید منبع مرجع فعال نمی‌کند.
