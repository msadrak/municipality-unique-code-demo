import React, { useEffect, useMemo, useState } from 'react';
import { AlertCircle, ArrowRight, CheckCircle2, Loader2, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { useNavigate, useParams } from 'react-router-dom';

import isfahanMunicipalityLogo from '../../assets/isfahan-municipality-logo.svg';
import {
  fetchFundingRequest,
  fetchFundingWorkflowHistory,
  FundingRequest,
  FundingWorkflowLog,
  transitionFundingRequest,
} from '../../services/funding';
import { useAuthStore } from '../../stores/useAuthStore';
import {
  canSeeFundingInbox,
  getFundingActions,
  getFundingStatusLabel,
  getRoleDisplayName,
} from './workflow';

const pageShellClass =
  'bg-white shadow-[0_25px_80px_-30px_rgba(15,23,42,0.35)] mx-auto aspect-[1/1.414] max-w-4xl p-8 sm:p-12 md:p-16 relative border border-slate-200 flex flex-col font-vazirmatn overflow-hidden';

const signedStatuses = new Set(['FINAL_APPROVED', 'CHARGING_IN_PROGRESS', 'COMPLETED']);

function formatAmount(value?: number | null) {
  if (typeof value !== 'number') return '---';
  return `${new Intl.NumberFormat('fa-IR').format(value)} ریال`;
}

function formatDateTime(value?: string | null) {
  if (!value) return '-';
  try {
    return new Intl.DateTimeFormat('fa-IR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function looksLikeHtml(value?: string | null) {
  return Boolean(value && /<\/?[a-z][\s\S]*>/i.test(value));
}

function getSignatureLog(history: FundingWorkflowLog[]) {
  const reversed = [...history].reverse();
  return (
    reversed.find((entry) => entry.to_status === 'FINAL_APPROVED') ||
    reversed.find((entry) => entry.to_status === 'COMPLETED')
  );
}

function getSignerLabel(entry?: FundingWorkflowLog) {
  if (!entry) return 'کاربر نامشخص';

  const roleLabel = entry.actor_role ? getRoleDisplayName(entry.actor_role) : '';
  const nameLabel = entry.actor_name?.trim() || '';

  if (roleLabel && nameLabel) {
    return `${roleLabel} - ${nameLabel}`;
  }
  return roleLabel || nameLabel || 'کاربر نامشخص';
}

function ReadOnlyLine({
  label,
  value,
  className = '',
}: {
  label: string;
  value?: string | null;
  className?: string;
}) {
  return (
    <div className={`flex items-baseline gap-2 ${className}`}>
      <span className="text-sm font-bold text-slate-700 min-w-[48px] shrink-0">{label}</span>
      <div className="w-full text-sm font-medium leading-relaxed text-slate-900 whitespace-pre-wrap">
        {value?.trim() || '---'}
      </div>
    </div>
  );
}

export function OfficialLetterViewer() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [letter, setLetter] = useState<FundingRequest | null>(null);
  const [history, setHistory] = useState<FundingWorkflowLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submittingAction, setSubmittingAction] = useState<string | null>(null);

  const requestId = Number(id);
  const backPath = canSeeFundingInbox(user?.role) ? '/hr/funding/inbox' : '/hr/funding/my-requests';

  const loadLetter = async () => {
    if (!requestId) {
      setError('شناسه نامه معتبر نیست.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const [requestData, historyData] = await Promise.all([
        fetchFundingRequest(requestId),
        fetchFundingWorkflowHistory(requestId),
      ]);
      setLetter(requestData);
      setHistory(historyData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'دریافت جزئیات نامه ناموفق بود.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadLetter();
  }, [requestId]);

  const availableActions = useMemo(
    () => (letter ? getFundingActions(user?.role, letter.status) : []),
    [letter, user?.role],
  );

  const approveAction = availableActions.find((action) => action.variant !== 'danger');
  const rejectAction = availableActions.find((action) => action.action === 'reject');
  const signatureLog = getSignatureLog(history);
  const isSigned = Boolean(letter && signedStatuses.has(letter.status));

  const handleTransition = async (action: string) => {
    if (!letter) return;

    setSubmittingAction(action);
    setError(null);
    try {
      const updated = await transitionFundingRequest(letter.id, {
        action,
        comment:
          action === 'reject'
            ? 'رد و بازگشت از روی نمایش نامه'
            : 'تایید و ارجاع از روی نمایش نامه',
      });
      setLetter(updated);
      setHistory(await fetchFundingWorkflowHistory(letter.id));
      toast.success('گردش کار نامه با موفقیت به‌روزرسانی شد.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'انجام عملیات ناموفق بود.';
      setError(message);
      toast.error(message);
    } finally {
      setSubmittingAction(null);
    }
  };

  if (loading) {
    return (
      <div dir="rtl" className="min-h-[60vh] flex items-center justify-center font-vazirmatn">
        <div className="flex items-center gap-3 text-slate-500">
          <Loader2 className="w-5 h-5 animate-spin text-emerald-600" />
          در حال بارگذاری نامه...
        </div>
      </div>
    );
  }

  if (error && !letter) {
    return (
      <div dir="rtl" className="font-vazirmatn max-w-3xl mx-auto">
        <div className="bg-white rounded-2xl shadow-sm border border-red-200 p-8 space-y-4">
          <div className="flex items-center gap-3 text-red-600">
            <AlertCircle className="w-5 h-5" />
            <h2 className="text-lg font-bold text-slate-800">خطا در دریافت نامه</h2>
          </div>
          <p className="text-sm text-slate-500 leading-7">{error}</p>
          <div className="flex justify-end gap-3">
            <button
              onClick={() => navigate(backPath)}
              className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors"
            >
              بازگشت
            </button>
            <button
              onClick={() => void loadLetter()}
              className="px-5 py-2 rounded-xl bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
            >
              تلاش مجدد
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!letter) {
    return null;
  }

  return (
    <div dir="rtl" className="min-h-full bg-[linear-gradient(180deg,#f4f7f6_0%,#eef3f1_100%)] px-4 py-8 font-vazirmatn">
      <div className="mx-auto max-w-5xl space-y-6 pb-10">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button
            onClick={() => navigate(backPath)}
            className="inline-flex items-center gap-2 rounded-2xl border border-white/70 bg-white/80 px-4 py-2 text-sm font-medium text-slate-700 shadow-sm backdrop-blur hover:bg-white"
          >
            <ArrowRight className="h-4 w-4" />
            بازگشت به کارتابل
          </button>
          <div className="rounded-2xl border border-emerald-100 bg-white/80 px-4 py-2 text-sm text-slate-600 shadow-sm backdrop-blur">
            <span className="font-bold text-slate-800">وضعیت فعلی:</span>{' '}
            {getFundingStatusLabel(letter.status)}
          </div>
        </div>

        {error ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-800">
            {error}
          </div>
        ) : null}

        <div className={pageShellClass} style={{ direction: 'rtl' }}>
          <div className="absolute inset-x-0 top-0 h-2 bg-gradient-to-l from-emerald-700 via-emerald-500 to-teal-400" />
          <div className="absolute inset-6 border border-emerald-100 pointer-events-none" />

          <header className="grid grid-cols-3 items-start gap-4 mb-6 relative">
            <div className="space-y-2 text-xs text-slate-600">
              <div className="flex items-center gap-1">
                <span className="font-semibold min-w-[52px]">تاریخ:</span>
                <span className="text-slate-800">{letter.letter_date}</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="font-semibold min-w-[52px]">شماره:</span>
                <span
                  className={`${
                    letter.letter_number ? 'text-slate-800 tracking-[0.12em]' : 'text-slate-400 tracking-[0.3em]'
                  }`}
                >
                  {letter.letter_number || '............... /'}
                </span>
              </div>
              <div className="flex items-center gap-1">
                <span className="font-semibold min-w-[52px]">پیوست:</span>
                <span className="text-slate-800">{letter.attachment_count}</span>
              </div>
            </div>

            <div className="space-y-2 text-center pt-1">
              <p className="text-base font-bold text-slate-500 tracking-wide">بسمه تعالی</p>
              <p className="text-[11px] font-extrabold text-slate-600">
                اقتصاد مقاومتی در سایه وحدت ملی و امنیت ملی
              </p>
            </div>

            <div className="flex justify-end">
              <img
                src={isfahanMunicipalityLogo}
                alt="لوگوی شهرداری اصفهان"
                className="w-24 h-24 object-contain"
              />
            </div>
          </header>

          <div className="border-t border-slate-200 mb-5" />

          <section className="space-y-3 mb-6">
            <ReadOnlyLine label="به:" value={letter.receiver_title} />
            <ReadOnlyLine label="از:" value={letter.sender_title} />
            <ReadOnlyLine label="موضوع:" value={letter.subject} />
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-bold text-slate-700 min-w-[48px] shrink-0">مبلغ:</span>
              <div className="w-full text-sm font-medium text-slate-900">{formatAmount(letter.amount)}</div>
            </div>
          </section>

          <div className="border-t border-slate-200 mb-5" />

          <section className="flex-1 mb-8">
            {looksLikeHtml(letter.body_text) ? (
              <div
                className="min-h-[220px] text-sm leading-8 text-justify text-slate-900
                  [&_p]:mb-4 [&_p]:leading-8
                  [&_table]:mt-4 [&_table]:w-full [&_table]:border-collapse
                  [&_thead]:bg-slate-100
                  [&_th]:border [&_th]:border-slate-300 [&_th]:px-3 [&_th]:py-2 [&_th]:text-center [&_th]:font-bold
                  [&_td]:border [&_td]:border-slate-300 [&_td]:px-3 [&_td]:py-2 [&_td]:text-center
                  [&_strong]:font-extrabold"
                dangerouslySetInnerHTML={{ __html: letter.body_text }}
              />
            ) : (
              <div className="min-h-[220px] text-sm leading-8 text-justify text-slate-900 whitespace-pre-wrap">
                {letter.body_text}
              </div>
            )}
          </section>

          <section className="mb-8 border-t border-slate-200 pt-6">
            <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/80 p-5">
              <p className="text-xs font-bold text-slate-500">ناحیه امضای دیجیتال</p>
              {isSigned ? (
                <div className="mt-4 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm leading-7 text-emerald-900">
                  تایید و امضا شده سیستمی توسط {getSignerLabel(signatureLog)} در تاریخ{' '}
                  {formatDateTime(signatureLog?.timestamp)}
                </div>
              ) : (
                <div className="mt-4 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-sm leading-7 text-slate-400">
                  این نامه هنوز به مرحله امضای سیستمی نهایی نرسیده است.
                </div>
              )}
            </div>
          </section>

          <footer className="border-t border-slate-200 pt-4 space-y-3">
            <div className="flex items-start gap-2">
              <span className="text-xs font-bold text-slate-600 min-w-[52px] shrink-0 pt-0.5">رونوشت:</span>
              <div className="text-xs leading-6 text-slate-700 whitespace-pre-wrap">
                {letter.cc_list?.trim() || '---'}
              </div>
            </div>
            <div className="grid gap-3 pt-2 text-xs text-slate-500 sm:grid-cols-3">
              <div>کد رهگیری: {letter.tracking_number}</div>
              <div>شماره نامه شارژ: {letter.charge_letter_number || '---'}</div>
              <div>کد بودجه: {letter.budget_code || '---'}</div>
            </div>
            <div className="border-t border-slate-200 pt-3 text-center text-[11px] font-medium leading-6 text-slate-500">
              اصفهان - میدان امام حسین (ع) - بلوار استانداری - اداره کل سرمایه انسانی شهرداری اصفهان - تلفن ۳۲۲۰۱۰۰۰
            </div>
          </footer>
        </div>

        <div className="sticky bottom-0 z-20">
          <div className="rounded-[28px] border border-slate-200/80 bg-white/95 px-4 py-4 shadow-2xl shadow-slate-200/70 backdrop-blur">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="text-sm leading-7 text-slate-500">
                <span className="font-bold text-slate-800">نامه:</span> {letter.subject}
              </div>
              <div className="flex flex-wrap items-center justify-end gap-3">
                {rejectAction ? (
                  <button
                    onClick={() => void handleTransition(rejectAction.action)}
                    disabled={submittingAction !== null}
                    className="inline-flex min-w-[148px] items-center justify-center gap-2 rounded-2xl bg-red-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-red-100 transition hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-slate-400"
                  >
                    {submittingAction === rejectAction.action ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <XCircle className="h-4 w-4" />
                    )}
                    رد و بازگشت
                  </button>
                ) : null}

                {approveAction ? (
                  <button
                    onClick={() => void handleTransition(approveAction.action)}
                    disabled={submittingAction !== null}
                    className="inline-flex min-w-[148px] items-center justify-center gap-2 rounded-2xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-emerald-100 transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-400"
                  >
                    {submittingAction === approveAction.action ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4" />
                    )}
                    {approveAction.action === 'approve' ? 'تایید و ارجاع' : approveAction.label}
                  </button>
                ) : null}

                {!approveAction && !rejectAction ? (
                  <div className="rounded-2xl bg-slate-100 px-4 py-3 text-sm text-slate-500">
                    اقدامی برای نقش شما در این مرحله تعریف نشده است.
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default OfficialLetterViewer;
