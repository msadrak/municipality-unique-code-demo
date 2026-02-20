import React from 'react';
import {
  FileEdit,
  UserCheck,
  Building,
  Landmark,
  BadgeCheck,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { cn } from '../ui/utils';

// Workflow step definitions
const WORKFLOW_STEPS = [
  { key: 'DRAFT', label: 'پیش‌نویس', icon: FileEdit, color: 'gray' },
  { key: 'PENDING_L1', label: 'قسمت', icon: UserCheck, color: 'amber' },
  { key: 'PENDING_L2', label: 'اداره', icon: Building, color: 'amber' },
  { key: 'PENDING_L3', label: 'حوزه', icon: Landmark, color: 'amber' },
  { key: 'PENDING_L4', label: 'ذی‌حساب', icon: BadgeCheck, color: 'amber' },
  { key: 'APPROVED', label: 'تایید نهایی', icon: CheckCircle2, color: 'green' },
] as const;

type WorkflowStep = (typeof WORKFLOW_STEPS)[number]['key'];

const STATUS_INDEX: Record<string, number> = {};
WORKFLOW_STEPS.forEach((s, i) => { STATUS_INDEX[s.key] = i; });

// Contract statuses mapped onto the same stepper for unified display
const CONTRACT_STATUS_MAP: Record<string, number> = {
  DRAFT: 0,
  PENDING_APPROVAL: 3,
  APPROVED: 5,
  REJECTED: -1,
  NOTIFIED: 5,
  IN_PROGRESS: 5,
  PENDING_COMPLETION: 5,
  COMPLETED: 5,
  CLOSED: 5,
};

interface WorkflowVisualizerProps {
  /** Current workflow status (e.g., PENDING_L2, APPROVED, REJECTED) */
  status: string;
  /** Entity type for label context */
  entityType?: 'TRANSACTION' | 'CONTRACT';
  /** Compact mode hides labels */
  compact?: boolean;
  className?: string;
}

export function WorkflowVisualizer({
  status,
  entityType = 'TRANSACTION',
  compact = false,
  className,
}: WorkflowVisualizerProps) {
  const isRejected = status === 'REJECTED';

  let activeIndex: number;
  if (entityType === 'CONTRACT') {
    activeIndex = CONTRACT_STATUS_MAP[status] ?? 0;
  } else {
    activeIndex = STATUS_INDEX[status] ?? 0;
  }

  return (
    <div className={cn('flex items-center gap-0.5', className)} dir="ltr">
      {WORKFLOW_STEPS.map((step, idx) => {
        const Icon = step.icon;
        const isCompleted = !isRejected && idx < activeIndex;
        const isActive = !isRejected && idx === activeIndex;
        const isFuture = !isRejected && idx > activeIndex;

        let ringClass = 'ring-1 ring-gray-200 bg-gray-50 text-gray-400';
        let lineClass = 'bg-gray-200';

        if (isRejected) {
          ringClass = 'ring-1 ring-red-200 bg-red-50 text-red-400';
          lineClass = 'bg-red-200';
        } else if (isCompleted) {
          ringClass = 'ring-1 ring-green-300 bg-green-50 text-green-600';
          lineClass = 'bg-green-400';
        } else if (isActive) {
          ringClass =
            step.color === 'green'
              ? 'ring-2 ring-green-500 bg-green-50 text-green-600'
              : 'ring-2 ring-amber-400 bg-amber-50 text-amber-600 animate-pulse';
          lineClass = 'bg-gray-200';
        }

        const iconSize = compact ? 'h-5 w-5' : 'h-6 w-6';
        const padClass = compact ? 'p-1' : 'p-1.5';

        return (
          <React.Fragment key={step.key}>
            {/* Connector line */}
            {idx > 0 && (
              <div
                className={cn(
                  'flex-shrink-0',
                  compact ? 'w-3 h-0.5' : 'w-5 h-0.5',
                  lineClass,
                )}
              />
            )}

            {/* Step node */}
            <div className="flex flex-col items-center flex-shrink-0">
              <div
                className={cn('rounded-full', padClass, ringClass)}
                title={step.label}
              >
                {isRejected && idx === 0 ? (
                  <XCircle className={cn(iconSize, 'text-red-500')} />
                ) : (
                  <Icon className={iconSize} />
                )}
              </div>
              {!compact && (
                <span
                  className={cn(
                    'text-[10px] mt-1 whitespace-nowrap',
                    isActive
                      ? 'text-foreground font-medium'
                      : 'text-muted-foreground',
                  )}
                >
                  {step.label}
                </span>
              )}
            </div>
          </React.Fragment>
        );
      })}

      {/* Rejected badge */}
      {isRejected && (
        <div className="flex items-center gap-1 mr-2 px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-xs font-medium">
          <XCircle className="h-3.5 w-3.5" />
          رد شده
        </div>
      )}
    </div>
  );
}

export default WorkflowVisualizer;
