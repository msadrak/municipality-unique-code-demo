import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { Popover, PopoverTrigger, PopoverContent } from './popover';
import { cn } from './utils';

export interface SegmentInfo {
    index: number;
    name: string;
    key: string;
    length: number;
    value: string;
    sourceTitle?: string;
    sourceCode?: string;
    formatNotes?: string;
}

/**
 * Combined CodeSegmentItem - Wrapper component that bundles the trigger and popover
 * This ensures proper positioning via Radix Portal and collision detection
 */
type CodeSegmentItemProps = {
    segment: SegmentInfo;
};

export function CodeSegmentItem({ segment }: CodeSegmentItemProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(segment.value);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
        }
    };

    return (
        <Popover open={isOpen} onOpenChange={setIsOpen}>
            <PopoverTrigger asChild>
                <button
                    className={cn(
                        "relative font-mono text-lg px-2 py-1 rounded-lg transition-all duration-300 ease-out",
                        isOpen
                            ? 'bg-blue-700 text-white scale-110 shadow-lg shadow-blue-900/30 z-10 font-bold'
                            : 'hover:bg-slate-100 hover:text-blue-800 text-slate-600'
                    )}
                    title={`${segment.name}: ${segment.value}`}
                >
                    {segment.value}
                </button>
            </PopoverTrigger>

            <PopoverContent
                side="bottom"
                align="center"
                sideOffset={12}
                className="w-[260px] bg-white dark:bg-slate-950 rounded-2xl shadow-2xl border border-slate-200/50 dark:border-slate-800 p-5 flex flex-col"
            >
                {/* Arrow indicator on top */}
                <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-4 h-4 rotate-45 bg-white dark:bg-slate-950 border-t border-l border-slate-200/50 dark:border-slate-800" />

                {/* Content wrapper */}
                <div className="relative z-10">
                    {/* Header - Minimal & Clean */}
                    <div className="flex items-center justify-between mb-4">
                        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            {segment.name}
                        </span>
                    </div>

                    {/* Central Focus - The Number */}
                    <div
                        className="flex flex-col items-center justify-center py-4 cursor-pointer group"
                        onClick={handleCopy}
                    >
                        <div className="relative flex items-center justify-center">
                            <span className="font-sans text-5xl font-black text-blue-700 dark:text-blue-400 leading-none tracking-tighter select-none transition-transform duration-300 group-hover:scale-105">
                                {segment.value}
                            </span>

                            {/* Copy indicator */}
                            <div className={cn(
                                "absolute -right-8 top-1/2 -translate-y-1/2 transition-all duration-300",
                                copied ? 'opacity-100 scale-100' : 'opacity-0 scale-75 group-hover:opacity-100'
                            )}>
                                {copied ? (
                                    <div className="bg-green-50 text-green-600 rounded-full p-1.5 shadow-sm">
                                        <Check className="h-4 w-4" />
                                    </div>
                                ) : (
                                    <div className="bg-slate-100 text-slate-400 rounded-full p-1.5 shadow-sm">
                                        <Copy className="h-4 w-4" />
                                    </div>
                                )}
                            </div>
                        </div>
                        <span className="text-[10px] text-slate-400 mt-2">برای کپی کلیک کنید</span>
                    </div>

                    {/* Footer - Essential Details */}
                    <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/50">
                        <div className="flex flex-col gap-2">
                            {segment.sourceTitle && (
                                <div className="flex items-baseline justify-between">
                                    <span className="text-[10px] text-slate-400">منبع</span>
                                    <span
                                        className="text-xs font-medium text-slate-700 dark:text-slate-300 truncate max-w-[140px]"
                                        title={segment.sourceTitle}
                                    >
                                        {segment.sourceTitle}
                                    </span>
                                </div>
                            )}
                            <div className="flex items-center justify-between">
                                <span className="text-[10px] text-slate-400">شناسه</span>
                                <span className="font-mono text-[10px] bg-slate-100 dark:bg-slate-900 px-2 py-0.5 rounded-full text-slate-500">
                                    {segment.key} • {segment.length} کاراکتر
                                </span>
                            </div>
                            {segment.formatNotes && (
                                <p className="text-[10px] text-slate-400 leading-tight mt-1 pt-2 border-t border-dashed border-slate-100 dark:border-slate-800">
                                    {segment.formatNotes}
                                </p>
                            )}
                        </div>
                    </div>
                </div>
            </PopoverContent>
        </Popover>
    );
}

/**
 * Segment metadata map - defines all 11 parts of the unique code
 */
export const SEGMENT_MAP = [
    { index: 0, name: 'منطقه/معاونت', key: 'zone', length: 2, formatNotes: 'کد عددی ۲ رقمی منطقه یا معاونت' },
    { index: 1, name: 'اداره', key: 'department', length: 2, formatNotes: 'کد عددی ۲ رقمی اداره' },
    { index: 2, name: 'قسمت', key: 'section', length: 3, formatNotes: 'کد عددی ۳ رقمی قسمت یا بخش' },
    { index: 3, name: 'کد بودجه', key: 'budget', length: 8, formatNotes: 'کد ردیف بودجه' },
    { index: 4, name: 'مرکز هزینه', key: 'costCenter', length: 3, formatNotes: 'کد ۳ رقمی مرکز هزینه' },
    { index: 5, name: 'اقدام مستمر', key: 'continuousAction', length: 2, formatNotes: 'کد ۲ رقمی اقدام مستمر' },
    { index: 6, name: 'فعالیت خاص', key: 'specialActivity', length: 3, formatNotes: 'هش ۳ کاراکتری فعالیت خاص' },
    { index: 7, name: 'هش ذینفع', key: 'beneficiary', length: 6, formatNotes: 'هش ۶ کاراکتری نام ذینفع (MD5)' },
    { index: 8, name: 'رویداد مالی', key: 'financialEvent', length: 3, formatNotes: 'کد ۳ رقمی رویداد مالی' },
    { index: 9, name: 'سال مالی', key: 'fiscalYear', length: 4, formatNotes: 'سال مالی ۴ رقمی (مثال: ۱۴۰۳)' },
    { index: 10, name: 'شماره ترتیب', key: 'sequence', length: 3, formatNotes: 'شماره ترتیب ۳ رقمی در سال مالی' },
];

export default CodeSegmentItem;
