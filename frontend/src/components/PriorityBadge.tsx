import type { TaskPriority } from "../api/types";

const LABEL: Record<TaskPriority, string> = {
  Alta: "Alta",
  Media: "Media",
  Baja: "Baja",
};

const CLASS: Record<TaskPriority, string> = {
  Alta: "stamp stamp--alta",
  Media: "stamp stamp--media",
  Baja: "stamp stamp--baja",
};

export function PriorityBadge({ priority }: { priority: TaskPriority }) {
  return <span className={CLASS[priority]}>{LABEL[priority]}</span>;
}
