export type TaskStatus = "Pendiente" | "En proceso" | "Terminado";
export type TaskPriority = "Alta" | "Media" | "Baja";
export type SortMode = "priority" | "due_date" | "none" | "manual";

export interface Category {
  id: number;
  name: string;
  slug: string;
  /** "#rrggbb" de sus tareas en el calendario; null = color por defecto. */
  color: string | null;
  is_archived: boolean;
  archived_at: string | null;
  active_project_count: number;
  archived_project_count: number;
}

export interface Project {
  id: number;
  category_id: number;
  name: string;
  description: string | null;
  client: string | null;
  is_archived: boolean;
  archived_at: string | null;
  created_at: string;
  task_count: number;
}

export interface Subtask {
  id: number;
  task_id: number;
  name: string;
  is_checked: boolean;
}

export interface Task {
  id: number;
  project_id: number | null;
  project_name: string | null;
  /** Bloque del proyecto. Solo viene relleno en la agenda (calendario). */
  category_id?: number | null;
  name: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  /** "HH:MM" dentro de due_date; null si la tarea solo tiene dia. */
  due_time: string | null;
  /** Planificacion en el calendario de la app: "YYYY-MM-DDTHH:MM:SS" en hora
   * local, sin zona. null = sin planificar. Nunca se envia a Google. */
  planned_start: string | null;
  planned_minutes: number | null;
  created_at: string;
  is_archived: boolean;
  archived_at: string | null;
  in_today: boolean;
  google_event_id: string | null;
  calendar_sync_warning: string | null;
  subtasks: Subtask[];
}

export interface TodayResponse {
  selected: Task[];
  suggestions: Task[];
}

export type KanbanColumns = Record<TaskStatus, Task[]>;

export interface CalendarStatus {
  connected: boolean;
  needs_reauth: boolean;
  google_account_email: string | null;
}

/** Regla de color: los eventos de Google cuyo titulo contiene `keyword` se
 * pintan con `color` ("#rrggbb"). Gana la primera que coincide. */
export interface ColorRule {
  id: number;
  keyword: string;
  color: string;
}

/** Evento de Google Calendar, de solo lectura. Con `all_day`, start/end son
 * fechas "YYYY-MM-DD" (end exclusivo); si no, ISO 8601 con zona. */
export interface AgendaEvent {
  id: string;
  summary: string;
  start: string;
  end: string | null;
  all_day: boolean;
}

export interface AgendaGoogleStatus {
  connected: boolean;
  needs_reauth: boolean;
  /** Conectado, pero la lectura de eventos fallo. */
  error: boolean;
}

export interface Agenda {
  blocks: Task[];
  deadlines: Task[];
  events: AgendaEvent[];
  google: AgendaGoogleStatus;
}

export interface AssistantScope {
  task_id?: number;
  project_id?: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface Proposal {
  id: string;
  action: string;
  summary: string;
  params: Record<string, unknown>;
}

export interface AssistantChatResponse {
  reply: string;
  proposals: Proposal[];
}
