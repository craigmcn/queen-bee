import type { buildPrefixCounts } from "../lib/spellingBee";

export function PrefixList({
  groups,
}: {
  groups: ReturnType<typeof buildPrefixCounts>;
}) {
  return (
    <ul className="prefix-list">
      {groups.map(({ letter, prefixes }) => (
        <li key={letter}>
          {prefixes.map(({ prefix, count }) => (
            <span key={prefix} className="prefix">
              {prefix.toUpperCase()}-{count}
            </span>
          ))}
        </li>
      ))}
    </ul>
  );
}
