import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  DndContext,
  DragOverlay,
  type DragEndEvent,
  type DragMoveEvent,
  type DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import type { Task } from "../api/types";
import { useAgenda, useUpdatePlanning } from "../hooks/useAgenda";
import { DEFAULT_PLANNED_MINUTES } from "../lib/planning";
import {
  addDays,
  formatDayMonth,
  formatDuration,
  formatLongDay,
  parseISODate,
  startOfWeek,
  toISODate,
  toLocalDateTime,
} from "../lib/dates";
import { CalendarColorsProvider } from "../components/calendar/CalendarColorsProvider";
import { colorStyle, useCalendarColors } from "../components/calendar/colors";
import { TimeGrid } from "../components/calendar/TimeGrid";
import { TrayCardContent, UnplannedTray } from "../components/calendar/UnplannedTray";
import type { DropPreview } from "../components/calendar/DayColumn";
import { offsetToMinutes, timedItems, visibleHours } from "../components/calendar/layout";
import "../components/calendar/Calendar.css";
import "./CalendarView.css";

type ViewMode = "semana" | "dia";

function useNow(): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);
  return now;
}

function rangeTitle(mode: ViewMode, days: Date[]): string {
  if (mode === "dia") return formatLongDay(days[0]);
  const first = days[0];
  const last = days[days.length - 1];
  return `${formatDayMonth(first)} – ${formatDayMonth(last)} ${last.getFullYear()}`;
}

