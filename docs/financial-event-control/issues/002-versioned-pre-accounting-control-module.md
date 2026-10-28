# 002 — ماژول نسخه‌دار کنترل پیش‌حسابداری

**Blocker:** ندارد

ماژول عمیق و configuration-driven برای Catalog/Crosswalk، Rule Profile Release، Package/Revision/Line/Snapshot، Source Reference، Override، Attachment Rule، Validation و Exception پیاده‌سازی کن. validation server-side باید precedence ADR-25، صفر ریال ADR-26، workflow ADR-17 و عدم handoff provisional را enforce کند. journal posting و masterهای فعلی تغییر نمی‌کنند.

**پذیرش:** migration، schema/router، testهای meaningful و مسیر inbox بدون posting وجود دارد؛ Rule Profile غیرauthoritative نمی‌تواند handoff نهایی بسازد؛ payload خام تغییرناپذیر است.
