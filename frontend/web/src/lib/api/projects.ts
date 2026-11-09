import { request } from "./client";
import type {
  ProjectResponse,
  ProjectListResponse,
  UploadResponse,
  ConvertResponse,
  AnalyzeResponse,
  VerifyResponse,
  AIReviewResponse,
  DescribeResponse,
  RunsResponse,
  Run,
} from "@/types/api";
const path = (id: string) => `/api/projects/${encodeURIComponent(id)}`;
const post = { method: "POST" };
export const createProject = (name: string) =>
  request<ProjectResponse>("/api/projects", {
    ...post,
    body: JSON.stringify({ name }),
  });
export const createDemoProject = () =>
  request<ProjectResponse>("/api/projects/demo", post);
export const listProjects = (signal?: AbortSignal) =>
  request<ProjectListResponse>("/api/projects", { signal });
export const getProject = (id: string, signal?: AbortSignal) =>
  request<ProjectResponse>(path(id), { signal });
export const deleteProject = (id: string) =>
  request<null>(path(id), { method: "DELETE" });
export const deleteProjectFile = (id: string, fileId: string) =>
  request<null>(`${path(id)}/files/${encodeURIComponent(fileId)}`, {
    method: "DELETE",
  });
export const uploadProjectFiles = (id: string, files: File[]) => {
  const body = new FormData();
  files.forEach((file) => body.append("files", file));
  return request<UploadResponse>(`${path(id)}/files`, { ...post, body });
};
export const convertProject = (id: string) =>
  request<ConvertResponse>(`${path(id)}/convert`, post);
export const analyzeProject = (id: string) =>
  request<AnalyzeResponse>(`${path(id)}/analyze`, post);
export const verifyProject = (id: string) =>
  request<VerifyResponse>(`${path(id)}/verify`, post);
export const reviewProject = (id: string) =>
  request<AIReviewResponse>(`${path(id)}/ai-review`, post);
export const describeProject = (id: string) =>
  request<DescribeResponse>(`${path(id)}/describe`, post);
export const listRuns = (id: string, signal?: AbortSignal) =>
  request<RunsResponse>(`${path(id)}/runs`, { signal });
export const getRun = (id: string, runId: string) =>
  request<Run>(`${path(id)}/runs/${encodeURIComponent(runId)}`);
export const runFilePath = (id: string, runId: string, name: string) =>
  `${path(id)}/runs/${encodeURIComponent(runId)}/files/${encodeURIComponent(name)}`;
