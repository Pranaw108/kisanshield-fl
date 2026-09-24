import { useRef, useState, type DragEvent, type KeyboardEvent } from "react";

interface Props {
  previewUrl: string | null;
  onSelect: (file: File) => void;
}

/** Click-or-drag image picker. Purely presentational — validation lives in usePrediction. */
export function Dropzone({ previewUrl, onSelect }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const openPicker = () => inputRef.current?.click();
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openPicker();
    }
  };
  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) onSelect(file);
  };
  const onDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(true);
  };
  const onDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload a leaf photo"
      onClick={openPicker}
      onKeyDown={onKeyDown}
      onDragEnter={onDragEnter}
      onDragOver={onDragEnter}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className={`cursor-pointer rounded-xl2 border-2 border-dashed p-10 text-center transition-all
        ${dragOver ? "border-brand dark:border-brand-dark bg-brand/10 scale-[1.01]" : "border-line dark:border-line-dark hover:border-brand dark:hover:border-brand-dark"}
        focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-brand focus-visible:outline-offset-2`}
    >
      {previewUrl ? (
        <img src={previewUrl} alt="Selected leaf preview" className="mx-auto max-h-[360px] rounded-lg" />
      ) : (
        <div>
          <span className="block text-4xl" aria-hidden>
            📷
          </span>
          <p className="mt-2.5 font-semibold">Drop a photo here, or click to choose one</p>
          <p className="mt-1 text-sm text-muted dark:text-muted-dark">JPEG, PNG or WebP · up to 10 MB</p>
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onSelect(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}
