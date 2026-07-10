import { Pill } from "lucide-react";
import { EmptyState } from "../components/EmptyState";
import { MedicineCard } from "../components/MedicineCard";
import { useAppSettings } from "../contexts/AppSettingsContext";
import { useMedicinesAllQuery } from "../features/medicines/cache";

export function MedicineListPage() {
  const { t } = useAppSettings();
  const { data: medicines = [] } = useMedicinesAllQuery();

  return (
    <section className="page-stack">
      {medicines.length ? (
        <div className="medicine-grid">
          {medicines.map((medicine) => (
            <MedicineCard key={medicine.client_medicine_id} medicine={medicine} t={t} />
          ))}
        </div>
      ) : (
        <EmptyState icon={<Pill />} text={t("noMedicines")} />
      )}
    </section>
  );
}
