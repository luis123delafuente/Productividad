import { Link } from "react-router-dom";
import type { Agenda, Task } from "../../api/types";
import { formatWeekday, isSameDay, toISODate } from "../../lib/dates";
import { DayColumn, type DropPreview } from "./DayColumn";
import { SLOT_HEIGHT, allDayCovers, layoutDay, type GridItem } from "./layout";

interface Props {
  days: Date[];
  agenda: Agenda;
  items: GridItem[];
  firstHour: number;
  lastHour: number;
  now: Date;
  preview: DropPreview | null;
  selectedTaskId: number | null;
  onSelect: (taskId: number | null) => void;
  onOpenDay: (day: Date) => void;
}

function DeadlineMarker({ task }: { task: Task }) {
  const done = task.status === "Terminado";
  const label = (
    <>
      <span className="cal-deadline__flag" aria-hidden>
        ⚑
      </span>
      {task.due_time && <span className="cal-deadline__time">{task.due_time.slice(0, 5)}</span>}
      <span className="cal-deadline__name">{task.name}</span>
    </>
  );
  const title = `Entrega: ${task.name}${task.project_name ? ` (${task.project_name})` : ""}`;
  const className = `cal-deadline ${done ? "is-done" : ""}`;
  return task.project_id ? (
    <Link className={className} to={`/proyecto/${task.project_id}`} title={title}>
      {label}
    </Link>
  ) : (
    <span className={className} title={title}>
      {label}
    </span>
  );
}

export function TimeGrid({
  days,
  agenda,
  items,
  firstHour,
  lastHour,
  now,
  preview,
  selectedTaskId,
  onSelect,
  onOpenDay,
}: Props) {
  const hours = Array.from({ length: lastHour - firstHour }, (_, i) => firstHour + i);
  const columns = `56px repeat(${days.length}, minmax(0, 1fr))`;
  const nowMinutes = now.getHours() * 60 + now.getMinutes();

  return (
    <div className={`cal-grid ${days.length === 1 ? "cal-grid--day" : ""}`}>
      <div className="cal-grid__head" style={{ gridTemplateColumns: columns }}>
        <div />
        {days.map((day) => (
          <button
            key={toISODate(day)}
            type="button"
            className={`cal-grid__day-label ${isSameDay(day, now) ? "is-today" : ""}`}
            onClick={() => onOpenDay(day)}
            title="Ver este día"
          >
            <span className="cal-grid__weekday">{formatWeekday(day)}</span>
            <span className="cal-grid__date">{day.getDate()}</span>
          </button>
        ))}
      </div>

      <div className="cal-grid__allday" style={{ gridTemplateColumns: columns }}>
        <div className="cal-grid__allday-label">Día</div>
        {days.map((day) => {
          const iso = toISODate(day);
          const events = agenda.events.filter((e) => e.all_day && allDayCovers(e, iso));
          const deadlines = agenda.deadlines.filter((t) => t.due_date === iso);
          return (
            <div key={iso} className="cal-grid__allday-cell">
              {deadlines.map((task) => (
                <DeadlineMarker key={task.id} task={task} />
              ))}
              {events.map((event) => (
                <span key={event.id} className="cal-allday-event" title={event.summary}>
                  {event.summary}
                </span>
              ))}
            </div>
          );
        })}
      </div>

      <div className="cal-grid__body" style={{ gridTemplateColumns: columns }}>
        <div className="cal-grid__hours">
          {hours.map((hour) => (
            <div key={hour} className="cal-grid__hour" style={{ height: SLOT_HEIGHT * 2 }}>
              {String(hour).padStart(2, "0")}:00
            </div>
          ))}
        </div>
        {days.map((day, index) => (
          <DayColumn
            key={toISODate(day)}
            day={day}
            items={layoutDay(items, day, firstHour)}
            firstHour={firstHour}
            lastHour={lastHour}
            nowMinutes={isSameDay(day, now) ? nowMinutes : null}
            preview={preview}
            selectedTaskId={selectedTaskId}
            popoverSide={days.length > 1 && index >= days.length - 2 ? "left" : "right"}
            onSelect={onSelect}
          />
        ))}
      </div>
    </div>
  );
}
