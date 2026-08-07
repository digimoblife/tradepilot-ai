import { SessionHistoryView } from "@/features/sessions/session-history-view";

type SessionHistoryPageProps = {
  params: Promise<{ sessionId: string }>;
};

export default async function SessionHistoryPage({ params }: SessionHistoryPageProps) {
  const { sessionId } = await params;
  return <SessionHistoryView sessionId={sessionId} />;
}
