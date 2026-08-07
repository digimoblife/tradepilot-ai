import { RoutePlaceholder } from "@/app/sessions/_components/route-placeholder";
import { CreateSessionNavigation } from "@/features/sessions/create-session-navigation";

export default function NewSessionPage() {
  return (
    <RoutePlaceholder
      title="Buat Sesi Baru"
      description="Masukkan identitas saham dan catatan awal untuk membuat satu sesi perdagangan."
    >
      <CreateSessionNavigation />
    </RoutePlaceholder>
  );
}
