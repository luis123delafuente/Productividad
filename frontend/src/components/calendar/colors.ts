import { createContext, useContext, type CSSProperties } from "react";
import type { Task } from "../../api/types";

export interface CalendarColors {
  /** Color de un evento de Google segun las reglas por palabra, o null. */
  eventColor: (title: string) => string | null;
  /** Color del bloque (categoria) de una tarea, o null. */
  taskColor: (task: Task) => string | null;
}

export const CalendarColorsContext = createContext<CalendarColors>({
  eventColor: () => null,
  taskColor: () => null,
});

export function useCalendarColors() {
  return useContext(CalendarColorsContext);
}

/** Estilo que expone el color al CSS como `--cal-color` (o nada si no hay). */
export function colorStyle(color: string | null): CSSProperties | undefined {
  return color ? ({ "--cal-color": color } as CSSProperties) : undefined;
}
