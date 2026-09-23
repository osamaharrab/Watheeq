import { Badge } from "./ui";

export function EntityTypeBadge({ type }: { type: string }) {
  if (type === "LegalEntity") return <Badge tone="info">Legal entity</Badge>;
  if (type === "NaturalPerson") return <Badge tone="success">Natural person</Badge>;
  return <Badge>{type}</Badge>;
}
