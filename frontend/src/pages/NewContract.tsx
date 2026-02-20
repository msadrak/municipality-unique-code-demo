import React from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { ArrowRight } from 'lucide-react';
import { ContractWizard } from '../components/contracts/ContractWizard';

export function NewContract() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const budgetParam = searchParams.get('budgetId');
  const budgetRowId = budgetParam ? Number(budgetParam) : Number.NaN;
  const hasValidBudget = Number.isFinite(budgetRowId) && budgetRowId > 0;

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 max-w-7xl">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">ثبت قرارداد جدید</h1>
          <p className="text-sm text-muted-foreground mt-1">
            تکمیل اطلاعات قرارداد برای ردیف بودجه انتخاب شده
          </p>
        </div>
        <Button variant="outline" onClick={() => navigate('/contracts')}>
          <ArrowRight className="h-4 w-4 ml-2" />
          بازگشت به داشبورد
        </Button>
      </div>

      {!hasValidBudget ? (
        <Card className="p-6 text-center space-y-3">
          <p className="text-destructive">ردیف بودجه معتبر یافت نشد.</p>
          <p className="text-sm text-muted-foreground">
            لطفاً ابتدا یک ردیف بودجه را انتخاب کنید.
          </p>
          <Button onClick={() => navigate('/contracts')}>
            بازگشت به داشبورد
          </Button>
        </Card>
      ) : (
        <ContractWizard budgetRowId={budgetRowId} />
      )}
    </div>
  );
}

export default NewContract;
