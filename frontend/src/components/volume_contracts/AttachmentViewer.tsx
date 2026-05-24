import React, { useEffect, useMemo, useState } from 'react';
import {
  Download,
  ExternalLink,
  Eye,
  FileArchive,
  FileDigit,
  FileImage,
  FileText,
  Paperclip,
} from 'lucide-react';

import type { VolumeContractDocument } from '../../services/volumeContracts';
import {
  formatPersianDateTime,
  getVolumeContractStepByDocumentType,
  VOLUME_CONTRACT_ATTACHMENT_SECTION_LABELS,
  type VolumeContractAttachmentSection,
} from '../../config/volumeContractWorkflow';

interface VolumeContractAttachmentViewerProps {
  documents: VolumeContractDocument[];
}

interface VolumeContractAttachmentItem {
  id: string;
  fileName: string;
  fileUrl: string;
  contentType?: string | null;
  size?: number | null;
  stepNumber?: number;
  stepTitle: string;
  stepLabel: string;
  section: VolumeContractAttachmentSection;
  submittedBy?: string | null;
  submittedAt?: string | null;
}

const EMPTY_GROUPS: Record<VolumeContractAttachmentSection, VolumeContractAttachmentItem[]> = {
  contract: [],
  monthly: [],
};

function getFileExtension(fileName: string): string {
  const segments = fileName.split('.');
  return segments.length > 1 ? segments.at(-1)?.toLowerCase() || '' : '';
}

function isPdfAttachment(file: VolumeContractAttachmentItem): boolean {
  return file.contentType?.includes('pdf') || getFileExtension(file.fileName) === 'pdf';
}

function isWordAttachment(file: VolumeContractAttachmentItem): boolean {
  const extension = getFileExtension(file.fileName);
  return (
    file.contentType?.includes('word')
    || file.contentType?.includes('officedocument')
    || extension === 'doc'
    || extension === 'docx'
  );
}

function isImageAttachment(file: VolumeContractAttachmentItem): boolean {
  return file.contentType?.startsWith('image/') || ['png', 'jpg', 'jpeg', 'webp'].includes(getFileExtension(file.fileName));
}

function formatFileSize(size?: number | null): string {
  if (!size || size <= 0) return 'نامشخص';
  if (size >= 1024 * 1024) {
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }
  if (size >= 1024) {
    return `${Math.round(size / 1024)} KB`;
  }
  return `${size} B`;
}

function getAttachmentIcon(file: VolumeContractAttachmentItem) {
  if (isPdfAttachment(file)) return FileText;
  if (isWordAttachment(file)) return FileDigit;
  if (isImageAttachment(file)) return FileImage;
  return FileArchive;
}

function getPreviewTitle(file: VolumeContractAttachmentItem): string {
  if (isPdfAttachment(file)) return 'پیش نمایش PDF';
  if (isWordAttachment(file)) return 'پیش نمایش فایل Word';
  if (isImageAttachment(file)) return 'پیش نمایش تصویر';
  return 'پیش نمایش فایل';
}

