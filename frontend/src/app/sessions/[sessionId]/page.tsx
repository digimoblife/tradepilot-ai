import { TradeSessionShell } from "@/features/trade-session/trade-session-shell";

interface Props {
  params: Promise<{ sessionId: string }>;
}

export default async function SessionDetailPage({ params }: Props) {
  const { sessionId } = await params;

  return (
    <TradeSessionShell sessionId={sessionId} />
  );
}
