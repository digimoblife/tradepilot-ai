import { ModernSessionWorkspace } from "@/features/sessions/modern-session-workspace";

type SessionDetailPageProps = {
  params: Promise<{ sessionId: string }>;
};

export default async function SessionDetailPage({ params }: SessionDetailPageProps) {
  const { sessionId } = await params;
  return <ModernSessionWorkspace sessionId={sessionId} />;
}
