import { PositionUpdateActionRoute } from "@/features/sessions/position-update-action-route";

export default async function PositionUpdatePage(props: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await props.params;
  return <PositionUpdateActionRoute sessionId={sessionId} />;
}
