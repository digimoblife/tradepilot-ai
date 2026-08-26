import { ModernSessionWorkspace } from "@/features/sessions/modern-session-workspace";

type SessionAnalysisPageProps = {
  params: Promise<{ sessionId: string }>;
};

export default async function SessionAnalysisPage({ params }: SessionAnalysisPageProps) {
  const { sessionId } = await params;
  return <ModernSessionWorkspace sessionId={sessionId} />;
}
