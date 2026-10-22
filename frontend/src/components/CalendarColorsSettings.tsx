import { useMemo, useState } from "react";
import { useAgenda } from "../hooks/useAgenda";
import { useCategories, useSetCategoryColor } from "../hooks/useCategories";
import { useColorRules, useCreateColorRule, useDeleteColorRule, useUpdateColorRule } from "../hooks/useColorRules";
import type { ColorRule } from "../api/types";
import { PALETTE, matchRule, normalize } from "../lib/colors";
import { startOfWeek, toISODate } from "../lib/dates";
import { SwatchPicker } from "./SwatchPicker";
import "./CalendarColorsSettings.css";

const MAX_SUGGESTIONS = 8;

/** Palabra sugerida a partir de un titulo: lo que va antes de ":" o "-". */
function keywordFromTitle(title: string): string {
  return title.split(/[:\-–(]/)[0].trim();
}

function RuleRow({ rule }: { rule: ColorRule }) {
  const update = useUpdateColorRule();
  const remove = useDeleteColorRule();
  const [keyword, setKeyword] = useState(rule.keyword);

  function saveKeyword() {
    const next = keyword.trim();
    if (!next) return setKeyword(rule.keyword);
    if (next !== rule.keyword) update.mutate({ id: rule.id, keyword: next });
  }

  return (
    <li className="color-rule">
      <span className="color-rule__preview" style={{ borderLeftColor: rule.color }}>
        <input
          className="color-rule__keyword"
          value={keyword}
          aria-label="Palabra"
          onChange={(e) => setKeyword(e.target.value)}
          onBlur={saveKeyword}
          onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
        />
      </span>
      <SwatchPicker
        label={`Color para ${rule.keyword}`}
        value={rule.color}
        onChange={(color) => color && update.mutate({ id: rule.id, color })}
      />
      <button
        type="button"
        className="btn btn--ghost color-rule__delete"
        aria-label={`Borrar regla ${rule.keyword}`}
        onClick={() => remove.mutate(rule.id)}
      >
        ✕
      </button>
    </li>
  );
}

export function CalendarColorsSettings() {
  const { data: rules = [] } = useColorRules();
  const create = useCreateColorRule();
  const { data: categories = [] } = useCategories();
  const setCategoryColor = useSetCategoryColor();
  // Titulos de esta semana, para sugerir palabras que aun no tienen color.
  const { data: agenda } = useAgenda(toISODate(startOfWeek(new Date())), 7);

  const [keyword, setKeyword] = useState("");
  const usedColors = new Set(rules.map((r) => r.color));
  const [color, setColor] = useState<string | null>(null);
  const nextColor = color ?? PALETTE.find((c) => !usedColors.has(c.hex))?.hex ?? PALETTE[0].hex;

  const suggestions = useMemo(() => {
    const seen = new Set<string>();
    const result: string[] = [];
    for (const event of agenda?.events ?? []) {
      const word = keywordFromTitle(event.summary);
      const key = normalize(word);
      if (!key || seen.has(key) || matchRule(event.summary, rules)) continue;
      seen.add(key);
      result.push(word);
    }
    return result.slice(0, MAX_SUGGESTIONS);
  }, [agenda, rules]);

  function addRule(e: React.FormEvent) {
    e.preventDefault();
    const word = keyword.trim();
    if (!word) return;
    create.mutate(
      { keyword: word, color: nextColor },
      {
        onSuccess: () => {
          setKeyword("");
          setColor(null);
        },
      },
    );
  }

  const activeCategories = categories.filter((c) => !c.is_archived);

  return (
    <div className="settings-view__card calendar-colors">
      <p>
        <strong>Colores del calendario</strong>
      </p>

      <h3 className="calendar-colors__heading">Eventos de Google</h3>
      <p className="settings-view__hint">
        Si el título de un evento contiene la palabra (sin importar mayúsculas ni acentos), se pinta de ese color.
        Si varias coinciden, gana la primera de la lista.
      </p>

      {rules.length > 0 && (
        <ul className="calendar-colors__rules">
          {rules.map((rule) => (
            <RuleRow key={rule.id} rule={rule} />
          ))}
        </ul>
      )}

      <form className="calendar-colors__add" onSubmit={addRule}>
        <input
          className="calendar-colors__input"
          placeholder="Palabra, p. ej. GYM"
          value={keyword}
          maxLength={60}
          onChange={(e) => setKeyword(e.target.value)}
        />
        <SwatchPicker label="Color de la nueva regla" value={nextColor} onChange={(c) => c && setColor(c)} />
        <button type="submit" className="btn btn--primary" disabled={!keyword.trim() || create.isPending}>
          Añadir
        </button>
      </form>

      {suggestions.length > 0 && (
        <div className="calendar-colors__suggestions">
          <span className="settings-view__hint">Sin color esta semana:</span>
          {suggestions.map((word) => (
            <button key={word} type="button" className="calendar-colors__suggestion" onClick={() => setKeyword(word)}>
              {word}
            </button>
          ))}
        </div>
      )}

      <h3 className="calendar-colors__heading">Tareas por bloque</h3>
      <p className="settings-view__hint">Las tareas planificadas toman el color de su bloque.</p>
      <ul className="calendar-colors__categories">
        {activeCategories.map((category) => (
          <li key={category.id} className="calendar-colors__category">
            <span className="calendar-colors__category-name">{category.name}</span>
            <SwatchPicker
              label={`Color del bloque ${category.name}`}
              allowNone
              value={category.color}
              onChange={(c) => setCategoryColor.mutate({ id: category.id, color: c })}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}
