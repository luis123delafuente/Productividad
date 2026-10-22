// Geometria del calendario: rango horario visible y reparto en carriles de
// los elementos que se solapan dentro de un dia.

import type { AgendaEvent, Task } from "../../api/types";
import { addDays, addMinutes, minutesSinceMidnight, parseDateTime } from "../../lib/dates";
import { DEFAULT_PLANNED_MINUTES } from "../../lib/planning";

export const SLOT_MINUTES = 30;
export const SLOT_HEIGHT = 24; // px por franja de 30 min
export const DEFAULT_FIRST_HOUR = 7;
export const DEFAULT_LAST_HOUR = 22;

export type GridItem =
  | { kind: "event"; key: string; start: Date; end: Date; event: AgendaEvent }
  | { kind: "block"; key: string; start: Date; end: Date; task: Task };

export interface PositionedItem {
  item: GridItem;
  top: number;
  height: number;
  lane: number;
  lanes: number;
}

export function blockInterval(task: Task): { start: Date; end: Date } {
  const start = parseDateTime(task.planned_start!);
  return { start, end: addMinutes(start, task.planned_minutes ?? DEFAULT_PLANNED_MINUTES) };
}

export function timedItems(events: AgendaEvent[], blocks: Task[]): GridItem[] {
  const items: GridItem[] = [];
  for (const event of events) {
    if (event.all_day) continue;
    const start = parseDateTime(event.start);
    const end = event.end ? parseDateTime(event.end) : addMinutes(start, 30);
    items.push({ kind: "event", key: `event:${event.id}`, start, end, event });
  }
  for (const task of blocks) {
    if (!task.planned_start) continue;
    items.push({ kind: "block", key: `block:${task.id}`, task, ...blockInterval(task) });
  }
  return items;
}

/** Rango de horas visible: 7-22 por defecto, ampliado si algo cae fuera. */
export function visibleHours(items: GridItem[]): { first: number; last: number } {
  let first = DEFAULT_FIRST_HOUR;
  let last = DEFAULT_LAST_HOUR;
  for (const { start, end } of items) {
    first = Math.min(first, start.getHours());
    const endMinutes = end.getDate() !== start.getDate() ? 24 * 60 : minutesSinceMidnight(end);
    last = Math.max(last, Math.ceil(endMinutes / 60));
  }
  return { first, last: Math.min(last, 24) };
}

/** Elementos de un dia (recortados a ese dia), con posicion y carril. */
export function layoutDay(items: GridItem[], day: Date, firstHour: number): PositionedItem[] {
  const dayStart = new Date(day);
  dayStart.setHours(0, 0, 0, 0);
  const dayEnd = addDays(dayStart, 1);

  const clipped = items
    .filter((it) => it.start < dayEnd && it.end > dayStart)
    .map((it) => ({
      item: it,
      start: it.start < dayStart ? dayStart : it.start,
      end: it.end > dayEnd ? dayEnd : it.end,
    }))
    .sort((a, b) => a.start.getTime() - b.start.getTime() || b.end.getTime() - a.end.getTime());

  const positioned: PositionedItem[] = [];
  // Grupos de elementos que se solapan en cadena: todos comparten el numero
  // de carriles del grupo, para que los anchos cuadren.
  let group: { pos: PositionedItem; end: Date }[] = [];
  let groupEnd = 0;

  const flush = () => {
    const lanes = Math.max(1, ...group.map((g) => g.pos.lane + 1));
    group.forEach((g) => (g.pos.lanes = lanes));
    group = [];
  };

  for (const { item, start, end } of clipped) {
    if (group.length && start.getTime() >= groupEnd) flush();

    const laneEnds: number[] = [];
    group.forEach((g) => (laneEnds[g.pos.lane] = Math.max(laneEnds[g.pos.lane] ?? 0, g.end.getTime())));
    let lane = laneEnds.findIndex((laneEnd) => laneEnd !== undefined && laneEnd <= start.getTime());
    if (lane === -1) lane = laneEnds.length;

    const startMin = (start.getTime() - dayStart.getTime()) / 60_000;
    const endMin = (end.getTime() - dayStart.getTime()) / 60_000;
    const pos: PositionedItem = {
      item,
      top: ((startMin - firstHour * 60) / SLOT_MINUTES) * SLOT_HEIGHT,
      height: Math.max(((endMin - startMin) / SLOT_MINUTES) * SLOT_HEIGHT, SLOT_HEIGHT * 0.75),
      lane,
      lanes: 1,
    };
    group.push({ pos, end });
    groupEnd = Math.max(groupEnd, end.getTime());
    positioned.push(pos);
  }
  if (group.length) flush();
  return positioned;
}

/** Minuto del dia (ajustado a franjas de 30 min) para un desplazamiento en px
 * dentro de la columna de un dia. */
export function offsetToMinutes(offsetPx: number, firstHour: number, lastHour: number): number {
  const slot = Math.round(offsetPx / SLOT_HEIGHT);
  const minutes = firstHour * 60 + slot * SLOT_MINUTES;
  return Math.min(Math.max(minutes, firstHour * 60), lastHour * 60 - SLOT_MINUTES);
}

/** Dias (YYYY-MM-DD) que cubre un evento de todo el dia (end exclusivo). */
export function allDayCovers(event: AgendaEvent, isoDay: string): boolean {
  const end = event.end ?? event.start;
  return event.start <= isoDay && (isoDay < end || event.start === end);
}
