// Minimal CSV parser for the demo's controlled sample files.
//
// A full CSV library (quoting, escaping, embedded commas) isn't warranted
// here — the seven demo files are authored by us and never contain commas,
// quotes, or embedded newlines inside a field. If real customer files were
// ever loaded, a proper parser would be required; this is demo-only.

export interface RawCsv {
  columns: string[];
  rows: Record<string, string>[];
}

export function parseCsv(text: string): RawCsv {
  const lines = text
    .trim()
    .split(/\r?\n/)
    .filter((line) => line.length > 0);

  if (lines.length === 0) {
    return { columns: [], rows: [] };
  }

  const columns = lines[0].split(",").map((column) => column.trim());
  const rows = lines.slice(1).map((line) => {
    const cells = line.split(",").map((cell) => cell.trim());
    const row: Record<string, string> = {};
    columns.forEach((column, index) => {
      row[column] = cells[index] ?? "";
    });
    return row;
  });

  return { columns, rows };
}
