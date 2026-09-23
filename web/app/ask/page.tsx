import { AskWatheeq } from "@/components/ask/AskWatheeq";
import { isSafeId } from "@/lib/validation";

export default async function AskPage({ searchParams }: { searchParams: Promise<{ entity?: string | string[] }> }) {
  const { entity } = await searchParams;
  // Only a canonical ID travels in the URL; the name is re-confirmed from the backend.
  const contextId = typeof entity === "string" && isSafeId(entity) ? entity : null;
  return <AskWatheeq key={contextId ?? ""} contextId={contextId} />;
}
