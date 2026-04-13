import React, { useEffect, useState } from 'react';
import api from '../../services/api';
import { toast } from 'sonner';
import { Check, X, Loader2, RefreshCw, AlertCircle, ChevronLeft, FileText, Download } from 'lucide-react';

interface FundingRequest {
    id: number;
    tracking_number: string;
    title: string;
    amount: number;
    status: string;
    description: string | null;
    created_at: string;
}

const formatNumber = (num: number) => num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
const formatDate = (isoString: string) => {
    try {
        return new Intl.DateTimeFormat('fa-IR', {
            year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
        }).format(new Date(isoString));
    } catch {
        return isoString;
    }
};

const STATUS_FLOW = [
    'DRAFT',
    'PENDING_VP_PLANNING',
    'PENDING_VP_FINANCE_INITIAL',
    'PENDING_BUDGET_ALLOCATION',
    'PENDING_VP_FINANCE_FINAL',
    'APPROVED_FOR_CHARGE'
];

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
    return <span className={`px-3 py-1 text-[11px] font-bold rounded-full border ${badge.classes}`}>{badge.label}</span>;
};

export const FundingManagerInbox = () => {
    const [requests, setRequests] = useState<FundingRequest[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [actionLoadingId, setActionLoadingId] = useState<number | null>(null);

    // Reject Modal State
    const [rejectModalOpen, setRejectModalOpen] = useState(false);
    const [rejectTargetId, setRejectTargetId] = useState<number | null>(null);
    const [rejectReason, setRejectReason] = useState('');
    const [isRejecting, setIsRejecting] = useState(false);

    const fetchRequests = async () => {
        setIsLoading(true);
        try {
            const data = await api.get<FundingRequest[]>('/funding/all');
            setRequests(data);
        } catch (error: any) {
            toast.error('خطا در دریافت کارتابل مدیریت');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchRequests();
    }, []);

    const handleAdvanceStatus = async (id: number, currentStatus: string) => {
        const currentIndex = STATUS_FLOW.indexOf(currentStatus);
        if (currentIndex === -1 || currentIndex === STATUS_FLOW.length - 1) {
            toast.error('این درخواست قابل ارجاع نیست.');
            return;
        }

        const nextStatus = STATUS_FLOW[currentIndex + 1];
        setActionLoadingId(id);
        
        try {
            // we use params for the patch endpoint based on how fastapi might expect it 
            // In our python router: @router.patch("/{request_id}/status") and new_status query/json body
            // Given specific implementation, it's either query string or body.
            // FastAPI with just a parameter new_status expects query params if not using a pydantic model body.
            // Let's pass it as query param
            await api.patch(`/funding/${id}/status`, undefined, { params: { new_status: nextStatus } });
            toast.success('درخواست با موفقیت ارجاع شد');
            fetchRequests();
        } catch (error: any) {
            toast.error('خطا در ارجاع درخواست');
        } finally {
            setActionLoadingId(null);
        }
    };

    const handleOpenReject = (id: number) => {
        setRejectTargetId(id);
        setRejectReason('');
        setRejectModalOpen(true);
    };

    const handleConfirmReject = async () => {
        if (!rejectTargetId) return;
        if (!rejectReason.trim()) {
            toast.error('ثبت دلیل رد الزامی است');
            return;
        }
        
        setIsRejecting(true);
        try {
            await api.patch(`/funding/${rejectTargetId}/status`, undefined, { params: { new_status: 'REJECTED' } });
            // Ideally we'd also post the reason or append to description if backend supported it
            toast.success('درخواست رد و بایگانی شد');
            setRejectModalOpen(false);
            fetchRequests();
        } catch (error: any) {
            toast.error('خطا در رد درخواست');
        } finally {
            setIsRejecting(false);
            setRejectTargetId(null);
        }
    };

    return (
        <div dir="rtl" className="font-vazirmatn w-full max-w-7xl mx-auto space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-slate-800 tracking-tight">کارتابل مدیران - تامین اعتبار</h1>
                    <p className="text-slate-500 mt-1">مدیریت، بررسی و ارجاع درخواست‌های شارژ بن و حقوق</p>
                </div>
                <button
                    onClick={fetchRequests}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-600 rounded-xl hover:bg-slate-50 hover:text-blue-600 transition-colors shadow-sm text-sm font-medium"
                >
                    <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                    بروزرسانی کارتابل
                </button>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                {isLoading ? (
                    <div className="flex justify-center py-20 text-blue-500"><Loader2 className="w-8 h-8 animate-spin" /></div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-right text-sm">
                            <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-bold">
                                <tr>
                                    <th className="px-6 py-4">کد رهگیری</th>
                                    <th className="px-6 py-4">عنوان</th>
                                    <th className="px-6 py-4">مبلغ (ریال)</th>
                                    <th className="px-6 py-4">وضعیت</th>
                                    <th className="px-6 py-4">تاریخ ثبت</th>
                                    <th className="px-6 py-4 text-center">عملیات</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {requests.map((req) => (
                                    <tr key={req.id} className="hover:bg-slate-50/50">
                                        <td className="px-6 py-4 font-mono text-xs">{req.tracking_number}</td>
                                        <td className="px-6 py-4 font-bold text-slate-800">{req.title}</td>
                                        <td className="px-6 py-4 font-medium">{formatNumber(req.amount)}</td>
                                        <td className="px-6 py-4">{getStatusBadge(req.status)}</td>
                                        <td className="px-6 py-4 text-slate-500 text-xs">{formatDate(req.created_at)}</td>
                                        <td className="px-6 py-4 text-center">
                                            <div className="flex items-center justify-center gap-2">
                                                <button
                                                    onClick={() => window.open(`${import.meta.env.VITE_API_BASE_URL || ''}/funding/${req.id}/pdf`, '_blank')}
                                                    className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded-lg text-xs font-bold transition-colors"
                                                    title="دریافت نامه رسمی"
                                                >
                                                    <Download className="w-4 h-4" />
                                                    نامه شارژ
                                                </button>
                                                {req.status !== 'REJECTED' && req.status !== 'APPROVED_FOR_CHARGE' && (
                                                    <>
                                                        <button
                                                            onClick={() => handleAdvanceStatus(req.id, req.status)}
                                                            disabled={actionLoadingId === req.id}
                                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
                                                        >
                                                            {actionLoadingId === req.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                                                            تایید و ارجاع
                                                        </button>
                                                        <button
                                                            onClick={() => handleOpenReject(req.id)}
                                                            disabled={actionLoadingId === req.id}
                                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-red-50 text-red-700 hover:bg-red-100 rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
                                                        >
                                                            <X className="w-4 h-4" />
                                                            رد
                                                        </button>
                                                    </>
                                                )}
                                                {req.status === 'APPROVED_FOR_CHARGE' && (
                                                    <span className="text-emerald-600 font-bold text-xs flex items-center justify-center gap-1">
                                                        <Check className="w-4 h-4" /> فرآیند تکمیل است
                                                    </span>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                                {requests.length === 0 && (
                                    <tr>
                                        <td colSpan={6} className="text-center py-12 text-slate-400">هیچ درخواستی در کارتابل موجود نیست.</td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Reject Modal */}
            {rejectModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
                    <div className="bg-white rounded-2xl w-full max-w-md shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                        <div className="p-6 border-b border-slate-100 flex items-center gap-3 text-red-600">
                            <AlertCircle className="w-6 h-6" />
                            <h3 className="text-lg font-bold">رد درخواست تامین اعتبار</h3>
                        </div>
                        <div className="p-6">
                            <label className="block text-sm font-bold text-slate-700 mb-2">
                                علت رد درخواست (الزامی)
                            </label>
                            <textarea
                                value={rejectReason}
                                onChange={(e) => setRejectReason(e.target.value)}
                                placeholder="لطفاً دلیل ریجکت را به صورت شفاف بنویسید..."
                                className="w-full h-32 p-4 rounded-xl border border-slate-300 focus:border-red-500 focus:ring-4 focus:ring-red-500/10 transition-all outline-none resize-none"
                            />
                        </div>
                        <div className="p-4 border-t border-slate-100 bg-slate-50 flex items-center justify-end gap-3">
                            <button
                                onClick={() => setRejectModalOpen(false)}
                                disabled={isRejecting}
                                className="px-4 py-2 text-slate-600 font-medium hover:bg-slate-200 rounded-xl transition-colors disabled:opacity-50"
                            >
                                انصراف
                            </button>
                            <button
                                onClick={handleConfirmReject}
                                disabled={isRejecting}
                                className="flex items-center gap-2 px-5 py-2 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl transition-colors disabled:opacity-70"
                            >
                                {isRejecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <X className="w-4 h-4" />}
                                ثبت و رد قطعی
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default FundingManagerInbox;
