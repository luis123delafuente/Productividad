import { useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { agendaApi } from "../api/agenda";
import { tasksApi } from "../api/tasks";
import type { Agenda, Task } from "../api/types";
import { addDays, parseDateTime, parseISODate } from "../lib/dates";
import { invalidateTaskViews } from "./useTasks";

export const DEFAULT_PLANNED_MINUTES = 60;

export function useAgenda(start: string, days: number) {
  return useQuery({
    queryKey: ["agenda", start, days],
    queryFn: () => agendaApi.get(start, days),
    // Cada carga consulta Google: no repetirla en cada cambio de foco.
    staleTime: 60_000,
  });
}

export function useUnplanned(projectId?: number) {
  return useQuery({
    queryKey: ["agenda-unplanned", projectId ?? "all"],
    queryFn: () => agendaApi.unplanned(projectId),
  });
}

interface PlanningVars {
  task: Task;
  /** null = quitar del calendario; omitido = no tocar. */
  planned_start?: string | null;
  planned_minutes?: number;
}

function applyPlanning(task: Task, vars: PlanningVars): Task {
  const plannedStart = vars.planned_start !== undefined ? vars.planned_start : task.planned_start;
  const plannedMinutes = plannedStart
    ? vars.planned_minutes ?? task.planned_minutes ?? DEFAULT_PLANNED_MINUTES
    : null;
  return { ...task, planned_start: plannedStart, planned_minutes: plannedMinutes };
}

function inRange(task: Task, start: string, days: number): boolean {
  if (!task.planned_start) return false;
  const at = parseDateTime(task.planned_start);
  const from = parseISODate(start);
  return at >= from && at < addDays(from, days);
}

export function useUpdatePlanning() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: ({ task, planned_start, planned_minutes }: PlanningVars) =>
      tasksApi.updatePlanning(task.id, {
        ...(planned_start !== undefined ? { planned_start } : {}),
        ...(planned_minutes !== undefined ? { planned_minutes } : {}),
      }),
    onMutate: async (vars) => {
      await qc.cancelQueries({ queryKey: ["agenda"] });
      await qc.cancelQueries({ queryKey: ["agenda-unplanned"] });
      const snapshot: [QueryKey, unknown][] = [
        ...qc.getQueriesData({ queryKey: ["agenda"] }),
        ...qc.getQueriesData({ queryKey: ["agenda-unplanned"] }),
      ];
      const updated = applyPlanning(vars.task, vars);

      for (const [key, data] of qc.getQueriesData<Agenda>({ queryKey: ["agenda"] })) {
        if (!data) continue;
        const [, start, days] = key as [string, string, number];
        const blocks = data.blocks.filter((t) => t.id !== updated.id);
        if (inRange(updated, start, days)) blocks.push(updated);
        blocks.sort((a, b) => (a.planned_start ?? "").localeCompare(b.planned_start ?? ""));
        qc.setQueryData<Agenda>(key, { ...data, blocks });
      }

      for (const [key, data] of qc.getQueriesData<Task[]>({ queryKey: ["agenda-unplanned"] })) {
        if (!data) continue;
        const scope = key[1];
        const rest = data.filter((t) => t.id !== updated.id);
        const belongs = scope === "all" || scope === updated.project_id;
        qc.setQueryData<Task[]>(key, updated.planned_start || !belongs ? rest : [updated, ...rest]);
      }

      return { snapshot };
    },
    onError: (_err, _vars, context) => {
      context?.snapshot.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSettled: () => invalidateTaskViews(qc),
  });
}
