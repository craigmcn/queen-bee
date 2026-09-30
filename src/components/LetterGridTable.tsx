import type { LetterGrid } from "../lib/spellingBee";

// Zero cells show "-" like the NYT hints grid, so the non-empty cells stand out.
function cell(count: number) {
  return count === 0 ? "-" : count;
}

export function LetterGridTable({ grid }: { grid: LetterGrid }) {
  return (
    <div className="table-responsive">
      <table className="table table--sm table--bordered letter-grid">
        <thead>
          <tr>
            <td />
            {grid.lengths.map((length) => (
              <th key={length} scope="col">
                {length}
              </th>
            ))}
            <th scope="col" aria-label="Total">
              &Sigma;
            </th>
          </tr>
        </thead>
        <tbody>
          {grid.rows.map((row) => (
            <tr key={row.letter}>
              <th scope="row">{row.letter.toUpperCase()}</th>
              {row.counts.map((count, i) => (
                <td key={grid.lengths[i]}>{cell(count)}</td>
              ))}
              <td className="letter-grid__total">{row.total}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th scope="row" aria-label="Total">
              &Sigma;
            </th>
            {grid.columnTotals.map((count, i) => (
              <td key={grid.lengths[i]}>{cell(count)}</td>
            ))}
            <td className="letter-grid__total">{grid.total}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
