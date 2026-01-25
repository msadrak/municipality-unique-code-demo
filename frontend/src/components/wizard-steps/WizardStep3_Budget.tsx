import React, { useState, useEffect, useMemo } from 'react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { TransactionFormData } from '../TransactionWizard';
import { Search, CheckCircle2, Loader2, Filter, AlertCircle } from 'lucide-react';
import { fetchBudgetsByActivity, BudgetRowResponse, adaptBudgetRowToFigma, FigmaBudgetItem } from '../../services/adapters';
import { ActivityConstraint } from '../../types/dashboard';

type Props = {
  formData: TransactionFormData;
  updateFormData: (data: Partial<TransactionFormData>) => void;
  constraints?: ActivityConstraint | null;  // Constraint from selected activity
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

export function WizardStep3_Budget({ formData, updateFormData, constraints }: Props) {
  const [searchTerm, setSearchTerm] = useState('');
  const [allBudgets, setAllBudgets] = useState<BudgetDisplayItem[]>([]);
  const [filteredBudgets, setFilteredBudgets] = useState<BudgetDisplayItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

      console.log("⚡ Triggering fetch for Activity:", formData.subsystemActivityId, "Zone:", formData.zoneId);
      setLoading(true);
      setError(null);

      try {
        // NEW ZERO-TRUST API: Fetch by activity_id + optional zone_id
        const budgetRows = await fetchBudgetsByActivity(
          formData.subsystemActivityId,
          formData.zoneId,
          '1403'  // Fiscal year
        );

        console.log("📊 Budget rows received in component:", budgetRows.length);

        // Map to display format
        const displayItems: BudgetDisplayItem[] = budgetRows.map(row => ({
          id: row.budget_row_id,
          code: row.budget_code,
          name: row.description,
          allocated: row.total_approved,
          remaining: row.remaining_available,
          status: row.status,
          utilization_percent: row.utilization_percent,
          budgetType: undefined, // Not needed for new API
        }));

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

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fa-IR').format(amount) + ' ریال';
  };

  const getBudgetStatus = (remaining: number, allocated: number) => {
    if (!allocated || allocated === 0) return 'sufficient';
    const percentage = (remaining / allocated) * 100;
    if (percentage > 20) return 'sufficient';
    if (percentage > 5) return 'warning';
    return 'critical';
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
            className="pr-10"
            disabled={!formData.zoneId}
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
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="mr-2 text-muted-foreground">در حال بارگیری...</span>
          </div>
        ) : error ? (
          <div className="text-center py-8 text-red-600">
            {error}
          </div>
        ) : !formData.zoneId ? (
          <div className="text-center py-8 text-muted-foreground">
            ابتدا واحد سازمانی را انتخاب کنید
          </div>
        ) : filteredBudgets.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            {constraints ? 'ردیف بودجه‌ای مطابق با محدودیت فعالیت یافت نشد' : 'ردیف بودجه‌ای یافت نشد'}
          </div>
        ) : (
          <div
            className="border rounded-lg overflow-y-auto"
            style={{
              maxHeight: '240px',
              scrollbarWidth: 'thin',
              scrollbarColor: '#94a3b8 transparent'
            }}
          >
            <style>{`
              .budget-list-container::-webkit-scrollbar {
                width: 6px;
              }
              .budget-list-container::-webkit-scrollbar-track {
                background: transparent;
              }
              .budget-list-container::-webkit-scrollbar-thumb {
                background-color: transparent;
                border-radius: 20px;
              }
              .budget-list-container:hover::-webkit-scrollbar-thumb {
                background-color: #94a3b8;
              }
            `}</style>
            <div className="budget-list-container h-full">
              {filteredBudgets.map((budget) => {
                const status = getBudgetStatus(budget.remaining, budget.allocated);
                const isSelected = formData.budgetItemId === budget.id;

                return (
                  <div
                    key={budget.id}
                    onClick={() => handleSelectBudget(budget)}
                    className={`p-4 border-b last:border-b-0 cursor-pointer transition-colors hover:bg-accent/50 ${isSelected ? 'bg-primary/5 border-r-4 border-r-primary' : ''
                      }`}
                  >
                    <div className="flex items-start gap-3">
                      {/* Selection Indicator */}
                      <div className="mt-1 flex-shrink-0">
                        {isSelected && (
                          <CheckCircle2 className="h-5 w-5 text-primary" />
                        )}
                      </div>

                      {/* Budget Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono text-sm">{budget.code}</span>
                          <span className={`text-xs px-2 py-0.5 rounded ${budget.budgetType === 'expense'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-purple-100 text-purple-700'
                            }`}>
                            {budget.budgetType === 'expense' ? 'هزینه‌ای' : 'سرمایه‌ای'}
                          </span>
                          {status === 'critical' && (
                            <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">
                              بودجه محدود
                            </span>
                          )}
                          {status === 'warning' && (
                            <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded">
                              توجه
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground mt-1 truncate">
                          {budget.name}
                        </p>
                      </div>

                      {/* Budget Amount */}
                      <div className="text-left flex-shrink-0">
                        <p className="text-xs text-muted-foreground">مانده</p>
                        <p className="font-mono text-sm">{formatCurrency(budget.remaining)}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Selected Budget Summary */}
      {formData.budgetItemId && (
        <div className="bg-accent p-4 rounded-lg border border-border">
          <p className="text-sm text-muted-foreground mb-2">ردیف بودجه انتخاب شده:</p>
          <p className="font-mono">{formData.budgetCode}</p>
          <p className="text-sm mt-1">{formData.budgetDescription}</p>
          <p className="text-sm mt-2 text-green-700">
            مانده قابل استفاده: {formatCurrency(formData.availableBudget || 0)}
          </p>
        </div>
      )}
    </div>
  );
}
