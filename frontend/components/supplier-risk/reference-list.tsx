export function ReferenceList({
  title,
  values,
}: {
  title: string;
  values: string[];
}) {
  return (
    <section>
      <h3>{title}</h3>
      {values.length ? (
        <ul className="reference-list">
          {values.map((value) => (
            <li key={value}>
              <code>{value}</code>
            </li>
          ))}
        </ul>
      ) : (
        <p>No permitted references were returned.</p>
      )}
    </section>
  );
}
