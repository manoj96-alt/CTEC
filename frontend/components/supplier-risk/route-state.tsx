export function RouteState({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: React.ReactNode;
}) {
  return (
    <section className="panel" role="status">
      <h1>{title}</h1>
      <p>{message}</p>
      {action}
    </section>
  );
}
