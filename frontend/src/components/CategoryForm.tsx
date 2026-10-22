import { useState } from "react";
import { ApiError } from "../api/client";
import { useCreateCategory } from "../hooks/useCategories";
import "./CategoryForm.css";

export function CategoryForm() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const createCategory = useCreateCategory();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setError(null);
    createCategory.mutate(
      { name: name.trim() },
      {
        onSuccess: () => {
          setName("");
          setOpen(false);
        },
        onError: (err) => {
          setError(err instanceof ApiError ? err.message : "No se pudo crear el bloque.");
        },
      }
    );
  }

  function handleCancel() {
    setName("");
    setError(null);
    setOpen(false);
  }

  if (!open) {
    return (
      <button className="sidebar__tab sidebar__tab--button" onClick={() => setOpen(true)}>
        + Nuevo bloque
      </button>
    );
  }

  return (
    <form className="category-form" onSubmit={handleSubmit}>
      <input
        autoFocus
        placeholder="Nombre del bloque..."
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      {error && <div className="category-form__error">{error}</div>}
      <div className="category-form__actions">
        <button type="submit" className="btn btn--primary" disabled={!name.trim() || createCategory.isPending}>
          Crear
        </button>
        <button type="button" className="btn btn--ghost" onClick={handleCancel}>
          Cancelar
        </button>
      </div>
    </form>
  );
}
