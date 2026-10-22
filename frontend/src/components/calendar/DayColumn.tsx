import { useDroppable } from "@dnd-kit/core";
import type { AgendaEvent } from "../../api/types";
import { formatTime, toISODate } from "../../lib/dates";
import { PlannedBlock } from "./PlannedBlock";
import { SLOT_HEIGHT, SLOT_MINUTES, type PositionedItem } from "./layout";

export interface DropPreview {
  isoDay: string;
  minutes: number;
  duration: number;
}

interface Props {
  day: Date;
  items: PositionedItem[];
  firstHour: number;
  lastHour: number;
  nowMinutes: number | null;
  preview: DropPreview | null;
  selectedTaskId: number | null;
  popoverSide: "left" | "right";
  onSelect: (taskId: number | null) => void;
}

function EventBlock({ event, pos }: { event: AgendaEvent; pos: PositionedItem }) {
  const { start, end } = pos.item;
  return (
    <div
      className="cal-item-slot"
      style={{
        top: pos.top,
        height: pos.height,
        left: `${(pos.lane / pos.lanes) * 100}%`,
        width: `${100 / pos.lanes}%`,
      }}
    >
      <div className={`cal-event ${pos.height < 40 ? "is-compact" : ""}`} title={`${event.summary} · ${formatTime(start)}–${formatTime(end)}`}>
        <span className="cal-event__name">{event.summary}</span>
        {pos.height >= 40 && (
          <span className="cal-event__meta">
            {formatTime(start)}–{formatTime(end)}
          </span>
        )}
      </div>
    </div>
  );
}

export function DayColumn({
  day,
  items,
  firstHour,
  lastHour,
  nowMinutes,
  preview,
  selectedTaskId,
  popoverSide,
  onSelect,
}: Props) {
  const isoDay = toISODate(day);
  const { setNodeRef, isOver } = useDroppable({ id: `day:${isoDay}`, data: { isoDay } });
  const slots = ((lastHour - firstHour) * 60) / SLOT_MINUTES;

  return (
    <div
      ref={setNodeRef}
      className={`cal-day ${isOver ? "is-over" : ""}`}
      style={{ height: slots * SLOT_HEIGHT }}
    >
      {Array.from({ length: slots }, (_, i) => (
        <div key={i} className={`cal-day__slot ${i % 2 === 0 ? "is-hour" : ""}`} style={{ height: SLOT_HEIGHT }} />
      ))}

      {preview && preview.isoDay === isoDay && (
        <div
          className="cal-drop-preview"
          style={{
            top: ((preview.minutes - firstHour * 60) / SLOT_MINUTES) * SLOT_HEIGHT,
            height: (preview.duration / SLOT_MINUTES) * SLOT_HEIGHT,
          }}
        />
      )}

      {items.map((pos) =>
        pos.item.kind === "event" ? (
          <EventBlock key={pos.item.key} event={pos.item.event} pos={pos} />
        ) : (
          <PlannedBlock
            key={pos.item.key}
            task={pos.item.task}
            pos={pos}
            selected={selectedTaskId === pos.item.task.id}
            popoverSide={popoverSide}
            onSelect={onSelect}
          />
        ),
      )}

      {nowMinutes !== null && nowMinutes >= firstHour * 60 && nowMinutes <= lastHour * 60 && (
        <div className="cal-now" style={{ top: ((nowMinutes - firstHour * 60) / SLOT_MINUTES) * SLOT_HEIGHT }} />
      )}
    </div>
  );
}
