---
status: accepted
---

# revision و lineage Package

Package ID در revisionها ثابت است و هر Package Revision یک Revision ID یکتا و immutable دارد. Classification Line بین شناسهٔ منطقی پایدار و snapshot revision-specific immutable تفکیک می‌کند؛ Line ادامه‌یافته Logical Classification Line ID خود را نگه می‌دارد اما در هر revision snapshot جدید دارد، و split/merge Line شناسه‌های منطقی جدید با رابطهٔ lineage صریح به predecessorها می‌سازد. snapshot handoffشده هرگز با اصلاحات بعدی بازنویسی نمی‌شود.
