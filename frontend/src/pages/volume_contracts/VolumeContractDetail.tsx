import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  CheckCircle2,
  ClipboardList,
  Clock,
  FileEdit,
  FileText,
  Menu,
  MoreVertical,
  Network,
  Paperclip,
  UserCheck,
  Wallet,
} from 'lucide-react';
import { toast } from 'sonner';

import { useAuthStore } from '../../stores/useAuthStore';
import {
  advanceVolumeContract,
  approveVolumeContractTask,
  getVolumeContract,
  VolumeContractDetail as VolumeContractDetailType,
} from '../../services/volumeContracts';
import { VolumeContractFormRenderer } from '../../components/volume_contracts/VolumeContractFormRenderer';
import { VolumeContractAttachmentViewer } from '../../components/volume_contracts/AttachmentViewer';
import { YektaIssuancePanel } from '../../components/volume_contracts/YektaIssuancePanel';
import { APPENDIX_5_FIELD_DEFINITIONS, formatRialCurrency } from '../../config/volumeContractWorkflow';
import { Button } from '../../components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';

export function VolumeContractDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [contract, setContract] = useState<VolumeContractDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [advancing, setAdvancing] = useState(false);
  const [activeTab, setActiveTab] = useState<'workflow' | 'payroll'>('workflow');
  const [domainError, setDomainError] = useState<string | null>(null);

  const fetchContract = async () => {
    try {
      if (!id) return;
      setLoading(true);
      setDomainError(null);
      const data = await getVolumeContract(id);
      if (!data.contract_category) {
        setContract(null);
        setDomainError('این شناسه متعلق به قراردادهای حجمی نیست.');
        return;
      }
      setContract(data);
    } catch (error) {
      console.error('Failed to fetch volume contract details', error);
      toast.error('خطا در دریافت اطلاعات قرارداد حجمی');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchContract();
  }, [id]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f8f9fa] p-8 text-center font-['Vazirmatn'] text-[#5a6062]">
        در حال بارگذاری پرونده قرارداد حجمی...
      </div>
    );
  }

  if (domainError) {
    return (
      <div className="min-h-screen bg-[#f8f9fa] p-8 font-['Vazirmatn']" dir="rtl">
        <Alert className="border-0 bg-[#fa746f]/10 text-[#6e0a12]">
          <AlertCircle className="h-4 w-4 text-[#a83836]" />
          <AlertTitle className="font-bold">عدم انطباق مسیر</AlertTitle>
          <AlertDescription>{domainError}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!contract) {
    return (
      <div className="min-h-screen bg-[#f8f9fa] p-8 font-['Vazirmatn']" dir="rtl">
        <Alert className="border-0 bg-[#fa746f]/10 text-[#6e0a12]">
          <AlertCircle className="h-4 w-4 text-[#a83836]" />
          <AlertTitle className="font-bold">خطا</AlertTitle>
          <AlertDescription>قرارداد حجمی یافت نشد.</AlertDescription>
        </Alert>
      </div>
    );
  }

  const stepInfo = contract.current_step_info;
  const formRequiredType = stepInfo?.required_form_type;
  const assignedRole = stepInfo?.assigned_role || null;
  const currentUserRole = user?.role || null;
  const normalizedAssignedRole = assignedRole?.trim().toUpperCase();
  const normalizedCurrentUserRole = currentUserRole?.trim().toUpperCase();
  const canExecuteCurrentStep =
    !normalizedAssignedRole ||
    normalizedCurrentUserRole === 'ADMIN' ||
    normalizedCurrentUserRole === normalizedAssignedRole;

  const pendingTasks = contract.approval_tasks?.filter((task) => task.status === 'PENDING') || [];
  const hasFormSubmitted = formRequiredType
    ? contract.documents?.some((document) => document.document_type === formRequiredType)
    : true;

  const workflowDocuments = contract.documents || [];
  const appendix5Doc = workflowDocuments.find((d) => d.document_type === 'APPENDIX_5_SALARY_ANALYSIS');
  const financialMatrixRows = contract.financial_matrix || [];
  const issuedYektaCount = financialMatrixRows.filter((row) => row.yekta_code).length;

  const handleAdvance = async () => {
    if (!id) return;
    try {
      setAdvancing(true);
      await advanceVolumeContract(id);
      toast.success('قرارداد با موفقیت به مرحله بعد ارجاع شد');
      void fetchContract();
    } catch (error) {
      toast.error('خطا در ارجاع قرارداد به مرحله بعد');
      console.error(error);
    } finally {
      setAdvancing(false);
    }
  };

  const handleApprove = async (taskId: number, status: 'APPROVED' | 'REJECTED') => {
    try {
      await approveVolumeContractTask(taskId, status);
      toast.success(status === 'APPROVED' ? 'اقدام تایید شد' : 'اقدام رد شد');
      void fetchContract();
    } catch (error) {
      toast.error('خطا در ثبت وضعیت تایید');
      console.error(error);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8f9fa] pb-24 font-['Vazirmatn'] text-[#2d3335] selection:bg-[#9febff] selection:text-[#004450]" dir="rtl">
      <header className="sticky top-0 z-50 flex h-20 w-full flex-row-reverse items-center justify-between bg-[#f8f9fa]/70 px-6 backdrop-blur-xl shadow-[0_30px_50px_rgba(45,51,53,0.04)]">
        <div className="flex items-center gap-3">
          <MoreVertical className="h-5 w-5 cursor-pointer text-[#04697a]" />
        </div>
        <h1 className="max-w-[200px] truncate text-xl font-bold text-[#04697a] md:max-w-none">
          {contract.title}
        </h1>
        <div className="flex items-center">
          <Menu className="h-5 w-5 cursor-pointer text-[#04697a]" />
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-10 px-4 py-8">
        <section className="relative overflow-hidden rounded-[1rem] bg-[#ffffff] p-8 shadow-[0_30px_50px_rgba(45,51,53,0.04)]">
          <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-gradient-to-br from-[#04697a] to-[#005c6b] opacity-5 blur-[80px]" />
          <div className="relative flex flex-col items-start gap-8 md:flex-row">
            <div className="flex-1 space-y-6">
              <div className="flex flex-wrap items-center gap-3">
                <span className="rounded-full bg-[#bbd6fe] px-4 py-1.5 text-xs font-bold text-[#304b6b] shadow-[0_4px_12px_rgba(187,214,254,0.4)]">
                  {stepInfo?.step_name || 'مرحله جاری'}
                </span>
                {contract.contract_category ? (
                  <span className="rounded-full bg-[#e8f7fb] px-4 py-1.5 text-xs font-bold text-[#04697a]">
                    {contract.contract_category}
                  </span>
                ) : null}
                {contract.budget_line ? (
                  <span className="rounded-full bg-[#f1f4f5] px-4 py-1.5 text-xs font-medium text-[#5a6062]">
                    ردیف بودجه: {contract.budget_line}
                  </span>
                ) : null}
                {issuedYektaCount > 0 ? (
                  <span className="rounded-full bg-[#f3fbf6] px-4 py-1.5 text-xs font-bold text-[#257a48]">
                    {issuedYektaCount.toLocaleString('fa-IR')} کد یکتای تراکنشی صادر شد
                  </span>
                ) : contract.yekta_code ? (
                  <span className="rounded-full bg-[#f3fbf6] px-4 py-1.5 text-xs font-bold text-[#257a48]">
                    کد یکتا: {contract.yekta_code}
                  </span>
                ) : null}
                <span className="rounded-full bg-[#f1f4f5] px-4 py-1.5 text-xs font-medium text-[#5a6062]">
                  کد قرارداد: {contract.project_code}
                </span>
              </div>
              <h2 className="text-3xl font-black tracking-tight text-[#2d3335]">پرونده قرارداد حجمی</h2>
              <p className="max-w-2xl text-[0.875rem] font-medium leading-relaxed text-[#5a6062]">
                این پرونده، جریان کامل قرارداد خدماتی را از ثبت پایه و آنالیز حقوق تا صدور کد یکتا، کارکرد ماهانه و پرداخت نهایی نمایش می‌دهد.
              </p>
            </div>
            <div className="flex h-28 w-28 shrink-0 items-center justify-center rounded-[1.5rem] bg-[#f1f4f5]">
              <ClipboardList className="h-10 w-10 text-[#04697a]" />
            </div>
          </div>
        </section>

        <nav className="flex rounded-[1rem] bg-[#f1f4f5] p-1.5 shadow-inner">
          <button
            onClick={() => setActiveTab('workflow')}
            className={`flex-1 rounded-[0.75rem] py-3 text-[0.875rem] font-bold transition-all duration-300 ${
              activeTab === 'workflow'
                ? 'bg-[#ffffff] text-[#04697a] shadow-[0_8px_16px_rgba(45,51,53,0.06)]'
                : 'text-[#5a6062] hover:bg-[#ffffff]/50'
            }`}
          >
            گردش کار قرارداد
          </button>
          <button
            onClick={() => setActiveTab('payroll')}
            className={`flex-1 rounded-[0.75rem] py-3 text-[0.875rem] font-bold transition-all duration-300 ${
              activeTab === 'payroll'
                ? 'bg-[#ffffff] text-[#04697a] shadow-[0_8px_16px_rgba(45,51,53,0.06)]'
                : 'text-[#5a6062] hover:bg-[#ffffff]/50'
            }`}
          >
            آنالیز حقوق و پرداخت
          </button>
        </nav>

        {activeTab === 'workflow' ? (
          <section className="animate-in slide-in-from-bottom-4 fade-in space-y-8 duration-500">
            <h3 className="mb-2 flex items-center gap-3 text-2xl font-black text-[#2d3335]">
              <Network className="h-6 w-6 text-[#04697a]" />
              مراحل اجرایی قرارداد
            </h3>

            <div className="relative flex flex-col gap-6">
              <div className="relative z-10 overflow-hidden rounded-[1rem] bg-[#ffffff] p-8 shadow-[0_30px_50px_rgba(45,51,53,0.04)]">
                <div className="absolute bottom-0 left-0 top-0 w-2 bg-[#04697a]" />
                <div className="mb-2 ml-4 flex items-start justify-between">
                  <span className="text-xl font-black text-[#2d3335]">{stepInfo?.step_name || 'مرحله نامشخص'}</span>
                  <span className="rounded-full bg-[#cbe7f5] px-3 py-1 text-[11px] font-bold text-[#3c5561]">در حال اجرا</span>
                </div>
                <p className="text-[0.875rem] font-medium text-[#5a6062]">
                  مرحله {stepInfo?.step_number} از {stepInfo?.total_steps}
                </p>
              </div>

              {pendingTasks.length > 0 ? (
                <div className="relative z-20 -mt-2 overflow-hidden rounded-[1rem] bg-[#ffffff] p-8 shadow-[0_20px_40px_rgba(45,51,53,0.03)]">
                  <div className="absolute bottom-0 left-0 top-0 w-2 bg-[#a83836]" />
                  <div className="mb-6 flex items-start justify-between">
                    <span className="flex items-center gap-2 text-lg font-black text-[#2d3335]">
                      <UserCheck className="h-5 w-5 text-[#a83836]" />
                      تاییدات و کارتابل مرحله
                    </span>
                    <span className="rounded-full bg-[#fa746f]/20 px-3 py-1 text-[11px] font-bold text-[#6e0a12]">منتظر اقدام</span>
                  </div>

                  <div className="space-y-4">
                    {pendingTasks.map((task) => {
                      const isMyRole =
                        user?.role?.trim().toUpperCase() === task.role?.trim().toUpperCase() ||
                        user?.role?.trim().toUpperCase() === 'ADMIN';

                      return (
                        <div
                          key={task.id}
                          className="flex flex-col items-start justify-between gap-4 rounded-[0.75rem] bg-[#f1f4f5] p-4 transition-all hover:bg-[#ffffff] hover:shadow-[0_10px_20px_rgba(45,51,53,0.05)] sm:flex-row sm:items-center"
                        >
                          <div className="flex items-center gap-3">
                            <Clock className="h-5 w-5 text-[#a83836]" />
                            <div className="text-[0.875rem] font-bold text-[#2d3335]">{task.role}</div>
                          </div>

                          {isMyRole ? (
                            <div className="flex w-full gap-3 sm:w-auto">
                              <Button
                                variant="default"
                                className="h-10 flex-1 rounded-[0.5rem] bg-gradient-to-br from-[#04697a] to-[#005c6b] px-6 font-bold text-[#effbff] shadow-[0_8px_16px_rgba(4,105,122,0.2)] transition-all hover:shadow-[0_12px_24px_rgba(4,105,122,0.3)] sm:flex-none"
                                onClick={() => handleApprove(task.id, 'APPROVED')}
                              >
                                تایید
                              </Button>
                              <Button
                                variant="outline"
                                className="h-10 flex-1 rounded-[0.5rem] border-0 bg-transparent px-6 font-bold text-[#a83836] hover:bg-[#fa746f]/10 sm:flex-none"
                                onClick={() => handleApprove(task.id, 'REJECTED')}
                              >
                                رد
                              </Button>
                            </div>
                          ) : (
                            <span className="rounded-full bg-[#e5e9eb] px-3 py-1.5 text-[11px] font-medium text-[#5a6062]">در انتظار نقش مسئول</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              {contract.can_advance && canExecuteCurrentStep ? (
                <div className="relative z-30 -mt-2 overflow-hidden rounded-[1rem] bg-[#ffffff] p-8 shadow-[0_20px_40px_rgba(45,51,53,0.05)]">
                  <div className="absolute bottom-0 left-0 top-0 w-2 bg-[#9febff]" />
                  <div className="mb-6">
                    <span className="text-xl font-black text-[#005867]">آماده ارجاع به مرحله بعد</span>
                    <p className="mt-2 text-[0.875rem] font-medium text-[#3c5561]">همه اقدامات این مرحله تکمیل شده و قرارداد آماده ادامه مسیر است.</p>
                  </div>
                  <button
                    className="w-full rounded-[0.75rem] bg-gradient-to-br from-[#04697a] to-[#005c6b] py-4 text-[1rem] font-bold text-[#effbff] shadow-[0_15px_30px_rgba(4,105,122,0.2)] transition-all hover:shadow-[0_20px_40px_rgba(4,105,122,0.3)] active:scale-[0.98] disabled:opacity-50"
                    onClick={handleAdvance}
                    disabled={advancing}
                  >
                    {advancing ? 'در حال ارجاع...' : 'ارجاع به مرحله بعد'}
                  </button>
                </div>
              ) : null}
            </div>

            {/* For file-upload steps, always show form so contractor can re-upload.
                For YEKTA_CODE_ISSUANCE (Step 103), always show the panel so
                Bahadori can fill in or review the 10-part Yekta payload. */}
            {formRequiredType ? (
              (() => {
                // Step 103 – Bahadori Yekta Sub-Process
                if (formRequiredType === 'YEKTA_CODE_ISSUANCE') {
                  return (
                    <YektaIssuancePanel
                      contract={contract}
                      canExecute={canExecuteCurrentStep}
                      hasSubmitted={hasFormSubmitted}
                      onSuccess={fetchContract}
                    />
                  );
                }

                const isFileUploadStep =
                  formRequiredType === 'APPENDIX_5_TIMESHEET' ||
                  formRequiredType === 'MONTHLY_TIMESHEET' ||
                  formRequiredType === 'CONTRACTOR_STATEMENT_UPLOAD';
                const showForm = isFileUploadStep || !hasFormSubmitted;

                if (!showForm) return null;

                return (
                  <div className="relative mt-12 rounded-[1rem] bg-[#ffffff] p-8 shadow-[0_30px_50px_rgba(45,51,53,0.03)]">
                    <div className="absolute right-8 top-0 h-1 w-16 rounded-b-full bg-[#04697a]" />
                    <h3 className="mb-6 flex items-center gap-3 text-lg font-black text-[#2d3335]">
                      <FileEdit className="h-6 w-6 text-[#04697a]" />
                      {isFileUploadStep ? 'بارگذاری فایل‌های مرحله' : 'تکمیل اطلاعات مرحله'}
                    </h3>
                    <VolumeContractFormRenderer
                      projectId={contract.id}
                      documentType={formRequiredType}
                      formSchema={stepInfo?.form_schema}
                      assignedRole={assignedRole}
                      currentUserRole={currentUserRole}
                      onSuccess={fetchContract}
                    />
                  </div>
                );
              })()
            ) : null}

            {/* Submitted notice only for non-file-upload, non-yekta steps */}
            {formRequiredType &&
              hasFormSubmitted &&
              formRequiredType !== 'APPENDIX_5_TIMESHEET' &&
              formRequiredType !== 'MONTHLY_TIMESHEET' &&
              formRequiredType !== 'CONTRACTOR_STATEMENT_UPLOAD' &&
              formRequiredType !== 'YEKTA_CODE_ISSUANCE' ? (
              <div className="mt-8 flex items-start gap-4 rounded-[1rem] bg-[#9febff]/20 p-6">
                <CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0 text-[#005867]" />
                <div>
                  <h4 className="text-lg font-bold text-[#004450]">فرم مرحله ثبت شده است</h4>
                  <p className="mt-1 text-[0.875rem] font-medium text-[#005867]">
                    اطلاعات فرم {formRequiredType} برای این قرارداد قبلا ثبت شده و در سوابق قرارداد موجود است.
                  </p>
                </div>
              </div>
            ) : null}

            {workflowDocuments.length > 0 ? (
              <section className="mt-12 space-y-6">
                <VolumeContractAttachmentViewer documents={workflowDocuments} />
              </section>
            ) : null}
          </section>
        ) : (
          <section className="animate-in slide-in-from-bottom-4 fade-in space-y-8 duration-500">
            <h3 className="mb-2 flex items-center gap-3 text-2xl font-black text-[#2d3335]">
              <Wallet className="h-6 w-6 text-[#04697a]" />
              آنالیز حقوق و پرداخت
            </h3>

            <div className="grid grid-cols-1 gap-4 rounded-[1.5rem] bg-[#f1f4f5] p-6 md:grid-cols-2">
              <div className="relative col-span-1 overflow-hidden rounded-[1rem] bg-[#ffffff] p-8 shadow-[0_20px_40px_rgba(45,51,53,0.03)] md:col-span-2">
                <div className="absolute -left-10 -top-10 h-40 w-40 rounded-full bg-gradient-to-br from-[#04697a] to-[#005c6b] opacity-5 blur-[40px]" />
                <div className="relative flex items-center justify-between gap-6">
                  <div className="space-y-2 text-right">
                    <div className="text-[0.875rem] font-bold text-[#5a6062]">سقف اعتبار متصل</div>
                    <div className="text-4xl font-black tracking-tight text-[#2d3335]">
                      {contract.financial_summary?.total_budget?.toLocaleString() || '۰'}{' '}
                      <span className="text-[1rem] font-bold text-[#adb3b5]">ریال</span>
                    </div>
                  </div>
                  <div className="hidden h-16 w-16 shrink-0 items-center justify-center rounded-[1rem] bg-[#cbe7f5] text-[#005867] sm:flex">
                    <Wallet className="h-8 w-8" />
                  </div>
                </div>
              </div>

              <div className="relative overflow-hidden rounded-[1rem] bg-[#ffffff] p-6 shadow-[0_15px_30px_rgba(45,51,53,0.02)]">
                <div className="relative z-10 space-y-2 text-right">
                  <div className="text-[0.75rem] font-bold uppercase tracking-wider text-[#5a6062]">تعهد ثبت‌شده</div>
                  <div className="text-2xl font-black text-[#2d3335]">
                    {contract.financial_summary?.committed_amount?.toLocaleString() || '۰'}{' '}
                    <span className="text-[0.75rem] font-bold text-[#adb3b5]">ریال</span>
                  </div>
                </div>
              </div>

              <div className="relative overflow-hidden rounded-[1rem] bg-gradient-to-br from-[#04697a] to-[#005c6b] p-6 shadow-[0_20px_40px_rgba(4,105,122,0.15)]">
                <div className="absolute right-0 top-0 h-32 w-32 translate-x-1/4 -translate-y-1/2 rounded-full bg-[#9febff] opacity-10 blur-2xl" />
                <div className="relative z-10 space-y-2 text-right">
                  <div className="text-[0.75rem] font-bold uppercase tracking-wider text-[#9febff]">پرداخت خالص</div>
                  <div className="text-2xl font-black text-[#ffffff]">
                    {contract.financial_summary?.total_paid_net?.toLocaleString() || '۰'}{' '}
                    <span className="text-[0.75rem] font-bold text-[#9febff]/70">ریال</span>
                  </div>
                </div>
              </div>
            </div>

            {appendix5Doc ? (
              <div className="mt-12">
                <h3 className="mb-6 flex items-center gap-3 text-xl font-black text-[#2d3335]">
                  <ClipboardList className="h-6 w-6 text-[#04697a]" />
                  آنالیز حقوق و دستمزد (پیوست ۵)
                </h3>
                <div className="overflow-hidden rounded-[1.5rem] bg-[#ffffff] shadow-[0_30px_50px_rgba(45,51,53,0.04)]">
                  <div className="overflow-x-auto">
                    <table className="w-full text-right text-[0.875rem]">
                      <thead className="bg-[#f8f9fa] text-[0.75rem] font-bold uppercase tracking-wider text-[#5a6062]">
                        <tr>
                          <th className="whitespace-nowrap p-5">شرح ردیف</th>
                          <th className="whitespace-nowrap p-5">مبلغ (ریال)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#f1f4f5]">
                        {APPENDIX_5_FIELD_DEFINITIONS.map((field) => {
                          const value = appendix5Doc.payload?.[field.key];
                          return (
                            <tr key={field.key} className="transition-colors hover:bg-[#f1f4f5]">
                              <td className="p-5 font-bold text-[#3c5561]">{field.label}</td>
                              <td className="p-5 font-black text-[#04697a]" dir="ltr">
                                {formatRialCurrency(value).replace(' ریال', '')}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : null}

            <div className="mt-12">
              <h3 className="mb-6 text-xl font-black text-[#2d3335]">ماتریس مالی و کدهای یکتای تراکنشی</h3>
              <div className="overflow-hidden rounded-[1.5rem] bg-[#ffffff] shadow-[0_30px_50px_rgba(45,51,53,0.04)]">
                <div className="overflow-x-auto">
                  <table className="w-full text-right text-[0.875rem]">
                    <thead className="bg-[#f8f9fa] text-[0.75rem] font-bold uppercase tracking-wider text-[#5a6062]">
                      <tr>
                        <th className="whitespace-nowrap p-5">رویداد مالی</th>
                        <th className="whitespace-nowrap p-5">مبلغ (ریال)</th>
                        <th className="whitespace-nowrap p-5">کد یکتا</th>
                        <th className="whitespace-nowrap p-5">وضعیت صف پرداخت</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#f1f4f5]">
                      {financialMatrixRows.length > 0 ? (
                        financialMatrixRows.map((row) => (
                          <tr key={row.id} className="transition-colors hover:bg-[#f1f4f5]">
                            <td className="p-5">
                              <div className="font-black text-[#3c5561]">{row.event_label || row.event_code}</div>
                              <div className="mt-1 font-mono text-xs text-[#adb3b5]" dir="ltr">{row.event_code}</div>
                            </td>
                            <td className="p-5 font-black text-[#04697a]">{row.amount?.toLocaleString() || '۰'}</td>
                            <td className="p-5 font-mono text-xs font-bold text-[#3c5561]" dir="ltr">{row.yekta_code || '—'}</td>
                            <td className="p-5">
                              <span className="rounded-full bg-[#f3fbf6] px-3 py-1 text-xs font-bold text-[#257a48]">
                                {row.payment_queue_status === 'READY_FOR_PAYMENT_QUEUE' ? 'آماده پرداخت' : row.payment_queue_status || 'در انتظار'}
                              </span>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={4} className="p-12 text-center text-[#5a6062]">
                            <div className="flex flex-col items-center gap-3">
                              <FileText className="h-10 w-10 text-[#adb3b5] opacity-50" />
                              <p className="text-[0.875rem] font-medium">هنوز ماتریس مالی چندردیفی برای این صورت‌وضعیت صادر نشده است</p>
                            </div>
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </section>
        )}

        <div className="flex justify-start">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="rounded-[0.75rem] bg-[#f1f4f5] px-4 py-2 text-sm font-bold text-[#5a6062] transition hover:bg-[#e5e9eb]"
          >
            بازگشت
          </button>
        </div>
      </main>
    </div>
  );
}

export default VolumeContractDetail;
