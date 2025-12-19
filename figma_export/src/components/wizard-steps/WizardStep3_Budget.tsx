import React, { useState, useEffect } from 'react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { TransactionFormData } from '../TransactionWizard';
import { Search, CheckCircle2, Loader2 } from 'lucide-react';
import { fetchBudgetsForOrg, FigmaBudgetItem } from '../../services/adapters';

type Props = {
  formData: TransactionFormData;
  updateFormData: (data: Partial<TransactionFormData>) => void;
};

// Internal type for UI display with additional calculated fields
interface BudgetDisplayItem extends FigmaBudgetItem {
  budgetType?: string;
}

export function WizardStep3_Budget({ formData, updateFormData }: Props) {
  const [searchTerm, setSearchTerm] = useState('');
  const [allBudgets, setAllBudgets] = useState<BudgetDisplayItem[]>([]);
  const [filteredBudgets, setFilteredBudgets] = useState<BudgetDisplayItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load budgets automatically when org context is set (zone is required)
  // NO trustee selection needed - budgets are derived from org context
  useEffect(() => {
    const loadBudgets = async () => {
      // Need at least zone to load budgets
      if (!formData.zoneId) {
        setAllBudgets([]);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        // Use new org-based API - no trustee parameter needed
        const budgets = await fetchBudgetsForOrg(
          formData.zoneId,
          formData.departmentId,
          formData.sectionId
        );

        // Map to display format with budgetType mapping
        const displayItems: BudgetDisplayItem[] = budgets.map(b => ({
          ...b,
          budgetType: b.type === 'expense' ? 'expense' : b.type === 'capital' ? 'capital' : 'expense'
        }));
        setAllBudgets(displayItems);
      } catch (err) {
        console.error('Failed to load budgets:', err);
        setError('خطا در بارگیری ردیف‌های بودجه');
      } finally {
        setLoading(false);
      }
    };

    loadBudgets();
  }, [formData.zoneId, formData.departmentId, formData.sectionId]);

  // Filter budgets by type and search term
  useEffect(() => {
    let items = allBudgets;

    // Filter by transaction type if set
    if (formData.transactionType) {
      items = items.filter(item => item.budgetType === formData.transactionType);
    }

    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      items = items.filter(item =>
        item.code.toLowerCase().includes(term) ||
        item.name.toLowerCase().includes(term)
      );
    }

    setFilteredBudgets(items);
  }, [searchTerm, formData.transactionType, allBudgets]);

  const handleSelectBudget = (budget: BudgetDisplayItem) => {
    updateFormData({
      budgetItemId: budget.id,
      budgetCode: budget.code,
      budgetDescription: budget.name,
      budgetType: budget.budgetType,
      availableBudget: budget.remaining,
      budgetRowType: budget.rowType, // For form selection in Step 5
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

      {/* Budget List as Searchable List */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label>لیست ردیف‌های بودجه</Label>
          {filteredBudgets.length > 0 && (
            <span className="text-xs text-muted-foreground">
              {filteredBudgets.length} ردیف ({formData.transactionType === 'expense' ? 'هزینه‌ای' : 'سرمایه‌ای'})
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
            ردیف بودجه‌ای یافت نشد
          </div>
        ) : (
          <div
            className="border rounded-lg overflow-y-auto"
            style={{
              maxHeight: '240px', // ارتفاع ثابت برای نمایش حدود 3 ردیف
              scrollbarWidth: 'thin', // برای فایرفاکس
              scrollbarColor: '#94a3b8 transparent' // رنگ اسکرول بار
            }}
          >
            <style>{`
              /* استایل اختصاصی برای اسکرول بار وب‌کیت (کروم، اج) داخل همین کامپوننت */
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

                      {/* Budget Info - Main */}
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
