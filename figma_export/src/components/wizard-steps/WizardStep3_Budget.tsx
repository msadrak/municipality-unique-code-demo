import React, { useState, useEffect } from 'react';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { TransactionFormData } from '../TransactionWizard';
import { Search, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../ui/accordion';
import { fetchBudgets, FigmaBudgetItem } from '../../services/adapters';

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

  // Load budgets when zone changes
  useEffect(() => {
    const loadBudgets = async () => {
      if (!formData.zoneCode) {
        setAllBudgets([]);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const budgets = await fetchBudgets(formData.zoneCode);
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
  }, [formData.zoneCode]);

  // Filter budgets by type and search term
  useEffect(() => {
    let items = allBudgets;

    // Filter by transaction type if set
    if (formData.transactionType) {
      items = items.filter(item => item.budgetType === formData.transactionType);
    }

    // Filter by search term
    if (searchTerm) {
      items = items.filter(item =>
        item.code.includes(searchTerm) ||
        item.name.includes(searchTerm)
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
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fa-IR').format(amount) + ' ریال';
  };

  const getBudgetStatus = (remaining: number, allocated: number) => {
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
          ردیف بودجه مناسب را انتخاب کنید (فقط ردیف‌های {formData.transactionType === 'expense' ? 'هزینه‌ای' : 'سرمایه‌ای'} نمایش داده می‌شود)
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
          />
        </div>
      </div>

      {/* Budget List - Complex Data in Accordion */}
      <div className="space-y-3">
        <Label>لیست ردیف‌های بودجه</Label>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="mr-2 text-muted-foreground">در حال بارگیری...</span>
          </div>
        ) : error ? (
          <div className="text-center py-8 text-red-600">
            {error}
          </div>
        ) : !formData.zoneCode ? (
          <div className="text-center py-8 text-muted-foreground">
            ابتدا واحد سازمانی را انتخاب کنید
          </div>
        ) : filteredBudgets.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            ردیف بودجه‌ای یافت نشد
          </div>
        ) : (
          <Accordion type="single" collapsible className="space-y-2">
            {filteredBudgets.map((budget) => {
              const status = getBudgetStatus(budget.remaining, budget.allocated);
              const isSelected = formData.budgetItemId === budget.id;

              return (
                <AccordionItem
                  key={budget.id}
                  value={budget.id.toString()}
                  className={`border rounded-lg ${isSelected ? 'border-primary bg-primary/5' : 'border-border'
                    }`}
                >
                  <AccordionTrigger className="px-4 hover:no-underline">
                    <div className="flex items-start gap-3 flex-1 text-right">
                      {/* Selection Indicator */}
                      <div className="mt-1">
                        {isSelected && (
                          <CheckCircle2 className="h-5 w-5 text-primary" />
                        )}
                      </div>

                      {/* Budget Info */}
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-mono">{budget.code}</span>
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
                        <p className="text-sm text-muted-foreground mt-0.5">
                          {budget.name}
                        </p>
                        <p className="text-sm mt-1">
                          مانده قابل استفاده: <span className="font-mono">{formatCurrency(budget.remaining)}</span>
                        </p>
                      </div>
                    </div>
                  </AccordionTrigger>

                  {/* Detailed Budget Info - Hidden by Default */}
                  <AccordionContent className="px-4 pb-4">
                    <div className="space-y-3 pt-3 border-t">
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <p className="text-muted-foreground">تخصیص</p>
                          <p className="font-mono">{formatCurrency(budget.allocated)}</p>
                        </div>
                        <div>
                          <p className="text-muted-foreground">مانده</p>
                          <p className="font-mono">{formatCurrency(budget.remaining)}</p>
                        </div>
                      </div>

                      {status === 'critical' && (
                        <div className="bg-red-50 border border-red-200 p-3 rounded flex items-start gap-2 text-sm text-red-800">
                          <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                          <p>بودجه باقیمانده این ردیف کمتر از ۵٪ است. لطفاً با احتیاط استفاده کنید.</p>
                        </div>
                      )}

                      <button
                        onClick={() => handleSelectBudget(budget)}
                        className="w-full bg-primary text-primary-foreground py-2 rounded hover:bg-primary/90 transition-colors"
                      >
                        {isSelected ? 'ردیف انتخاب شده' : 'انتخاب این ردیف'}
                      </button>
                    </div>
                  </AccordionContent>
                </AccordionItem>
              );
            })}
          </Accordion>
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
