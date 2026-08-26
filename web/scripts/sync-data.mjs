import { cpSync, existsSync, mkdirSync, rmSync } from "fs";
import path from "path";

const src = path.resolve(process.cwd(), "..", "data");
const dst = path.resolve(process.cwd(), "public", "data");
if (existsSync(src)) {
  rmSync(dst, { recursive: true, force: true });
  mkdirSync(dst, { recursive: true });
  cpSync(src, dst, { recursive: true });
  console.log("synced data ->", dst);
} else {
  console.warn("no ../data directory found; skipping sync");
}
