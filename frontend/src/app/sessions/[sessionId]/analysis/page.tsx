import { SessionAnalysisView } from "@/features/sessions/session-analysis-view";

type SessionAnalysisPageProps = {
  params: Promise<{ sessionId: string }>;
};

export default async function SessionAnalysisPage({ params }: SessionAnalysisPageProps) {
  const { sessionId } = await params;

  return <SessionAnalysisView sessionId={sessionId} />;
}
