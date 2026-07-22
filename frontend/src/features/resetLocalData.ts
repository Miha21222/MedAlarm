export function resetLocalAppData(
  storage: Pick<Storage, "clear"> = localStorage,
  reload: () => void = () => window.location.reload(),
): void {
  storage.clear();
  reload();
}
