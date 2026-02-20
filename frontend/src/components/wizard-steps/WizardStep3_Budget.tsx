import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { TransactionFormData } from '../TransactionWizard';
import { Search, CheckCircle2, Loader2, Filter, Wallet, ArrowLeft, Activity, Landmark } from 'lucide-react';
import { fetchBudgetsByActivity } from '../../services/adapters';
import { ActivityConstraint } from '../../types/dashboard';
import { formatRial } from '../../lib/utils';

type Props = {
  formData: TransactionFormData;
  updateFormData: (data: Partial<TransactionFormData>) => void;
  constraints?: ActivityConstraint | null;  // Constraint from selected activity
  onConfirmAndNext?: () => void;
};

// Internal type for UI display (now based on BudgetRowResponse)
interface BudgetDisplayItem {
  id: number;
  code: string;
  name: string;
  allocated: number;
  remaining: number;
  status: 'AVAILABLE' | 'LOW' | 'EXHAUSTED';
  utilization_percent: number;
  budgetType?: string;
}

type BudgetSummaryPanelProps = {
  selectedBudget: BudgetDisplayItem | null;
  selectedActivityName?: string;
  onConfirmAndNext?: () => void;
  onProceedToContract?: () => void;
  getBudgetStatus: (remaining: number, allocated: number) => 'sufficient' | 'warning' | 'critical';
};

function BudgetSummaryPanel({
  selectedBudget,
  selectedActivityName,
  onConfirmAndNext,
  onProceedToContract,
  getBudgetStatus,
}: BudgetSummaryPanelProps) {
  if (!selectedBudget) {
    return (
      <div className="bg-white rounded-lg border border-dashed border-slate-300 p-5 text-center shadow-sm">
        <Wallet className="h-8 w-8 text-slate-400 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">لطفاً یک ردیف بودجه را انتخاب کنید</p>
      </div>
    );
  }

  const budgetStatus = getBudgetStatus(selectedBudget.remaining, selectedBudget.allocated);
  const remainingCreditClassName =
    budgetStatus === 'critical'
      ? 'text-red-600'
      : budgetStatus === 'warning'
        ? 'text-amber-600'
        : 'text-green-600';

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm space-y-4">
        <div className="flex items-center gap-2 text-slate-700">
          <Activity className="h-4 w-4" />
          <p className="text-xs text-muted-foreground">فعالیت انتخاب شده</p>
        </div>
        <p className="text-sm font-medium leading-6 text-right">{selectedActivityName || 'نامشخص'}</p>

        <div className="border-t border-slate-100 pt-4">
          <div className="flex items-center gap-2 text-slate-700">
            <Landmark className="h-4 w-4" />
            <p className="text-xs text-muted-foreground">کد بودجه</p>
          </div>
          <p dir="ltr" className="font-mono text-xl font-bold mt-1 tracking-wide text-left tabular-nums">{selectedBudget.code}</p>
        </div>

        <div className="border-t border-slate-100 pt-4">
          <p className="text-xs text-muted-foreground text-right">مانده اعتبار</p>
          <p className={`mt-1 text-lg font-semibold font-mono-num ${remainingCreditClassName}`}>
            {formatRial(selectedBudget.remaining)}
          </p>
        </div>
      </div>

      <Button
        type="button"
        variant="outline"
        className="w-full"
        onClick={onConfirmAndNext}
        disabled={!onConfirmAndNext}
      >
        تایید و ادامه
        <ArrowLeft className="h-4 w-4 mr-2" />
      </Button>
      <Button
        type="button"
        className="w-full"
        onClick={onProceedToContract}
        disabled={!onProceedToContract}
      >
        ثبت قرارداد برای این بودجه
        <ArrowLeft className="h-4 w-4 mr-2" />
      </Button>
    </div>
  );
}