function minutesLabel(minutes: number): string {
  return `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

function CalendarScreen() {
  const [params, setParams] = useSearchParams();
  const mode: ViewMode = params.get("vista") === "dia" ? "dia" : "semana";
  const anchor = params.get("fecha") ? parseISODate(params.get("fecha")!) : new Date();
  const anchorIso = toISODate(anchor);

  const days = useMemo(() => {
    const base = parseISODate(anchorIso);
    if (mode === "dia") return [base];
    const monday = startOfWeek(base);
    return Array.from({ length: 7 }, (_, i) => addDays(monday, i));
  }, [anchorIso, mode]);

  const { data: agenda, isLoading } = useAgenda(toISODate(days[0]), days.length);
  const updatePlanning = useUpdatePlanning();
  const now = useNow();

  const items = useMemo(() => (agenda ? timedItems(agenda.events, agenda.blocks) : []), [agenda]);
  const { first: firstHour, last: lastHour } = useMemo(() => visibleHours(items), [items]);

  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [preview, setPreview] = useState<DropPreview | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));
  const onSelect = useCallback((taskId: number | null) => setSelectedTaskId(taskId), []);

  function navigate(next: { vista?: ViewMode; fecha?: Date }) {
    const vista = next.vista ?? mode;
    const fecha = next.fecha ?? anchor;
    setSelectedTaskId(null);
    setParams({ vista, fecha: toISODate(fecha) }, { replace: true });
  }

  const step = mode === "dia" ? 1 : 7;

  // Dia y minuto donde caeria lo que se arrastra: el borde superior de lo
  // arrastrado, relativo a la columna del dia, ajustado a franjas de 30 min.
  function dropTarget(event: DragMoveEvent | DragEndEvent): DropPreview | null {
    const { active, over } = event;
    const translated = active.rect.current.translated;
    const isoDay = over?.data.current?.isoDay as string | undefined;
    if (!over || !translated || !isoDay) return null;
    const task = active.data.current?.task as Task;
    return {
      isoDay,
      minutes: offsetToMinutes(translated.top - over.rect.top, firstHour, lastHour),
      duration: task.planned_minutes ?? DEFAULT_PLANNED_MINUTES,
    };
  }

  function handleDragStart(event: DragStartEvent) {
    setSelectedTaskId(null);
    setActiveTask((event.active.data.current?.task as Task) ?? null);
  }

  function handleDragEnd(event: DragEndEvent) {
    const task = event.active.data.current?.task as Task | undefined;
    const target = dropTarget(event);
    setActiveTask(null);
    setPreview(null);
    if (!task || !event.over) return;

    if (event.over.id === "tray") {
      if (task.planned_start) updatePlanning.mutate({ task, planned_start: null });
      return;
    }
    if (!target) return;
    const start = parseISODate(target.isoDay);
    start.setMinutes(target.minutes);
    const plannedStart = toLocalDateTime(start);
    if (plannedStart !== task.planned_start) updatePlanning.mutate({ task, planned_start: plannedStart });
  }

  const google = agenda?.google;
  const { taskColor } = useCalendarColors();

  return (
    <div className="calendar-view">
      <div className="main__header calendar-view__header">
        <div>
          <h1 className="main__title">Calendario</h1>
          <p className="main__subtitle calendar-view__range">{rangeTitle(mode, days)}</p>
        </div>
        <div className="calendar-view__controls">
          <div className="calendar-view__nav">
            <button type="button" className="btn btn--ghost" onClick={() => navigate({ fecha: addDays(anchor, -step) })} aria-label="Anterior">
              ‹
            </button>
            <button type="button" className="btn btn--ghost" onClick={() => navigate({ fecha: new Date() })}>
              Hoy
            </button>
            <button type="button" className="btn btn--ghost" onClick={() => navigate({ fecha: addDays(anchor, step) })} aria-label="Siguiente">
              ›
            </button>
          </div>
          <div className="calendar-view__modes" role="group" aria-label="Vista">
            <button
              type="button"
              className={`calendar-view__mode ${mode === "semana" ? "is-active" : ""}`}
              aria-pressed={mode === "semana"}
              onClick={() => navigate({ vista: "semana" })}
            >
              Semana
            </button>
            <button
              type="button"
              className={`calendar-view__mode ${mode === "dia" ? "is-active" : ""}`}
              aria-pressed={mode === "dia"}
              onClick={() => navigate({ vista: "dia" })}
            >
              Día
            </button>
          </div>
        </div>
      </div>

      {google && !google.connected && (
        <p className="calendar-view__note">
          Google Calendar no está conectado: solo ves tus tareas. <Link to="/ajustes">Conectar en Ajustes</Link>
        </p>
      )}
      {google?.error && <p className="calendar-view__note">No se pudieron cargar los eventos de Google. Se reintentará al volver a la pantalla.</p>}

      <DndContext
        sensors={sensors}
        onDragStart={handleDragStart}
        onDragMove={(event) => setPreview(dropTarget(event))}
        onDragEnd={handleDragEnd}
        onDragCancel={() => {
          setActiveTask(null);
          setPreview(null);
        }}
      >
        <div className="calendar-view__layout">
          {isLoading || !agenda ? (
            <p className="calendar-view__loading">Cargando calendario...</p>
          ) : (
            <TimeGrid
              days={days}
              agenda={agenda}
              items={items}
              firstHour={firstHour}
              lastHour={lastHour}
              now={now}
              preview={preview}
              selectedTaskId={selectedTaskId}
              onSelect={onSelect}
              onOpenDay={(day) => navigate({ vista: "dia", fecha: day })}
            />
          )}
          <UnplannedTray />
        </div>

        <DragOverlay dropAnimation={null}>
          {activeTask && (
            <div
              className={activeTask.planned_start ? "cal-block cal-block--overlay" : "cal-tray-card cal-tray-card--overlay"}
              style={colorStyle(taskColor(activeTask))}
            >
              {activeTask.planned_start ? (
                <div className="cal-block__body">
                  <span className="cal-block__name">{activeTask.name}</span>
                </div>
              ) : (
                <TrayCardContent task={activeTask} />
              )}
              {preview && (
                <span className="cal-overlay-time">
                  {minutesLabel(preview.minutes)} · {formatDuration(preview.duration)}
                </span>
              )}
            </div>
          )}
        </DragOverlay>
      </DndContext>
    </div>
  );
}

export function CalendarView() {
  return (
    <CalendarColorsProvider>
      <CalendarScreen />
    </CalendarColorsProvider>
  );
}
