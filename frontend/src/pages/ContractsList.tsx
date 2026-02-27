import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Plus, Search, Filter, MoreVertical, ChevronLeft, ChevronRight, FileText, Wallet, Clock } from 'lucide-react';
import { fetchContracts, type ContractListItem } from '../services/contracts';
import { formatRial } from '../lib/utils';

const STATUS_CONFIG: Record<string, { label: string; dotColor: string; bgColor: string; textColor: string; borderColor: string }> = {
  DRAFT: { label: 'پیش‌نویس', dotColor: 'bg-slate-400', bgColor: 'bg-slate-50', textColor: 'text-slate-700', borderColor: 'border-slate-100' },
  PENDING_APPROVAL: { label: 'منتظر تایید', dotColor: 'bg-amber-600', bgColor: 'bg-amber-50', textColor: 'text-amber-700', borderColor: 'border-amber-100' },
  APPROVED: { label: 'تکمیل شده', dotColor: 'bg-emerald-600', bgColor: 'bg-emerald-50', textColor: 'text-emerald-700', borderColor: 'border-emerald-100' },
  REJECTED: { label: 'رد شده', dotColor: 'bg-red-600', bgColor: 'bg-red-50', textColor: 'text-red-700', borderColor: 'border-red-100' },
  IN_PROGRESS: { label: 'در جریان', dotColor: 'bg-blue-600', bgColor: 'bg-blue-50', textColor: 'text-blue-700', borderColor: 'border-blue-100' },
};

function getStatusConfig(status?: string) {
  const key = status?.toUpperCase() ?? '';
  return STATUS_CONFIG[key] ?? { label: status || 'نامشخص', dotColor: 'bg-slate-400', bgColor: 'bg-slate-50', textColor: 'text-slate-700', borderColor: 'border-slate-100' };
}

// Color palette for contractor initials
const AVATAR_COLORS = [
  { bg: 'bg-blue-100', text: 'text-blue-600' },
  { bg: 'bg-emerald-100', text: 'text-emerald-600' },
  { bg: 'bg-orange-100', text: 'text-orange-600' },
  { bg: 'bg-purple-100', text: 'text-purple-600' },
  { bg: 'bg-teal-100', text: 'text-teal-600' },
  { bg: 'bg-rose-100', text: 'text-rose-600' },
];

function getAvatarColor(index: number) {
  return AVATAR_COLORS[index % AVATAR_COLORS.length];
}

