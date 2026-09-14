import { statusLabels, statusTone, type KnownStatus } from '@/lib/status';
import { Badge } from './Badge';

export function StatusBadge({ status }: { status: KnownStatus }) {
  return <Badge tone={statusTone(status)}>{statusLabels[status]}</Badge>;
}
