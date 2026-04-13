import React, { FormEvent, useMemo, useState } from 'react';
import { Loader2, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import api from '../../services/api';
import isfahanMunicipalityLogo from '../../assets/isfahan-municipality-logo.svg';
import { useAuthStore } from '../../stores/useAuthStore';
import { canCreateFundingRequest } from './workflow';

const fieldClass =
  'w-full rounded-xl border border-slate-200 bg-white/80 px-3 py-2 text-sm font-medium text-slate-900 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10';

const inlineFieldClass =
  'inline-flex min-w-[150px] rounded-lg border-b-2 border-emerald-300 bg-transparent px-2 py-0.5 text-center text-sm font-bold text-slate-900 outline-none transition focus:border-emerald-600';

const tableInputClass =
  'w-full bg-transparent px-2 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-300';

const todayPersian = (): string =>
  new Intl.DateTimeFormat('fa-IR-u-ca-persian-nu-latn', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
    .format(new Date())
    .replace(/\u200f/g, '');

interface TableRow {
  id: number;
  creditCode: string;
  description: string;
  count: string;
  unitAmount: string;
  total: number;
}

interface LetterPayload {
  letter_date: string;
  receiver_title: string;
  sender_title: string;
  subject: string;
  body_text: string;
  cc_list: string | null;
  attachment_count: number;
  amount: number | null;
  request_type: string;
}

function createTableRow(id: number): TableRow {
  return {
    id,
    creditCode: '',
    description: '',
    count: '',
    unitAmount: '',
    total: 0,
  };
}

function normalizeNumberInput(value: string) {
  return value.replace(/[^0-9]/g, '');
}

function parseNumeric(value: string) {
  const normalized = normalizeNumberInput(value);
  return normalized ? Number(normalized) : 0;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('fa-IR').format(value);
}

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function buildCompiledBodyHtml(chargeMonthName: string, rows: TableRow[], grandTotalAmount: number, grandTotalCount: number) {
  const safeMonth = escapeHtml(chargeMonthName);
  const rowsHtml = rows
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row.creditCode)}</td>
          <td>${escapeHtml(row.description)}</td>
          <td>${formatCurrency(parseNumeric(row.count))}</td>
          <td>${formatCurrency(parseNumeric(row.unitAmount))}</td>
          <td>${formatCurrency(row.total)}</td>
        </tr>`,
    )
    .join('');

  return `
    <p>
      پس از حمد خدا و صلوات بر پیامبر اعظم و خاندان پاک ایشان، خواهشمند است موافقت و دستور فرمایید مبلغ
      <strong>${formatCurrency(grandTotalAmount)}</strong>
      ریال به منظور شارژ «بن غیرنقدی
      <strong>${safeMonth}</strong>
      » کارکنان و بازنشستگان شهرداری و سازمان آتش‌نشانی به شرح زیر تأمین اعتبار هزینه و برای واریز به حساب ارزاق اصفهان کارت افراد اقدامات لازم صورت پذیرد.
    </p>
    <table>
      <thead>
        <tr>
          <th>ردیف اعتبارات</th>
          <th>شرح</th>
          <th>تعداد</th>
          <th>مبلغ بن ریال</th>
          <th>مجموع ریال</th>
        </tr>
      </thead>
      <tbody>
        ${rowsHtml}
        <tr>
          <td colspan="2"><strong>جمع کل</strong></td>
          <td><strong>${formatCurrency(grandTotalCount)}</strong></td>
          <td></td>
          <td><strong>${formatCurrency(grandTotalAmount)}</strong></td>
        </tr>
      </tbody>
    </table>
  `;
}

export function OfficialLetterForm() {
  const { user } = useAuthStore();
  const [letterDate] = useState(todayPersian);
  const [letterNumber] = useState('............... /');
  const [receiverTitle, setReceiverTitle] = useState(
    'جناب آقای ابراهیمی - معاون محترم برنامه‌ریزی و توسعه سرمایه انسانی',
  );
  const [senderTitle, setSenderTitle] = useState('سید عباس روحانی - مدیرکل سرمایه انسانی');
  const [subject, setSubject] = useState('درخواست تأمین اعتبار شارژ بن غیرنقدی کارکنان و بازنشستگان');
  const [chargeMonthName, setChargeMonthName] = useState('فروردین ۱۴۰۵');
  const [tableRows, setTableRows] = useState<TableRow[]>([createTableRow(1)]);
  const [nextRowId, setNextRowId] = useState(2);
  const [ccList, setCcList] = useState('مدیرکل امور مالی\nواحد بودجه و اعتبارات');
  const [attachmentCount, setAttachmentCount] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const canCreate = canCreateFundingRequest(user?.role);

  const grandTotalCount = useMemo(
    () => tableRows.reduce((sum, row) => sum + parseNumeric(row.count), 0),
    [tableRows],
  );
  const grandTotalAmount = useMemo(
    () => tableRows.reduce((sum, row) => sum + row.total, 0),
    [tableRows],
  );

  const compiledBodyHtml = useMemo(
    () => buildCompiledBodyHtml(chargeMonthName.trim(), tableRows, grandTotalAmount, grandTotalCount),
    [chargeMonthName, grandTotalAmount, grandTotalCount, tableRows],
  );

  const updateRow = (id: number, field: keyof TableRow, value: string) => {
    setTableRows((current) =>
      current.map((row) => {
        if (row.id !== id) return row;

        const nextRow = {
          ...row,
          [field]: field === 'count' || field === 'unitAmount' ? normalizeNumberInput(value) : value,
        };
        const count = parseNumeric(nextRow.count);
        const unitAmount = parseNumeric(nextRow.unitAmount);
        nextRow.total = count * unitAmount;
        return nextRow;
      }),
    );
  };

  const addRow = () => {
    setTableRows((current) => [...current, createTableRow(nextRowId)]);
    setNextRowId((current) => current + 1);
  };

  const removeLastRow = () => {
    if (tableRows.length === 1) return;
    setTableRows((current) => current.slice(0, -1));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    const normalizedReceiver = receiverTitle.trim();
    const normalizedSender = senderTitle.trim();
    const normalizedSubject = subject.trim();
    const normalizedMonth = chargeMonthName.trim();
    const completedRows = tableRows.filter(
      (row) =>
        row.creditCode.trim() &&
        row.description.trim() &&
        parseNumeric(row.count) > 0 &&
        parseNumeric(row.unitAmount) > 0,
    );

    if (!normalizedReceiver || !normalizedSender || !normalizedSubject || !normalizedMonth) {
      toast.error('گیرنده، فرستنده، موضوع و ماه شارژ الزامی است');
      return;
    }
    if (completedRows.length !== tableRows.length) {
      toast.error('تمام ردیف‌های جدول باید کامل و دارای تعداد و مبلغ معتبر باشند');
      return;
    }
    if (grandTotalAmount <= 0 || grandTotalCount <= 0) {
      toast.error('جدول شارژ باید حداقل یک ردیف معتبر با جمع مثبت داشته باشد');
      return;
    }
    if (!canCreate) {
      toast.error('دسترسی ثبت درخواست برای نقش شما فعال نیست');
      return;
    }

    const payload: LetterPayload = {
      letter_date: letterDate,
      receiver_title: normalizedReceiver,
      sender_title: normalizedSender,
      subject: normalizedSubject,
      body_text: compiledBodyHtml,
      cc_list: ccList.trim() || null,
      attachment_count: attachmentCount,
      amount: grandTotalAmount,
      request_type: 'voucher_charge',
    };

    setSubmitting(true);
    try {
      await api.post('/funding/requests', payload);
      setSubmitted(true);
      toast.success('نامه با موفقیت ثبت شد');
    } catch (error: any) {
      toast.error(error?.message || 'خطا در ارسال نامه');
    } finally {
      setSubmitting(false);
    }
  };

  if (!canCreate) {
    return (
      <div dir="rtl" className="font-vazirmatn max-w-2xl mx-auto w-full">
        <div className="bg-white rounded-2xl shadow-sm border border-red-200 p-8">
          <h2 className="text-xl font-bold text-slate-800">دسترسی غیرمجاز</h2>
          <p className="text-sm text-slate-500 mt-3 leading-7">
            ثبت نامه تامین اعتبار فقط برای مدیرکل سرمایه انسانی یا ادمین فعال است.
          </p>
        </div>
      </div>
    );
  }

  if (submitted) {
    return (
      <div dir="rtl" className="min-h-[70vh] flex items-center justify-center px-4">
        <div className="bg-white rounded-3xl shadow-xl border border-emerald-100 p-10 text-center space-y-4 max-w-md w-full">
          <div className="w-16 h-16 rounded-full bg-emerald-50 text-emerald-600 mx-auto flex items-center justify-center text-2xl">
            ✓
          </div>
          <h2 className="text-xl font-bold text-slate-800">نامه با موفقیت ثبت شد</h2>
          <p className="text-slate-500 text-sm leading-7">فرم شارژ بن غیرنقدی در گردش کار منابع انسانی ثبت گردید.</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 px-6 py-2.5 bg-emerald-600 text-white rounded-xl hover:bg-emerald-700 transition text-sm font-bold"
          >
            ثبت نامه جدید
          </button>
        </div>
      </div>
    );
  }

  return (
    <div dir="rtl" className="min-h-screen bg-[linear-gradient(180deg,#eef4f1_0%,#e4ece8_100%)] py-10 px-4">
      <form onSubmit={handleSubmit} className="relative max-w-5xl mx-auto font-vazirmatn">
        <div
          className="bg-white shadow-[0_25px_80px_-30px_rgba(15,23,42,0.35)] mx-auto aspect-[1/1.414] max-w-4xl p-8 sm:p-10 md:p-14 relative border border-slate-300 flex flex-col overflow-hidden"
          style={{ direction: 'rtl' }}
        >
          <div className="absolute inset-x-0 top-0 h-2 bg-gradient-to-l from-emerald-900 via-emerald-700 to-emerald-500" />
          <div className="absolute inset-5 border border-emerald-100 pointer-events-none" />

          <header className="relative mb-6 border-b border-slate-200 pb-5">
            <div className="grid grid-cols-3 items-start gap-4">
              <div className="space-y-2 text-xs text-slate-700">
                <div className="flex items-center gap-2">
                  <span className="font-semibold min-w-[52px]">تاریخ:</span>
                  <span>{letterDate}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold min-w-[52px]">شماره:</span>
                  <span className="tracking-[0.3em] text-slate-400">{letterNumber}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold min-w-[52px]">پیوست:</span>
                  <input
                    type="number"
                    min={0}
                    value={attachmentCount}
                    onChange={(e) => setAttachmentCount(Math.max(0, Number(e.target.value) || 0))}
                    className="w-16 rounded-md border border-slate-200 px-2 py-1 text-center text-xs text-slate-800 outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="space-y-2 text-center">
                <p className="text-lg font-bold tracking-wide text-slate-700">بسمه تعالی</p>
                <p className="text-[11px] font-extrabold text-slate-600">
                  اقتصاد مقاومتی در سایه وحدت ملی و امنیت ملی
                </p>
              </div>

              <div className="flex justify-end">
                <img
                  src={isfahanMunicipalityLogo}
                  alt="لوگوی شهرداری اصفهان"
                  className="h-24 w-24 object-contain"
                />
              </div>
            </div>
          </header>

          <section className="space-y-3 mb-5">
            <div className="grid grid-cols-[72px_minmax(0,1fr)] items-center gap-3">
              <label className="text-sm font-bold text-slate-700">به:</label>
              <input
                type="text"
                value={receiverTitle}
                onChange={(e) => setReceiverTitle(e.target.value)}
                className={fieldClass}
              />
            </div>
            <div className="grid grid-cols-[72px_minmax(0,1fr)] items-center gap-3">
              <label className="text-sm font-bold text-slate-700">از:</label>
              <input
                type="text"
                value={senderTitle}
                onChange={(e) => setSenderTitle(e.target.value)}
                className={fieldClass}
              />
            </div>
            <div className="grid grid-cols-[72px_minmax(0,1fr)] items-center gap-3">
              <label className="text-sm font-bold text-slate-700">موضوع:</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className={fieldClass}
              />
            </div>
          </section>

          <section className="mb-6 rounded-[24px] border border-slate-200 bg-slate-50/70 px-5 py-5 text-sm leading-9 text-justify text-slate-800">
            <p>
              پس از حمد خدا و صلوات بر پیامبر اعظم و خاندان پاک ایشان، خواهشمند است موافقت و دستور فرمایید مبلغ{' '}
              <span className="mx-1 inline-flex rounded-lg bg-emerald-100 px-3 py-1 font-bold text-emerald-900">
                {formatCurrency(grandTotalAmount)}
              </span>{' '}
              ریال به منظور شارژ «بن غیرنقدی{' '}
              <input
                type="text"
                value={chargeMonthName}
                onChange={(e) => setChargeMonthName(e.target.value)}
                className={inlineFieldClass}
              />
              » کارکنان و بازنشستگان شهرداری و سازمان آتش‌نشانی به شرح زیر تأمین اعتبار هزینه و برای واریز به حساب ارزاق
              اصفهان کارت افراد اقدامات لازم صورت پذیرد.
            </p>
          </section>

          <section className="mb-5">
            <div className="overflow-hidden rounded-[24px] border border-slate-300">
              <table className="w-full border-collapse text-sm">
                <thead className="bg-slate-100 text-slate-700">
                  <tr className="[&>th]:border [&>th]:border-slate-300 [&>th]:px-3 [&>th]:py-3 [&>th]:text-center [&>th]:font-bold">
                    <th className="w-[18%]">ردیف اعتبارات</th>
                    <th className="w-[32%]">شرح</th>
                    <th className="w-[14%]">تعداد</th>
                    <th className="w-[18%]">مبلغ بن ریال</th>
                    <th className="w-[18%]">مجموع ریال</th>
                  </tr>
                </thead>
                <tbody>
                  {tableRows.map((row) => (
                    <tr
                      key={row.id}
                      className="[&>td]:border [&>td]:border-slate-300 [&>td]:align-middle [&>td]:bg-white"
                    >
                      <td>
                        <input
                          type="text"
                          value={row.creditCode}
                          onChange={(e) => updateRow(row.id, 'creditCode', e.target.value)}
                          className={tableInputClass}
                          placeholder="کد اعتبار"
                        />
                      </td>
                      <td>
                        <input
                          type="text"
                          value={row.description}
                          onChange={(e) => updateRow(row.id, 'description', e.target.value)}
                          className={tableInputClass}
                          placeholder="شرح ردیف"
                        />
                      </td>
                      <td>
                        <input
                          type="text"
                          inputMode="numeric"
                          value={row.count}
                          onChange={(e) => updateRow(row.id, 'count', e.target.value)}
                          className={`${tableInputClass} text-center`}
                          placeholder="0"
                        />
                      </td>
                      <td>
                        <input
                          type="text"
                          inputMode="numeric"
                          value={row.unitAmount}
                          onChange={(e) => updateRow(row.id, 'unitAmount', e.target.value)}
                          className={`${tableInputClass} text-center`}
                          placeholder="0"
                        />
                      </td>
                      <td className="px-3 py-2 text-center font-bold text-slate-700">
                        {formatCurrency(row.total)}
                      </td>
                    </tr>
                  ))}
                  <tr className="bg-emerald-50/80 [&>td]:border [&>td]:border-slate-300 [&>td]:px-3 [&>td]:py-3 [&>td]:font-bold">
                    <td colSpan={2} className="text-right text-emerald-900">
                      جمع کل
                    </td>
                    <td className="text-center text-emerald-900">{formatCurrency(grandTotalCount)}</td>
                    <td className="text-center text-slate-400">-</td>
                    <td className="text-center text-emerald-900">{formatCurrency(grandTotalAmount)}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="mt-3 flex items-center justify-between">
              <div className="text-xs text-slate-500">
                مبلغ کل نامه به صورت خودکار از جمع ردیف‌ها محاسبه می‌شود.
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={removeLastRow}
                  disabled={tableRows.length === 1}
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <Trash2 className="h-4 w-4" />
                  حذف آخرین ردیف
                </button>
                <button
                  type="button"
                  onClick={addRow}
                  className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white transition hover:bg-emerald-700"
                >
                  <Plus className="h-4 w-4" />
                  افزودن ردیف
                </button>
              </div>
            </div>
          </section>

          <div className="mt-auto space-y-5 pt-5">
            <div className="grid grid-cols-2 gap-8 border-t border-slate-200 pt-5 text-sm">
              <div className="space-y-2">
                <p className="font-bold text-slate-700">رونوشت:</p>
                <textarea
                  value={ccList}
                  onChange={(e) => setCcList(e.target.value)}
                  rows={3}
                  className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm leading-7 text-slate-700 outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10"
                />
              </div>

              <div className="flex justify-end">
                <div className="w-[240px] text-center">
                  <p className="text-sm font-bold text-slate-700">{senderTitle || 'مدیرکل سرمایه انسانی'}</p>
                  <div className="mx-auto mt-10 w-36 border-b border-dashed border-slate-400" />
                  <p className="mt-3 text-xs text-slate-500">محل امضا و مهر</p>
                </div>
              </div>
            </div>

            <footer className="absolute inset-x-10 bottom-6 border-t border-slate-200 pt-3 text-center text-[11px] font-medium leading-6 text-slate-500">
              اصفهان - میدان امام حسین (ع) - بلوار استانداری - اداره کل سرمایه انسانی شهرداری اصفهان - تلفن ۳۲۲۰۱۰۰۰
            </footer>
          </div>
        </div>

        <div className="sticky bottom-6 mt-8 flex justify-center z-10">
          <button
            type="submit"
            disabled={submitting}
            className="px-10 py-3 rounded-2xl bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-400 text-white font-bold text-sm shadow-lg shadow-emerald-200 transition-all duration-200 flex items-center gap-2"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                در حال ارسال...
              </>
            ) : (
              'ثبت و ارسال نامه'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

export default OfficialLetterForm;
