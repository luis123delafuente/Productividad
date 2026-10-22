import { useMemo, type ReactNode } from "react";
import { useCategories } from "../../hooks/useCategories";
import { useColorRules } from "../../hooks/useColorRules";
import { matchRule } from "../../lib/colors";
import { CalendarColorsContext, type CalendarColors } from "./colors";

export function CalendarColorsProvider({ children }: { children: ReactNode }) {
  const { data: rules } = useColorRules();
  const { data: categories } = useCategories();

  const value = useMemo<CalendarColors>(() => {
    const byCategory = new Map(categories?.map((c) => [c.id, c.color]) ?? []);
    return {
      eventColor: (title) => matchRule(title, rules ?? []),
      taskColor: (task) => (task.category_id != null ? byCategory.get(task.category_id) ?? null : null),
    };
  }, [rules, categories]);

  return <CalendarColorsContext.Provider value={value}>{children}</CalendarColorsContext.Provider>;
}
