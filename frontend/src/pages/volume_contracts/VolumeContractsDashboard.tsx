import React, { FormEvent, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Activity,
  ArrowLeft,
  BadgeCheck,
  BriefcaseBusiness,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ClipboardList,
  FileText,
  Loader2,
  Mail,
  Plus,
  ShieldCheck,
  Tag,
  UserRound,
  X,
} from "lucide-react";

import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "../../components/ui/collapsible";
import { Progress } from "../../components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { cn } from "../../components/ui/utils";
import { useAuthStore } from "../../stores/useAuthStore";
import {
  ContractorDashboardData,
  ContractorUser,
  createVolumeContract,
  fetchContractorUsers,
  getContractorDashboard,
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

const numberFormatter = new Intl.NumberFormat("fa-IR");

function formatNumber(value: number | null | undefined) {
  return numberFormatter.format(value ?? 0);
}

function formatRial(value: number | null | undefined) {
  return `${formatNumber(value)} ریال`;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("fa-IR");
}

function getStepProgress(step: number) {
  if (step >= 110) return 100;
  if (step <= 101) return 8;
  return Math.min(96, Math.max(12, Math.round(((step - 101) / 9) * 100)));
}

function stepStatusMeta(step: number) {
  if (step === 102) {
    return {
      label: "در انتظار بارگذاری",
      className: "border-amber-200 bg-amber-50 text-amber-700",
      barClassName: "bg-amber-500",
    };
  }
  if (step === 103) {
    return {
      label: "ارسال شده به بهادری",
      className: "border-blue-200 bg-blue-50 text-blue-700",
      barClassName: "bg-blue-500",
    };
  }
  if (step === 104) {
    return {
      label: "صدور کد یکتا",
      className: "border-purple-200 bg-purple-50 text-purple-700",
      barClassName: "bg-purple-500",
    };
  }
  if (step === 105) {
    return {
      label: "ثبت کارکرد ماهانه",
      className: "border-indigo-200 bg-indigo-50 text-indigo-700",
      barClassName: "bg-indigo-500",
    };
  }
  if (step === 106 || step === 107) {
    return {
      label: "محاسبه و کسورات",
      className: "border-orange-200 bg-orange-50 text-orange-700",
      barClassName: "bg-orange-500",
    };
  }
  if (step === 108 || step === 109) {
    return {
      label: "تایید و ممیزی",
      className: "border-cyan-200 bg-cyan-50 text-cyan-700",
      barClassName: "bg-cyan-500",
    };
  }
  if (step >= 110) {
    return {
      label: "پرداخت شده",
      className: "border-emerald-200 bg-emerald-50 text-emerald-700",
      barClassName: "bg-emerald-500",
    };
  }
  return {
    label: "در جریان",
    className: "border-slate-200 bg-slate-50 text-slate-700",
    barClassName: "bg-slate-500",
  };
}

function StatusBadge({ step }: { step: number }) {
  const meta = stepStatusMeta(step);
  return (
    <Badge variant="outline" className={cn("font-bold", meta.className)}>
      {meta.label}
    </Badge>
  );
}

function EmptyState({
  icon: Icon,
  title,
}: {
  icon: typeof Mail;
  title: string;
}) {
  return (
    <div className="flex min-h-40 flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50/60 p-8 text-center text-slate-500">
      <Icon className="mb-3 h-10 w-10 text-slate-300" />
      <p className="text-sm font-bold">{title}</p>
    </div>
  );
}

function StatCard({
  icon: Icon,
  title,
  value,
  accent,
}: {
  icon: typeof FileText;
  title: string;
  value: number;
  accent: string;
}) {
  return (
    <div className="group rounded-lg border border-white/70 bg-white/90 p-5 shadow-[0_16px_35px_rgba(15,23,42,0.07)] backdrop-blur transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_22px_45px_rgba(15,23,42,0.1)]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-bold text-slate-500">{title}</p>
          <p className="mt-3 text-3xl font-black text-slate-900">{formatNumber(value)}</p>
        </div>
        <div className={cn("flex h-12 w-12 items-center justify-center rounded-lg", accent)}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );
}

function ContractorTable({
  contracts,
  completed = false,
  onOpen,
}: {
  contracts: VolumeContractListItem[];
  completed?: boolean;
  onOpen: (id: number) => void;
}) {
  if (contracts.length === 0) {
    return (
      <EmptyState
        icon={completed ? CheckCircle2 : Activity}
        title={completed ? "سابقه تکمیل شده‌ای ثبت نشده است" : "قرارداد فعالی ثبت نشده است"}
      />
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <Table>
        <TableHeader className="bg-slate-50/90">
          <TableRow className="hover:bg-transparent">
            <TableHead className="text-right font-black text-slate-600">کد</TableHead>
            <TableHead className="text-right font-black text-slate-600">عنوان</TableHead>
            <TableHead className="text-right font-black text-slate-600">دسته</TableHead>
            <TableHead className="text-right font-black text-slate-600">مرحله</TableHead>
            <TableHead className="text-right font-black text-slate-600">وضعیت</TableHead>
            {completed ? (
              <TableHead className="text-right font-black text-slate-600">مبلغ پرداختی</TableHead>
            ) : (
              <TableHead className="text-right font-black text-slate-600">پیشرفت</TableHead>
            )}
          </TableRow>
        </TableHeader>
        <TableBody>
          {contracts.map((contract) => {
            const meta = stepStatusMeta(contract.current_step);
            return (
              <TableRow
                key={contract.id}
                onClick={() => onOpen(contract.id)}
                className="cursor-pointer bg-white transition hover:bg-slate-50"
              >
                <TableCell className="font-mono text-xs font-bold text-slate-500" dir="ltr">
                  {contract.project_code}
                </TableCell>
                <TableCell className="min-w-64 font-bold text-slate-900">
                  {contract.title}
                </TableCell>
                <TableCell className="text-sm text-slate-600">
                  {contract.contract_category || "-"}
                </TableCell>
                <TableCell className="text-sm font-black text-slate-700">
                  {formatNumber(contract.current_step)}
                </TableCell>
                <TableCell>
                  <StatusBadge step={contract.current_step} />
                </TableCell>
                <TableCell className="min-w-44">
                  {completed ? (
                    <span className="font-mono-num text-sm font-black text-emerald-700">
                      {formatRial(contract.paid_amount)}
                    </span>
                  ) : (
                    <div className="space-y-2">
                      <Progress value={getStepProgress(contract.current_step)} className="h-2 bg-slate-100" />
                      <div className={cn("h-0.5 w-full rounded-full", meta.barClassName)} />
                    </div>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

function ContractorWorkspace({
  data,
  onOpenContract,
}: {
  data: ContractorDashboardData;
  onOpenContract: (id: number) => void;
}) {
  const [completedOpen, setCompletedOpen] = useState(true);
  const typeLabel = data.contractor_type === "INDIVIDUAL" ? "حقیقی" : "حقوقی";

  return (
    <div
      dir="rtl"
      className="min-h-screen space-y-8 bg-[linear-gradient(180deg,#f6faf8_0%,#eef6f4_42%,#f8fafc_100%)] p-4 font-['Vazirmatn'] text-slate-900 sm:p-6 lg:p-8"
    >
      <section className="relative overflow-hidden rounded-lg border border-emerald-200/60 bg-gradient-to-br from-emerald-700 via-teal-700 to-slate-900 p-6 text-white shadow-[0_24px_60px_rgba(15,118,110,0.25)] sm:p-8">
        <div className="absolute inset-x-0 top-0 h-px bg-white/40" />
        <div className="relative z-10 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 rounded-lg border border-white/20 bg-white/10 px-3 py-1.5 text-sm font-bold text-emerald-50 backdrop-blur">
              <ShieldCheck className="h-4 w-4" />
              {data.is_verified ? "پروفایل تایید شده" : "در انتظار تایید پروفایل"}
            </div>
            <h1 className="text-2xl font-black leading-tight sm:text-4xl">
              پیمانکار محترم، خوش آمدید
            </h1>
            <div className="mt-5 flex flex-wrap items-center gap-3 text-sm font-bold text-emerald-50">
              <span className="inline-flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2 backdrop-blur">
                <Building2 className="h-4 w-4" />
                {data.contractor_name}
              </span>
              <span className="inline-flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2 backdrop-blur">
                <UserRound className="h-4 w-4" />
                {typeLabel}
              </span>
            </div>
          </div>
          <div className="grid min-w-56 grid-cols-2 gap-3 rounded-lg border border-white/15 bg-white/10 p-4 backdrop-blur">
            <div>
              <p className="text-xs font-bold text-emerald-100">کل قراردادها</p>
              <p className="mt-1 text-3xl font-black">{formatNumber(data.stats.total_contracts)}</p>
            </div>
            <div>
              <p className="text-xs font-bold text-emerald-100">دعوتنامه‌ها</p>
              <p className="mt-1 text-3xl font-black">{formatNumber(data.stats.pending_invitations)}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard icon={FileText} title="کل قرارداد" value={data.stats.total_contracts} accent="bg-slate-100 text-slate-700" />
        <StatCard icon={Activity} title="فعال" value={data.stats.active_contracts} accent="bg-blue-50 text-blue-700" />
        <StatCard icon={CheckCircle2} title="تکمیل شده" value={data.stats.completed_contracts} accent="bg-emerald-50 text-emerald-700" />
        <StatCard icon={Mail} title="دعوتنامه" value={data.stats.pending_invitations} accent="bg-amber-50 text-amber-700" />
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-black text-slate-900">دعوتنامه‌ها / وظایف جدید</h2>
            <p className="mt-1 text-sm font-medium text-slate-500">پرونده‌های مرحله ۱۰۲</p>
          </div>
          <Badge variant="outline" className="border-amber-200 bg-amber-50 text-amber-700">
            {formatNumber(data.invitations.length)}
          </Badge>
        </div>
        {data.invitations.length === 0 ? (
          <EmptyState icon={Mail} title="دعوتنامه جدیدی ندارید" />
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            {data.invitations.map((invitation) => (
              <div
                key={invitation.id}
                className="relative overflow-hidden rounded-lg border border-amber-300 bg-white p-5 shadow-[0_16px_35px_rgba(245,158,11,0.12)] ring-2 ring-amber-100/70"
              >
                <div className="absolute inset-x-0 top-0 h-1 animate-pulse bg-gradient-to-l from-amber-400 via-orange-400 to-amber-300" />
                <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
                  <div className="min-w-0">
                    <div className="mb-3 flex flex-wrap items-center gap-2">
                      <span className="rounded-md bg-slate-100 px-2.5 py-1 font-mono text-xs font-black text-slate-600" dir="ltr">
                        {invitation.project_code}
                      </span>
                      <StatusBadge step={invitation.current_step} />
                    </div>
                    <h3 className="line-clamp-2 text-lg font-black leading-7 text-slate-900">
                      {invitation.title}
                    </h3>
                    <p className="mt-2 text-sm font-bold text-slate-500">
                      {invitation.contract_category} • {invitation.current_step_name || "مرحله ۱۰۲"}
                    </p>
                    <p className="mt-2 text-xs font-bold text-slate-400">
                      تاریخ دریافت: {formatDate(invitation.created_at)}
                    </p>
                  </div>
                  <Button
                    type="button"
                    onClick={() => onOpenContract(invitation.id)}
                    className="h-11 rounded-lg bg-slate-900 px-5 font-black text-white hover:bg-slate-800"
                  >
                    مشاهده و اقدام
                    <ArrowLeft className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-4">
        <div className="flex items-center gap-3">
          <Activity className="h-5 w-5 text-blue-700" />
          <h2 className="text-xl font-black text-slate-900">قراردادهای فعال</h2>
        </div>
        <ContractorTable contracts={data.active_contracts} onOpen={onOpenContract} />
      </section>

      <Collapsible open={completedOpen} onOpenChange={setCompletedOpen} className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-700" />
            <h2 className="text-xl font-black text-slate-900">سوابق تکمیل شده</h2>
          </div>
          <CollapsibleTrigger asChild>
            <Button variant="outline" size="sm" className="rounded-lg">
              <ChevronDown className={cn("h-4 w-4 transition", completedOpen ? "rotate-180" : "")} />
            </Button>
          </CollapsibleTrigger>
        </div>
        <CollapsibleContent>
          <ContractorTable contracts={data.completed_contracts} completed onOpen={onOpenContract} />
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

export function VolumeContractsDashboard() {
  const [contracts, setContracts] = useState<VolumeContractListItem[]>([]);
  const [contractorDashboard, setContractorDashboard] = useState<ContractorDashboardData | null>(null);
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
  const isContractor = user?.role === "CONTRACTOR";

  const dashboardTitle = useMemo(
    () =>
      selectedCategory
        ? `داشبورد قراردادهای حجمی - ${selectedCategory}`
        : "داشبورد قراردادهای حجمی",
    [selectedCategory],
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
      if (isContractor) return;

      if (!selectedCategory) {
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
          setContracts(data.filter((item) => item.contract_category === selectedCategory));
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
  }, [isContractor, selectedCategory]);

  useEffect(() => {
    let mounted = true;

    async function fetchDashboard() {
      if (!isContractor) return;

      try {
        setIsLoading(true);
        const data = await getContractorDashboard();
        if (mounted) {
          setContractorDashboard(data);
          setError(null);
        }
      } catch (fetchError: any) {
        if (mounted) {
          setError(fetchError.message || "خطا در دریافت داشبورد پیمانکار");
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    void fetchDashboard();

    return () => {
      mounted = false;
    };
  }, [isContractor]);

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
          setCreateError(fetchError.message || "خطا در دریافت فهرست پیمانکاران");
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

  if (isContractor) {
    return contractorDashboard ? (
      <ContractorWorkspace
        data={contractorDashboard}
        onOpenContract={(id) => navigate(`/volume-contracts/${id}`)}
      />
    ) : null;
  }

  return (
    <div
      dir="rtl"
      className="flex min-h-screen flex-col space-y-10 bg-[#f8f9fa] p-8 font-['Vazirmatn'] selection:bg-[#9febff] selection:text-[#004450]"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-4 text-3xl font-black text-[#2d3335]">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg bg-[#cbe7f5] text-[#005867] shadow-[0_10px_20px_rgba(203,231,245,0.4)]">
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
            پایش چرخه قراردادهای خدماتی، صدور کد یکتا، کارکرد ماهانه و کنترل پرداخت در یک محیط مستقل.
          </p>
        </div>
        {selectedCategory ? (
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 rounded-lg bg-gradient-to-br from-[#04697a] to-[#005c6b] px-6 py-3.5 text-[0.875rem] font-bold text-[#effbff] shadow-[0_10px_20px_rgba(4,105,122,0.15)] transition-all hover:scale-[1.02] hover:shadow-[0_15px_30px_rgba(4,105,122,0.25)] active:scale-[0.98]"
          >
            <Plus className="h-5 w-5" />
            ثبت قرارداد جدید
          </button>
        ) : null}
      </div>

      {!selectedCategory ? (
        <div className="flex min-h-[340px] flex-col items-center justify-center rounded-lg bg-white p-10 text-center shadow-[0_30px_50px_rgba(45,51,53,0.04)]">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-lg bg-[#f1f4f5] text-[#04697a]">
            <ClipboardList className="h-8 w-8" />
          </div>
          <h2 className="text-xl font-black text-[#2d3335]">یک دسته قراردادی را انتخاب کنید</h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-[#5a6062]">
            این داشبورد قراردادهای حجمی هر دسته خدماتی را به صورت مستقل نمایش می‌دهد.
          </p>
        </div>
      ) : (
        <div className="flex flex-1 snap-x gap-6 overflow-x-auto pb-6">
          {PHASES.map((phase) => {
            const phaseContracts = contracts.filter(
              (contract) => contract.current_phase === phase.id,
            );

            return (
              <div
                key={phase.id}
                className="flex h-full w-[360px] min-w-[360px] snap-center flex-col rounded-lg bg-[#f1f4f5] shadow-inner"
              >
                <div className="flex items-center justify-between p-6 pb-4">
                  <h3 className="text-lg font-black text-[#2d3335]">{phase.title}</h3>
                  <span className="flex h-8 min-w-8 items-center justify-center rounded-lg bg-white px-3 text-[0.875rem] font-black text-[#04697a] shadow-[0_4px_8px_rgba(45,51,53,0.04)]">
                    {formatNumber(phaseContracts.length)}
                  </span>
                </div>

                <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-6 pb-6 pt-2">
                  {phaseContracts.map((contract) => (
                    <div
                      key={contract.id}
                      onClick={() => navigate(`/volume-contracts/${contract.id}`)}
                      className="group relative cursor-pointer overflow-hidden rounded-lg bg-white p-6 shadow-[0_15px_30px_rgba(45,51,53,0.03)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_20px_40px_rgba(45,51,53,0.06)]"
                    >
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
                          <div className="mb-3 rounded-lg bg-[#f3fbf6] px-3 py-2 text-[0.75rem] font-bold text-[#257a48]">
                            کد یکتا: {contract.yekta_code}
                          </div>
                        ) : null}
                        <h4 className="mb-3 line-clamp-2 text-[1rem] font-black leading-snug text-[#2d3335]">
                          {contract.title}
                        </h4>
                        {contract.budget_line ? (
                          <div className="mb-4 rounded-lg bg-[#f8f9fa] px-3 py-2 text-[0.75rem] font-medium text-[#5a6062]">
                            ردیف بودجه متصل: {contract.budget_line}
                          </div>
                        ) : null}

                        <div className="mt-5 flex items-center justify-between text-[0.875rem] text-[#5a6062]">
                          <div className="flex items-center gap-2 font-medium">
                            <BriefcaseBusiness className="h-4 w-4 text-[#adb3b5]" />
                            <span>{contract.owning_org_unit_name || "قراردادهای حجمی"}</span>
                          </div>
                          <div className="flex h-8 w-8 -translate-x-2 items-center justify-center rounded-full bg-[#f8f9fa] opacity-0 transition-all group-hover:translate-x-0 group-hover:bg-[#cbe7f5] group-hover:opacity-100">
                            <ChevronLeft className="h-4 w-4 text-[#04697a]" />
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}

                  {phaseContracts.length === 0 ? (
                    <div className="flex h-40 flex-col items-center justify-center rounded-lg bg-transparent text-center">
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
          <div className="w-full max-w-xl rounded-lg bg-white p-6 shadow-[0_30px_80px_rgba(0,0,0,0.18)]">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-black text-[#2d3335]">ثبت قرارداد حجمی جدید</h2>
                <p className="mt-1 text-sm font-bold text-[#04697a]">{selectedCategory}</p>
              </div>
              <button
                type="button"
                onClick={closeCreateModal}
                className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#f1f4f5] text-[#5a6062] transition hover:bg-[#e3e8ea]"
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
                    setFormData((prev) => ({ ...prev, contract_title: event.target.value }))
                  }
                  className="rounded-lg border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
                />
              </label>
              <label className="grid gap-2 text-sm font-bold text-[#2d3335]">
                نام پیمانکار خدماتی
                <select
                  required
                  value={formData.contractor_id}
                  onChange={(event) => {
                    const selectedContractor = contractorUsers.find(
                      (contractor) => String(contractor.id) === event.target.value,
                    );
                    setFormData((prev) => ({
                      ...prev,
                      contractor_id: event.target.value,
                      contractor_name:
                        selectedContractor?.full_name || selectedContractor?.username || "",
                    }));
                  }}
                  className="rounded-lg border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
                  disabled={isLoadingContractors}
                >
                  <option value="">
                    {isLoadingContractors ? "در حال دریافت پیمانکاران..." : "انتخاب پیمانکار"}
                  </option>
                  {contractorUsers.map((contractor) => (
                    <option key={contractor.id} value={contractor.id}>
                      {contractor.full_name || contractor.username} ({contractor.username})
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
                    setFormData((prev) => ({ ...prev, total_amount: event.target.value }))
                  }
                  className="rounded-lg border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
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
                      setFormData((prev) => ({ ...prev, start_date: event.target.value }))
                    }
                    className="rounded-lg border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
                  />
                </label>
                <label className="grid gap-2 text-sm font-bold text-[#2d3335]">
                  تاریخ پایان
                  <input
                    required
                    type="date"
                    value={formData.end_date}
                    onChange={(event) =>
                      setFormData((prev) => ({ ...prev, end_date: event.target.value }))
                    }
                    className="rounded-lg border border-[#d9e1e4] px-4 py-3 text-sm outline-none focus:border-[#04697a]"
                  />
                </label>
              </div>
              {createError ? (
                <p className="rounded-lg bg-rose-50 p-3 text-sm font-bold text-rose-700">
                  {createError}
                </p>
              ) : null}
              <button
                type="submit"
                disabled={isCreating}
                className="mt-2 rounded-lg bg-[#04697a] px-5 py-3 text-sm font-black text-white transition hover:bg-[#005c6b] disabled:cursor-wait disabled:opacity-70"
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
