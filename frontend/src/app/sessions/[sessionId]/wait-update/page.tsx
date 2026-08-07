import { WaitUpdateActionRoute } from "@/features/sessions/wait-update-action-route";

export default async function WaitUpdatePage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <WaitUpdateActionRoute sessionId={sessionId} />;
}
