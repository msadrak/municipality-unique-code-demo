import React, { useEffect, useState } from 'react';
import { Loader2, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';

import api from '../../services/api';
import { useAuthStore } from '../../stores/useAuthStore';
import { canSeeFundingInbox, getFundingStatusLabel } from './workflow';

interface FundingRequestItem {
  id: number;
  tracking_number: string;
  subject: string;
  receiver_title: string;
  sender_title: string;
  amount: number | null;
  status: string;
  updated_at: string;
  budget_code?: string | null;
  charge_letter_number?: string | null;
  letter_number?: string | null;
}

const formatNumber = (num: number | null) =>
  typeof num === 'number' ? num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',') : '---';

const badgeClassMap: Record<string, string> = {
  REJECTED: 'bg-red-50 text-red-700 border-red-200',
  COMPLETED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  FINAL_APPROVED: 'bg-blue-50 text-blue-700 border-blue-200',
  CHARGING_IN_PROGRESS: 'bg-amber-50 text-amber-700 border-amber-200',
};

export function FundingManagerInboxV2() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [requests, setRequests] = useState<FundingRequestItem[]>([]);
  const [loading, setLoading] = useState(true);

  const canAccessInbox = canSeeFundingInbox(user?.role);

  const fetchInbox = async () => {
    setLoading(true);
    try {
      const data = await api.get<FundingRequestItem[]>('/funding/inbox');
      setRequests(data);
    } catch (error: any) {
      toast.error(error?.message || 'خطا در دریافت کارتابل');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (canAccessInbox) {
      void fetchInbox();
      return;
    }
    setLoading(false);
  }, [canAccessInbox]);

  if (!canAccessInbox) {
    return (
      <div dir="rtl" className="font-vazirmatn w-full max-w-3xl mx-auto">
        <div className="bg-white rounded-2xl shadow-sm border border-red-200 p-8">
          <h2 className="text-xl font-bold text-slate-800">دسترسی غیرمجاز</h2>
          <p className="text-sm text-slate-500 mt-3 leading-7">
            کارتابل funding فقط برای نقش‌های گردش کار منابع انسانی قابل مشاهده است.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div dir="rtl" className="font-vazirmatn w-full max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 tracking-tight">کارتابل نامه‌های منابع انسانی</h1>
          <p className="text-slate-500 mt-1">نامه‌هایی که اکنون نیازمند بررسی و اقدام نقش شما هستند</p>
        </div>
        <button
          onClick={() => void fetchInbox()}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-600 rounded-xl hover:bg-slate-50 hover:text-blue-600 transition-colors shadow-sm text-sm font-medium disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          بروزرسانی کارتابل
        </button>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-20 text-blue-500">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
        ) : requests.length === 0 ? (
          <div className="text-center py-16 text-slate-500">درخواستی در کارتابل شما وجود ندارد.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-right text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold">
                <tr>
                  <th className="px-6 py-4">کد رهگیری</th>
                  <th className="px-6 py-4">موضوع نامه</th>
                  <th className="px-6 py-4">فرستنده / گیرنده</th>
                  <th className="px-6 py-4">مبلغ (ریال)</th>
                  <th className="px-6 py-4">وضعیت فعلی</th>
                  <th className="px-6 py-4">شماره نامه</th>
                  <th className="px-6 py-4">شماره نامه شارژ</th>
                  <th className="px-6 py-4 text-center">نمایش</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {requests.map((req) => {
                  const badgeClass = badgeClassMap[req.status] || 'bg-slate-100 text-slate-700 border-slate-200';

                  return (
                    <tr key={req.id} className="hover:bg-slate-50/50">
                      <td className="px-6 py-4 font-mono text-xs text-slate-500">{req.tracking_number}</td>
                      <td className="px-6 py-4 font-bold text-slate-800">{req.subject}</td>
                      <td className="px-6 py-4 text-slate-600">
                        <div>{req.sender_title}</div>
                        <div className="text-xs text-slate-400 mt-1">{req.receiver_title}</div>
                      </td>
                      <td className="px-6 py-4 font-medium">{formatNumber(req.amount)}</td>
                      <td className="px-6 py-4">
                        <span className={`px-3 py-1 text-[11px] font-bold rounded-full border ${badgeClass}`}>
                          {getFundingStatusLabel(req.status)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-500">{req.letter_number || '---'}</td>
                      <td className="px-6 py-4 text-slate-500">{req.charge_letter_number || '---'}</td>
                      <td className="px-6 py-4">
                        <div className="flex items-center justify-center">
                          <button
                            onClick={() => navigate(`/hr/funding/letters/${req.id}`)}
                            className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700"
                          >
                            مشاهده نامه
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default FundingManagerInboxV2;
