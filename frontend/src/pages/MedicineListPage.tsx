import { ListPlus, Pill } from "lucide-react";
import { EmptyState } from "../components/EmptyState";
import { MedicineCard } from "../components/MedicineCard";
import { useAppSettings } from "../contexts/AppSettingsContext";
import { useMedicinesAllQuery } from "../features/medicines/cache";
import { usePersistentEnumState } from "../hooks/usePersistentEnumState";

const FILTERS = ["active", "all"] as const;

export function MedicineListPage() {
  const { t } = useAppSettings();
  const { data: medicines = [] } = useMedicinesAllQuery();
  const filter = usePersistentEnumState<(typeof FILTERS)[number]>("medalarm.medicines.filter", "active", FILTERS);
  // listLocalMedicines() (backing useMedicinesAllQuery) already excludes
  // soft-deleted tombstones, so this only needs to toggle active vs. inactive.
  const visible = medicines.filter((medicine) => filter.value === "all" || medicine.is_active);

  return (
    <section className="page-stack">
      <div className="filter-card">
        <ListPlus size={20} />
        <div className="segmented grow">
          <button className={filter.value === "active" ? "selected" : ""} onClick={() => filter.setValue("active")}>
            {t("active")}
          </button>
          <button className={filter.value === "all" ? "selected" : ""} onClick={() => filter.setValue("all")}>
            {t("all")}
          </button>
        </div>
      </div>
      {visible.length ? (
        <div className="medicine-grid">
          {visible.map((medicine) => (
            <MedicineCard key={medicine.client_medicine_id} medicine={medicine} t={t} />
          ))}
        </div>
      ) : (
        <EmptyState icon={<Pill />} text={t("noMedicines")} />
      )}
    </section>
  );
}
