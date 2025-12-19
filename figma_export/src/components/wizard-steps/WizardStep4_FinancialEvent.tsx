import React, { useState, useEffect } from 'react';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { TransactionFormData } from '../TransactionWizard';
import { FileText, Target, Activity, Loader2 } from 'lucide-react';
import {
  fetchFinancialEvents,
  fetchCostCentersForOrg,
  fetchContinuousActionsForOrg,
  FigmaFinancialEvent,
  FigmaCostCenter,
  FigmaContinuousAction
} from '../../services/adapters';

type Props = {
  formData: TransactionFormData;
  updateFormData: (data: Partial<TransactionFormData>) => void;
};

export function WizardStep4_FinancialEvent({ formData, updateFormData }: Props) {
  const [financialEvents, setFinancialEvents] = useState<FigmaFinancialEvent[]>([]);
  const [costCenters, setCostCenters] = useState<FigmaCostCenter[]>([]);
  const [continuousActions, setContinuousActions] = useState<FigmaContinuousAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load data on mount and when org context changes
  // Cost centers and continuous actions use org-filtered APIs from Hesabdary Information.xlsx
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);

      try {
        // Financial events remain global (not org-specific)
        const eventsPromise = fetchFinancialEvents();

        // Cost centers and continuous actions use org-filtered endpoints
        // Only fetch if zoneId is set
        if (formData.zoneId) {
          const [events, centers, actions] = await Promise.all([
            eventsPromise,
            fetchCostCentersForOrg(formData.zoneId, formData.departmentId, formData.sectionId),
            fetchContinuousActionsForOrg(formData.zoneId, formData.departmentId, formData.sectionId)
          ]);
          setFinancialEvents(events);
          setCostCenters(centers);
          setContinuousActions(actions);
        } else {
          // If no zone selected, just load financial events
          const events = await eventsPromise;
          setFinancialEvents(events);
          setCostCenters([]);
          setContinuousActions([]);
        }
      } catch (err) {
        console.error('Failed to load data:', err);
        setError('خطا در بارگیری اطلاعات');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [formData.zoneId, formData.departmentId, formData.sectionId]);

  const handleFinancialEventChange = (eventId: string) => {
    const event = financialEvents.find(e => e.id === parseInt(eventId));
    if (event) {
      updateFormData({
        financialEventId: event.id,
        financialEventCode: event.code,
        financialEventName: event.name,
      });
    }
  };

  const handleCostCenterChange = (centerId: string) => {
    const center = costCenters.find(c => c.id === parseInt(centerId));
    if (center) {
      updateFormData({
        costCenterId: center.id,
        costCenterCode: center.code,
        costCenterName: center.name,
      });
    }
  };

  const handleContinuousActionChange = (actionId: string) => {
    const action = continuousActions.find(a => a.id === parseInt(actionId));
    if (action) {
      updateFormData({
        continuousActionId: action.id,
        continuousActionCode: action.code,
        continuousActionName: action.name,
      });
    }
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
    return (
      <div className="text-center py-12 text-red-600">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3>رویداد مالی و مرکز هزینه</h3>
        <p className="text-sm text-muted-foreground mt-1">
          اطلاعات دسته‌بندی مالی تراکنش را مشخص کنید
        </p>
      </div>

      {/* Financial Event - Required */}
      <div className="space-y-3">
        <Label htmlFor="financialEvent">
          رویداد مالی <span className="text-destructive">*</span>
        </Label>
        <div className="relative">
          <FileText className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10" />
          <Select
            value={formData.financialEventId?.toString()}
            onValueChange={handleFinancialEventChange}
          >
            <SelectTrigger id="financialEvent" className="pr-10">
              <SelectValue placeholder="انتخاب رویداد مالی" />
            </SelectTrigger>
            <SelectContent>
              {financialEvents.map(event => (
                <SelectItem key={event.id} value={event.id.toString()}>
                  {event.name} (کد: {event.code})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <p className="text-xs text-muted-foreground">
          نوع عملیات مالی که در حال انجام است
        </p>
      </div>

      {/* Cost Center - Required (from Hesabdary Information.xlsx) */}
      <div className="space-y-3">
        <Label htmlFor="costCenter">
          مرکز هزینه <span className="text-destructive">*</span>
        </Label>
        <div className="relative">
          <Target className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10" />
          <Select
            value={formData.costCenterId?.toString()}
            onValueChange={handleCostCenterChange}
          >
            <SelectTrigger id="costCenter" className="pr-10">
              <SelectValue placeholder={
                costCenters.length === 0
                  ? "مرکز هزینه‌ای برای این واحد یافت نشد"
                  : "انتخاب مرکز هزینه"
              } />
            </SelectTrigger>
            <SelectContent>
              {costCenters.map(center => (
                <SelectItem key={center.id} value={center.id.toString()}>
                  {center.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <p className="text-xs text-muted-foreground">
          مرکز مسئول تحقق این هزینه (از فایل اطلاعات حسابداری)
        </p>
      </div>

      {/* Continuous Action - Optional (from Hesabdary Information.xlsx - سرفصل جزء) */}
      <div className="space-y-3">
        <Label htmlFor="continuousAction">
          اقدام مستمر (سرفصل جزء) <span className="text-muted-foreground">(اختیاری)</span>
        </Label>
        <div className="relative">
          <Activity className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground z-10" />
          <Select
            value={formData.continuousActionId?.toString()}
            onValueChange={handleContinuousActionChange}
          >
            <SelectTrigger id="continuousAction" className="pr-10">
              <SelectValue placeholder={
                continuousActions.length === 0
                  ? "سرفصل جزء‌ای برای این واحد یافت نشد"
                  : "انتخاب اقدام مستمر"
              } />
            </SelectTrigger>
            <SelectContent>
              {continuousActions.map(action => (
                <SelectItem key={action.id} value={action.id.toString()}>
                  {action.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <p className="text-xs text-muted-foreground">
          سرفصل جزء از فایل اطلاعات حسابداری
        </p>
      </div>

      {/* Summary */}
      {formData.financialEventId && formData.costCenterId && (
        <div className="bg-accent p-4 rounded-lg border border-border space-y-2">
          <p className="text-sm text-muted-foreground">دسته‌بندی مالی:</p>
          <div className="space-y-1 text-sm">
            <p>
              <span className="text-muted-foreground">رویداد مالی:</span>{' '}
              {formData.financialEventName} ({formData.financialEventCode})
            </p>
            <p>
              <span className="text-muted-foreground">مرکز هزینه:</span>{' '}
              {formData.costCenterName}
            </p>
            {formData.continuousActionName && (
              <p>
                <span className="text-muted-foreground">اقدام مستمر:</span>{' '}
                {formData.continuousActionName}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

