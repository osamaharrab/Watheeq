import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { Notice } from "@/components/ui";

export default function OwnershipIndexPage() {
  return (
    <>
      <PageHeader
        title="Ownership"
        subtitle="See who owns a company today, or on a past date."
      />
      <Notice tone="info" title="Choose a company first">
        <p>
          Find the company in Entity Search, then choose “View ownership”. Picking the exact company first keeps
          similarly named companies from being mixed up.
        </p>
        <p className="mt-2">
          <Link href="/" className="font-semibold text-blue-700 hover:underline">
            Go to Entity Search
          </Link>
        </p>
      </Notice>
    </>
  );
}
