import React from "react";
import { HealthDomainInfo } from "../types/HealthDomain";

type Props = {
  domainKey?: string | null;
  domainInfo?: HealthDomainInfo | null;
};

function fallbackTitleCase(s: string) {
  return s
    .split("_")
    .filter(Boolean)
    .map((p) => p.slice(0, 1).toUpperCase() + p.slice(1))
    .join(" ");
}

export function DomainMeta({ domainKey, domainInfo }: Props) {
  if (!domainKey) return null;

  const name = domainInfo?.display_name || fallbackTitleCase(domainKey);
  const description = domainInfo?.description;
  const examples = domainInfo?.example_signals || [];

  return (
    <div className="mt-2">
      <div className="text-xs text-gray-600">
        Domain: <strong>{name}</strong>
      </div>

      {/* Read-only, non-actionable explanation. Hide if we don't have canonical info loaded yet. */}
      {description && (
        <details className="mt-1">
          <summary className="cursor-pointer text-xs text-gray-500">
            What area of health is this?
          </summary>
          <div className="mt-1 text-xs bg-gray-50 p-2 rounded text-gray-700">
            <div>{description}</div>
            {examples.length > 0 && (
              <div className="mt-1 text-gray-600">
                Based on signals like: <strong>{examples.join(", ")}</strong>
              </div>
            )}
          </div>
        </details>
      )}
    </div>
  );
}


