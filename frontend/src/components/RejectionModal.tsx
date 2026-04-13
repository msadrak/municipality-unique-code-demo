import React, { useState } from 'react';

interface RejectionModalProps {
    statementNumber: string;
    onConfirm: (reason: string) => Promise<void>;
    onCancel: () => void;
}

export function RejectionModal({ statementNumber, onConfirm, onCancel }: RejectionModalProps) {
    const [reason, setReason] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async () => {
        if (!reason.trim()) {
            setError('لطفاً دلیل رد را وارد کنید');
            return;
        }
        setLoading(true);
        setError('');
        try {
            await onConfirm(reason.trim());
        } catch (err: unknown) {
            setError(err instanceof Error ? err.message : 'خطا در ثبت رد ');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center" dir="rtl">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/50 backdrop-blur-sm"
                onClick={onCancel}
            />

            {/* Card */}
            <div className="relative w-full max-w-lg mx-4 bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden animate-fade-in-up">
                {/* Header gradient bar */}
                <div className="h-1 bg-gradient-to-l from-red-500 via-rose-500 to-pink-500" />

                <div className="p-6 space-y-5">
                    {/* Title */}
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center">
                            <svg className="w-5 h-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 5.636l-12.728 12.728M5.636 5.636l12.728 12.728" />
                            </svg>
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-slate-800">دلیل رد </h3>
                            <p className="text-sm text-slate-500">
                                شماره <span className="font-semibold text-slate-700">{statementNumber}</span>
                            </p>
                        </div>
                    </div>

                    {/* Textarea */}
                    <div>
                        <textarea
                            id="rejection-reason"
                            rows={4}
                            value={reason}
                            onChange={(e) => {
                                setReason(e.target.value);
                                if (error) setError('');
                            }}
                            placeholder="دلیل رد را بنویسید..."
                            className={`w-full rounded-xl border px-4 py-3 text-sm text-slate-700 placeholder-slate-400 transition-colors focus:outline-none focus:ring-2 resize-none ${error
                                ? 'border-red-300 bg-red-50/50 focus:ring-red-200'
                                : 'border-slate-200 bg-slate-50 focus:ring-blue-200 focus:border-blue-300'
                                }`}
                            disabled={loading}
                            autoFocus
                        />
                        {error && (
                            <p className="mt-1.5 text-xs text-red-500 flex items-center gap-1">
                                <svg className="w-3.5 h-3.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                </svg>
                                {error}
                            </p>
                        )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-3 pt-1">
                        <button
                            id="rejection-submit"
                            onClick={handleSubmit}
                            disabled={loading}
                            className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-l from-red-600 to-rose-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:from-red-700 hover:to-rose-700 hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? (
                                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                </svg>
                            ) : (
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            )}
                            {loading ? 'در حال ثبت...' : 'ثبت رد'}
                        </button>
                        <button
                            id="rejection-cancel"
                            onClick={onCancel}
                            disabled={loading}
                            className="flex-1 inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-600 transition-all hover:bg-slate-50 hover:border-slate-300 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            انصراف
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default RejectionModal;
