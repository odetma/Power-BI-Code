// Reload the report open in Power BI Desktop, including reports opened from <name>.Report\definition.pbir.
//
// The official CLI (`powerbi-desktop reload`) refuses that case in its own client-side check: it only accepts a
// .pbip or a .Report folder as Desktop's current file. Desktop's bridge method (file.reload/v1) takes no path and
// reloads whatever is open, so this script calls it directly through the package's own library.
//
// Usage: node pbir-reload.mjs <pid> [--model] [--allow-unsaved]
//   <pid>    Desktop process id, from `powerbi-desktop status`
//   --model  also reload the semantic model definition
// Prints JSON; exits 1 on failure.
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const PACKAGE = path.join("@microsoft", "powerbi-desktop-bridge-cli", "dist", "index.js");

function findLibrary() {
  const roots = [path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../.runtime/node/node_modules")];
  if (process.env.APPDATA) roots.push(path.join(process.env.APPDATA, "npm/node_modules"));
  roots.push(path.join(path.dirname(process.execPath), "node_modules"));
  for (const root of roots) {
    const candidate = path.join(root, PACKAGE);
    if (fs.existsSync(candidate)) return candidate;
  }
  throw new Error("@microsoft/powerbi-desktop-bridge-cli is not installed. Run scripts/setup.ps1.");
}

const pid = process.argv[2];
if (!pid || !/^\d+$/.test(pid)) {
  console.error("usage: node pbir-reload.mjs <pid> [--model] [--allow-unsaved]");
  process.exit(2);
}

const { openSession, METHODS, isDesktopBridgeError } = await import(pathToFileURL(findLibrary()).href);
let session;
try {
  session = await openSession({ pid, waitMs: 60_000 });
  const state = await session.getApplicationState();
  if (state.hasUnsavedChanges !== false && !process.argv.includes("--allow-unsaved")) {
    throw new Error("Desktop has unsaved or unknown state. Resolve manually, or use --allow-unsaved only after user authorization.");
  }
  const result = await session.connection.client.sendBridgeMethod(METHODS.reload, {
    reloadModelDefinition: process.argv.includes("--model"),
  });
  console.log(JSON.stringify({ pid, currentFilePath: state.currentFilePath, result }, null, 2));
  if (!result?.success) process.exit(1);
} catch (error) {
  const payload = isDesktopBridgeError(error)
    ? { code: error.code, details: error.details, message: error.message }
    : { message: String(error?.message ?? error) };
  console.error(JSON.stringify(payload));
  process.exit(1);
} finally {
  session?.dispose();
}
