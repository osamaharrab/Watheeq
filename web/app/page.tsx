import { PageHeader } from "@/components/PageHeader";
import { EntitySearch } from "@/components/search/EntitySearch";

export default async function EntitySearchPage({ searchParams }: { searchParams: Promise<{ q?: string | string[] }> }) {
  const { q } = await searchParams;
  const initialQuery = typeof q === "string" ? q : "";
  return (
    <>
      <PageHeader
        title="Find an entity"
        subtitle="Search by company name, person name, or entity ID."
      />
      {/* key resets the search component when navigating between ?q= values */}
      <EntitySearch key={initialQuery} initialQuery={initialQuery} />
    </>
  );
}
