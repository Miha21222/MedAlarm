import { QueryClient, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import type { Medicine } from "../../types";
import { bootstrapMedicineSync, listLocalMedicines } from "./localMedicineRepository";

export const MEDICINES_ALL_QUERY_KEY = ["medicines", "all"] as const;
export const MEDICINES_SYNC_QUERY_KEY = ["medicines", "sync"] as const;

export function useMedicinesAllQuery(enabled = true) {
  const queryClient = useQueryClient();
  const medicinesQuery = useQuery({
    queryKey: MEDICINES_ALL_QUERY_KEY,
    queryFn: () => listLocalMedicines(),
    enabled,
  });
  const syncQuery = useQuery({
    queryKey: MEDICINES_SYNC_QUERY_KEY,
    queryFn: bootstrapMedicineSync,
    enabled,
    staleTime: 0,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (syncQuery.data) {
      queryClient.setQueryData<Medicine[]>(MEDICINES_ALL_QUERY_KEY, syncQuery.data);
    }
  }, [queryClient, syncQuery.data]);

  return {
    ...medicinesQuery,
    syncPending: syncQuery.isPending,
    syncError: syncQuery.error,
  };
}

export function updateMedicineInCache(queryClient: QueryClient, medicine: Medicine) {
  queryClient.setQueryData<Medicine[]>(MEDICINES_ALL_QUERY_KEY, (current) => {
    if (!current || current.length === 0) return [medicine];
    const idx = current.findIndex((item) => item.client_medicine_id === medicine.client_medicine_id);
    if (idx === -1) return [medicine, ...current];
    const next = [...current];
    next[idx] = medicine;
    return next;
  });
}

export function removeMedicineFromCache(queryClient: QueryClient, clientMedicineId: string) {
  queryClient.setQueryData<Medicine[]>(MEDICINES_ALL_QUERY_KEY, (current) =>
    current ? current.filter((medicine) => medicine.client_medicine_id !== clientMedicineId) : current,
  );
}
