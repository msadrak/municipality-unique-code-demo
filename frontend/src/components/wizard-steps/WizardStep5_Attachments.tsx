import React, { useState, useEffect } from 'react';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import {
    FileText,
    Upload,
    CloudDownload,
    CheckCircle2,
    Loader2,
    Search,
    Paperclip,
    X,
    File,
    Info,
    DollarSign,
    User
} from 'lucide-react';
import { TransactionFormData } from '../TransactionWizard';

type Props = {
    formData: TransactionFormData;
    updateFormData: (data: Partial<TransactionFormData>) => void;
};

type Attachment = {
    id: string;
    name: string;
    type: string;
    source: 'system' | 'manual';
    status: 'pending' | 'attached';
    date?: string;
    size?: string;
};

// Mock data for "System Inquiry"
const FOUND_SYSTEM_DOCS = [
    { id: 'sys_500', name: 'قرارداد شماره ۱۴۰۲/۵۰۰ - اسکن شده', type: 'contract', date: '1402/10/01', size: '2.4 MB', meta: { ben: 'شرکت پیمانکاری نمونه', amt: 1500000000 } },
    { id: 'sys_501', name: 'صورت‌جلسه تحویل زمین', type: 'minutes', date: '1402/10/05', size: '1.1 MB', meta: { ben: 'شرکت عمران سازان', amt: 850000000 } },
    { id: 'sys_502', name: 'مجوز کمیسیون ماده ۵', type: 'license', date: '1402/09/15', size: '850 KB', meta: { ben: 'شهرداری منطقه ۱', amt: 0 } },
];

