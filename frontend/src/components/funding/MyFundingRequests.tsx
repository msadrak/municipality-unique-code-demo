import React, { useEffect, useState } from 'react';
import api from '../../services/api';
import { toast } from 'sonner';
import { FileText, Loader2, RefreshCw } from 'lucide-react';

interface FundingRequest {
    id: number;
    tracking_number: string;
    title: string;
    amount: number;
    status: string;
    description: string | null;
    created_at: string;
}

const formatNumber = (num: number) => {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
};

const formatDate = (isoString: string) => {
    try {
        return new Intl.DateTimeFormat('fa-IR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        }).format(new Date(isoString));
    } catch {
        return isoString;
    }
};

const getStatusBadge = (status: string) => {
    const badges: Record<string, { label: string; classes: string }> = {
        DRAFT: { label: 'پیش‌نویس اولیه', classes: 'bg-slate-100 text-slate-700 border-slate-200' },
        PENDING_VP_PLANNING: { label: 'انتظار معاون برنامه‌ریزی', classes: 'bg-blue-50 text-blue-700 border-blue-200' },
        PENDING_VP_FINANCE_INITIAL: { label: 'بررسی اولیه مالی', classes: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
        PENDING_BUDGET_ALLOCATION: { label: 'تامین اعتبار بودجه', classes: 'bg-purple-50 text-purple-700 border-purple-200' },
        PENDING_VP_FINANCE_FINAL: { label: 'دستور نهایی شارژ', classes: 'bg-amber-50 text-amber-700 border-amber-200' },
        APPROVED_FOR_CHARGE: { label: 'ارسال جهت شارژ', classes: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
        REJECTED: { label: 'رد شده', classes: 'bg-red-50 text-red-700 border-red-200' },
    };

    const badge = badges[status] || { label: status, classes: 'bg-gray-100 text-gray-700' };

    return (
        <span className={`px-3 py-1 text-[11px] font-bold rounded-full border ${badge.classes}`}>
            {badge.label}
        </span>
    );
};

export const MyFundingRequests = () => {
    const [requests, setRequests] = useState<FundingRequest[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    const fetchRequests = async () => {
        setIsLoading(true);
        try {
            const data = await api.get<FundingRequest[]>('/funding/');
            setRequests(data);
        } catch (error: any) {
            toast.error(error.message || 'خطا در دریافت لیست درخواست‌ها');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchRequests();
    }, []);

    return (
        <div dir="rtl" className="font-vazirmatn w-full max-w-6xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-slate-800 tracking-tight">درخواست‌های من</h1>
                    <p className="text-slate-500 mt-1">آرشیو و پیگیری وضعیت درخواست‌های تامین اعتبار شما</p>
                </div>
                <button
                    onClick={fetchRequests}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-600 rounded-xl hover:bg-slate-50 hover:text-blue-600 transition-colors disabled:opacity-50 font-medium text-sm shadow-sm"
                >
                    <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                    بروزرسانی
                </button>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-24 text-slate-400">
                        <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
                        <p>در حال دریافت اطلاعات...</p>
                    </div>
                ) : requests.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-24 text-slate-400">
                        <FileText className="w-12 h-12 mb-4 opacity-20" />
                        <p>هنوز رویه و درخواستی ثبت نکرده‌اید.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-right text-sm">
                            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold">
                                <tr>
                                    <th className="px-6 py-4 whitespace-nowrap">کد رهگیری</th>
                                    <th className="px-6 py-4">عنوان درخواست</th>
                                    <th className="px-6 py-4">مبلغ (ریال)</th>
                                    <th className="px-6 py-4">وضعیت</th>
                                    <th className="px-6 py-4">تاریخ ثبت</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {requests.map((req) => (
                                    <tr key={req.id} className="hover:bg-slate-50/50 transition-colors">
                                        <td className="px-6 py-4">
                                            <span className="font-mono text-slate-500 bg-slate-100 px-2 py-1 rounded-md text-xs">
                                                {req.tracking_number}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 font-bold text-slate-800">
                                            {req.title}
                                            {req.description && (
                                                <p className="text-xs text-slate-400 font-normal mt-1 truncate max-w-xs">{req.description}</p>
                                            )}
                                        </td>
                                        <td className="px-6 py-4 font-medium text-slate-700">
                                            {formatNumber(req.amount)}
                                        </td>
                                        <td className="px-6 py-4">
                                            {getStatusBadge(req.status)}
                                        </td>
                                        <td className="px-6 py-4 text-slate-500 text-xs">
                                            {formatDate(req.created_at)}
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
};

export default MyFundingRequests;
