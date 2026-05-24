import React, { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  BadgeCheck,
  BriefcaseBusiness,
  ChevronLeft,
  ClipboardList,
  Loader2,
  Plus,
  Tag,
  X,
} from "lucide-react";

import { useAuthStore } from "../../stores/useAuthStore";
import {
  ContractorUser,
  createVolumeContract,
  fetchContractorUsers,
  getVolumeContracts,
  VolumeContractListItem,
} from "../../services/volumeContracts";

const PHASES = [
  { id: 1, title: "تعریف قرارداد و پیوست ۵" },
  { id: 2, title: "کد یکتا و کارکرد ماهانه" },
  { id: 3, title: "ممیزی و کنترل بودجه" },
  { id: 4, title: "خزانه و پرداخت" },
];

const EMPTY_CREATE_FORM = {
  contract_title: "",
  contractor_id: "",
  contractor_name: "",
  total_amount: "",
  start_date: "",
  end_date: "",
};

export function VolumeContractsDashboard() {
  const [contracts, setContracts] = useState<VolumeContractListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [contractorUsers, setContractorUsers] = useState<ContractorUser[]>([]);
  const [isLoadingContractors, setIsLoadingContractors] = useState(false);
  const [formData, setFormData] = useState({ ...EMPTY_CREATE_FORM });
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const selectedCategory = searchParams.get("category");

  const dashboardTitle = useMemo(
    () =>
      selectedCategory
        ? `داشبورد قراردادهای حجمی - ${selectedCategory}`
        : user?.role === "CONTRACTOR"
          ? "قراردادهای حجمی من"
          : "داشبورد قراردادهای حجمی",
    [selectedCategory, user?.role],
  );

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

    async function fetchContracts() {
      if (!selectedCategory && user?.role !== "CONTRACTOR") {
        if (mounted) {
          setContracts([]);
          setError(null);
          setIsLoading(false);
        }
        return;
      }

      try {
        setIsLoading(true);
        const data = await getVolumeContracts(selectedCategory);
        if (mounted) {
          setContracts(
            selectedCategory
              ? data.filter(
                  (item) => item.contract_category === selectedCategory,
                )
              : data,
          );
          setError(null);
        }
      } catch (fetchError: any) {
        if (mounted) {
          setError(fetchError.message || "خطا در دریافت فهرست قراردادهای حجمی");
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    void fetchContracts();

    return () => {
      mounted = false;
    };
  }, [selectedCategory, user?.role]);

  useEffect(() => {
    let mounted = true;

    async function loadContractorUsers() {
      if (!isCreateOpen) return;

      try {
        setIsLoadingContractors(true);
        const users = await fetchContractorUsers();
        if (mounted) {
          setContractorUsers(users);
          setCreateError((previous) =>
            previous === "خطا در دریافت فهرست پیمانکاران" ? null : previous,
          );
        }
      } catch (fetchError: any) {
        if (mounted) {
          setCreateError(
            fetchError.message || "خطا در دریافت فهرست پیمانکاران",
          );
        }
      } finally {
        if (mounted) {
          setIsLoadingContractors(false);
        }
      }
    }

    void loadContractorUsers();

    return () => {
      mounted = false;
    };
  }, [isCreateOpen]);

  const handleCreateSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedCategory) return;

    try {
      setIsCreating(true);
      setCreateError(null);
      const selectedContractor = contractorUsers.find(
        (contractor) => String(contractor.id) === formData.contractor_id,
      );
      const created = await createVolumeContract({
        contract_category: selectedCategory,
        contract_title: formData.contract_title,
        contractor_id: selectedContractor ? selectedContractor.id : undefined,
        contractor_name:
          selectedContractor?.full_name ||
          selectedContractor?.username ||
          formData.contractor_name,
        total_amount: Number(formData.total_amount),
        start_date: formData.start_date,
        end_date: formData.end_date,
      });
      closeCreateModal();
      navigate(`/volume-contracts/${created.id}`);
    } catch (submitError: any) {
      setCreateError(submitError.message || "خطا در ثبت قرارداد حجمی جدید");
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
      <div className="min-h-screen bg-[#f8f9fa] p-8 text-center font-['Vazirmatn'] text-[#a83836]">
        <p className="font-bold">{error}</p>
      </div>
    );
  }

  return (
    <div
      dir="rtl"
      className="flex min-h-screen flex-col space-y-10 bg-[#f8f9fa] p-8 font-['Vazirmatn'] selection:bg-[#9febff] selection:text-[#004450]"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-4 text-3xl font-black text-[#2d3335]">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[1rem] bg-[#cbe7f5] text-[#005867] shadow-[0_10px_20px_rgba(203,231,245,0.4)]">
              <ClipboardList className="h-7 w-7" />
            </div>
            {dashboardTitle}
          </h1>
          {selectedCategory ? (
            <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-[#e8f7fb] px-4 py-2 text-sm font-bold text-[#04697a]">
              <Tag className="h-4 w-4" />
              دسته خدماتی: {selectedCategory}
            </div>
          ) : null}
          <p className="mt-3 text-[0.875rem] font-medium text-[#5a6062]">
            پایش چرخه قراردادهای خدماتی، صدور کد یکتا، کارکرد ماهانه و کنترل
            پرداخت در یک محیط مستقل.
          </p>
        </div>
        {selectedCategory && user?.role !== "CONTRACTOR" ? (
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 rounded-[0.75rem] bg-gradient-to-br from-[#04697a] to-[#005c6b] px-6 py-3.5 text-[0.875rem] font-bold text-[#effbff] shadow-[0_10px_20px_rgba(4,105,122,0.15)] transition-all hover:scale-[1.02] hover:shadow-[0_15px_30px_rgba(4,105,122,0.25)] active:scale-[0.98]"
          >
            <Plus className="h-5 w-5" />
            ثبت قرارداد جدید
          </button>
        ) : null}
      </div>

      {!selectedCategory && user?.role !== "CONTRACTOR" ? (
        <div className="flex min-h-[340px] flex-col items-center justify-center rounded-[1.5rem] bg-white p-10 text-center shadow-[0_30px_50px_rgba(45,51,53,0.04)]">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-[1.25rem] bg-[#f1f4f5] text-[#04697a]">
            <ClipboardList className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-black text-[#2d3335]">
            یک دسته قراردادی را انتخاب کنید
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-[#5a6062]">
            این داشبورد فقط قراردادهای حجمی هر دسته خدماتی را به صورت مستقل
            نمایش می‌دهد تا جریان بررسی، کد یکتا و پرداخت‌ها شفاف بماند.
          </p>
        </div>
      ) : (
        <div className="flex flex-1 gap-6 overflow-x-auto pb-6 snap-x">
          {PHASES.map((phase) => {
            const phaseContracts = contracts.filter(
              (contract) => contract.current_phase === phase.id,
            );

            return (
              <div
                key={phase.id}
                className="flex h-full w-[360px] min-w-[360px] flex-col rounded-[1.5rem] bg-[#f1f4f5] shadow-inner snap-center"
              >
                <div className="flex items-center justify-between p-6 pb-4">
                  <h3 className="text-lg font-black text-[#2d3335]">
                    {phase.title}
                  </h3>
                  <span className="flex h-8 min-w-8 items-center justify-center rounded-[0.75rem] bg-[#ffffff] px-3 text-[0.875rem] font-black text-[#04697a] shadow-[0_4px_8px_rgba(45,51,53,0.04)]">
                    {phaseContracts.length}
                  </span>
                </div>

                <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-6 pb-6 pt-2">
                  {phaseContracts.map((contract) => (
                    <div
                      key={contract.id}
                      onClick={() =>
                        navigate(`/volume-contracts/${contract.id}`)
                      }
                      className="group relative cursor-pointer overflow-hidden rounded-[1rem] bg-[#ffffff] p-6 shadow-[0_15px_30px_rgba(45,51,53,0.03)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_20px_40px_rgba(45,51,53,0.06)]"
                    >
                      <div className="absolute -left-8 -top-8 h-24 w-24 rounded-full bg-gradient-to-br from-[#04697a] to-[#005c6b] opacity-5 blur-[30px]" />
                      <div className="relative z-10">
                        <div className="mb-4 flex items-start justify-between gap-3">
                          <span className="rounded-full bg-[#f1f4f5] px-3 py-1.5 text-[0.75rem] font-bold tracking-widest text-[#5a6062]">
                            {contract.project_code}
                          </span>
                          {contract.current_step_name ? (
                            <span className="rounded-full bg-[#f3fbf6] px-3 py-1.5 text-[0.7rem] font-bold text-[#257a48]">
                              {contract.current_step_name}
                            </span>
                          ) : null}
                        </div>
                        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full bg-[#e8f7fb] px-3 py-1 text-[0.75rem] font-bold text-[#04697a]">
                          <Tag className="h-3.5 w-3.5" />
                          {contract.contract_category || selectedCategory}
                        </div>
                        {contract.yekta_code ? (
                          <div className="mb-3 rounded-[0.75rem] bg-[#f3fbf6] px-3 py-2 text-[0.75rem] font-bold text-[#257a48]">
                            کد یکتا: {contract.yekta_code}
                          </div>
                        ) : null}
                        <h4 className="mb-3 line-clamp-2 text-[1rem] font-black leading-snug text-[#2d3335]">
                          {contract.title}
                        </h4>
                        {contract.budget_line ? (
                          <div className="mb-4 rounded-[0.75rem] bg-[#f8f9fa] px-3 py-2 text-[0.75rem] font-medium text-[#5a6062]">
                            ردیف بودجه متصل: {contract.budget_line}
                          </div>
                        ) : null}

                        <div className="mt-5 flex items-center justify-between text-[0.875rem] text-[#5a6062]">
                          <div className="flex items-center gap-2 font-medium">
                            <BriefcaseBusiness className="h-4 w-4 text-[#adb3b5]" />
                            <span>
                              {contract.owning_org_unit_name ||
                                "قراردادهای حجمی"}
                            </span>
                          </div>
                          <div className="flex h-8 w-8 -translate-x-2 items-center justify-center rounded-full bg-[#f8f9fa] opacity-0 transition-all group-hover:translate-x-0 group-hover:bg-[#cbe7f5] group-hover:opacity-100">
                            <ChevronLeft className="h-4 w-4 text-[#04697a]" />
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}

                  {phaseContracts.length === 0 ? (
                    <div className="flex h-40 flex-col items-center justify-center rounded-[1rem] bg-transparent text-center">
                      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[#e5e9eb]">
                        <BadgeCheck className="h-5 w-5 text-[#adb3b5]" />
                      </div>
                      <p className="text-[0.875rem] font-bold text-[#adb3b5]">
                        قراردادی در این بخش نیست
                      </p>
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {isCreateOpen && selectedCategory ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/35 p-4">
          <div className="w-full max-w-xl rounded-[1rem] bg-white p-6 shadow-[0_30px_80px_rgba(0,0,0,0.18)]">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-black text-[#2d3335]">
                  ثبت قرارداد حجمی جدید
                </h2>
                <p className="mt-1 text-sm font-bold text-[#04697a]">
                  {selectedCategory}
                </p>
                <p className="mt-2 text-xs font-medium text-[#5a6062]">
                  پرونده جدید برای پیمانکار خدماتی شما مستقیما از مرحله ۱۰۱ «ثبت
                  پایه قرارداد» شروع می‌شود.
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
                عنوان قرارداد حجمی
                <input
                  required
                  value={formData.contract_title}
                  onChange={(event) =>
                    setFormData((prev) => ({
                      ...prev,
                      contract_title: event.target.value,
                    }))
                  }
                  className="rounded-[0.75rem] border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
                />
              </label>
              <label className="grid gap-2 text-sm font-bold text-[#2d3335]">
                نام پیمانکار خدماتی
                <select
                  required
                  value={formData.contractor_id}
                  onChange={(event) => {
                    const selectedContractor = contractorUsers.find(
                      (contractor) =>
                        String(contractor.id) === event.target.value,
                    );
                    setFormData((prev) => ({
                      ...prev,
                      contractor_id: event.target.value,
                      contractor_name:
                        selectedContractor?.full_name ||
                        selectedContractor?.username ||
                        "",
                    }));
                  }}
                  className="rounded-[0.75rem] border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
                  disabled={isLoadingContractors}
                >
                  <option value="">
                    {isLoadingContractors
                      ? "در حال دریافت پیمانکاران..."
                      : "انتخاب پیمانکار"}
                  </option>
                  {contractorUsers.map((contractor) => (
                    <option key={contractor.id} value={contractor.id}>
                      {contractor.full_name || contractor.username} (
                      {contractor.username})
                    </option>
                  ))}
                </select>
              </label>
              <label className="grid gap-2 text-sm font-bold text-[#2d3335]">
                مبلغ کل قرارداد
                <input
                  required
                  type="number"
                  min="1"
                  value={formData.total_amount}
                  onChange={(event) =>
                    setFormData((prev) => ({
                      ...prev,
                      total_amount: event.target.value,
                    }))
                  }
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
                    onChange={(event) =>
                      setFormData((prev) => ({
                        ...prev,
                        start_date: event.target.value,
                      }))
                    }
                    className="rounded-[0.75rem] border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
                  />
                </label>
                <label className="grid gap-2 text-sm font-bold text-[#2d3335]">
                  تاریخ پایان
                  <input
                    required
                    type="date"
                    value={formData.end_date}
                    onChange={(event) =>
                      setFormData((prev) => ({
                        ...prev,
                        end_date: event.target.value,
                      }))
                    }
                    className="rounded-[0.75rem] border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
                  />
                </label>
              </div>
              {createError ? (
                <p className="rounded-[0.75rem] bg-rose-50 p-3 text-sm font-bold text-rose-700">
                  {createError}
                </p>
              ) : null}
              <button
                type="submit"
                disabled={isCreating}
                className="mt-2 rounded-[0.75rem] bg-[#04697a] px-5 py-3 text-sm font-black text-white transition hover:bg-[#005c6b] disabled:cursor-wait disabled:opacity-70"
              >
                {isCreating ? "در حال ثبت..." : "ثبت و شروع مرحله ۱۰۱"}
              </button>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default VolumeContractsDashboard;
