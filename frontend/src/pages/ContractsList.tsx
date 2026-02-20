import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import { Loader2, Plus, Eye } from 'lucide-react';
import { fetchContracts, type ContractListItem } from '../services/contracts';
import { formatRial } from '../lib/utils';

const getStatusConfig = (status?: string) => {
  const normalized = status?.toUpperCase() ?? '';
  switch (normalized) {
    case 'DRAFT':
      return { label: 'پیش‌نویس', className: 'bg-slate-100 text-slate-700' };
    case 'PENDING_APPROVAL':
      return { label: 'در انتظار تایید', className: 'bg-amber-100 text-amber-700' };
    case 'APPROVED':
      return { label: 'تایید شده', className: 'bg-green-100 text-green-700' };
    case 'REJECTED':
      return { label: 'رد شده', className: 'bg-red-100 text-red-700' };
    default:
      return { label: status || 'نامشخص', className: 'bg-slate-100 text-slate-700' };
  }
};

export function ContractsList() {
  const navigate = useNavigate();
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const loadContracts = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchContracts({ page: 1, limit: 50 });
        setContracts(response.items ?? []);
      } catch (err) {
        console.error('Failed to load contracts:', err);
        setError('خطا در بارگیری قراردادها');
      } finally {
        setLoading(false);
      }
    };

    loadContracts();
  }, []);

  const handleCreateNew = () => {
    navigate('/portal');
  };

  return (
    <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 max-w-7xl">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">داشبورد قراردادها</h1>
          <p className="text-sm text-muted-foreground mt-1">
            فهرست قراردادهای ثبت شده و وضعیت هر قرارداد
          </p>
        </div>
        <Button onClick={handleCreateNew}>
          <Plus className="h-4 w-4 ml-2" />
          ایجاد قرارداد جدید
        </Button>
      </div>

      <Card className="p-4 bg-amber-50/60 border-amber-200 text-sm text-amber-900">
        برای ایجاد قرارداد جدید ابتدا باید ردیف بودجه را انتخاب کنید.
      </Card>

      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-right">شماره قرارداد</TableHead>
              <TableHead className="text-right">عنوان</TableHead>
              <TableHead className="text-right">پیمانکار</TableHead>
              <TableHead className="text-right">وضعیت</TableHead>
              <TableHead className="text-right">مبلغ</TableHead>
              <TableHead className="text-right">عملیات</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mx-auto mb-2" />
                  <span className="text-muted-foreground">در حال بارگیری قراردادها...</span>
                </TableCell>
              </TableRow>
            ) : error ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-destructive">
                  {error}
                </TableCell>
              </TableRow>
            ) : contracts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                  قراردادی یافت نشد
                </TableCell>
              </TableRow>
            ) : (
              contracts.map((contract) => {
                const status = getStatusConfig(contract.status);
                return (
                  <TableRow key={contract.id}>
                    <TableCell className="font-mono text-sm" dir="ltr">
                      {contract.contract_number}
                    </TableCell>
                    <TableCell className="max-w-[280px] truncate">{contract.title}</TableCell>
                    <TableCell className="max-w-[200px] truncate">
                      {contract.contractor_name || '—'}
                    </TableCell>
                    <TableCell>
                      <Badge className={status.className}>{status.label}</Badge>
                    </TableCell>
                    <TableCell className="font-mono-num" dir="ltr">
                      {formatRial(contract.total_amount)}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => navigate(`/contracts/${contract.id}`)}
                      >
                        <Eye className="h-4 w-4 ml-1" />
                        مشاهده جزئیات
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </Card>

    </div>
  );
}

export default ContractsList;
