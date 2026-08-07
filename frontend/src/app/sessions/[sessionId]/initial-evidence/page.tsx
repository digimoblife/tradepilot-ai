import { InitialEvidenceActionRoute } from "@/features/sessions/initial-evidence-action-route";

export default async function InitialEvidencePage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = await params;
  return <InitialEvidenceActionRoute sessionId={sessionId} />;
}
