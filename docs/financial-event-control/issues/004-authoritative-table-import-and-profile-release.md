# 004 — import جدول مرجع و انتشار Rule Profile

**Blocker:** دریافت جدول آقای خداپرست و تکمیل 002

adapter/importer نسخه‌دار برای جدول مرجع بساز؛ source rows، validation errors، authority/status و profile releases را نگه دار. رابطهٔ Event–Cost Center، ابعاد، cardinality و مدارک فقط پس از publish مجاز فعال می‌شوند. absence با prohibition یکی نیست.

**پذیرش:** import هیچ رابطه‌ای را بدون release فعال نمی‌کند؛ profile release اتمیک است؛ هر Line نسخهٔ catalog/profile را حفظ می‌کند؛ promotion/rejection audit دارد.
