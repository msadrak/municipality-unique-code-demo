import React, { FormEvent, useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, Plus, LayoutDashboard, Building2, ChevronLeft, Tag, X } from 'lucide-react';
import { createVolumeContractProject, getCivilProjects, CivilProjectListItem } from '../../services/civil';

const PHASES = [
  { id: 1, title: 'شروع و برنامه‌ریزی' },
  { id: 2, title: 'مناقصه و پیمان' },
  { id: 3, title: 'اجرا و نظارت' },
  { id: 4, title: 'پایان کار و تحویل' },
];

const EMPTY_CREATE_FORM = {
  contract_title: '',
  contractor_name: '',
  total_amount: '',
  start_date: '',
  end_date: '',
};

export function CivilDashboard() {
  const [projects, setProjects] = useState<CivilProjectListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [formData, setFormData] = useState({ ...EMPTY_CREATE_FORM });
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const selectedCategory = searchParams.get('category');

  const openCreateModal = () => {
    setCreateError(null);
    setFormData({ ...EMPTY_CREATE_FORM });
    setIsCreateOpen(true);
  };

  const closeCreateModal = () => {
    setCreateError(null);
    setIsCreateOpen(false);
    setFormData({ ...EMPTY_CREATE_FORM });
  };

  useEffect(() => {
    let mounted = true;

    const fetchProjects = async () => {
      if (selectedCategory) {
        navigate(`/volume-contracts/dashboard?category=${encodeURIComponent(selectedCategory)}`, { replace: true });
        return;
      }

      try {
        setIsLoading(true);
        const data = await getCivilProjects(selectedCategory);
        if (mounted) {
          setProjects(data.filter((project) => !project.contract_category));
          setError(null);
        }
      } catch (err: any) {
        if (mounted) {
          setError(err.message || 'خطا در دریافت اطلاعات پروژه‌ها');
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    void fetchProjects();

    return () => {
      mounted = false;
    };
  }, [navigate, selectedCategory]);

  const handleCreateSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedCategory) return;

    try {
      setIsCreating(true);
      setCreateError(null);
      const created = await createVolumeContractProject({
        contract_category: selectedCategory,
        contract_title: formData.contract_title,
        contractor_name: formData.contractor_name,
        total_amount: Number(formData.total_amount),
        start_date: formData.start_date,
        end_date: formData.end_date,
      });
      closeCreateModal();
      navigate(`/civil/projects/${created.id}`);
    } catch (err: any) {
      setCreateError(err.message || 'خطا در ثبت قرارداد جدید');
    } finally {
      setIsCreating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-[80vh] items-center justify-center bg-[#f8f9fa] font-['Vazirmatn']">
        <Loader2 className="h-10 w-10 animate-spin text-[#04697a]" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 text-center text-[#a83836] bg-[#f8f9fa] min-h-screen font-['Vazirmatn']">
        <p className="font-bold">{error}</p>
      </div>
    );
  }

  return (
    <div dir="rtl" className="flex h-screen flex-col p-8 space-y-10 animate-in fade-in duration-500 bg-[#f8f9fa] font-['Vazirmatn'] selection:bg-[#9febff] selection:text-[#004450]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-[#2d3335] flex items-center gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[1rem] bg-[#cbe7f5] text-[#005867] shadow-[0_10px_20px_rgba(203,231,245,0.4)]">
              <LayoutDashboard className="h-7 w-7" />
            </div>
            تخته پروژه‌های عمرانی
          </h1>
          {selectedCategory && (
            <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-[#e8f7fb] px-4 py-2 text-sm font-bold text-[#04697a]">
              <Tag className="h-4 w-4" />
              نمایش قراردادهای حجمی: {selectedCategory}
            </div>
          )}
          <p className="text-[0.875rem] text-[#5a6062] font-medium mt-3">
            مدیریت یکپارچه وضعیت پروژه‌های عمرانی مناطق
          </p>
        </div>
        {selectedCategory && (
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 rounded-[0.75rem] bg-gradient-to-br from-[#04697a] to-[#005c6b] px-6 py-3.5 text-[0.875rem] font-bold text-[#effbff] shadow-[0_10px_20px_rgba(4,105,122,0.15)] transition-all hover:shadow-[0_15px_30px_rgba(4,105,122,0.25)] hover:scale-[1.02] active:scale-[0.98]"
          >
            <Plus className="h-5 w-5" />
            ثبت قرارداد جدید
          </button>
        )}
      </div>

      <div className="flex flex-1 gap-6 overflow-x-auto pb-6 snap-x">
        {PHASES.map((phase) => {
          const phaseProjects = projects.filter((p) => p.current_phase === phase.id);
          
          return (
            <div key={phase.id} className="flex h-full w-[360px] min-w-[360px] flex-col rounded-[1.5rem] bg-[#f1f4f5] shadow-inner snap-center">
              <div className="flex items-center justify-between p-6 pb-4">
                <h3 className="font-black text-[#2d3335] text-lg">{phase.title}</h3>
                <span className="flex h-8 min-w-8 items-center justify-center rounded-[0.75rem] bg-[#ffffff] text-[#04697a] px-3 text-[0.875rem] font-black shadow-[0_4px_8px_rgba(45,51,53,0.04)]">
                  {phaseProjects.length}
                </span>
              </div>
              
              <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-6 pb-6 pt-2">
                {phaseProjects.map((project) => (
                  <div
                    key={project.id}
                    onClick={() => navigate(`/civil/projects/${project.id}`)}
                    className="group relative cursor-pointer overflow-hidden rounded-[1rem] bg-[#ffffff] p-6 shadow-[0_15px_30px_rgba(45,51,53,0.03)] transition-all duration-300 hover:shadow-[0_20px_40px_rgba(45,51,53,0.06)] hover:-translate-y-1"
                  >
                    <div className="absolute -left-8 -top-8 h-24 w-24 rounded-full bg-gradient-to-br from-[#04697a] to-[#005c6b] opacity-5 blur-[30px]" />
                    <div className="relative z-10">
                      <div className="mb-4 flex items-start justify-between">
                        <span className="rounded-full bg-[#f1f4f5] px-3 py-1.5 text-[0.75rem] font-bold tracking-widest text-[#5a6062]">
                          {project.project_code}
                        </span>
                      </div>
                      {project.contract_category && (
                        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-[#e8f7fb] px-3 py-1 text-[0.75rem] font-bold text-[#04697a]">
                          <Tag className="h-3.5 w-3.5" />
                          {project.contract_category}
                        </div>
                      )}
                      {project.yekta_code && (
                        <div className="mb-3 rounded-[0.75rem] bg-[#f3fbf6] px-3 py-2 text-[0.75rem] font-bold text-[#257a48]">
                          کد یکتا: {project.yekta_code}
                        </div>
                      )}
                      <h4 className="font-black text-[#2d3335] mb-3 line-clamp-2 text-[1rem] leading-snug">
                        {project.title}
                      </h4>
                      
                      <div className="mt-5 flex items-center justify-between text-[0.875rem] text-[#5a6062]">
                        <div className="flex items-center gap-2 font-medium">
                          <Building2 className="h-4 w-4 text-[#adb3b5]" />
                          <span>{project.owning_org_unit_name || 'شهرداری مرکزی'}</span>
                        </div>
                        <div className="h-8 w-8 rounded-full bg-[#f8f9fa] flex items-center justify-center opacity-0 -translate-x-2 transition-all group-hover:opacity-100 group-hover:translate-x-0 group-hover:bg-[#cbe7f5]">
                          <ChevronLeft className="h-4 w-4 text-[#04697a]" />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}

                {phaseProjects.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-36 rounded-[1rem] bg-transparent">
                    <div className="h-12 w-12 rounded-full bg-[#e5e9eb] flex items-center justify-center mb-3">
                      <LayoutDashboard className="h-5 w-5 text-[#adb3b5]" />
                    </div>
                    <p className="text-[0.875rem] font-bold text-[#adb3b5]">پروژه‌ای در این مرحله نیست</p>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {isCreateOpen && selectedCategory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4">
          <div className="w-full max-w-xl rounded-[1rem] bg-white p-6 shadow-[0_30px_80px_rgba(0,0,0,0.18)]">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-black text-[#2d3335]">ثبت قرارداد جدید</h2>
                <p className="mt-1 text-sm font-bold text-[#04697a]">{selectedCategory}</p>
                <p className="mt-2 text-xs font-medium text-[#5a6062]">
                  پرونده جدید مستقیما روی گردش کار قراردادهای حجمی و از مرحله ۱۰۱ شروع می‌شود.
                </p>
              </div>
              <button
                type="button"
                onClick={closeCreateModal}
                className="flex h-10 w-10 items-center justify-center rounded-[0.75rem] bg-[#f1f4f5] text-[#5a6062] transition hover:bg-[#e3e8ea]"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="grid gap-4">
              <label className="grid gap-2 text-sm font-bold text-[#2d3335]">
                عنوان قرارداد
                <input
                  required
                  value={formData.contract_title}
                  onChange={(event) => setFormData((prev) => ({ ...prev, contract_title: event.target.value }))}
                  className="rounded-[0.75rem] border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
                />
              </label>
              <label className="grid gap-2 text-sm font-bold text-[#2d3335]">
                نام پیمانکار
                <input
                  required
                  value={formData.contractor_name}
                  onChange={(event) => setFormData((prev) => ({ ...prev, contractor_name: event.target.value }))}
                  className="rounded-[0.75rem] border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
                />
              </label>
              <label className="grid gap-2 text-sm font-bold text-[#2d3335]">
                مبلغ کل قرارداد
                <input
                  required
                  type="number"
                  min="1"
                  value={formData.total_amount}
                  onChange={(event) => setFormData((prev) => ({ ...prev, total_amount: event.target.value }))}
                  className="rounded-[0.75rem] border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
                />
              </label>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="grid gap-2 text-sm font-bold text-[#2d3335]">
                  تاریخ شروع
                  <input
                    required
                    type="date"
                    value={formData.start_date}
                    onChange={(event) => setFormData((prev) => ({ ...prev, start_date: event.target.value }))}
                    className="rounded-[0.75rem] border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
                  />
                </label>
                <label className="grid gap-2 text-sm font-bold text-[#2d3335]">
                  تاریخ پایان
                  <input
                    required
                    type="date"
                    value={formData.end_date}
                    onChange={(event) => setFormData((prev) => ({ ...prev, end_date: event.target.value }))}
                    className="rounded-[0.75rem] border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
                  />
                </label>
              </div>
              {createError && <p className="rounded-[0.75rem] bg-rose-50 p-3 text-sm font-bold text-rose-700">{createError}</p>}
              <button
                type="submit"
                disabled={isCreating}
                className="mt-2 rounded-[0.75rem] bg-[#04697a] px-5 py-3 text-sm font-black text-white transition hover:bg-[#005c6b] disabled:cursor-wait disabled:opacity-70"
              >
                {isCreating ? 'در حال ثبت...' : 'شروع گردش کار'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default CivilDashboard;