export function WizardStep5_Attachments({ formData, updateFormData }: Props) {
    const [activeTab, setActiveTab] = useState<'system' | 'manual'>('system');
    const [isSearching, setIsSearching] = useState(false);
    const [searchResult, setSearchResult] = useState<typeof FOUND_SYSTEM_DOCS | null>(null);
    const [autoParsed, setAutoParsed] = useState(false);

    // Local state for attachments (synced with formData via effect or direct update)
    // We initialize from formData if it exists, otherwise empty array
    // Assuming formData.attachments is where we store it (we'll need to enable this field)
    const [attachments, setAttachments] = useState<Attachment[]>(
        (formData.attachments as Attachment[]) || []
    );

    const [manualFile, setManualFile] = useState<File | null>(null);
    const [manualDocType, setManualDocType] = useState('صورت وضعیت تایید شده');

    // Sync to parent
    const updateParent = (newAttachments: Attachment[]) => {
        setAttachments(newAttachments);
        updateFormData({ attachments: newAttachments });
    };

    const handleSystemSearch = () => {
        setIsSearching(true);
        setSearchResult(null);
        setAutoParsed(false);

        // Simulate API delay
        setTimeout(() => {
            setIsSearching(false);
            setSearchResult(FOUND_SYSTEM_DOCS);
        }, 2000); // 2 second delay for realism
    };

    const handleAttachSystemDoc = (doc: typeof FOUND_SYSTEM_DOCS[0]) => {
        // Check if already added
        if (attachments.some(a => a.id === doc.id)) return;

        const newAttachment: Attachment = {
            id: doc.id,
            name: doc.name,
            type: doc.type,
            source: 'system',
            status: 'attached',
            date: doc.date,
            size: doc.size
        };

        // SIMULATION: Auto-populate Metadata Logic
        if (doc.meta.amt > 0) {
            updateFormData({
                beneficiaryName: doc.meta.ben,
                amount: doc.meta.amt,
                attachments: [...attachments, newAttachment]
            });
            setAttachments([...attachments, newAttachment]);
            setAutoParsed(true); // Show confirmation badge
        } else {
            // Just attach if no metadata
            updateParent([...attachments, newAttachment]);
        }
    };

    const handleManualUpload = () => {
        // In a real app, this would handle the file object.
        // For demo, we just create a record.
        const fileId = `manual_${Date.now()}`;
        const fileName = manualFile ? manualFile.name : `سند_اسکن_شده_${Math.floor(Math.random() * 100)}.pdf`;

        const newAttachment: Attachment = {
            id: fileId,
            name: `${manualDocType} - ${fileName}`,
            type: 'manual_upload',
            source: 'manual',
            status: 'attached',
            date: '1403/10/02', // Today
            size: manualFile ? `${(manualFile.size / 1024).toFixed(0)} KB` : '1.5 MB'
        };

        updateParent([...attachments, newAttachment]);
        setManualFile(null); // Reset input
    };

    const removeAttachment = (id: string) => {
        updateParent(attachments.filter(a => a.id !== id));
        if (attachments.length <= 1) setAutoParsed(false); // Reset parse badge if empty
    };

    // Helper to convert Persian digits to English
    const toEnglishDigits = (str: string) => {
        return str.replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d).toString());
    };

    const handleAmountChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        // 1. Get raw value
        let val = e.target.value;

        // 2. Normalize Persian digits
        val = toEnglishDigits(val);

        // 3. Remove non-numeric chars (keep only digits)
        val = val.replace(/[^0-9]/g, '');

        // 4. Update state (as number)
        if (val) {
            updateFormData({ amount: Number(val) });
        } else {
            updateFormData({ amount: undefined });
        }
    };

    // Helper for currency formatting
    const formatAmount = (val: number | undefined) => {
        if (!val) return '';
        return new Intl.NumberFormat('fa-IR').format(val);
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-start">
                <div>
                    <h3>مستندات و اطلاعات پایه</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                        مدارک مربوطه را بارگذاری کرده و اطلاعات ذینفع را تکمیل کنید
                    </p>
                </div>
                {autoParsed && (
                    <Badge variant="secondary" className="bg-green-100 text-green-800 border-green-200 animate-in fade-in slide-in-from-right-2">
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        مبلغ و ذینفع از سند خوانده شد
                    </Badge>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Left Column: Input Area */}
                <div className="md:col-span-2 space-y-4">
                    <Tabs value={activeTab} onValueChange={(v: string) => setActiveTab(v as any)} className="w-full">
                        <TabsList className="grid w-full grid-cols-2">
                            <TabsTrigger value="system">استعلام سیستمی (پیشنهادی)</TabsTrigger>
                            <TabsTrigger value="manual">بارگذاری دستی</TabsTrigger>
                        </TabsList>

                        {/* MODE A: SYSTEM INQUIRY */}
                        <TabsContent value="system" className="space-y-4 mt-4">
                            <Card className="p-6 border-dashed border-2 flex flex-col items-center justify-center space-y-4 min-h-[300px] bg-slate-50/50">
                                {!searchResult && !isSearching && (
                                    <div className="text-center space-y-4">
                                        <div className="bg-primary/10 p-4 rounded-full inline-block">
                                            <CloudDownload className="h-8 w-8 text-primary" />
                                        </div>
                                        <div>
                                            <h4 className="font-medium text-lg">اتصال به سامانه آرشیو</h4>
                                            <p className="text-sm text-muted-foreground max-w-xs mx-auto mt-2">
                                                برای فراخوانی خودکار اسناد و اطلاعات (مبلغ/ذینفع) از سامانه آرشیو، دکمه زیر را بزنید.
                                            </p>
                                        </div>
                                        <Button onClick={handleSystemSearch} size="lg" className="mt-2">
                                            <Search className="mr-2 h-4 w-4" />
                                            بررسی سوابق در سامانه آرشیو
                                        </Button>
                                    </div>
                                )}

                                {isSearching && (
                                    <div className="text-center space-y-4">
                                        <Loader2 className="h-10 w-10 text-primary animate-spin" />
                                        <p className="text-sm text-muted-foreground animate-pulse">
                                            در حال پردازش هوشمند و خواندن متادیتای اسناد...
                                        </p>
                                    </div>
                                )}

                                {searchResult && (
                                    <div className="w-full space-y-3">
                                        <div className="flex items-center justify-between mb-2">
                                            <p className="text-sm font-medium text-green-700 flex items-center">
                                                <CheckCircle2 className="h-4 w-4 ml-2" />
                                                {searchResult.length} سند با قابلیت استخراج داده یافت شد
                                            </p>
                                            <Button variant="ghost" size="sm" onClick={() => setSearchResult(null)} className="text-xs">
                                                جستجوی مجدد
                                            </Button>
                                        </div>

                                        <div className="grid gap-3">
                                            {searchResult.map((doc) => {
                                                const isAdded = attachments.some(a => a.id === doc.id);
                                                return (
                                                    <div
                                                        key={doc.id}
                                                        className={`flex items-center justify-between p-3 rounded-lg border transition-all ${isAdded ? 'bg-green-50 border-green-200 opacity-70' : 'bg-white hover:border-primary/50'
                                                            }`}
                                                    >
                                                        <div className="flex items-start gap-3">
                                                            <div className="bg-blue-50 p-2 rounded">
                                                                <FileText className="h-5 w-5 text-blue-600" />
                                                            </div>
                                                            <div>
                                                                <p className="font-medium text-sm">{doc.name}</p>
                                                                <div className="flex items-center gap-2 mt-1">
                                                                    <span className="text-[10px] bg-slate-100 px-1 rounded text-slate-600">
                                                                        ذینفع: {doc.meta.ben}
                                                                    </span>
                                                                    {doc.meta.amt > 0 && (
                                                                        <span className="text-[10px] bg-slate-100 px-1 rounded text-slate-600">
                                                                            مبلغ: {new Intl.NumberFormat('fa-IR').format(doc.meta.amt)}
                                                                        </span>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </div>
                                                        <Button
                                                            size="sm"
                                                            variant={isAdded ? "outline" : "default"}
                                                            disabled={isAdded}
                                                            onClick={() => handleAttachSystemDoc(doc)}
                                                        >
                                                            {isAdded ? 'اضافه شد' : 'افزودن'}
                                                        </Button>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}
                            </Card>
                        </TabsContent>

                        {/* MODE B: MANUAL UPLOAD */}
                        <TabsContent value="manual" className="space-y-4 mt-4">
                            <Card className="p-6 space-y-6">

                                {/* Manual Metadata Inputs */}
                                <div className="grid gap-6 md:grid-cols-2">
                                    <div className="space-y-2">
                                        <Label htmlFor="beneficiary">نام ذینفع / پیمانکار <span className="text-destructive">*</span></Label>
                                        <div className="relative">
                                            <User className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                            <Input
                                                id="beneficiary"
                                                placeholder="نام شرکت یا شخص..."
                                                className="pr-10"
                                                value={formData.beneficiaryName || ''}
                                                onChange={(e) => updateFormData({ beneficiaryName: e.target.value })}
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <Label htmlFor="amount">مبلغ (ریال) <span className="text-destructive">*</span></Label>
                                        <div className="relative">
                                            <DollarSign className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                            <Input
                                                id="amount"
                                                type="text"
                                                inputMode="numeric"
                                                placeholder="0"
                                                className="pr-10"
                                                value={formData.amount ? new Intl.NumberFormat('fa-IR').format(formData.amount) : ''}
                                                onChange={handleAmountChange}
                                            />
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-2 pt-4 border-t">
                                    <Label>بارگذاری فایل مستندات <span className="text-destructive">*</span></Label>
                                    <div className="border-2 border-dashed rounded-lg p-8 text-center hover:bg-slate-50 transition-colors cursor-pointer relative mt-2">
                                        <input
                                            type="file"
                                            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                            onChange={(e) => setManualFile(e.target.files?.[0] || null)}
                                        />
                                        <div className="flex flex-col items-center gap-2">
                                            <Upload className="h-8 w-8 text-muted-foreground" />
                                            <p className="text-sm font-medium">
                                                {manualFile ? manualFile.name : 'فایل را اینجا رها کنید یا کلیک کنید'}
                                            </p>
                                            <p className="text-xs text-muted-foreground">
                                                PDF, JPG, PNG (حداکثر ۵ مگابایت)
                                            </p>
                                        </div>
                                    </div>

                                    <div className="flex justify-end mt-2">
                                        <Button
                                            onClick={handleManualUpload}
                                            disabled={!manualFile || !formData.beneficiaryName || !formData.amount}
                                            variant="outline"
                                            className="w-full md:w-auto"
                                        >
                                            افزودن به لیست پیوست‌ها
                                        </Button>
                                    </div>
                                </div>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </div>

                {/* Right Column: List of Attached Files */}
                <div className="md:col-span-1">
                    <Card className="h-full p-4 flex flex-col">
                        <h4 className="font-medium text-sm mb-4 flex items-center">
                            <Info className="h-4 w-4 ml-2 text-primary" />
                            خلاصه اطلاعات
                        </h4>

                        {/* Metadata Summary */}
                        <div className="bg-slate-50 p-3 rounded-md mb-4 space-y-2 border text-sm">
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">ذینفع:</span>
                                <span className="font-medium text-foreground">{formData.beneficiaryName || '-'}</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-muted-foreground">مبلغ:</span>
                                <span className="font-medium text-foreground">{formData.amount ? formatAmount(formData.amount) : '0'} <span className="text-[10px] text-muted-foreground">ریال</span></span>
                            </div>
                        </div>

                        <h4 className="font-medium text-sm mb-2 flex items-center">
                            <Paperclip className="h-4 w-4 ml-2" />
                            پیوست‌ها
                            <Badge variant="secondary" className="mr-auto">{attachments.length}</Badge>
                        </h4>

                        {attachments.length === 0 ? (
                            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground text-center p-4 border-2 border-dashed rounded-lg bg-slate-50">
                                <File className="h-8 w-8 mb-2 opacity-20" />
                                <p className="text-xs">هنوز سندی پیوست نشده است</p>
                            </div>
                        ) : (
                            <div className="space-y-2 overflow-y-auto max-h-[250px] pr-1">
                                {attachments.map((file) => (
                                    <div key={file.id} className="group flex items-start justify-between p-2 rounded border bg-card text-card-foreground shadow-sm">
                                        <div className="min-w-0">
                                            <p className="text-xs font-medium truncate" title={file.name}>{file.name}</p>
                                            <div className="flex items-center gap-2 mt-1">
                                                <Badge variant="outline" className="text-[10px] px-1 py-0 h-4">
                                                    {file.source === 'system' ? 'سیستمی' : 'دستی'}
                                                </Badge>
                                                <span className="text-[10px] text-muted-foreground">{file.size}</span>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => removeAttachment(file.id)}
                                            className="text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                                        >
                                            <X className="h-4 w-4" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </Card>
                </div>
            </div>
        </div>
    );
}
