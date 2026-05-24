import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/useAuthStore';
import { getCivilProject, advanceProject, approveTask, CivilProjectDetail as CivilProjectDetailType } from '../../services/civil';
import { DynamicFormRenderer } from '../../components/civil/DynamicFormRenderer';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { toast } from 'sonner';
import { CheckCircle2, AlertCircle, Clock, FileText, UserCheck, MoreVertical, Menu, Network, Wallet, FileEdit, Paperclip } from 'lucide-react';

export function CivilProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [project, setProject] = useState<CivilProjectDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [advancing, setAdvancing] = useState(false);
  const [activeTab, setActiveTab] = useState<'workflow' | 'financial'>('workflow');

  const fetchProject = async () => {
    try {
      if (!id) return;
      setLoading(true);
      const data = await getCivilProject(id);
      if (data.contract_category) {
        navigate(`/volume-contracts/${data.id}`, { replace: true });
        return;
      }
      setProject(data);
    } catch (error) {
      console.error('Failed to fetch project details', error);
      toast.error('خطا در دریافت اطلاعات پروژه');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchProject();
  }, [id, navigate]);

  if (loading) {
    return <div className="p-8 text-center text-[#5a6062] font-['Vazirmatn'] bg-[#f8f9fa] min-h-screen flex items-center justify-center">در حال بارگذاری اطلاعات پرونده دیجیتال...</div>;
  }

  if (!project) {
    return (
      <div className="p-8 bg-[#f8f9fa] min-h-screen font-['Vazirmatn']" dir="rtl">
        <Alert className="bg-[#fa746f]/10 border-0 text-[#6e0a12]">
          <AlertCircle className="h-4 w-4 text-[#a83836]" />
          <AlertTitle className="font-bold">خطا</AlertTitle>
          <AlertDescription>پروژه یافت نشد.</AlertDescription>
        </Alert>
      </div>
    );
  }

  const stepInfo = project.current_step_info;
  const formRequiredType = stepInfo?.required_form_type;
  const assignedRole = stepInfo?.assigned_role || null;
  const currentUserRole = user?.role || null;
  const normalizedAssignedRole = assignedRole?.trim().toUpperCase();
  const normalizedCurrentUserRole = currentUserRole?.trim().toUpperCase();
  const canExecuteCurrentStep =
    !normalizedAssignedRole ||
    normalizedCurrentUserRole === 'ADMIN' ||
    normalizedCurrentUserRole === normalizedAssignedRole;
  
  const pendingTasks = project.approval_tasks?.filter(t => t.status === 'PENDING') || [];
  const hasFormSubmitted = formRequiredType 
    ? project.documents?.some(d => d.document_type === formRequiredType)
    : true;

  const isReadyToAdvance = project.can_advance;
  const workflowDocuments = project.documents || [];

  const handleAdvance = async () => {
    if (!id) return;
    try {
      setAdvancing(true);
      await advanceProject(id);
      toast.success('پروژه با موفقیت به مرحله بعد ارتقا یافت');
      fetchProject();
    } catch (error) {
      toast.error('خطا در ارتقای مرحله پروژه');
      console.error(error);
    } finally {
      setAdvancing(false);
    }
  };

  const handleApprove = async (taskId: number, status: 'APPROVED' | 'REJECTED') => {
    try {
      await approveTask(taskId, status);
      toast.success(status === 'APPROVED' ? 'تایید شد' : 'رد شد');
      fetchProject();
    } catch (error) {
      toast.error('خطا در ثبت وضعیت');
      console.error(error);
    }
  };

  return (
    <div className="text-[#2d3335] min-h-screen pb-24 bg-[#f8f9fa] font-['Vazirmatn'] selection:bg-[#9febff] selection:text-[#004450]" dir="rtl">
      {/* TopAppBar Section - Glassmorphism */}
      <header className="bg-[#f8f9fa]/70 backdrop-blur-xl sticky top-0 z-50 flex items-center justify-between px-6 h-20 w-full flex-row-reverse shadow-[0_30px_50px_rgba(45,51,53,0.04)]">
        <div className="flex items-center gap-3">
          <MoreVertical className="w-5 h-5 text-[#04697a] cursor-pointer" />
        </div>
        <h1 className="font-bold text-xl text-[#04697a] truncate max-w-[200px] md:max-w-none">
          {project.title}
        </h1>
        <div className="flex items-center">
          <Menu className="w-5 h-5 text-[#04697a] cursor-pointer" />
        </div>
      </header>

      <main className="px-4 py-8 space-y-10 max-w-5xl mx-auto">
        {/* Project Hero Card - Asymmetric, No Lines */}
        <section className="relative overflow-hidden rounded-[1rem] bg-[#ffffff] p-8 shadow-[0_30px_50px_rgba(45,51,53,0.04)]">
          <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-gradient-to-br from-[#04697a] to-[#005c6b] opacity-5 blur-[80px]" />
          <div className="relative flex flex-col md:flex-row gap-8 items-start">
            <div className="flex-1 space-y-6">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="bg-[#bbd6fe] text-[#304b6b] px-4 py-1.5 rounded-full text-xs font-bold shadow-[0_4px_12px_rgba(187,214,254,0.4)]">
                  {stepInfo?.step_name || 'در حال اجرا'}
                </span>
                {project.contract_category && (
                  <span className="bg-[#e8f7fb] text-[#04697a] px-4 py-1.5 rounded-full text-xs font-bold">
                    {project.contract_category}
                  </span>
                )}
                {project.budget_line && (
                  <span className="bg-[#f1f4f5] text-[#5a6062] px-4 py-1.5 rounded-full text-xs font-medium">
                    ردیف بودجه: {project.budget_line}
                  </span>
                )}
                {project.yekta_code && (
                  <span className="bg-[#f3fbf6] text-[#257a48] px-4 py-1.5 rounded-full text-xs font-bold">
                    کد یکتا: {project.yekta_code}
                  </span>
                )}
                <span className="bg-[#f1f4f5] text-[#5a6062] px-4 py-1.5 rounded-full text-xs font-medium">
                  کد پروژه: {project.project_code}
                </span>
              </div>
              <h2 className="text-3xl font-black text-[#2d3335] tracking-tight">پرونده دیجیتال پروژه عمرانی</h2>
              <p className="text-[#5a6062] text-[0.875rem] leading-relaxed max-w-2xl font-medium">
                این پرونده نمایانگر گردش کار جامع پروژه و خلاصه وضعیت مالی مصوب و پرداخت‌های مرتبط با پیمانکاران می‌باشد.
              </p>
            </div>
            <div className="flex h-28 w-28 shrink-0 items-center justify-center rounded-[1.5rem] bg-[#f1f4f5]">
              <FileText className="h-10 w-10 text-[#04697a]" />
            </div>
          </div>
        </section>

        {/* Segmented Control (Tabs) */}
        <nav className="flex p-1.5 bg-[#f1f4f5] rounded-[1rem] shadow-inner">
          <button 
            onClick={() => setActiveTab('workflow')}
            className={`flex-1 py-3 text-[0.875rem] font-bold transition-all duration-300 rounded-[0.75rem] ${activeTab === 'workflow' ? 'bg-[#ffffff] text-[#04697a] shadow-[0_8px_16px_rgba(45,51,53,0.06)]' : 'text-[#5a6062] hover:bg-[#ffffff]/50'}`}
          >
            عملیات و گردش کار
          </button>
          <button 
            onClick={() => setActiveTab('financial')}
            className={`flex-1 py-3 text-[0.875rem] font-bold transition-all duration-300 rounded-[0.75rem] ${activeTab === 'financial' ? 'bg-[#ffffff] text-[#04697a] shadow-[0_8px_16px_rgba(45,51,53,0.06)]' : 'text-[#5a6062] hover:bg-[#ffffff]/50'}`}
          >
            دفترچه مالی
          </button>
        </nav>

        {/* Tab Content Area */}
        {activeTab === 'workflow' ? (
          <section className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h3 className="text-2xl font-black flex items-center gap-3 text-[#2d3335] mb-2">
              <Network className="w-6 h-6 text-[#04697a]" />
              مراحل اجرایی پروژه
            </h3>
            
            {/* Workflow Stack (Soft-path stepper, no lines) */}
            <div className="flex flex-col gap-6 relative">
              
              {/* Active Step Indicator */}
              <div className="bg-[#ffffff] p-8 rounded-[1rem] shadow-[0_30px_50px_rgba(45,51,53,0.04)] relative overflow-hidden z-10">
                <div className="absolute left-0 top-0 bottom-0 w-2 bg-[#04697a]" />
                <div className="flex justify-between items-start mb-2 ml-4">
                  <span className="text-xl font-black text-[#2d3335]">{stepInfo?.step_name || 'مرحله نامشخص'}</span>
                  <span className="bg-[#cbe7f5] text-[#3c5561] px-3 py-1 rounded-full text-[11px] font-bold">در حال اجرا</span>
                </div>
                <p className="text-[#5a6062] text-[0.875rem] font-medium">مرحله {stepInfo?.step_number} از {stepInfo?.total_steps}</p>
              </div>

              {/* Approval Inbox */}
              {pendingTasks.length > 0 && (
                <div className="bg-[#ffffff] p-8 rounded-[1rem] shadow-[0_20px_40px_rgba(45,51,53,0.03)] relative overflow-hidden z-20 -mt-2">
                  <div className="absolute left-0 top-0 bottom-0 w-2 bg-[#a83836]" />
                  <div className="flex justify-between items-start mb-6">
                    <span className="font-black text-lg flex items-center gap-2 text-[#2d3335]">
                      <UserCheck className="w-5 h-5 text-[#a83836]" />
                      تاییدات مورد نیاز
                    </span>
                    <span className="bg-[#fa746f]/20 text-[#6e0a12] px-3 py-1 rounded-full text-[11px] font-bold">منتظر اقدام</span>
                  </div>
                  
                  <div className="space-y-4">
                    {pendingTasks.map(task => {
                      const isMyRole = user?.role?.trim().toUpperCase() === task.role?.trim().toUpperCase() || user?.role?.trim().toUpperCase() === 'ADMIN';
                      return (
                        <div key={task.id} className="p-4 bg-[#f1f4f5] rounded-[0.75rem] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 transition-all hover:bg-[#ffffff] hover:shadow-[0_10px_20px_rgba(45,51,53,0.05)]">
                          <div className="flex items-center gap-3">
                            <Clock className="w-5 h-5 text-[#a83836]" />
                            <div className="text-[0.875rem] font-bold text-[#2d3335]">{task.role}</div>
                          </div>
                          
                          {isMyRole ? (
                            <div className="flex gap-3 w-full sm:w-auto">
                              <Button 
                                variant="default" 
                                className="bg-gradient-to-br from-[#04697a] to-[#005c6b] text-[#effbff] shadow-[0_8px_16px_rgba(4,105,122,0.2)] hover:shadow-[0_12px_24px_rgba(4,105,122,0.3)] transition-all flex-1 sm:flex-none font-bold rounded-[0.5rem] h-10 px-6"
                                onClick={() => handleApprove(task.id, 'APPROVED')}
                              >
                                تایید
                              </Button>
                              <Button 
                                variant="outline" 
                                className="bg-transparent border-0 text-[#a83836] hover:bg-[#fa746f]/10 flex-1 sm:flex-none font-bold rounded-[0.5rem] h-10 px-6"
                                onClick={() => handleApprove(task.id, 'REJECTED')}
                              >
                                رد
                              </Button>
                            </div>
                          ) : (
                            <span className="text-[11px] text-[#5a6062] bg-[#e5e9eb] px-3 py-1.5 rounded-full font-medium">در انتظار شخص دیگر</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Ready to Advance */}
              {isReadyToAdvance && canExecuteCurrentStep && (
                <div className="bg-[#ffffff] p-8 rounded-[1rem] shadow-[0_20px_40px_rgba(45,51,53,0.05)] relative overflow-hidden z-30 -mt-2">
                  <div className="absolute left-0 top-0 bottom-0 w-2 bg-[#9febff]" />
                  <div className="mb-6">
                    <span className="font-black text-xl text-[#005867]">آماده ارتقا</span>
                    <p className="text-[0.875rem] text-[#3c5561] mt-2 font-medium">تمامی اقدامات این مرحله انجام شده است.</p>
                  </div>
                  <button 
                    className="w-full bg-gradient-to-br from-[#04697a] to-[#005c6b] text-[#effbff] font-bold py-4 rounded-[0.75rem] shadow-[0_15px_30px_rgba(4,105,122,0.2)] hover:shadow-[0_20px_40px_rgba(4,105,122,0.3)] transition-all active:scale-[0.98] disabled:opacity-50 text-[1rem]"
                    onClick={handleAdvance}
                    disabled={advancing}
                  >
                    {advancing ? 'در حال ارتقا...' : 'ارجاع به مرحله بعد'}
                  </button>
                </div>
              )}
            </div>

            {/* Dynamic Form Section */}
            {formRequiredType && !hasFormSubmitted && (
              <div className="bg-[#ffffff] rounded-[1rem] p-8 mt-12 shadow-[0_30px_50px_rgba(45,51,53,0.03)] relative">
                <div className="absolute top-0 right-8 w-16 h-1 bg-[#04697a] rounded-b-full" />
                <h3 className="text-lg font-black mb-6 flex items-center gap-3 text-[#2d3335]">
                  <FileEdit className="text-[#04697a] w-6 h-6" />
                  تکمیل اطلاعات {formRequiredType}
                </h3>
                <DynamicFormRenderer 
                  projectId={project.id} 
                  documentType={formRequiredType} 
                  formSchema={stepInfo?.form_schema}
                  assignedRole={assignedRole}
                  currentUserRole={currentUserRole}
                  onSuccess={fetchProject} 
                />
              </div>
            )}
            {formRequiredType && hasFormSubmitted && (
              <div className="bg-[#9febff]/20 p-6 rounded-[1rem] flex gap-4 items-start mt-8">
                <CheckCircle2 className="h-6 w-6 text-[#005867] shrink-0 mt-0.5" />
                <div>
                  <h4 className="font-bold text-[#004450] text-lg">فرم تکمیل شده</h4>
                  <p className="text-[#005867] text-[0.875rem] font-medium mt-1">
                    اطلاعات فرم {formRequiredType} قبلا ثبت شده است.
                  </p>
                </div>
              </div>
            )}

            {/* Document History */}
            {workflowDocuments.length > 0 && (
              <section className="bg-[#f1f4f5] rounded-[1.5rem] p-8 mt-12">
                <h3 className="text-lg font-black mb-6 flex items-center gap-3 text-[#2d3335]">
                  <FileText className="text-[#04697a] w-6 h-6" />
                  سوابق فرم‌ها و پیوست‌ها
                </h3>
                <div className="space-y-4">
                  {workflowDocuments.map((doc) => {
                    const attachments = Array.isArray(doc.payload?._attachments)
                      ? doc.payload._attachments
                      : [];
                    return (
                      <div key={doc.id} className="bg-[#ffffff] rounded-[1rem] p-5 shadow-[0_10px_20px_rgba(45,51,53,0.02)] transition-all hover:shadow-[0_15px_30px_rgba(45,51,53,0.05)]">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                          <div className="font-black text-[#2d3335] text-[0.875rem]">{doc.document_type}</div>
                          <div className="text-[11px] font-bold text-[#5a6062] bg-[#f1f4f5] px-3 py-1 rounded-full">
                            {doc.submitted_by || '-'} | {doc.submitted_at || '-'}
                          </div>
                        </div>
                        {attachments.length > 0 && (
                          <div className="mt-4 flex flex-wrap gap-2">
                            {attachments.map((attachment: any, index: number) => (
                              <a
                                key={`${attachment.file_url}-${index}`}
                                href={attachment.file_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1.5 rounded-[0.5rem] bg-[#cbe7f5]/50 px-3 py-1.5 text-[11px] font-bold text-[#005867] hover:bg-[#cbe7f5] transition-colors"
                              >
                                <Paperclip className="h-3 w-3" />
                                {attachment.file_name || `پیوست ${index + 1}`}
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            )}
          </section>
        ) : (
          <section className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h3 className="text-2xl font-black flex items-center gap-3 text-[#2d3335] mb-2">
              <Wallet className="w-6 h-6 text-[#04697a]" />
              خلاصه وضعیت مالی
            </h3>
            
            {/* KPI Cards Bento - Nested Surface approach */}
            <div className="bg-[#f1f4f5] p-6 rounded-[1.5rem] grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-[#ffffff] shadow-[0_20px_40px_rgba(45,51,53,0.03)] rounded-[1rem] p-8 col-span-1 md:col-span-2 relative overflow-hidden">
                <div className="absolute -left-10 -top-10 h-40 w-40 rounded-full bg-gradient-to-br from-[#04697a] to-[#005c6b] opacity-5 blur-[40px]" />
                <div className="relative flex items-center justify-between gap-6">
                  <div className="space-y-2 text-right">
                    <div className="text-[0.875rem] font-bold text-[#5a6062]">بودجه کل مصوب</div>
                    <div className="text-4xl font-black tracking-tight text-[#2d3335]">
                      {project.financial_summary?.total_budget?.toLocaleString() || '۲۴,۵۰۰,۰۰۰,۰۰۰'} <span className="text-[1rem] font-bold text-[#adb3b5]">ریال</span>
                    </div>
                  </div>
                  <div className="hidden sm:flex h-16 w-16 shrink-0 items-center justify-center rounded-[1rem] bg-[#cbe7f5] text-[#005867]">
                    <Wallet className="h-8 w-8" />
                  </div>
                </div>
              </div>
              
              <div className="bg-[#ffffff] shadow-[0_15px_30px_rgba(45,51,53,0.02)] rounded-[1rem] p-6 relative overflow-hidden">
                <div className="space-y-2 text-right relative z-10">
                  <div className="text-[0.75rem] font-bold uppercase tracking-wider text-[#5a6062]">تعهد شده</div>
                  <div className="text-2xl font-black text-[#2d3335]">
                    {project.financial_summary?.committed_amount?.toLocaleString() || '۱۸,۲۰۰,۰۰۰,۰۰۰'} <span className="text-[0.75rem] font-bold text-[#adb3b5]">ریال</span>
                  </div>
                </div>
              </div>
              
              <div className="bg-gradient-to-br from-[#04697a] to-[#005c6b] shadow-[0_20px_40px_rgba(4,105,122,0.15)] rounded-[1rem] p-6 relative overflow-hidden">
                <div className="absolute right-0 top-0 w-32 h-32 bg-[#9febff] opacity-10 rounded-full blur-2xl -translate-y-1/2 translate-x-1/4" />
                <div className="space-y-2 text-right relative z-10">
                  <div className="text-[0.75rem] font-bold uppercase tracking-wider text-[#9febff]">پرداختی خالص</div>
                  <div className="text-2xl font-black text-[#ffffff]">
                    {project.financial_summary?.total_paid_net?.toLocaleString() || '۹,۸۵۰,۰۰۰,۰۰۰'} <span className="text-[0.75rem] font-bold text-[#9febff]/70">ریال</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Transactions Table - No borders, tonal hover */}
            <div className="mt-12">
              <h3 className="text-xl font-black mb-6 text-[#2d3335]">تراکنش‌های مالی ثبت شده</h3>
              <div className="bg-[#ffffff] rounded-[1.5rem] shadow-[0_30px_50px_rgba(45,51,53,0.04)] overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-[0.875rem] text-right">
                    <thead className="bg-[#f8f9fa] text-[#5a6062] text-[0.75rem] font-bold uppercase tracking-wider">
                      <tr>
                        <th className="p-5 whitespace-nowrap">شماره سند</th>
                        <th className="p-5 whitespace-nowrap">تاریخ</th>
                        <th className="p-5 whitespace-nowrap">مبلغ (ریال)</th>
                        <th className="p-5 whitespace-nowrap">توضیحات</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#f1f4f5]">
                      {project.transactions && project.transactions.length > 0 ? (
                        project.transactions.map((tx: any) => (
                          <tr key={tx.id} className="hover:bg-[#f1f4f5] transition-colors">
                            <td className="p-5 font-mono text-[#3c5561] font-bold">{tx.document_number}</td>
                            <td className="p-5 text-[#5a6062] font-medium">{tx.date}</td>
                            <td className="p-5 font-black text-[#04697a]">{tx.amount?.toLocaleString()}</td>
                            <td className="p-5 text-[#5a6062] font-medium max-w-[200px] truncate">{tx.description}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan={4} className="p-12 text-center text-[#5a6062]">
                            <div className="flex flex-col items-center gap-3">
                              <FileText className="w-10 h-10 text-[#adb3b5] opacity-50" />
                              <p className="font-medium text-[0.875rem]">تراکنشی در سیستم ثبت نشده است</p>
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
      </main>
    </div>
  );
}

export default CivilProjectDetail;
