import { RouteSessionPlaceholder } from "@/app/sessions/_components/route-session-placeholder";

type SessionDetailPageProps = {
  params: Promise<{ sessionId: string }>;
};

export default async function SessionDetailPage({ params }: SessionDetailPageProps) {
  const { sessionId } = await params;

  return (
    <RouteSessionPlaceholder
      sessionId={sessionId}
      currentHref={`/sessions/${sessionId}`}
      title="Ringkasan Sesi"
      description="Ringkasan dan langkah berikutnya untuk sesi ini akan tersedia pada tahap berikutnya."
      backHref="/sessions"
      backLabel="Kembali ke Sesi"
      successMode="session-detail-header"
    />
  );
}
