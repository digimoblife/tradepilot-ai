import { RoutePlaceholder } from "@/app/sessions/_components/route-placeholder";
import { SessionsListSurface } from "@/features/sessions/sessions-list-surface";

export default function SessionsPage() {
  return (
    <RoutePlaceholder
      title="Sesi Perdagangan"
      description="Daftar sesi aktif dan selesai yang belum diarsipkan."
    >
      <SessionsListSurface />
    </RoutePlaceholder>
  );
}
