import React, { useState } from 'react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { X, CheckCircle, XCircle, FileText, User, Calendar, Building2, Wallet } from 'lucide-react';
import { Separator } from './ui/separator';

type Transaction = {
  id: number;
  uniqueCode: string;
  status: 'PENDING_L1' | 'PENDING_L2' | 'PENDING_L3' | 'PENDING_L4' | 'APPROVED' | 'REJECTED' | 'DRAFT';
  amount: number;
  budgetCode?: string;
  budgetDescription?: string;
  beneficiaryName?: string;
  createdBy?: string;
  createdAt?: string;
  zoneName?: string;
  departmentName?: string;
  sectionName?: string;
  financialEventName?: string;
  rejectionReason?: string;
};

type TransactionReviewPanelProps = {
  transaction: Transaction;
  onClose: () => void;
  onApprove: (txId: number) => void;
  onReject: (txId: number, reason: string) => void;
};

export function TransactionReviewPanel({
  transaction,
  onClose,
  onApprove,
  onReject
}: TransactionReviewPanelProps) {
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fa-IR').format(amount) + ' ریال';
  };

  const handleReject = () => {
    if (rejectionReason.trim()) {
      onReject(transaction.id, rejectionReason);
    }
  };

  const isPending = transaction.status.startsWith('PENDING_');

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={onClose}
      />

      {/* Side Panel */}
      <div className="fixed left-0 top-0 h-full w-full md:w-[600px] bg-card border-r border-border z-50 overflow-y-auto shadow-2xl animate-in slide-in-from-left duration-300">
        {/* Header */}
        <div className="sticky top-0 bg-card border-b border-border p-4 flex items-center justify-between">
          <div>
            <h2>بررسی تراکنش</h2>
            <p className="text-sm text-muted-foreground font-mono" dir="ltr">
              {transaction.uniqueCode}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Status Badge */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">وضعیت فعلی:</span>
            <span className={`px-3 py-1 rounded text-white text-sm ${transaction.status.startsWith('PENDING_') ? 'bg-amber-500' :
              transaction.status === 'APPROVED' ? 'bg-green-600' :
                transaction.status === 'REJECTED' ? 'bg-red-600' :
                  transaction.status === 'DRAFT' ? 'bg-gray-500' :
                    'bg-gray-500'
              }`}>
              {transaction.status.startsWith('PENDING_') ? 'در انتظار تایید' :
                transaction.status === 'APPROVED' ? 'تایید شده' :
                  transaction.status === 'REJECTED' ? 'رد شده' :
                    transaction.status === 'DRAFT' ? 'پیش‌نویس' :
                      'نامشخص'}
            </span>
          </div>

          <Separator />

          {/* Transaction Details - Grouped Information */}
          <div className="space-y-4">
            {/* General Info */}
            <div className="bg-accent/50 p-4 rounded-lg space-y-3">
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-primary" />
                <h4>اطلاعات عمومی</h4>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-muted-foreground">ایجادکننده</p>
                  <p>{transaction.createdBy}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">تاریخ ایجاد</p>
                  <p>{transaction.createdAt}</p>
                </div>
              </div>
            </div>

            {/* Organization */}
            <div className="bg-accent/50 p-4 rounded-lg space-y-3">
              <div className="flex items-center gap-2">
                <Building2 className="h-4 w-4 text-primary" />
                <h4>واحد سازمانی</h4>
              </div>
              <div className="text-sm space-y-1">
                <p>{transaction.zoneName}</p>
                <p className="text-muted-foreground">← {transaction.departmentName}</p>
                <p className="text-muted-foreground">← {transaction.sectionName}</p>
              </div>
            </div>

            {/* Budget */}
            <div className="bg-accent/50 p-4 rounded-lg space-y-3">
              <div className="flex items-center gap-2">
                <Wallet className="h-4 w-4 text-primary" />
                <h4>ردیف بودجه</h4>
              </div>
              <div className="text-sm space-y-1">
                <p className="font-mono">{transaction.budgetCode}</p>
                <p>{transaction.budgetDescription}</p>
              </div>
            </div>

            {/* Financial Event */}
            <div className="bg-accent/50 p-4 rounded-lg space-y-3">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-primary" />
                <h4>رویداد مالی</h4>
              </div>
              <div className="text-sm">
                <p>{transaction.financialEventName}</p>
              </div>
            </div>

            {/* Beneficiary & Amount */}
            <div className="bg-primary/5 p-4 rounded-lg border-2 border-primary/20 space-y-3">
              <div className="flex items-center gap-2">
                <User className="h-4 w-4 text-primary" />
                <h4>ذینفع و مبلغ</h4>
              </div>
              <div className="space-y-2 text-sm">
                {transaction.beneficiaryName && (
                  <div>
                    <p className="text-muted-foreground">نام ذینفع</p>
                    <p>{transaction.beneficiaryName}</p>
                  </div>
                )}
                <div>
                  <p className="text-muted-foreground">مبلغ تراکنش</p>
                  <p className="text-2xl font-mono text-primary mt-1">
                    {formatCurrency(transaction.amount)}
                  </p>
                </div>
              </div>
            </div>

            {/* Rejection Reason (if rejected) */}
            {transaction.status === 'REJECTED' && transaction.rejectionReason && (
              <div className="bg-destructive/10 border border-destructive/20 p-4 rounded-lg">
                <p className="text-sm text-destructive mb-1">دلیل رد:</p>
                <p className="text-sm">{transaction.rejectionReason}</p>
              </div>
            )}
          </div>

          <Separator />

          {/* Actions - One Decision at a Time */}
          {isPending && (
            <div className="space-y-4">
              {!showRejectForm ? (
                <>
                  <p className="text-sm">تصمیم خود را انتخاب کنید:</p>

                  {/* Primary Action - Approve (Visually Dominant) */}
                  <Button
                    onClick={() => onApprove(transaction.id)}
                    className="w-full h-12 bg-green-600 hover:bg-green-700"
                  >
                    <CheckCircle className="h-5 w-5 ml-2" />
                    تایید تراکنش
                  </Button>

                  {/* Secondary Action - Reject */}
                  <Button
                    onClick={() => setShowRejectForm(true)}
                    variant="outline"
                    className="w-full border-destructive text-destructive hover:bg-destructive/10"
                  >
                    <XCircle className="h-5 w-5 ml-2" />
                    رد تراکنش
                  </Button>
                </>
              ) : (
                /* Reject Form - Progressive Disclosure */
                <div className="space-y-4 bg-destructive/5 p-4 rounded-lg border border-destructive/20">
                  <div>
                    <h4 className="text-destructive">رد تراکنش</h4>
                    <p className="text-sm text-muted-foreground mt-1">
                      لطفاً دلیل رد تراکنش را وارد کنید
                    </p>
                  </div>

                  <Textarea
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    placeholder="دلیل رد تراکنش را به صورت واضح بنویسید..."
                    rows={4}
                    className="resize-none"
                  />

                  <div className="flex gap-2">
                    <Button
                      onClick={handleReject}
                      disabled={!rejectionReason.trim()}
                      className="flex-1 bg-destructive hover:bg-destructive/90"
                    >
                      ثبت رد تراکنش
                    </Button>
                    <Button
                      onClick={() => {
                        setShowRejectForm(false);
                        setRejectionReason('');
                      }}
                      variant="outline"
                    >
                      انصراف
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Info for non-pending transactions */}
          {!isPending && (
            <div className="bg-muted/50 p-4 rounded-lg text-sm text-center text-muted-foreground">
              این تراکنش قبلاً بررسی شده و قابل ویرایش نیست
            </div>
          )}
        </div>
      </div>
    </>
  );
}
