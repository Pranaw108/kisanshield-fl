/** Purely decorative ambient blobs behind the page content. */
export function BackgroundShapes() {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden" aria-hidden>
      <span className="animate-drift absolute -top-28 -left-24 h-80 w-80 rounded-full bg-brand/35 blur-[60px]" />
      <span className="animate-drift absolute -bottom-24 -right-20 h-64 w-64 rounded-full bg-amber/20 blur-[60px] [animation-duration:22s]" />
      <span className="animate-drift absolute right-[10%] top-[40%] h-44 w-44 rounded-full bg-brand/10 blur-[60px] [animation-duration:26s]" />
    </div>
  );
}
