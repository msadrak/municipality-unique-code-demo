import React, { useEffect, useState } from 'react';
import { FileText, Loader2, Target } from 'lucide-react';

import { FINANCIAL_EVENTS } from '../../lib/financialEvents';
import { FigmaCostCenter } from '../../services/adapters';
import { TransactionFormData } from '../TransactionWizard';
import { Label } from '../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';

type Props = {
  formData: TransactionFormData;
  updateFormData: (data: Partial<TransactionFormData>) => void;
};

export function WizardStep4_FinancialEvent({ formData, updateFormData }: Props) {
  const [costCenters, setCostCenters] = useState<FigmaCostCenter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);

      try {
        // MOCK: Hardcoded data to unblock wizard flow.
        const mockCostCenters: FigmaCostCenter[] = [
          { id: 1, code: '201', name: 'مرکز هزینه ستاد مرکزی' },
          { id: 2, code: '202', name: 'مرکز هزینه منطقه ۱ - امور شهری' },
          { id: 3, code: '203', name: 'مرکز هزینه منطقه ۱ - عمرانی' },
        ];

        setCostCenters(mockCostCenters);
      } catch (err) {
        console.error('Failed to load data:', err);
        setError('خطا در بارگیری اطلاعات');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [formData.zoneId, formData.departmentId, formData.sectionId]);

  const handleFinancialEventChange = (eventValue: string) => {
    const event = FINANCIAL_EVENTS.find((item) => item.value === eventValue);
    if (!event) return;

    updateFormData({
      financialEventId: undefined,
      financialEventCode: event.value,
      financialEventName: event.label,
    });
  };

  const handleCostCenterChange = (centerId: string) => {
    const center = costCenters.find((item) => item.id === Number.parseInt(centerId, 10));
    if (!center) return;

    updateFormData({
      costCenterId: center.id,
      costCenterCode: center.code,
      costCenterName: center.name,
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="mr-3 text-muted-foreground">در حال بارگیری...</span>
      </div>
    );
  }

  if (error) {
    return <div className="py-12 text-center text-red-600">{error}</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h3>رویداد مالی و مرکز هزینه</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          اطلاعات دسته بندی مالی تراکنش را مشخص کنید.
        </p>
      </div>

      <div className="space-y-3">
        <Label htmlFor="financialEvent">
          رویداد مالی <span className="text-destructive">*</span>
        </Label>
        <div className="relative">
          <FileText className="absolute right-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Select value={formData.financialEventCode} onValueChange={handleFinancialEventChange}>
            <SelectTrigger id="financialEvent" className="pr-10">
              <SelectValue placeholder="انتخاب رویداد مالی" />
            </SelectTrigger>
            <SelectContent>
              {FINANCIAL_EVENTS.map((event) => (
                <SelectItem key={event.value} value={event.value}>
                  {event.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <p className="text-xs text-muted-foreground">نوع عملیات مالی که در حال انجام است.</p>
      </div>

      <div className="space-y-3">
        <Label htmlFor="costCenter">
          مرکز هزینه <span className="text-destructive">*</span>
        </Label>
        <div className="relative">
          <Target className="absolute right-3 top-1/2 z-10 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Select value={formData.costCenterId?.toString()} onValueChange={handleCostCenterChange}>
            <SelectTrigger id="costCenter" className="pr-10">
              <SelectValue
                placeholder={
                  costCenters.length === 0
                    ? 'مرکز هزینه‌ای برای این واحد یافت نشد'
                    : 'انتخاب مرکز هزینه'
                }
              />
            </SelectTrigger>
            <SelectContent>
              {costCenters.map((center) => (
                <SelectItem key={center.id} value={center.id.toString()}>
                  {center.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <p className="text-xs text-muted-foreground">
          مرکز مسئول تحقق این هزینه (از فایل اطلاعات حسابداری).
        </p>
      </div>

      {formData.financialEventCode && formData.costCenterId && (
        <div className="space-y-2 rounded-lg border border-border bg-accent p-4">
          <p className="text-sm text-muted-foreground">دسته بندی مالی:</p>
          <div className="space-y-1 text-sm">
            <p>
              <span className="text-muted-foreground">رویداد مالی:</span>{' '}
              {formData.financialEventName} ({formData.financialEventCode})
            </p>
            <p>
              <span className="text-muted-foreground">مرکز هزینه:</span>{' '}
              {formData.costCenterName}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
