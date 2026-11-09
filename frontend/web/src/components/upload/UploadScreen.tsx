"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowUpRight,
  Plus,
  Sparkles,
  Upload,
  FolderPlus,
  FileCode2,
  GitBranch,
  ShieldCheck,
} from "lucide-react";
import { useProject } from "@/hooks/useProject";
import { useSavedProjects } from "@/hooks/useSavedProjects";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { ProgressStatus } from "@/components/layout/ProgressStatus";
import { OpenProject } from "./OpenProject";
import { ReadingGuide } from "@/components/guide/ReadingGuide";
import { SavedProjectList } from "./SavedProjectList";
export function UploadScreen() {
  const params = useSearchParams(),
    router = useRouter();
  const p = useProject(params.get("project") ?? undefined),
    saved = useSavedProjects();
  const [name, setName] = useState("");
  const disabled = !p.ready || Boolean(p.busy) || Boolean(p.loadingId);
  useEffect(() => {
    if (p.project && !p.loadingId && !params.get("project"))
      router.replace(`/upload?project=${encodeURIComponent(p.project.id)}`, {
        scroll: false,
      });
  }, [p.project, p.loadingId, params, router]);
  function showProject(id: string | undefined) {
    if (id && window.location.pathname.replace(/\/$/, "").endsWith("/upload"))
      router.replace(`/upload?project=${encodeURIComponent(id)}`, {
        scroll: false,
      });
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    showProject(await p.create(name));
  }
  const edited = p.results.some(
    (file) => file.python !== p.originalPython[file.python_name],
  );
  const allowMutation = () =>
    !edited ||
    window.confirm(
      "Changing source files resets generated results and local Python edits. Download your edits first. Continue?",
    );
  return (
    <div className={`upload-surface ${p.project ? "has-project" : ""}`}>
      <PageHeader
        title="A new chapter for your code."
        description="Bring your COBOL together. We’ll help you take it forward."
        actions={
          <>
            <ReadingGuide />
            <Link className="text-link" href="/batch">
              Just a few files? Try batch{" "}
              <ArrowUpRight size={16} aria-hidden="true" />
            </Link>
          </>
        }
      />
      <div className="upload-grid">
        <div className="upload-main">
          <Card
            title="Create a project"
            eyebrow={p.project ? undefined : "Start here"}
            className={`create-card ${p.project ? "compact-create" : ""}`}
            actions={
              <span className="decor-icon">
                <FolderPlus size={23} aria-hidden="true" />
              </span>
            }
          >
            <p className="muted">
              A home for your programs, copybooks, and the data that connects
              them.
            </p>
            <form className="create-form" onSubmit={submit}>
              <div className="field">
                <label htmlFor="project-name">Project name</label>
                <input
                  id="project-name"
                  name="project-name"
                  autoComplete="off"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Customer banking system"
                  maxLength={100}
                  disabled={Boolean(p.busy)}
                />
              </div>
              <Button
                variant="primary"
                type="submit"
                disabled={disabled}
                isPending={p.busy === "creating"}
              >
                <Plus size={18} aria-hidden="true" />
                {p.busy === "creating" ? "Creating…" : "Create project"}
              </Button>
            </form>
            {!p.ready && (
              <p className="hint">
                Connect the API to create a project or load the demo.
              </p>
            )}
          </Card>
          {p.project ? (
            <OpenProject
              key={p.project.id}
              project={p.project}
              disabled={disabled}
              uploading={p.busy === "uploading"}
              onUpload={(files) => {
                if (allowMutation()) void p.upload(files);
              }}
              onRemove={(id) => {
                if (allowMutation()) void p.removeFile(id);
              }}
            />
          ) : (
            <div className="upload-placeholder">
              <span className="upload-cloud">
                <Upload size={29} aria-hidden="true" />
              </span>
              <h2>A place for your source.</h2>
              <p>Create a project above, then add your files here.</p>
              <div className="file-type-pills">
                <span>.cbl</span>
                <span>.cob</span>
                <span>.cpy</span>
                <span>.dat</span>
              </div>
            </div>
          )}
          <SavedProjectList
            {...saved}
            busy={disabled}
            onOpen={saved.open}
            onRemove={saved.remove}
            onClearAll={saved.clearAll}
            onRetry={saved.refresh}
          />
        </div>
        <div className="upload-aside">
          <ProgressStatus />
          <section id="demo" className="demo-card">
            <div className="demo-heading">
              <Sparkles size={20} aria-hidden="true" />
              <span>TAKE IT FOR A SPIN</span>
            </div>
            <h2>
              Meet your first
              <br />
              modernization project.
            </h2>
            <p>
              Explore a working COBOL banking system. Source files, copybooks,
              and test data — all ready to go.
            </p>
            <div className="demo-file-stack" aria-hidden="true">
              <div>
                <FileCode2 size={17} /> BANKMAIN.cbl <span>COBOL</span>
              </div>
              <div>
                <FileCode2 size={17} /> INTCALC.cbl <span>COBOL</span>
              </div>
              <div>
                <GitBranch size={17} /> ACCTDEF.cpy <span>COPYBOOK</span>
              </div>
            </div>
            <Button
              onClick={async () => showProject(await p.loadDemo())}
              disabled={disabled}
              isPending={p.busy === "demo"}
            >
              {p.busy === "demo" ? "Loading demo…" : "Load demo project"}
              <ArrowUpRight size={17} aria-hidden="true" />
            </Button>
            <p className="demo-caption">
              Creates a sample project in your account.
            </p>
          </section>
          <div className="trust-note">
            <ShieldCheck size={21} aria-hidden="true" />
            <p>
              Your source is preserved.
              <br />
              <span>Every conversion is a reviewable draft.</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
