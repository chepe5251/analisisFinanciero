import type { ReconciliationStatus, UploadStatus } from "@/lib/types";
import {
  STATUS_LABEL, STATUS_COLOR,
  UPLOAD_STATUS_LABEL, UPLOAD_STATUS_COLOR,
} from "@/lib/utils";

interface ReconciliationBadgeProps {
  status: ReconciliationStatus;
}

export function ReconciliationBadge({ status }: ReconciliationBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLOR[status]}`}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}

interface UploadBadgeProps {
  status: UploadStatus;
}

export function UploadBadge({ status }: UploadBadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${UPLOAD_STATUS_COLOR[status]}`}
    >
      {UPLOAD_STATUS_LABEL[status]}
    </span>
  );
}
