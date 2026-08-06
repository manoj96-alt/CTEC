export function ContentPage({
  title,
  children,
}: {
  title: string;
  children: string;
}) {
  return (
    <section className="max-w-3xl">
      <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-[var(--accent)]">
        Project foundation
      </p>
      <h1 className="text-4xl font-bold tracking-tight">{title}</h1>
      <p className="mt-6 text-lg leading-8 text-[var(--muted)]">{children}</p>
    </section>
  );
}
