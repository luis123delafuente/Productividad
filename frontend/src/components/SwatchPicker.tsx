import { PALETTE } from "../lib/colors";
import "./SwatchPicker.css";

interface Props {
  value: string | null;
  onChange: (color: string | null) => void;
  /** Muestra una opcion "sin color" (vuelve al color por defecto). */
  allowNone?: boolean;
  label: string;
}

export function SwatchPicker({ value, onChange, allowNone = false, label }: Props) {
  return (
    <div className="swatch-picker" role="radiogroup" aria-label={label}>
      {allowNone && (
        <button
          type="button"
          role="radio"
          aria-checked={value === null}
          className={`swatch swatch--none ${value === null ? "is-selected" : ""}`}
          title="Color por defecto"
          onClick={() => onChange(null)}
        />
      )}
      {PALETTE.map((color) => (
        <button
          key={color.hex}
          type="button"
          role="radio"
          aria-checked={value === color.hex}
          aria-label={color.name}
          title={color.name}
          className={`swatch ${value === color.hex ? "is-selected" : ""}`}
          style={{ background: color.hex }}
          onClick={() => onChange(color.hex)}
        />
      ))}
    </div>
  );
}
