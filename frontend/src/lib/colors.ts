// Colores del calendario: paleta fija (tonos medios que se leen bien sobre el
// papel claro y el oscuro) y coincidencia de reglas por palabra clave.

import type { ColorRule } from "../api/types";

export const PALETTE: { name: string; hex: string }[] = [
  { name: "Azul", hex: "#4a7fc1" },
  { name: "Índigo", hex: "#6b6fd1" },
  { name: "Morado", hex: "#9466b8" },
  { name: "Rosa", hex: "#c9628b" },
  { name: "Rojo", hex: "#c4553f" },
  { name: "Naranja", hex: "#d4843a" },
  { name: "Ámbar", hex: "#c9a227" },
  { name: "Verde", hex: "#4f9a62" },
  { name: "Turquesa", hex: "#2f9a94" },
  { name: "Petróleo", hex: "#3f7880" },
  { name: "Pizarra", hex: "#6e7f8d" },
];

export function colorName(hex: string): string {
  return PALETTE.find((c) => c.hex === hex.toLowerCase())?.name ?? hex;
}

/** Minusculas y sin acentos: "Estúdio" y "ESTUDIO" coinciden. */
export function normalize(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim();
}

/** Color de la primera regla cuya palabra aparece en el titulo, o null. */
export function matchRule(title: string, rules: ColorRule[]): string | null {
  const normalized = normalize(title);
  return rules.find((rule) => normalized.includes(normalize(rule.keyword)))?.color ?? null;
}
