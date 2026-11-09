import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
const backend = path.resolve("../../backend");
const python = path.join(
  backend,
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const args = [path.resolve("scripts/test-api.py")];
const child = existsSync(python)
  ? spawn(python, args, { stdio: "inherit" })
  : spawn("uv", ["run", "--frozen", "python", ...args], {
      cwd: backend,
      stdio: "inherit",
    });
process.on("SIGTERM", () => child.kill());
process.on("SIGINT", () => child.kill());
child.on("exit", (code) => process.exit(code ?? 0));
