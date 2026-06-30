import { getPlayers } from "@/lib/data";
import PlayersTable from "@/components/PlayersTable";
import { PageHead, Empty } from "@/app/value/page";

export const metadata = { title: "Players" };

export default function PlayersPage() {
  const { players, event } = getPlayers();
  return (
    <>
      <PageHead
        title="Players"
        sub={`Every player's stroke rating and simulated profile${event ? ` · ${event}` : ""}. Tap a row for round-by-round scoring and finish distribution.`}
      />
      {players.length === 0 ? <Empty msg="No field loaded." /> : <PlayersTable players={players} />}
    </>
  );
}
