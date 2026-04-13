import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Info, Loader2, Plus } from 'lucide-react';
import { toast } from 'sonner';

import api from '../../services/api';
import { useAuthStore } from '../../stores/useAuthStore';
import { canCreateFundingRequest } from './workflow';

const formatNumberWithCommas = (value: string) => {
  const numericValue = value.replace(/\D/g, '');
  return numericValue.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

const calculateToman = (rialStr: string) => {
  const rawNum = rialStr.replace(/\D/g, '');
  if (!rawNum) return '0';
  const num = parseInt(rawNum, 10);
  return formatNumberWithCommas(Math.floor(num / 10).toString());
};

export function FundingRequestFormV2() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [title, setTitle] = useState('');
  const [amountStr, setAmountStr] = useState('');
  const [description, setDescription] = useState('');
  const [budgetYear, setBudgetYear] = useState('1405');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const canCreate = canCreateFundingRequest(user?.role);
  const tomanValue = useMemo(() => calculateToman(amountStr), [amountStr]);

  const handleAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setAmountStr(formatNumberWithCommas(e.target.value));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const rawAmount = parseInt(amountStr.replace(/\D/g, ''), 10);
    const normalizedBudgetYear = budgetYear.trim() ? parseInt(budgetYear, 10) : undefined;

    if (!title.trim()) {
      toast.error('عنوان درخواست الزامی است');
      return;
    }
    if (!rawAmount || rawAmount <= 0) {
      toast.error('مبلغ معتبر نیست');
      return;
    }
    if (budgetYear.trim() && (!normalizedBudgetYear || normalizedBudgetYear < 1300)) {
      toast.error('سال بودجه معتبر نیست');
      return;
    }
    if (!canCreate) {
      toast.error('دسترسی ثبت درخواست برای نقش شما فعال نیست');
      return;
    }

    setIsSubmitting(true);
    try {
      await api.post('/funding/requests', {
        title: title.trim(),
        amount: rawAmount,
        description: description.trim() || null,
        budget_year: normalizedBudgetYear,
      });
      toast.success('درخواست با موفقیت ثبت شد');
      navigate('/hr/funding/my-requests');
    } catch (error: any) {
      toast.error(error?.message || 'خطا در ثبت درخواست');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!canCreate) {
    return (
      <div dir="rtl" className="font-vazirmatn max-w-2xl mx-auto w-full">
        <div className="bg-white rounded-2xl shadow-sm border border-red-200 p-8">
          <h2 className="text-xl font-bold text-slate-800">دسترسی غیرمجاز</h2>
          <p className="text-sm text-slate-500 mt-3 leading-7">
            ثبت درخواست بن فقط برای مدیرکل سرمایه انسانی یا ادمین فعال است.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div dir="rtl" className="font-vazirmatn max-w-2xl mx-auto w-full">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        <div className="flex items-center gap-3 mb-8 pb-4 border-b border-slate-100">
          <div className="w-10 h-10 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center">
            <Plus className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-800">ثبت درخواست تامین اعتبار جدید</h2>
            <p className="text-sm text-slate-500 mt-1">ویژه مدیرکل سرمایه انسانی</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="text-sm font-bold text-slate-700 mb-2 block">عنوان درخواست</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="مثال: شارژ بن فروردین کارکنان"
              className="w-full h-12 rounded-xl border border-slate-300 px-4 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all outline-none"
              required
            />
          </div>

          <div>
            <label className="text-sm font-bold text-slate-700 mb-2 block">
              مبلغ <span className="font-normal text-slate-500">(ریال)</span>
            </label>
            <div className="relative">
              <input
                type="text"
                dir="ltr"
                value={amountStr}
                onChange={handleAmountChange}
                placeholder="0"
                className="w-full h-12 rounded-xl border border-slate-300 px-4 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all outline-none font-mono text-lg text-right"
                required
              />
              <div className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400">ریال</div>
            </div>
            {amountStr && (
              <div className="mt-2 flex items-center gap-1.5 text-xs text-amber-600 font-medium bg-amber-50 rounded-lg p-2 border border-amber-100/50">
                <Info className="w-4 h-4" />
                معادل {tomanValue} تومان
              </div>
            )}
          </div>

          <div>
            <label className="text-sm font-bold text-slate-700 mb-2 block">
              سال بودجه <span className="font-normal text-slate-500">(اختیاری)</span>
            </label>
            <input
              type="number"
              value={budgetYear}
              onChange={(e) => setBudgetYear(e.target.value)}
              placeholder="1405"
              className="w-full h-12 rounded-xl border border-slate-300 px-4 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all outline-none"
            />
          </div>

          <div>
            <label className="text-sm font-bold text-slate-700 mb-2 block">
              توضیحات تکمیلی <span className="font-normal text-slate-500">(اختیاری)</span>
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="جزئیات بیشتر درخواست را اینجا بنویسید..."
              className="w-full min-h-[120px] p-4 rounded-xl border border-slate-300 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all outline-none resize-y"
            />
          </div>

          <div className="pt-4 mt-8 border-t border-slate-100">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-12 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white rounded-xl font-bold text-base transition-colors flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  در حال ثبت...
                </>
              ) : (
                'ثبت نهایی درخواست'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default FundingRequestFormV2;
