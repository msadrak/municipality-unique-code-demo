import React, { useDeferredValue, useEffect, useMemo, useState } from 'react';
import { Loader2, Search, Download } from 'lucide-react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

import { getFundingStatusLabel } from '../../components/funding/workflow';
import { FundingRequest, fetchFundingArchive } from '../../services/funding';

function formatDate(value?: string | null) {
  return value || '-';
}

export default function LetterArchive() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<FundingRequest[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const deferredSearch = useDeferredValue(search);

  useEffect(() => {
    const loadArchive = async () => {
      setLoading(true);
      try {
        setRows(await fetchFundingArchive());
      } catch (error: any) {
        toast.error(error?.message || 'دریافت بایگانی نامه‌ها ناموفق بود');
      } finally {
        setLoading(false);
      }
    };

    void loadArchive();
  }, []);

  const filteredRows = useMemo(() => {
    const query = deferredSearch.trim().toLowerCase();
    if (!query) return rows;

    return rows.filter((row) => {
      const letterNumber = row.letter_number?.toLowerCase() || '';
      const subject = row.subject.toLowerCase();
      return letterNumber.includes(query) || subject.includes(query);
    });
  }, [deferredSearch, rows]);

  return (
    <div dir="rtl" className="font-vazirmatn w-full max-w-7xl mx-auto space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-800">بایگانی کل نامه‌ها</h1>
          <p className="mt-1 text-sm text-slate-500">
            جستجو و مشاهده همه نامه‌های ثبت‌شده در گردش کار اسناد منابع انسانی
          </p>
        </div>

        <div className="relative w-full max-w-md">
          <Search className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="جستجو بر اساس شماره نامه یا موضوع..."
            className="w-full rounded-2xl border border-slate-200 bg-white px-10 py-3 text-sm text-slate-800 shadow-sm outline-none transition focus:border-emerald-500 focus:ring-4 focus:ring-emerald-500/10"
          />
        </div>
      </div>

      <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center py-24 text-slate-500">
            <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
          </div>
        ) : filteredRows.length === 0 ? (
          <div className="py-20 text-center text-sm text-slate-500">هیچ نامه‌ای با این معیار پیدا نشد.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-right text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr className="[&>th]:border-b [&>th]:border-slate-200 [&>th]:px-6 [&>th]:py-4 [&>th]:font-bold">
                  <th>شماره نامه</th>
                  <th>تاریخ</th>
                  <th>موضوع</th>
                  <th>از</th>
                  <th>به</th>
                  <th>وضعیت</th>
                  <th className="text-center">عملیات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredRows.map((row) => (
                  <tr key={row.id} className="transition-colors hover:bg-slate-50/80">
                    <td className="px-6 py-4 font-mono text-slate-700">{row.letter_number || '---'}</td>
                    <td className="px-6 py-4 text-slate-600">{formatDate(row.letter_date)}</td>
                    <td className="px-6 py-4 font-bold text-slate-800">{row.subject}</td>
                    <td className="px-6 py-4 text-slate-600">{row.sender_title}</td>
                    <td className="px-6 py-4 text-slate-600">{row.receiver_title}</td>
                    <td className="px-6 py-4">
                      <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-[11px] font-bold text-slate-700">
                        {getFundingStatusLabel(row.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex justify-center">
                        <button
                          onClick={() => window.open(`${import.meta.env.VITE_API_BASE_URL || ''}/funding/${row.id}/pdf`, '_blank')}
                          className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-bold text-slate-700 transition hover:bg-slate-50 flex items-center gap-2"
                        >
                          <Download className="h-4 w-4 text-emerald-600" />
                          دریافت فایل
                        </button>
                        <button
                          onClick={() => navigate(`/hr/funding/letters/${row.id}`)}
                          className="rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white transition hover:bg-emerald-700"
                        >
                          مشاهده نامه
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
