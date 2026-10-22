export type TaskStatus = "Pendiente" | "En proceso" | "Terminado";
export type TaskPriority = "Alta" | "Media" | "Baja";
export type SortMode = "priority" | "due_date" | "none" | "manual";

export interface Category {
  id: number;
  name: string;
  slug: string;
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
  name: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  due_date: string | null;
  /** "HH:MM" dentro de due_date; null si la tarea solo tiene dia. */
  due_time: string | null;
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
