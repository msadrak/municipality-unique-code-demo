import React, { useMemo, useState } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  Bot,
  Check,
  CheckCircle2,
  FolderOpen,
  Info,
  Landmark,
  Link2,
  ListChecks,
  Loader2,
  LockKeyhole,
  Paperclip,
  PencilLine,
  Plus,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Upload,
  UserCheck,
  X,
} from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Checkbox } from '../../components/ui/checkbox';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { Textarea } from '../../components/ui/textarea';
import { cn } from '../../components/ui/utils';
import {
  DEMO_AI_SUGGESTION,
  DEMO_COST_CENTERS,
  DEMO_IMMUTABLE_PROVENANCE,
  DEMO_SOURCE_SUBSYSTEMS,
  type SourceMode,
} from './demoData';

type DemoViewState = 'ready' | 'loading' | 'error';

type ClassificationLine = {
  id: string;
  costCenterId: string;
  attribution: 'unallocated' | 'source-backed';
  dimensions: Record<string, string>;
};

type DocumentChecks = {
  source: boolean;
  contract: boolean;
  technical: boolean;
};

const STEPS = [
  'زیرسامانه مبدأ',
  'زمینه عملیاتی',
  'پیشنهاد رویداد',
  'سطرهای طبقه‌بندی',
  'مستندات',
  'بازبینی منشأ',
  'ارجاع حسابداری',
] as const;

const INITIAL_LINE: ClassificationLine = {
  id: 'LINE-DEMO-001',
  costCenterId: 'CC-502',
  attribution: 'source-backed',
  dimensions: { project: 'روکش بلوار فرهنگ', contract: '۱۴۰۵/ع/۱۲' },
};

const INITIAL_DOCUMENTS: DocumentChecks = {
  source: true,
  contract: true,
  technical: false,
};

const cardClass = 'border-slate-200 bg-white shadow-[0_2px_7px_rgba(15,23,42,0.04)]';

function StepMarker({ index, active, complete }: { index: number; active: boolean; complete: boolean }) {
  return (
    <span
      className={cn(
        'grid h-7 w-7 shrink-0 place-items-center rounded-md border text-xs font-bold',
        complete && 'border-teal-600 bg-teal-600 text-white',
        active && !complete && 'border-amber-400 bg-amber-50 text-amber-800',
        !active && !complete && 'border-slate-200 bg-slate-50 text-slate-500',
      )}
    >
      {complete ? <Check className="h-4 w-4" /> : index + 1}
    </span>
  );
}

function SectionHeader({
  number,
  title,
  caption,
  state,
}: {
  number: number;
  title: string;
  caption: string;
  state?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 px-5 py-4">
      <div className="flex items-start gap-3">
        <span className="grid h-7 w-7 place-items-center rounded-md bg-slate-900 text-xs font-bold text-white">
          {number}
        </span>
        <div>
          <h2 className="text-sm font-bold text-slate-950">{title}</h2>
          <p className="mt-1 text-xs leading-5 text-slate-500">{caption}</p>
        </div>
      </div>
      {state}
    </div>
  );
}

function StatePanel({ viewState, retry }: { viewState: DemoViewState; retry: () => void }) {
  if (viewState === 'loading') {
    return (
      <div className="flex min-h-[28rem] flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-slate-300 bg-white text-center">
        <Loader2 className="h-8 w-8 animate-spin text-teal-700" />
        <div>
          <p className="font-bold text-slate-900">در حال آماده‌سازی بستهٔ دمو</p>
          <p className="mt-1 text-sm text-slate-500">منبع محلیِ آزمایشی در حال بارگذاری است.</p>
        </div>
      </div>
    );
  }

  if (viewState === 'error') {
    return (
      <Alert variant="destructive" className="min-h-44 border-red-200 bg-red-50 p-6">
        <AlertCircle />
        <AlertTitle>نمونهٔ وضعیت خطا: بارگذاری دادهٔ دمو انجام نشد</AlertTitle>
        <AlertDescription>
          این صفحه برای نمایش حالت خطا است؛ هیچ داده‌ای به‌عنوان واقعیت مرجع یا نتیجهٔ حسابداری ثبت نشده است.
          <Button variant="outline" size="sm" className="mt-4 border-red-200 bg-white text-red-700" onClick={retry}>
            <RotateCcw /> تلاش مجدد
          </Button>
        </AlertDescription>
      </Alert>
    );
  }

  return null;
}

