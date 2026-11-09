import { request } from "./client";
import type { ConvertFilesResponse } from "@/types/api";
export function convertFiles(files: File[]) {
  const body = new FormData();
  files.forEach((file) => body.append("files", file));
  return request<ConvertFilesResponse>("/api/convert", {
    method: "POST",
    body,
  });
}
export const batchFilePath = (id: string, name: string) =>
  `/api/convert/${encodeURIComponent(id)}/files/${encodeURIComponent(name)}`;
