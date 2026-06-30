import { getCompare } from "@/lib/data";
import CompareTable from "@/components/CompareTable";
import { PageHead, Empty } from "@/app/value/page";

export const metadata = { title: "Compare" };

export default function ComparePage() {
  const { rows, event } = getCompare();
  return (
    <>
      <PageHead
        title="Model vs the books"
        sub={`The model's fair price for every player and market, side by side with each bookmaker${event ? ` · ${event}` : ""}. Best available book price is highlighted.`}
      />
      {rows.length === 0 ? <Empty msg="No odds loaded yet." /> : <CompareTable rows={rows} />}
    </>
  );
}