export function PreAccountingPackagePage() {
  const [viewState, setViewState] = useState<DemoViewState>('ready');
  const [sourceMode, setSourceMode] = useState<SourceMode>('unique-code');
  const [sourceSubsystemId, setSourceSubsystemId] = useState('civil');
  const [context, setContext] = useState('صورت‌وضعیت موقت روکش آسفالت بلوار فرهنگ؛ منطقه ۱۴');
  const [suggestionSelected, setSuggestionSelected] = useState(true);
  const [reviewerAdopted, setReviewerAdopted] = useState(false);
  const [lines, setLines] = useState<ClassificationLine[]>([INITIAL_LINE]);
  const [documents, setDocuments] = useState<DocumentChecks>(INITIAL_DOCUMENTS);
  const [uploadName, setUploadName] = useState('');
  const [missingReferenceReason, setMissingReferenceReason] = useState('');
  const [overrideRequested, setOverrideRequested] = useState(false);

  const sourceSubsystem = DEMO_SOURCE_SUBSYSTEMS.find((source) => source.id === sourceSubsystemId);
  const selectedCostCenters = useMemo(
    () => lines.map((line) => DEMO_COST_CENTERS.find((center) => center.id === line.costCenterId)).filter(Boolean),
    [lines],
  );
  const currentStep = reviewerAdopted ? 3 : suggestionSelected ? 2 : sourceSubsystem ? 1 : 0;
  const documentsReady = documents.source && (documents.contract || Boolean(missingReferenceReason));

  const resetDemo = () => {
    setSourceMode('unique-code');
    setSourceSubsystemId('');
    setContext('');
    setSuggestionSelected(false);
    setReviewerAdopted(false);
    setLines([]);
    setDocuments({ source: false, contract: false, technical: false });
    setUploadName('');
    setMissingReferenceReason('');
    setOverrideRequested(false);
    setViewState('ready');
  };

  const updateLine = (lineId: string, patch: Partial<ClassificationLine>) => {
    setLines((previous) => previous.map((line) => (line.id === lineId ? { ...line, ...patch } : line)));
  };

  const updateDimension = (lineId: string, dimension: string, value: string) => {
    setLines((previous) => previous.map((line) => (
      line.id === lineId ? { ...line, dimensions: { ...line.dimensions, [dimension]: value } } : line
    )));
  };

  const addLine = () => {
    const firstCenter = DEMO_COST_CENTERS[0];
    setLines((previous) => [
      ...previous,
      {
        id: `LINE-DEMO-${String(previous.length + 1).padStart(3, '0')}`,
        costCenterId: firstCenter.id,
        attribution: 'unallocated',
        dimensions: {},
      },
    ]);
  };

  return (
    <div className="mx-auto max-w-[1560px] space-y-5 pb-10 text-right text-slate-900" dir="rtl">
      <header className="border-b-2 border-slate-900 pb-4">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="border-amber-300 bg-amber-50 text-amber-900">
                <Sparkles className="h-3.5 w-3.5" /> دمو / موقت
              </Badge>
              <span className="text-xs font-medium text-slate-500">بستهٔ نمونه: PKG-DEMO-001 · هویت داخلی غیرمعنایی</span>
            </div>
            <h1 className="text-xl font-extrabold tracking-tight text-slate-950 sm:text-2xl">دروازهٔ کنترل پیش‌حسابداری</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              بسته، فراداده و مستندات مشترک را نگه می‌دارد؛ طبقه‌بندی مالی در سطرهای مستقل انجام می‌شود.
              این محیط فقط جریان بازبینی را نمایش می‌دهد و مرجع یا تأیید حسابداری نیست.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => setViewState('loading')}>
              <Loader2 /> حالت بارگذاری
            </Button>
            <Button variant="outline" size="sm" onClick={() => setViewState('error')}>
              <AlertCircle /> حالت خطا
            </Button>
            <Button variant="outline" size="sm" onClick={resetDemo}>
              <RotateCcw /> شروع بستهٔ خالی
            </Button>
          </div>
        </div>
      </header>

      <Alert className="border-amber-300 bg-amber-50/80">
        <ShieldAlert className="text-amber-700" />
        <AlertTitle className="text-amber-950">کنترل موقت، نه مجوز کسب‌وکاری</AlertTitle>
        <AlertDescription className="text-amber-900/80">
          کاتالوگ دمو، مراکز پیشنهادی و پیشنهاد AI/history authoritative نیستند. تا Rule Profile منتشرشده، master فعال،
          اسناد و اعتبارسنجی سطرها موجود نباشد، ارجاع حسابداری مسدود است.
        </AlertDescription>
      </Alert>

      {viewState !== 'ready' ? <StatePanel viewState={viewState} retry={() => setViewState('ready')} /> : (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
          <main className="space-y-5">
            <nav aria-label="مراحل بستهٔ پیش‌حسابداری" className="overflow-x-auto border-y border-slate-200 bg-slate-50 px-3 py-3">
              <ol className="flex min-w-[790px] items-start justify-between gap-2">
                {STEPS.map((step, index) => (
                  <li key={step} className="flex min-w-24 flex-1 items-center gap-2">
                    <StepMarker index={index} active={index <= currentStep} complete={index < currentStep} />
                    <span className={cn('text-xs leading-5', index <= currentStep ? 'font-bold text-slate-900' : 'text-slate-500')}>{step}</span>
                  </li>
                ))}
              </ol>
            </nav>

            <section className={cn('overflow-hidden rounded-lg border', cardClass)} aria-labelledby="source-heading">
              <SectionHeader
                number={1}
                title="زیرسامانهٔ مبدأ"
                caption="هر بسته دقیقاً یک کانال ورود دارد؛ زیرسامانهٔ مبدأ با حوزهٔ خدمت مرکز هزینه یکسان نیست."
                state={sourceSubsystem ? <Badge className="bg-teal-700 text-white">انتخاب شده</Badge> : <Badge variant="outline">انتخاب نشده</Badge>}
              />
              <div className="grid gap-4 p-5 md:grid-cols-[minmax(0,1fr)_300px]">
                <div className="space-y-2">
                  <Label htmlFor="source-subsystem">انتخاب زیرسامانهٔ مبدأ (۱۴ مورد دمو)</Label>
                  <Select value={sourceSubsystemId} onValueChange={setSourceSubsystemId}>
                    <SelectTrigger id="source-subsystem" className="w-full border-slate-300">
                      <SelectValue placeholder="یک زیرسامانهٔ مبدأ انتخاب کنید" />
                    </SelectTrigger>
                    <SelectContent>
                      {DEMO_SOURCE_SUBSYSTEMS.map((source) => (
                        <SelectItem key={source.id} value={source.id}>{source.title}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="border-r-2 border-teal-600 bg-teal-50 px-4 py-3 text-sm text-teal-950">
                  <span className="text-xs font-bold text-teal-800">منشأ انتخاب‌شده</span>
                  <p className="mt-1 font-bold">{sourceSubsystem?.sourceLabel ?? '—'}</p>
                  <p className="mt-1 text-xs leading-5 text-teal-800">فقط برای نمایش دادهٔ مبدأ در این دمو؛ وضعیت فعال‌بودن بررسی نشده است.</p>
                </div>
              </div>
            </section>

            <section className={cn('overflow-hidden rounded-lg border', cardClass)} aria-labelledby="context-heading">
              <SectionHeader number={2} title="زمینهٔ عملیاتی" caption="زمینه، شاهد بازبینی است؛ پیش از Rule Profile، فرم هیچ بُعدی را الزامی یا ممنوع فرض نمی‌کند." />
              <div className="space-y-4 p-5">
                <div className="grid grid-cols-2 gap-2 sm:max-w-md">
                  <Button
                    type="button"
                    variant={sourceMode === 'unique-code' ? 'default' : 'outline'}
                    className={cn('justify-between', sourceMode === 'unique-code' && 'bg-slate-900 hover:bg-slate-800')}
                    onClick={() => setSourceMode('unique-code')}
                  >
                    <LockKeyhole /> دریافت از کد یکتا
                  </Button>
                  <Button
                    type="button"
                    variant={sourceMode === 'controlled' ? 'default' : 'outline'}
                    className={cn('justify-between', sourceMode === 'controlled' && 'bg-slate-900 hover:bg-slate-800')}
                    onClick={() => setSourceMode('controlled')}
                  >
                    <PencilLine /> ورود کنترل‌شده
                  </Button>
                </div>

                {sourceMode === 'unique-code' ? (
                  <div className="grid gap-3 border border-teal-200 bg-teal-50/70 p-4 lg:grid-cols-[1fr_auto]">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <ProvenanceField label="کد یکتا (مرجع مبدأ)" value={DEMO_IMMUTABLE_PROVENANCE.uniqueCode} />
                      <ProvenanceField label="ارجاع مبدأ" value={DEMO_IMMUTABLE_PROVENANCE.sourceReference} />
                      <ProvenanceField label="زمان دریافت" value={DEMO_IMMUTABLE_PROVENANCE.receivedAt} />
                      <ProvenanceField label="payload خام" value={DEMO_IMMUTABLE_PROVENANCE.sourcePayload} />
                    </div>
                    <div className="flex min-w-44 flex-col justify-between gap-3 border-t border-teal-200 pt-3 lg:border-r lg:border-t-0 lg:pr-4 lg:pt-0">
                      <p className="text-xs leading-5 text-teal-900">کد یکتا هویت Package یا Line نیست و payload بالادستی تغییرناپذیر باقی می‌ماند.</p>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className={cn('border-teal-300 bg-white text-teal-900', overrideRequested && 'border-amber-400 bg-amber-50 text-amber-900')}
                        onClick={() => setOverrideRequested((requested) => !requested)}
                      >
                        <PencilLine /> {overrideRequested ? 'درخواست override ثبت شد' : 'درخواست override'}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="grid gap-4 border border-slate-200 bg-slate-50 p-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="controlled-reference">مرجع مبدأ</Label>
                      <Input id="controlled-reference" placeholder="شناسهٔ سند یا پرونده" value={DEMO_IMMUTABLE_PROVENANCE.sourceReference} readOnly />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="operational-context">شرح زمینهٔ عملیاتی</Label>
                      <Input id="operational-context" value={context} onChange={(event) => setContext(event.target.value)} placeholder="شرح کنترل‌شدهٔ عملیات" />
                    </div>
                    <p className="col-span-full text-xs leading-5 text-slate-500">ورود کنترل‌شده مقدار محلی موقت است؛ تغییر آن، تصحیح یا بازنویسی منبع بالادستی نیست.</p>
                  </div>
                )}
              </div>
            </section>

            <section className={cn('overflow-hidden rounded-lg border', cardClass)} aria-labelledby="suggestion-heading">
              <SectionHeader
                number={3}
                title="پیشنهاد رویداد مالی"
                caption="AI و تاریخچه فقط شاهد هستند. Initiator نمی‌تواند طبقه‌بندی موقت بسازد؛ پذیرش صریح بازبین لازم است."
                state={<Badge variant="outline" className="border-amber-300 bg-amber-50 text-amber-900">پیشنهادی / نیازمند بازبینی</Badge>}
              />
              <div className="grid gap-4 p-5 lg:grid-cols-[minmax(0,1fr)_280px]">
                <button
                  type="button"
                  aria-pressed={suggestionSelected}
                  onClick={() => { setSuggestionSelected((selected) => !selected); setReviewerAdopted(false); }}
                  className={cn(
                    'border p-4 text-right transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500',
                    suggestionSelected ? 'border-amber-400 bg-amber-50' : 'border-slate-200 bg-white hover:border-slate-400',
                  )}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex gap-3">
                      <Bot className="mt-0.5 h-5 w-5 text-amber-700" />
                      <div>
                        <p className="font-bold text-slate-950">{DEMO_AI_SUGGESTION.event}</p>
                        <p className="mt-1 text-xs text-slate-600">شاهد: {DEMO_AI_SUGGESTION.evidence}</p>
                      </div>
                    </div>
                    <Badge variant="outline" className="border-amber-300 bg-white text-amber-900">{DEMO_AI_SUGGESTION.confidence}</Badge>
                  </div>
                </button>
                <div className="border-r-2 border-amber-500 bg-amber-50/60 p-4">
                  <p className="text-xs font-bold text-amber-900">کنترل بازبین در حالت دمو</p>
                  <p className="mt-2 text-xs leading-5 text-amber-950">پذیرش، طبقه‌بندی را فقط موقت می‌کند و رابطهٔ مجاز یا Rule Profile ایجاد نمی‌کند.</p>
                  <Button
                    type="button"
                    size="sm"
                    disabled={!suggestionSelected}
                    onClick={() => setReviewerAdopted((adopted) => !adopted)}
                    className={cn('mt-4 w-full', reviewerAdopted ? 'bg-teal-700 hover:bg-teal-800' : 'bg-slate-900 hover:bg-slate-800')}
                  >
                    <UserCheck /> {reviewerAdopted ? 'پذیرفته‌شده توسط بازبین' : 'پذیرش صریح بازبین'}
                  </Button>
                </div>
              </div>
            </section>

            <section className={cn('overflow-hidden rounded-lg border', cardClass)} aria-labelledby="lines-heading">
              <SectionHeader
                number={4}
                title="سطرهای طبقه‌بندی"
                caption="هر سطر هویت داخلی مستقل دارد. مرکز پیشنهادی فقط در Draft / Review قابل انتخاب است و حوزهٔ خدمت از مرکز هزینه مشتق می‌شود."
                state={<Badge variant="outline" className="border-slate-300">{lines.length} سطر</Badge>}
              />
              <div className="space-y-4 p-5">
                {!sourceSubsystem ? (
                  <EmptyDependentState />
                ) : lines.length === 0 ? (
                  <div className="flex flex-col items-center justify-center border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
                    <ListChecks className="h-8 w-8 text-slate-400" />
                    <p className="mt-3 font-bold text-slate-800">سطر طبقه‌بندی ندارید</p>
                    <p className="mt-1 text-xs text-slate-500">پس از انتخاب زیرسامانه، یک یا چند سطر صریح اضافه کنید.</p>
                    <Button size="sm" className="mt-4 bg-slate-900 hover:bg-slate-800" onClick={addLine}><Plus /> افزودن سطر</Button>
                  </div>
                ) : lines.map((line, lineIndex) => {
                  const center = DEMO_COST_CENTERS.find((item) => item.id === line.costCenterId);
                  return (
                    <article key={line.id} className="border border-slate-200 bg-slate-50/70">
                      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 bg-white px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-slate-800">{line.id}</span>
                          <Badge variant="outline" className="border-amber-300 bg-amber-50 text-amber-900">موقت</Badge>
                        </div>
                        <Button variant="ghost" size="sm" disabled={lines.length === 1} onClick={() => setLines((previous) => previous.filter((item) => item.id !== line.id))}>
                          <X /> حذف سطر
                        </Button>
                      </div>
                      <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)_minmax(0,1fr)]">
                        <div className="space-y-2">
                          <Label htmlFor={`cost-center-${line.id}`}>مرکز هزینهٔ پیشنهادی</Label>
                          <Select value={line.costCenterId} onValueChange={(costCenterId) => updateLine(line.id, { costCenterId, dimensions: {} })}>
                            <SelectTrigger id={`cost-center-${line.id}`} className="w-full border-slate-300"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              {DEMO_COST_CENTERS.map((item) => <SelectItem key={item.id} value={item.id}>{item.id} — {item.title}</SelectItem>)}
                            </SelectContent>
                          </Select>
                          <p className="text-xs leading-5 text-slate-500">baseline دمو؛ این نمایش، active یا authoritative بودن را القا نمی‌کند.</p>
                        </div>
                        <div className="border-r-2 border-teal-600 bg-teal-50 px-3 py-2">
                          <span className="text-xs font-bold text-teal-800">حوزهٔ خدمت مشتق‌شده</span>
                          <p className="mt-1 text-sm font-bold text-teal-950">{center?.serviceDomain ?? '—'}</p>
                          <p className="mt-1 text-xs text-teal-800">از مرکز هزینهٔ این سطر؛ هرگز زیرسامانهٔ مبدأ نیست.</p>
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor={`attribution-${line.id}`}>وضعیت انتساب مبلغ</Label>
                          <Select value={line.attribution} onValueChange={(attribution) => {
                            if (attribution === 'source-backed' || attribution === 'unallocated') {
                              updateLine(line.id, { attribution });
                            }
                          }}>
                            <SelectTrigger id={`attribution-${line.id}`} className="w-full border-slate-300"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="source-backed">دارای پشتوانهٔ مبدأ</SelectItem>
                              <SelectItem value="unallocated">هنوز بدون انتساب مبلغ</SelectItem>
                            </SelectContent>
                          </Select>
                          <p className="text-xs text-slate-500">تقسیم یا تخصیص ضمنی انجام نمی‌شود.</p>
                        </div>
                      </div>
                      <div className="grid gap-3 border-t border-slate-200 p-4 md:grid-cols-2">
                        {center?.dimensions.map((dimension) => (
                          <div key={dimension.id} className="space-y-2">
                            <Label htmlFor={`${line.id}-${dimension.id}`}>{dimension.label} <span className="font-normal text-slate-400">(اختیاری)</span></Label>
                            <Input
                              id={`${line.id}-${dimension.id}`}
                              value={line.dimensions[dimension.id] ?? ''}
                              placeholder={dimension.placeholder}
                              onChange={(event) => updateDimension(line.id, dimension.id, event.target.value)}
                            />
                          </div>
                        ))}
                      </div>
                    </article>
                  );
                })}
                <Button variant="outline" size="sm" disabled={!sourceSubsystem} onClick={addLine}>
                  <Plus /> افزودن سطر طبقه‌بندی
                </Button>
              </div>
            </section>

            <section className={cn('overflow-hidden rounded-lg border', cardClass)} aria-labelledby="documents-heading">
              <SectionHeader number={5} title="مستندات و مرجع مبدأ" caption="قواعد الزامی و advisory جدا نمایش داده می‌شوند. مرجع مبدأ یا توجیه ساخت‌یافتهٔ فقدان آن لازم است." />
              <div className="grid gap-4 p-5 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="space-y-3">
                  <DocumentRequirement checked={documents.source} onCheckedChange={(checked) => setDocuments((previous) => ({ ...previous, source: checked }))} title="مرجع مبدأ" detail={DEMO_IMMUTABLE_PROVENANCE.sourceReference} mandatory />
                  <DocumentRequirement checked={documents.contract} onCheckedChange={(checked) => setDocuments((previous) => ({ ...previous, contract: checked }))} title="قرارداد یا توجیه فقدان مرجع" detail="برای این بستهٔ نمونه" mandatory />
                  <DocumentRequirement checked={documents.technical} onCheckedChange={(checked) => setDocuments((previous) => ({ ...previous, technical: checked }))} title="گزارش فنی ناظر" detail="راهنمایی برای بازبینی؛ الزام Rule Profile هنوز معلوم نیست" />
                </div>
                <div className="space-y-3 border border-dashed border-slate-300 bg-slate-50 p-4">
                  <div>
                    <p className="text-sm font-bold text-slate-900">پیوست محلی</p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">فقط نام فایل در مرورگر نگهداری می‌شود و به backend ارسال نمی‌شود.</p>
                  </div>
                  <Label htmlFor="document-upload" className="flex cursor-pointer items-center justify-center gap-2 border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:border-teal-600 hover:text-teal-800">
                    <Upload className="h-4 w-4" /> انتخاب فایل
                  </Label>
                  <Input id="document-upload" type="file" className="sr-only" onChange={(event) => setUploadName(event.target.files?.[0]?.name ?? '')} />
                  {uploadName ? <p className="flex items-center gap-2 text-xs text-teal-800"><Paperclip className="h-3.5 w-3.5" /> {uploadName}</p> : <p className="text-xs text-slate-500">فایلی انتخاب نشده است.</p>}
                </div>
                {!documents.contract && (
                  <div className="space-y-2 lg:col-span-2">
                    <Label htmlFor="missing-reference">توجیه ساخت‌یافتهٔ فقدان قرارداد <span className="text-red-700">(اجباری در نبود مرجع)</span></Label>
                    <Textarea id="missing-reference" value={missingReferenceReason} onChange={(event) => setMissingReferenceReason(event.target.value)} placeholder="علت، مسئول پیگیری و مرجع جایگزین را ثبت کنید…" />
                  </div>
                )}
              </div>
            </section>

            <section className={cn('overflow-hidden rounded-lg border', cardClass)} aria-labelledby="review-heading">
              <SectionHeader number={6} title="بازبینی منشأ و مسئولیت" caption="هر مقدار باید منشأ خود را نگه دارد؛ پیشنهاد AI هرگز به‌تنهایی منشأ authoritative نمی‌شود." />
              <div className="overflow-x-auto p-5">
                <table className="min-w-[720px] w-full border-collapse text-sm">
                  <thead className="bg-slate-900 text-right text-xs text-slate-100">
                    <tr><th className="px-3 py-3 font-medium">مقدار</th><th className="px-3 py-3 font-medium">مقدار مؤثر در دمو</th><th className="px-3 py-3 font-medium">منشأ</th><th className="px-3 py-3 font-medium">وضعیت</th></tr>
                  </thead>
                  <tbody>
                    <ReviewRow label="کد یکتا" value={DEMO_IMMUTABLE_PROVENANCE.uniqueCode} origin="مبدأ / payload تغییرناپذیر" state="مرجع مبدأ" />
                    <ReviewRow label="زیرسامانهٔ مبدأ" value={sourceSubsystem?.title ?? 'انتخاب نشده'} origin="کاربر / selector کنترل‌شده" state={sourceSubsystem ? 'ثبت‌شده در دمو' : 'ناقص'} alert={!sourceSubsystem} />
                    <ReviewRow label="رویداد مالی" value={suggestionSelected ? DEMO_AI_SUGGESTION.event : 'انتخاب نشده'} origin={reviewerAdopted ? 'پیشنهاد AI + اقدام صریح بازبین' : 'پیشنهاد AI/history'} state={reviewerAdopted ? 'موقت / بازبینی‌شده' : 'نیازمند بازبینی'} alert />
                    <ReviewRow label="مراکز هزینهٔ سطرها" value={selectedCostCenters.map((center) => center?.id).join('، ') || 'سطر ندارد'} origin="کاربر / مرکز پیشنهادی baseline" state="فقط Draft / Review" alert />
                    <ReviewRow label="مستندات" value={documentsReady ? 'مرجع یا توجیه ثبت شده' : 'ناقص'} origin={uploadName ? 'کاربر / پیوست محلی' : 'کاربر / checklist'} state={documentsReady ? 'آمادهٔ بازبینی' : 'مسدودکننده'} alert={!documentsReady} />
                  </tbody>
                </table>
              </div>
            </section>

            <section className="overflow-hidden rounded-lg border border-red-200 bg-red-50/50" aria-labelledby="handoff-heading">
              <SectionHeader number={7} title="ارجاع به حسابداری" caption="ارجاع یک انتقال versioned و قابل‌ممیزی به inbox است؛ ثبت خودکار journal در این جریان وجود ندارد." state={<Badge variant="outline" className="border-red-300 bg-red-50 text-red-800">مسدود</Badge>} />
              <div className="flex flex-col justify-between gap-4 p-5 md:flex-row md:items-center">
                <div className="flex items-start gap-3">
                  <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-red-700" />
                  <p className="max-w-3xl text-sm leading-6 text-red-950">Rule Profile authoritative و master/crosswalk فعال برای این دمو وجود ندارد؛ حتی با تکمیل سطرها و پیوست‌ها، handoff ممکن نیست.</p>
                </div>
                <Button disabled className="bg-slate-900"><Landmark /> ارجاع به کارتابل حسابداری <ArrowLeft /></Button>
              </div>
            </section>
          </main>

          <aside className="space-y-4 xl:sticky xl:top-4 xl:self-start" aria-label="ریل ممیزی بسته">
            <div className="border-t-4 border-slate-900 bg-slate-900 p-5 text-slate-50 shadow-[0_4px_12px_rgba(15,23,42,0.14)]">
              <div className="flex items-center gap-2 text-xs font-bold text-teal-300"><ClipboardCheck className="h-4 w-4" /> ریل ممیزی</div>
              <p className="mt-3 text-lg font-extrabold">PKG-DEMO-001</p>
              <p className="mt-1 text-xs leading-5 text-slate-300">شناسهٔ بسته غیرمعنایی است. Lineها نیز شناسهٔ مستقل دارند؛ کد یکتا فقط Source Reference است.</p>
              <div className="mt-4 border-t border-slate-700 pt-4 text-xs text-slate-300">
                <p>نسخهٔ نمایش: <span className="font-mono text-white">demo-0.1</span></p>
                <p className="mt-2">حالت: <span className="font-bold text-amber-300">موقت / غیرauthoritative</span></p>
              </div>
            </div>

            <div className={cn('border-t-4 border-teal-600 p-5', cardClass)}>
              <div className="flex items-center gap-2 text-sm font-bold text-slate-950"><Link2 className="h-4 w-4 text-teal-700" /> زنجیرهٔ منشأ</div>
              <ol className="mt-4 space-y-4 border-r border-slate-200 pr-4 text-xs">
                <AuditItem icon={LockKeyhole} title="payload مبدأ" description="کد یکتا و ارجاع بدون بازنویسی" tone="teal" />
                <AuditItem icon={Bot} title="AI / تاریخچه" description="شاهد رتبه‌بندی‌شده، فاقد authority" tone="amber" />
                <AuditItem icon={UserCheck} title="بازبین طبقه‌بندی" description={reviewerAdopted ? 'پذیرش صریحِ موقت ثبت شد' : 'هنوز پذیرش صریحی ثبت نشده'} tone={reviewerAdopted ? 'teal' : 'amber'} />
                <AuditItem icon={ShieldCheck} title="قواعد authoritative" description="برای دمو موجود نیست؛ handoff قفل است" tone="red" />
              </ol>
            </div>

            <div className={cn('p-5', cardClass)}>
              <p className="text-sm font-bold text-slate-950">کنترل‌های قابل مشاهده</p>
              <ul className="mt-3 space-y-3 text-xs leading-5 text-slate-600">
                <li className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" /> دادهٔ مبدأ، کاربر، بازبین و AI جداگانه ثبت می‌شوند.</li>
                <li className="flex gap-2"><Info className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" /> رابطهٔ مشاهده‌شده مجوز کسب‌وکاری نیست.</li>
                <li className="flex gap-2"><ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-red-700" /> هیچ posting خودکار journal ارائه نمی‌شود.</li>
              </ul>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}

function ProvenanceField({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-b border-teal-100 pb-2 last:border-b-0">
      <dt className="text-[11px] font-bold text-teal-800">{label}</dt>
      <dd className="mt-1 break-words font-mono text-xs text-teal-950">{value}</dd>
    </div>
  );
}

function EmptyDependentState() {
  return (
    <div className="flex flex-col items-center justify-center border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
      <FolderOpen className="h-8 w-8 text-slate-400" />
      <p className="mt-3 font-bold text-slate-800">انتخاب مرکز هزینه تا تعیین زیرسامانهٔ مبدأ غیرفعال است</p>
      <p className="mt-1 text-xs leading-5 text-slate-500">ابتدا یک زیرسامانهٔ مبدأ برای بسته انتخاب کنید؛ Service Domain از مرکز هزینهٔ سطر تعیین می‌شود.</p>
    </div>
  );
}

function DocumentRequirement({
  checked,
  onCheckedChange,
  title,
  detail,
  mandatory = false,
}: {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  title: string;
  detail: string;
  mandatory?: boolean;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-3 border border-slate-200 bg-white p-3 hover:border-slate-400">
      <Checkbox checked={checked} onCheckedChange={(value) => onCheckedChange(value === true)} className="mt-0.5" />
      <span>
        <span className="flex flex-wrap items-center gap-2 text-sm font-bold text-slate-900">{title}{mandatory ? <Badge variant="outline" className="border-red-200 bg-red-50 text-red-800">الزامی</Badge> : <Badge variant="outline" className="border-slate-200 text-slate-600">راهنمایی</Badge>}</span>
        <span className="mt-1 block text-xs leading-5 text-slate-500">{detail}</span>
      </span>
    </label>
  );
}

function ReviewRow({ label, value, origin, state, alert = false }: { label: string; value: string; origin: string; state: string; alert?: boolean }) {
  return (
    <tr className="border-b border-slate-200 last:border-0">
      <th scope="row" className="px-3 py-3 text-right text-xs font-bold text-slate-800">{label}</th>
      <td className="px-3 py-3 text-xs text-slate-700">{value}</td>
      <td className="px-3 py-3 text-xs text-slate-600">{origin}</td>
      <td className="px-3 py-3"><Badge variant="outline" className={cn(alert ? 'border-amber-300 bg-amber-50 text-amber-900' : 'border-teal-200 bg-teal-50 text-teal-800')}>{state}</Badge></td>
    </tr>
  );
}

function AuditItem({
  icon: Icon,
  title,
  description,
  tone,
}: {
  icon: typeof ShieldCheck;
  title: string;
  description: string;
  tone: 'teal' | 'amber' | 'red';
}) {
  const color = tone === 'teal' ? 'text-teal-700' : tone === 'amber' ? 'text-amber-700' : 'text-red-700';
  return (
    <li className="relative">
      <Icon className={cn('absolute -right-[1.55rem] top-0 h-4 w-4 rounded-full bg-white', color)} />
      <p className="font-bold text-slate-800">{title}</p>
      <p className="mt-1 leading-5 text-slate-500">{description}</p>
    </li>
  );
}

export default PreAccountingPackagePage;
