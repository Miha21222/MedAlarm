import { resetLocalAppData } from "../src/features/resetLocalData";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

let cleared = false;
let reloaded = false;
resetLocalAppData(
  { clear: () => { cleared = true; } },
  () => { reloaded = true; },
);
assert(cleared, "reset should clear local storage");
assert(reloaded, "reset should reload the app after clearing storage");

console.log("resetLocalData tests passed");
