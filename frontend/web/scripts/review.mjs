import { spawn } from "node:child_process";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const cwd = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
if (!existsSync(path.join(cwd, ".next/BUILD_ID"))) {
  throw new Error("Build the frontend first with npm run build.");
}
const backend = path.resolve(cwd, "../../backend");
const python = path.join(
  backend,
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const apiArgs = [path.join(cwd, "scripts/review-api.py")];
const api = existsSync(python)
  ? spawn(python, apiArgs, { cwd, stdio: "inherit" })
  : spawn("uv", ["run", "--frozen", "python", ...apiArgs], {
      cwd: backend,
      stdio: "inherit",
    });
const web = spawn(
  process.execPath,
  [
    path.join(cwd, "node_modules/next/dist/bin/next"),
    "start",
    "--hostname",
    "127.0.0.1",
    "--port",
    "3000",
  ],
  {
    cwd,
    stdio: "inherit",
    env: { ...process.env, API_URL: "http://127.0.0.1:8000" },
  },
);
let stopping = false;
mkdirSync(path.join(cwd, "review-runtime"), { recursive: true });
writeFileSync(
  path.join(cwd, "review-runtime", "processes.json"),
  JSON.stringify(
    {
      launcher: process.pid,
      api: api.pid,
      web: web.pid,
      startedAt: new Date().toISOString(),
    },
    null,
    2,
  ),
);
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  api.kill();
  web.kill();
  process.exitCode = code;
}
process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());
for (const child of [api, web]) {
  child.on("error", (error) => {
    console.error(error.message);
    stop(1);
  });
  child.on("exit", (code) => {
    if (!stopping) stop(code ?? 1);
  });
}
console.log("Review website: http://localhost:3000");
console.log(
  "Local review account: review@legacylift.local / LegacyLiftReview1!",
);
