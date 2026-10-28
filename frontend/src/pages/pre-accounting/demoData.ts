/**
 * DEMO / PROVISIONAL ONLY
 *
 * This configuration demonstrates UI flow before authoritative source catalogs,
 * master-data activation, and Rule Profiles are available. It MUST NOT be used
 * for accounting validation or handoff.
 */

export type SourceMode = 'unique-code' | 'controlled';

export interface DemoSourceSubsystem {
  id: string;
  title: string;
  sourceLabel: string;
}

export interface DemoDimension {
  id: string;
  label: string;
  placeholder: string;
}

export interface DemoCostCenter {
  id: string;
  title: string;
  serviceDomain: string;
  dimensions: DemoDimension[];
}

export const DEMO_SOURCE_SUBSYSTEMS: readonly DemoSourceSubsystem[] = [
  { id: 'revenue', title: 'درآمد و وصول عوارض', sourceLabel: 'سامانه درآمد' },
  { id: 'treasury', title: 'خزانه‌داری و پرداخت', sourceLabel: 'سامانه خزانه' },
  { id: 'payroll', title: 'حقوق و مزایا', sourceLabel: 'سامانه حقوق' },
  { id: 'assets', title: 'اموال و انبار', sourceLabel: 'سامانه اموال' },
  { id: 'contracts', title: 'قراردادها', sourceLabel: 'سامانه قراردادها' },
  { id: 'civil', title: 'عملیات عمرانی', sourceLabel: 'سامانه عمران' },
  { id: 'urbanism', title: 'شهرسازی و معماری', sourceLabel: 'سامانه شهرسازی' },
  { id: 'transport', title: 'حمل‌ونقل و ترافیک', sourceLabel: 'سامانه ترافیک' },
  { id: 'services', title: 'خدمات شهری', sourceLabel: 'سامانه خدمات شهری' },
  { id: 'parks', title: 'فضای سبز', sourceLabel: 'سامانه فضای سبز' },
  { id: 'projects', title: 'مدیریت پروژه‌ها', sourceLabel: 'سامانه کنترل پروژه' },
  { id: 'planning', title: 'برنامه‌ریزی و بودجه', sourceLabel: 'سامانه بودجه' },
  { id: 'insurance', title: 'بیمه و کسورات', sourceLabel: 'سامانه بیمه' },
  { id: 'accounting', title: 'حسابداری تعهدی', sourceLabel: 'سامانه حسابداری' },
] as const;

export const DEMO_COST_CENTERS: readonly DemoCostCenter[] = [
  {
    id: 'CC-502',
    title: 'بهسازی، روکش و لکه‌گیری آسفالت معابر',
    serviceDomain: 'عمران، معابر و ابنیه فنی شهری',
    dimensions: [
      { id: 'project', label: 'پروژه / مسیر', placeholder: 'مثلاً روکش بلوار …' },
      { id: 'contract', label: 'شماره قرارداد', placeholder: 'مثلاً ۱۴۰۵/ع/۱۲' },
    ],
  },
  {
    id: 'CC-503',
    title: 'احداث و بهسازی پیاده‌روها و مسیرهای پیاده',
    serviceDomain: 'عمران، معابر و ابنیه فنی شهری',
    dimensions: [
      { id: 'project', label: 'پروژه / محور', placeholder: 'مثلاً پیاده‌راه محله …' },
      { id: 'district', label: 'منطقه', placeholder: 'مثلاً منطقه ۱۴' },
    ],
  },
  {
    id: 'CC-504',
    title: 'مناسب‌سازی فضاهای شهری برای توان‌خواهان و معلولین',
    serviceDomain: 'عمران، معابر و ابنیه فنی شهری',
    dimensions: [
      { id: 'project', label: 'پروژه مناسب‌سازی', placeholder: 'مثلاً رمپ و خط بساوایی …' },
      { id: 'district', label: 'منطقه', placeholder: 'مثلاً منطقه ۱۴' },
    ],
  },
  {
    id: 'CC-505',
    title: 'احداث و نگهداری پل‌های سواره‌رو، تقاطع‌های غیرهمسطح و تونل‌ها',
    serviceDomain: 'عمران، معابر و ابنیه فنی شهری',
    dimensions: [
      { id: 'asset', label: 'شناسه ابنیه فنی', placeholder: 'مثلاً پل …' },
      { id: 'project', label: 'پروژه', placeholder: 'مثلاً تقاطع …' },
    ],
  },
  {
    id: 'CC-506',
    title: 'مدیریت و نظارت بر حفاری‌ها و تأسیسات شهری',
    serviceDomain: 'عمران، معابر و ابنیه فنی شهری',
    dimensions: [
      { id: 'permit', label: 'شماره مجوز حفاری', placeholder: 'مثلاً ح-۱۴۰۵-…' },
      { id: 'utility', label: 'دستگاه خدمات‌رسان', placeholder: 'مثلاً آب و فاضلاب' },
    ],
  },
] as const;

export const DEMO_AI_SUGGESTION = {
  event: 'صورت‌وضعیت موقت عملیات آسفالت',
  confidence: '۸۴٪',
  evidence: 'شرح منبع و الگوی تاریخی مشابه',
} as const;

export const DEMO_IMMUTABLE_PROVENANCE = {
  uniqueCode: '۱۴۰۵-۱۴-۰۲-۴۷۱-۰۰۰۲۳۱',
  sourceReference: 'SV-۱۴۰۵-۰۰۸۷',
  receivedAt: '۱۴۰۵/۰۶/۳۱، ۱۰:۴۲',
  sourcePayload: 'صورت‌وضعیت موقت / روکش آسفالت بلوار فرهنگ',
} as const;