export function WizardStep3_Budget({ formData, updateFormData, constraints, onConfirmAndNext }: Props) {
  const [searchTerm, setSearchTerm] = useState('');
  const [allBudgets, setAllBudgets] = useState<BudgetDisplayItem[]>([]);
  const [filteredBudgets, setFilteredBudgets] = useState<BudgetDisplayItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const toNumber = (value: unknown) => {
    if (typeof value === 'number') return value;
    if (typeof value === 'string' && value.trim() !== '') return Number(value);
    return 0;
  };

  // Load budgets when activity is selected (Zero-Trust: activity-based filtering)
  useEffect(() => {
    const loadBudgets = async () => {
      // REQUIRE: subsystemActivityId (activity_id) to fetch budgets
      if (!formData.subsystemActivityId) {
        console.log("⚡ Budget fetch skipped: No activity selected");
        setAllBudgets([]);
        setError(null);
        return;
      }

      const orgUnitFilterId = formData.sectionId ?? formData.zoneId;
      console.log("⚡ Triggering fetch for Activity:", formData.subsystemActivityId, "OrgUnit:", orgUnitFilterId);
      setLoading(true);
      setError(null);

      try {
        // NEW ZERO-TRUST API: Fetch by activity_id + optional zone_id
        const budgetRows = await fetchBudgetsByActivity(
          formData.subsystemActivityId,
          orgUnitFilterId,
          '1403'  // Fiscal year
        );

        console.log("📊 Budget rows received in component:", budgetRows.length);

        // Map to display format
        const displayItems: BudgetDisplayItem[] = budgetRows.map((row: any, index: number) => {
          const budgetRowId =
            row.budget_row_id ?? row.budgetRowId ?? row.id ?? index;
          const budgetCode =
            row.budget_code ?? row.budgetCode ?? row.budget_coding ?? row.budgetCoding ?? row.code ?? '';
          const description = row.description ?? row.title ?? '';
          // Accept both snake_case and camelCase to avoid API naming mismatch.
          const totalApproved =
            row.total_approved ?? row.totalApproved ?? row.approved_amount ?? row.approvedAmount ?? row.approved ?? 0;
          const remainingAvailable =
            row.remaining_available ?? row.remainingAvailable ?? row.remaining_balance ?? row.remainingBalance ?? row.remaining ?? 0;
          const status = row.status ?? 'AVAILABLE';
          const utilizationPercent =
            row.utilization_percent ?? row.utilizationPercent ?? 0;
          const budgetType = row.budget_type ?? row.budgetType ?? undefined;

          return {
            id: budgetRowId,
            code: String(budgetCode),
            name: String(description),
            allocated: toNumber(totalApproved),
            remaining: toNumber(remainingAvailable),
            status,
            utilization_percent: toNumber(utilizationPercent),
            budgetType,
          };
        });

        setAllBudgets(displayItems);

        if (displayItems.length === 0) {
          console.warn("⚠️ No budget rows returned for activity", formData.subsystemActivityId);
          setError('هیچ ردیف بودجه‌ای برای این فعالیت یافت نشد');
        }
      } catch (err) {
        console.error('❌ Failed to load budgets:', err);
        console.error('Error details:', err instanceof Error ? err.message : String(err));
        setError('خطا در بارگیری ردیف‌های بودجه');
      } finally {
        setLoading(false);
      }
    };

    loadBudgets();
  }, [formData.subsystemActivityId, formData.zoneId]);

  // Derive active constraint info for display
  const constraintInfo = useMemo(() => {
    if (!constraints) return null;

    const parts: string[] = [];

    if (constraints.budget_code_pattern) {
      parts.push(`کد: ${constraints.budget_code_pattern}`);
    }

    if (constraints.allowed_budget_types?.length) {
      const typeLabels = constraints.allowed_budget_types.map(t =>
        t === 'expense' ? 'هزینه‌ای' : t === 'capital' ? 'سرمایه‌ای' : t
      );
      parts.push(`نوع: ${typeLabels.join(', ')}`);
    }

    return parts.length > 0 ? parts.join(' | ') : null;
  }, [constraints]);

  // Filter budgets by type, search term, and CONSTRAINTS
  useEffect(() => {
    let items = allBudgets;

    // 1. Filter by constraint: allowed_budget_types
    if (constraints?.allowed_budget_types?.length) {
      // FIXED: Allow undefined budgetType (trust the API result), or check against constraint
      items = items.filter(item =>
        !item.budgetType ||
        constraints.allowed_budget_types!.includes(item.budgetType)
      );
    } else if (formData.transactionType) {
      // Fallback to transaction type if no constraint
      // FIXED: Allow items with undefined budgetType (new API data), otherwise they get filtered out
      items = items.filter(item => !item.budgetType || item.budgetType === formData.transactionType);
    }

    // 2. Filter by constraint: budget_code_pattern (SQL LIKE pattern)
    if (constraints?.budget_code_pattern) {
      const pattern = constraints.budget_code_pattern;

      // Convert SQL LIKE pattern to regex
      // "1%" -> starts with "1"
      // "%123" -> ends with "123"
      // "%123%" -> contains "123"
      if (pattern.endsWith('%') && !pattern.startsWith('%')) {
        // Starts with pattern: "1%" or "10%"
        const prefix = pattern.slice(0, -1);
        items = items.filter(item => item.code.startsWith(prefix));
      } else if (pattern.startsWith('%') && !pattern.endsWith('%')) {
        // Ends with pattern: "%01"
        const suffix = pattern.slice(1);
        items = items.filter(item => item.code.endsWith(suffix));
      } else if (pattern.startsWith('%') && pattern.endsWith('%')) {
        // Contains pattern: "%123%"
        const substring = pattern.slice(1, -1);
        items = items.filter(item => item.code.includes(substring));
      } else {
        // Exact match
        items = items.filter(item => item.code === pattern);
      }
    }

    // 3. Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      items = items.filter(item =>
        item.code.toLowerCase().includes(term) ||
        item.name.toLowerCase().includes(term)
      );
    }

    setFilteredBudgets(items);
  }, [searchTerm, formData.transactionType, allBudgets, constraints]);

  const handleSelectBudget = (budget: BudgetDisplayItem) => {
    updateFormData({
      budgetItemId: budget.id,
      budgetCode: budget.code,
      budgetDescription: budget.name,
      budgetType: budget.budgetType,
      availableBudget: budget.remaining,
      // budgetRowType removed - not available in new Zero-Trust API
    });
  };

  const formatCurrency = (amount: number) => formatRial(amount);

  const getBudgetStatus = (remaining: number, allocated: number) => {
    if (!allocated || allocated === 0) return 'sufficient';
    const percentage = (remaining / allocated) * 100;
    if (percentage > 20) return 'sufficient';
    if (percentage > 5) return 'warning';
    return 'critical';
  };

  const selectedBudget = useMemo(() => {
    if (!formData.budgetItemId) return null;
    return allBudgets.find((budget) => budget.id === formData.budgetItemId) ?? null;
  }, [allBudgets, formData.budgetItemId]);

  const handleProceedToContract = () => {
    if (!selectedBudget) return;
    navigate(`/contracts/new?budgetId=${selectedBudget.id}`);
  };

  return (
    <div className="space-y-6">
      <div>
        <h3>انتخاب ردیف بودجه</h3>
        <p className="text-sm text-muted-foreground mt-1">
          ردیف بودجه مناسب را بر اساس واحد سازمانی انتخابی انتخاب نمایید
        </p>
      </div>

      {/* Constraint Banner - shows active filtering */}
      {constraintInfo && (
        <div className="bg-primary/10 border border-primary/20 px-4 py-3 rounded-lg flex items-center gap-3">
          <Filter className="h-4 w-4 text-primary flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-primary">فیلتر فعال بر اساس فعالیت</p>
            <p className="text-xs text-muted-foreground truncate">{constraintInfo}</p>
          </div>
          <Badge variant="secondary" className="text-xs flex-shrink-0">
            {filteredBudgets.length} نتیجه
          </Badge>
        </div>
      )}

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12 lg:col-span-8 space-y-4">
          {/* Search Budget */}
          <div className="space-y-3">
            <Label htmlFor="budgetSearch">جستجو در ردیف‌های بودجه</Label>
            <div className="relative">
              <Search className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                id="budgetSearch"
                placeholder="جستجو بر اساس کد یا شرح ردیف..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pr-10 bg-white"
                disabled={!formData.subsystemActivityId}
              />
            </div>
          </div>

          {/* Budget List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>لیست ردیف‌های بودجه</Label>
              {filteredBudgets.length > 0 && (
                <span className="text-xs text-muted-foreground">
                  {filteredBudgets.length} ردیف
                  {constraints?.allowed_budget_types?.length === 1 && (
                    <> ({constraints.allowed_budget_types[0] === 'expense' ? 'هزینه‌ای' : 'سرمایه‌ای'})</>
                  )}
                </span>
              )}
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-8 bg-white rounded-lg border border-slate-200">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="mr-2 text-muted-foreground">در حال بارگیری...</span>
              </div>
            ) : error ? (
              <div className="text-center py-8 text-red-600 bg-white rounded-lg border border-red-100">
                {error}
              </div>
            ) : filteredBudgets.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground bg-white rounded-lg border border-slate-200">
                {constraints ? 'ردیف بودجه‌ای مطابق با محدودیت فعالیت یافت نشد' : 'ردیف بودجه‌ای یافت نشد'}
              </div>
            ) : (
              <div className="space-y-3 max-h-[480px] overflow-y-auto pl-1">
                {filteredBudgets.map((budgetRow) => {
                  if (!budgetRow) return null;
                  const budget = budgetRow;
                  const status = getBudgetStatus(budget.remaining, budget.allocated);
                  const isSelected = formData.budgetItemId === budget.id;
                  const statusBadgeClass =
                    status === 'critical'
                      ? 'bg-red-100 text-red-700'
                      : status === 'warning'
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-green-100 text-green-700';

                  return (
                    <button
                      key={budget.id}
                      type="button"
                      onClick={() => handleSelectBudget(budget)}
                      className={`w-full text-right bg-white shadow-sm rounded-lg border p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-blue-500 ${isSelected
                        ? 'border-l-4 border-green-500 bg-green-50/50 border-green-200 scale-[1.01] shadow-md'
                        : 'border-slate-200'
                        }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-1 flex-shrink-0">
                          {isSelected ? (
                            <CheckCircle2 className="h-5 w-5 text-green-600" />
                          ) : (
                            <div className="h-5 w-5 rounded-full border border-slate-300" />
                          )}
                        </div>

                        <div className="flex-1 min-w-0 space-y-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span dir="ltr" className="font-mono font-semibold text-base text-left tabular-nums">{budget.code}</span>
                            {budget.budgetType && (
                              <span className={`text-xs px-2 py-0.5 rounded ${budget.budgetType === 'expense'
                                ? 'bg-blue-100 text-blue-700'
                                : 'bg-purple-100 text-purple-700'
                                }`}>
                                {budget.budgetType === 'expense' ? 'هزینه‌ای' : 'سرمایه‌ای'}
                              </span>
                            )}
                            <span className={`text-xs px-2 py-0.5 rounded ${statusBadgeClass}`}>
                              {status === 'critical' ? 'اعتبار کم' : status === 'warning' ? 'نزدیک سقف' : 'مناسب'}
                            </span>
                          </div>
                          <p className="text-sm text-slate-600 leading-6 line-clamp-2 text-right">{budget.name}</p>
                        </div>

                        <div className="text-left flex-shrink-0">
                          <p className="text-xs text-muted-foreground">اعتبار مصوب</p>
                          <p className="font-mono-num text-sm font-semibold">{formatCurrency(budget.allocated)}</p>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div className="col-span-12 lg:col-span-4">
          <div className="sticky top-4 space-y-3">
            <Label>خلاصه بودجه انتخابی</Label>
            <BudgetSummaryPanel
              selectedBudget={selectedBudget}
              selectedActivityName={formData.subsystemActivityTitle}
              onConfirmAndNext={selectedBudget ? onConfirmAndNext : undefined}
              onProceedToContract={selectedBudget ? handleProceedToContract : undefined}
              getBudgetStatus={getBudgetStatus}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
