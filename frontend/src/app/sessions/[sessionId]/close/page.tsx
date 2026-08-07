import { CloseActionRoute } from "@/features/sessions/close-action-route";

export default async function ClosePage(props: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await props.params;
  return <CloseActionRoute sessionId={sessionId} />;
}