export function ContractsList() {
  const navigate = useNavigate();
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

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

  // Client-side search filter
  const filteredContracts = contracts.filter((c) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.contract_number?.toLowerCase().includes(q) ||
      c.title?.toLowerCase().includes(q) ||
      c.contractor_name?.toLowerCase().includes(q)
    );
  });

  // Stats
  const totalContracts = contracts.length;
  const completedContracts = contracts.filter(c => c.status?.toUpperCase() === 'APPROVED').length;
  const pendingContracts = contracts.filter(c => c.status?.toUpperCase() === 'PENDING_APPROVAL').length;

  return (
    <div className="space-y-6">
      {/* ── Page Header ────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl md:text-3xl font-black text-slate-900 tracking-tight">لیست قراردادها</h2>
          <p className="text-slate-500 mt-1 text-sm">مدیریت و پیگیری وضعیت قراردادهای پیمانکاران</p>
        </div>
        <button
          onClick={handleCreateNew}
          className="inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white h-11 px-6 rounded-xl text-sm font-bold shadow-sm shadow-blue-500/20 transition-all hover:shadow-blue-500/40 transform hover:-translate-y-0.5"
        >
          <Plus className="h-5 w-5" />
          <span>قرارداد جدید</span>
        </button>
      </div>

      {/* ── Search & Filter Toolbar ────────────────────── */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <div className="flex flex-col md:flex-row gap-4 items-center">
          <div className="relative flex-1 w-full">
            <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none text-slate-400">
              <Search className="h-5 w-5" />
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-11 pr-10 pl-4 rounded-lg bg-slate-50 border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 transition-all text-slate-900 placeholder:text-slate-400"
              placeholder="جستجو در شماره قرارداد، نام پیمانکار..."
            />
          </div>
          <div className="flex gap-3 w-full md:w-auto">
            <select className="h-11 pr-3 pl-10 rounded-lg bg-slate-50 border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 appearance-none cursor-pointer text-slate-900 min-w-[160px]">
              <option>همه وضعیت‌ها</option>
              <option>در جریان</option>
              <option>تکمیل شده</option>
              <option>منتظر تایید</option>
              <option>معلق</option>
            </select>
            <button className="h-11 px-4 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-500 flex items-center gap-2 transition-colors whitespace-nowrap">
              <Filter className="h-5 w-5" />
              <span className="text-sm font-medium">فیلترهای پیشرفته</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── Data Table ──────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col min-h-[400px]">
        <div className="overflow-x-auto">
          <table className="w-full text-right border-collapse">
            <thead>
              <tr className="bg-slate-50/50 border-b border-slate-200">
                <th className="py-4 px-6 text-sm font-semibold text-slate-500 w-24">شماره</th>
                <th className="py-4 px-6 text-sm font-semibold text-slate-500 min-w-[200px]">پیمانکار</th>
                <th className="py-4 px-6 text-sm font-semibold text-slate-500 min-w-[200px]">موضوع قرارداد</th>
                <th className="py-4 px-6 text-sm font-semibold text-slate-500">مبلغ (ریال)</th>
                <th className="py-4 px-6 text-sm font-semibold text-slate-500 w-32">وضعیت</th>
                <th className="py-4 px-6 text-sm font-semibold text-slate-500 w-16"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center">
                    <Loader2 className="h-6 w-6 animate-spin text-blue-600 mx-auto mb-3" />
                    <span className="text-slate-500">در حال بارگیری قراردادها...</span>
                  </td>
                </tr>
              ) : error ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-red-600">{error}</td>
                </tr>
              ) : filteredContracts.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-16 text-center text-slate-500">
                    {searchQuery ? 'نتیجه‌ای برای جستجوی شما یافت نشد' : 'قراردادی یافت نشد'}
                  </td>
                </tr>
              ) : (
                filteredContracts.map((contract, idx) => {
                  const status = getStatusConfig(contract.status);
                  const colors = getAvatarColor(idx);
                  const initial = contract.contractor_name?.charAt(0) || 'ق';
                  return (
                    <tr
                      key={contract.id}
                      className="group hover:bg-slate-50 transition-colors cursor-pointer"
                      onClick={() => navigate(`/contracts/${contract.id}`)}
                    >
                      <td className="py-4 px-6 text-sm font-medium text-slate-900">{contract.contract_number}</td>
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-full ${colors.bg} ${colors.text} flex items-center justify-center text-xs font-bold shrink-0`}>
                            {initial}
                          </div>
                          <span className="text-sm font-medium text-slate-900">{contract.contractor_name || '—'}</span>
                        </div>
                      </td>
                      <td className="py-4 px-6 text-sm text-slate-500">{contract.title}</td>
                      <td className="py-4 px-6 text-sm font-medium text-slate-900">{formatRial(contract.total_amount)}</td>
                      <td className="py-4 px-6">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${status.bgColor} ${status.textColor} border ${status.borderColor}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${status.dotColor}`} />
                          {status.label}
                        </span>
                      </td>
                      <td className="py-4 px-6">
                        <button
                          onClick={(e) => { e.stopPropagation(); navigate(`/contracts/${contract.id}`); }}
                          className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        >
                          <MoreVertical className="h-5 w-5" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!loading && filteredContracts.length > 0 && (
          <div className="mt-auto flex items-center justify-between p-4 border-t border-slate-200 bg-slate-50/50">
            <p className="text-sm text-slate-500">نمایش ۱ تا {filteredContracts.length} از {contracts.length} نتیجه</p>
            <div className="flex items-center gap-2">
              <button className="p-2 rounded-lg border border-slate-200 bg-white text-slate-400 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors" disabled>
                <ChevronRight className="h-4 w-4" />
              </button>
              <span className="text-sm font-medium px-2 text-slate-900">صفحه ۱ از ۱</span>
              <button className="p-2 rounded-lg border border-slate-200 bg-white text-slate-400 hover:bg-slate-50 transition-colors">
                <ChevronLeft className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Quick Stats Row ──────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 flex flex-col gap-2">
          <div className="flex justify-between items-center">
            <span className="text-blue-600 text-sm font-semibold">مجموع قراردادها</span>
            <FileText className="h-5 w-5 text-blue-500" />
          </div>
          <p className="text-2xl font-black text-slate-900">{totalContracts}</p>
          <p className="text-xs text-slate-500">قرارداد فعال در سال جاری</p>
        </div>
        <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-4 flex flex-col gap-2">
          <div className="flex justify-between items-center">
            <span className="text-emerald-600 text-sm font-semibold">تکمیل شده</span>
            <Wallet className="h-5 w-5 text-emerald-500" />
          </div>
          <p className="text-2xl font-black text-slate-900">{completedContracts}</p>
          <p className="text-xs text-slate-500">پروژه تکمیل شده</p>
        </div>
        <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 flex flex-col gap-2">
          <div className="flex justify-between items-center">
            <span className="text-amber-600 text-sm font-semibold">در انتظار اقدام</span>
            <Clock className="h-5 w-5 text-amber-500" />
          </div>
          <p className="text-2xl font-black text-slate-900">{pendingContracts}</p>
          <p className="text-xs text-slate-500">قرارداد نیاز به تایید دارند</p>
        </div>
      </div>
    </div>
  );
}

export default ContractsList;
