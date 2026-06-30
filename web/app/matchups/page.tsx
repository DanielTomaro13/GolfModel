import { getExtras } from "@/lib/data";
import MatchupsView from "@/components/MatchupsView";
import { PageHead } from "@/app/value/page";

export const metadata = { title: "Matchups" };

export default function MatchupsPage() {
  const extras = getExtras();
  return (
    <>
      <PageHead
        title="Matchups & specials"
        sub={`Head-to-head, 3-balls, round leaders and group markets${extras.event ? ` · ${extras.event}` : ""}, each priced by the simulation. EV is the model's expected value at the bookmaker's price — head-to-heads and 3-balls are the cleanest; leaders and groups carry heavy overround.`}
      />
      <MatchupsView extras={extras} />
    </>
  );
}