export function VolumeContractAttachmentViewer({ documents }: VolumeContractAttachmentViewerProps) {
  const attachments = useMemo<VolumeContractAttachmentItem[]>(() => {
    return documents
      .flatMap((document) => {
        const step = getVolumeContractStepByDocumentType(document.document_type);
        const rawAttachments = Array.isArray(document.payload?._attachments)
          ? document.payload._attachments
          : [];

        return rawAttachments.map((attachment: Record<string, unknown>, index: number) => ({
          id: `${document.id}-${index}`,
          fileName: String(attachment.file_name || `پیوست ${index + 1}`),
          fileUrl: String(attachment.file_url || ''),
          contentType: attachment.content_type ? String(attachment.content_type) : null,
          size: typeof attachment.size === 'number' ? attachment.size : Number(attachment.size || 0),
          stepNumber: step?.stepNumber,
          stepTitle: step?.title || document.document_type,
          stepLabel: step ? `مرحله ${step.stepNumber}` : 'مرحله ثبت نشده',
          section: step?.attachmentSection || 'contract',
          submittedBy: document.submitted_by,
          submittedAt: document.submitted_at,
        }));
      })
      .filter((attachment) => attachment.fileUrl);
  }, [documents]);

  const [selectedAttachmentId, setSelectedAttachmentId] = useState<string | null>(attachments[0]?.id ?? null);

  useEffect(() => {
    if (!attachments.length) {
      setSelectedAttachmentId(null);
      return;
    }

    setSelectedAttachmentId((current) => {
      if (current && attachments.some((attachment) => attachment.id === current)) {
        return current;
      }
      return attachments[0].id;
    });
  }, [attachments]);

  const groupedAttachments = useMemo(() => {
    return attachments.reduce<Record<VolumeContractAttachmentSection, VolumeContractAttachmentItem[]>>((groups, attachment) => {
      groups[attachment.section].push(attachment);
      return groups;
    }, { ...EMPTY_GROUPS });
  }, [attachments]);

  const selectedAttachment = attachments.find((attachment) => attachment.id === selectedAttachmentId) || null;

  if (!attachments.length) {
    return (
      <div className="rounded-[1rem] bg-[#ffffff] p-8 shadow-[0_20px_40px_rgba(45,51,53,0.03)]">
        <div className="mb-3 flex items-center gap-3 text-[#2d3335]">
          <Paperclip className="h-5 w-5 text-[#04697a]" />
          <h3 className="text-lg font-black">اسناد و پیوست‌های قرارداد</h3>
        </div>
        <p className="text-sm font-medium leading-7 text-[#5a6062]">
          هنوز فایل Word یا PDF برای این قرارداد بارگذاری نشده است. فایل‌های مراحل ۱۰۱ تا ۱۱۰ پس از ثبت فرم‌ها در این بخش قابل مشاهده خواهند بود.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.25fr)]">
      <div className="space-y-4">
        {(Object.keys(groupedAttachments) as VolumeContractAttachmentSection[]).map((sectionKey) => {
          const sectionItems = groupedAttachments[sectionKey];
          if (!sectionItems.length) return null;

          return (
            <div key={sectionKey} className="rounded-[1rem] bg-[#ffffff] p-5 shadow-[0_20px_40px_rgba(45,51,53,0.03)]">
              <div className="mb-4 flex items-center gap-2">
                <Paperclip className="h-4 w-4 text-[#04697a]" />
                <h4 className="text-sm font-black text-[#2d3335]">
                  {VOLUME_CONTRACT_ATTACHMENT_SECTION_LABELS[sectionKey]}
                </h4>
              </div>

              <div className="space-y-3">
                {sectionItems.map((attachment) => {
                  const Icon = getAttachmentIcon(attachment);
                  const isActive = attachment.id === selectedAttachmentId;

                  return (
                    <button
                      key={attachment.id}
                      type="button"
                      onClick={() => setSelectedAttachmentId(attachment.id)}
                      className={`w-full rounded-[0.9rem] border px-4 py-3 text-right transition-all ${
                        isActive
                          ? 'border-[#04697a] bg-[#e8f7fb] shadow-[0_12px_24px_rgba(4,105,122,0.08)]'
                          : 'border-[#eef2f4] bg-[#f8f9fa] hover:border-[#cbe7f5] hover:bg-[#ffffff]'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-[0.8rem] bg-white text-[#04697a] shadow-[0_4px_10px_rgba(45,51,53,0.04)]">
                          <Icon className="h-5 w-5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-black text-[#2d3335]">{attachment.fileName}</div>
                          <div className="mt-1 text-xs font-bold text-[#04697a]">
                            {attachment.stepLabel} - {attachment.stepTitle}
                          </div>
                          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] font-medium text-[#5a6062]">
                            <span>حجم: {formatFileSize(attachment.size)}</span>
                            <span>ثبت کننده: {attachment.submittedBy || '—'}</span>
                            <span>{formatPersianDateTime(attachment.submittedAt)}</span>
                          </div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      <div className="rounded-[1rem] bg-[#ffffff] p-6 shadow-[0_24px_48px_rgba(45,51,53,0.04)]">
        {selectedAttachment ? (
          <>
            <div className="mb-5 flex flex-wrap items-start justify-between gap-4 border-b border-[#eef2f4] pb-5">
              <div>
                <div className="text-lg font-black text-[#2d3335]">{selectedAttachment.fileName}</div>
                <div className="mt-2 text-sm font-bold text-[#04697a]">
                  {selectedAttachment.stepLabel} - {selectedAttachment.stepTitle}
                </div>
                <div className="mt-2 text-xs font-medium text-[#5a6062]">
                  {getPreviewTitle(selectedAttachment)} | {formatFileSize(selectedAttachment.size)}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <a
                  href={selectedAttachment.fileUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-2 rounded-[0.75rem] bg-[#04697a] px-4 py-2 text-sm font-bold text-white transition hover:bg-[#005c6b]"
                >
                  <Eye className="h-4 w-4" />
                  باز کردن فایل
                </a>
                <a
                  href={selectedAttachment.fileUrl}
                  download={selectedAttachment.fileName}
                  className="inline-flex items-center gap-2 rounded-[0.75rem] bg-[#f1f4f5] px-4 py-2 text-sm font-bold text-[#2d3335] transition hover:bg-[#e5e9eb]"
                >
                  <Download className="h-4 w-4" />
                  دانلود
                </a>
              </div>
            </div>

            {isImageAttachment(selectedAttachment) ? (
              <img
                src={selectedAttachment.fileUrl}
                alt={selectedAttachment.fileName}
                className="h-[520px] w-full rounded-[0.9rem] border border-[#eef2f4] object-contain bg-[#f8f9fa]"
              />
            ) : isPdfAttachment(selectedAttachment) || isWordAttachment(selectedAttachment) ? (
              <div className="space-y-3">
                <iframe
                  src={selectedAttachment.fileUrl}
                  title={selectedAttachment.fileName}
                  className="h-[520px] w-full rounded-[0.9rem] border border-[#eef2f4] bg-[#f8f9fa]"
                />
                {isWordAttachment(selectedAttachment) ? (
                  <div className="rounded-[0.75rem] bg-[#f8f9fa] px-4 py-3 text-xs font-medium leading-6 text-[#5a6062]">
                    اگر مرورگر امکان نمایش مستقیم فایل Word را نداشت، از گزینه «باز کردن فایل» یا «دانلود» استفاده کنید.
                  </div>
                ) : null}
              </div>
            ) : (
              <div className="flex h-[520px] flex-col items-center justify-center rounded-[0.9rem] border border-dashed border-[#d9e1e4] bg-[#f8f9fa] text-center">
                <ExternalLink className="mb-3 h-10 w-10 text-[#04697a]" />
                <p className="text-sm font-bold text-[#2d3335]">پیش نمایش مستقیم برای این نوع فایل در دسترس نیست.</p>
                <p className="mt-2 max-w-md text-xs font-medium leading-6 text-[#5a6062]">
                  برای مشاهده فایل، آن را در یک برگه جدید باز کنید یا نسخه اصلی را دانلود نمایید.
                </p>
              </div>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}

export default VolumeContractAttachmentViewer;
