import { useEffect, useMemo, useState } from 'react'
import {
  apiConfigured,
  checkBackend,
  convertFiles,
  convertProject,
  createProject,
  uploadProjectFiles,
} from './api'
import './App.css'

const sampleCobol = `IDENTIFICATION DIVISION.
PROGRAM-ID. HELLO-TEAM.
DATA DIVISION.
WORKING-STORAGE SECTION.
01 WS-NAME PIC X(20) VALUE "LegacyLift".
01 WS-COUNT PIC 9(3) VALUE 1.
PROCEDURE DIVISION.
DISPLAY "Hello, " WS-NAME.
ADD 1 TO WS-COUNT.
DISPLAY "Demo count: " WS-COUNT.
STOP RUN.`

function programFilesFromProject(project) {
  if (!project?.files?.length) return []
  return project.files.filter((file) => file.kind === 'program')
}

export default function App() {
  const [files, setFiles] = useState([])
  const [sourceText, setSourceText] = useState('')
  const [selectedFile, setSelectedFile] = useState(0)
  const [results, setResults] = useState([])
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [isConverting, setIsConverting] = useState(false)
  const [viewMode, setViewMode] = useState('split')
  const [projectName, setProjectName] = useState('')
  const [project, setProject] = useState(null)
  const [backendReady, setBackendReady] = useState(false)
  const [backendChecked, setBackendChecked] = useState(false)

  const projectPrograms = useMemo(() => programFilesFromProject(project), [project])
  const canConvert = backendReady && (files.length > 0 || projectPrograms.length > 0) && !isConverting

  useEffect(() => {
    let cancelled = false
    async function probe() {
      if (!apiConfigured) {
        if (!cancelled) {
          setBackendReady(false)
          setBackendChecked(true)
        }
        return
      }
      const ok = await checkBackend()
      if (!cancelled) {
        setBackendReady(ok)
        setBackendChecked(true)
        if (!ok) {
          setStatus(
            'Backend not reachable on port 8000. Start it from backend/, then refresh this page.'
          )
        } else {
          setStatus('Connected to LegacyLift API. Choose COBOL files or a project, then Convert.')
        }
      }
    }
    probe()
    return () => {
      cancelled = true
    }
  }, [])

  async function showFile(file, index) {
    setSelectedFile(index)
    try {
      setSourceText(await file.text())
    } catch {
      setSourceText('Could not read this file.')
    }
  }

  function showProjectProgram(program, index) {
    setSelectedFile(index)
    setSourceText(program.content || '')
  }

  function rejectFiles(message) {
    setFiles([])
    setSourceText('')
    setSelectedFile(0)
    setResults([])
    setError(message)
  }

  function chooseFiles(event) {
    const chosen = Array.from(event.target.files || [])
    event.target.value = ''
    if (!chosen.length) return

    if (chosen.length > 5 || chosen.some((file) => file.size > 100_000)) {
      rejectFiles('Choose up to 5 files, each up to 100 KB.')
      return
    }
    if (chosen.some((file) => !/\.(cbl|cob)$/i.test(file.name))) {
      rejectFiles('Choose only .cbl or .cob files.')
      return
    }

    setFiles(chosen)
    setResults([])
    setError('')
    setStatus(`${chosen.length} file(s) ready for batch conversion via /api/convert.`)
    showFile(chosen[0], 0)
  }

  function loadSample() {
    const sample = new File([sampleCobol], 'hello_team.cbl', { type: 'text/plain' })
    setFiles([sample])
    setResults([])
    setError('')
    setStatus('Sample loaded. Click Convert files to run the Python backend.')
    showFile(sample, 0)
  }

  async function handleConvert() {
    if (!backendReady) {
      setError('Backend is offline. Start the FastAPI server, then try again.')
      return
    }

    setIsConverting(true)
    setError('')
    try {
      // Prefer explicit file-picker batch when the user selected files.
      // Otherwise convert programs already uploaded to the open project.
      if (files.length > 0) {
        const converted = await convertFiles(files)
        setResults(converted)
        setStatus(`Converted ${converted.length} file(s) through /api/convert.`)
        if (selectedFile >= converted.length) setSelectedFile(0)
      } else if (project && projectPrograms.length > 0) {
        const conversion = await convertProject(project.id)
        setResults(conversion.files)
        setStatus(
          `Converted project "${project.name}" (${conversion.files.length} program(s), status: ${conversion.status}).`
        )
        // Align source panel with project programs so tabs match result indices.
        const asFiles = projectPrograms.map(
          (program) => new File([program.content], program.name, { type: 'text/plain' })
        )
        setFiles(asFiles)
        setSelectedFile(0)
        setSourceText(projectPrograms[0].content || '')
      } else {
        setError('Choose COBOL files or upload programs to a project first.')
      }
    } catch (cause) {
      setResults([])
      setError(cause.message)
    } finally {
      setIsConverting(false)
    }
  }

  async function handleCreateProject() {
    const name = projectName.trim()
    if (!name) {
      setError('Enter a project name.')
      return
    }
    if (!backendReady) {
      setError('Backend is offline. Start the FastAPI server, then try again.')
      return
    }
    setError('')
    try {
      const created = await createProject(name)
      setProject(created)
      setStatus(`Project "${created.name}" created. Upload .cbl/.cob files, then Convert.`)
    } catch (cause) {
      setProject(null)
      setError(cause.message)
    }
  }

  async function handleUpload(event) {
    const chosen = Array.from(event.target.files || [])
    event.target.value = ''
    if (!project) {
      setError('Create a project first.')
      return
    }
    if (!chosen.length) return
    if (!backendReady) {
      setError('Backend is offline. Start the FastAPI server, then try again.')
      return
    }
    setError('')
    try {
      const uploaded = await uploadProjectFiles(project.id, chosen)
      const next = {
        ...project,
        files: project.files.concat(uploaded.files),
      }
      setProject(next)
      const programs = programFilesFromProject(next)
      setStatus(
        `Uploaded ${uploaded.files.length} file(s). ${programs.length} program(s) ready to convert.`
      )
      if (programs.length && !files.length) {
        setSourceText(programs[0].content || '')
        setSelectedFile(0)
      }
    } catch (cause) {
      setError(cause.message)
    }
  }

  function downloadPython(result) {
    const file = new Blob([result.python], { type: 'text/x-python;charset=utf-8' })
    const url = URL.createObjectURL(file)
    const link = document.createElement('a')
    link.href = url
    link.download = result.python_name
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const currentResult = results[selectedFile]
  const sourceTabs = files.length
    ? files.map((file, index) => ({
        key: `${file.name}-${index}`,
        label: file.name,
        onSelect: () => showFile(file, index),
      }))
    : projectPrograms.map((program, index) => ({
        key: program.id || `${program.name}-${index}`,
        label: program.name,
        onSelect: () => showProjectProgram(program, index),
      }))

  return (
    <div className="page">
      <header className="site-header">
        <span className="logo">L</span>
        <div>
          <strong>LegacyLift</strong>
          <span>COBOL to Python demo</span>
        </div>
        {backendChecked && (
          <span className={backendReady ? 'api-badge ok' : 'api-badge down'} role="status">
            {backendReady ? 'API connected' : 'API offline'}
          </span>
        )}
      </header>

      <main className="workspace">
        <div className="intro">
          <p className="eyebrow">BACKEND-LINKED DEMO</p>
          <h1>Turn COBOL files into Python drafts.</h1>
          <p>
            Select files for a batch convert, or create a project, upload programs, and convert
            through the FastAPI COBOL translator.
          </p>
        </div>

        {!apiConfigured && (
          <p className="message" role="status">
            The frontend is ready. Set VITE_API_URL to your backend origin to enable conversion on
            this host.
          </p>
        )}
        {status && !error && (
          <p className="message" role="status">
            {status}
          </p>
        )}
        {error && (
          <p className="message error" role="alert">
            {error}
          </p>
        )}

        <div className="actions project-row">
          <input
            value={projectName}
            onChange={(event) => setProjectName(event.target.value)}
            placeholder="Project name"
          />
          <button
            className="button dark"
            type="button"
            onClick={handleCreateProject}
            disabled={!backendReady}
          >
            Create project
          </button>
        </div>

        {project && (
          <div className="project-row">
            <p className="file-limit">
              Project: {project.name} ({projectPrograms.length} program
              {projectPrograms.length === 1 ? '' : 's'}
              {project.files.length !== projectPrograms.length
                ? `, ${project.files.length - projectPrograms.length} other`
                : ''}
              )
            </p>
            <label className="button secondary" htmlFor="project-files">
              Upload project files
              <input
                id="project-files"
                className="file-input"
                type="file"
                accept=".cbl,.cob,.cpy,.dat"
                multiple
                onChange={handleUpload}
              />
            </label>
            <ul>
              {project.files.map((file) => (
                <li key={file.id}>
                  {file.name} <span className="file-kind">({file.kind})</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="actions">
          <label className="button primary" htmlFor="cobol-files">
            Choose COBOL files
            <input
              id="cobol-files"
              className="file-input"
              type="file"
              accept=".cbl,.cob"
              multiple
              disabled={isConverting}
              onChange={chooseFiles}
            />
          </label>
          <button className="button secondary" type="button" onClick={loadSample} disabled={isConverting}>
            Load sample
          </button>
          <button
            className="button dark"
            type="button"
            onClick={handleConvert}
            disabled={!canConvert}
          >
            {isConverting
              ? 'Converting…'
              : files.length
                ? 'Convert files'
                : projectPrograms.length
                  ? 'Convert project'
                  : 'Convert'}
          </button>
        </div>

        <p className="file-limit">
          Batch: up to 5 UTF-8 .cbl/.cob files (100 KB each) via /api/convert. Projects: up to 10
          files via /api/projects, then /convert.
        </p>

        <div>
          <button
            className={viewMode === 'split' ? 'button dark' : 'button secondary'}
            type="button"
            onClick={() => setViewMode('split')}
          >
            Both
          </button>
          <button
            className={viewMode === 'cobol' ? 'button dark' : 'button secondary'}
            type="button"
            onClick={() => setViewMode('cobol')}
          >
            COBOL only
          </button>
          <button
            className={viewMode === 'python' ? 'button dark' : 'button secondary'}
            type="button"
            onClick={() => setViewMode('python')}
          >
            Python only
          </button>
        </div>

        <div className={viewMode === 'split' ? 'panels' : 'panels single'}>
          {(viewMode === 'split' || viewMode === 'cobol') && (
            <section className="panel" aria-labelledby="source-title">
              <div className="panel-heading">
                <span>INPUT</span>
                <h2 id="source-title">COBOL files</h2>
              </div>
              {sourceTabs.length > 0 && (
                <div className="file-tabs">
                  {sourceTabs.map((tab, index) => (
                    <button
                      key={tab.key}
                      type="button"
                      className={selectedFile === index ? 'active' : ''}
                      onClick={tab.onSelect}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              )}
              <pre className="code">
                {sourceTabs.length
                  ? sourceText
                  : 'Choose files, load the sample, or upload programs to a project.'}
              </pre>
            </section>
          )}

          {(viewMode === 'split' || viewMode === 'python') && (
            <section className="panel" aria-labelledby="output-title">
              <div className="panel-heading">
                <span>OUTPUT</span>
                <h2 id="output-title">Python files</h2>
              </div>
              {currentResult && (
                <div className="output-toolbar">
                  <span>
                    {currentResult.python_name}
                    {currentResult.status ? ` · ${currentResult.status}` : ''}
                  </span>
                  <button className="download" type="button" onClick={() => downloadPython(currentResult)}>
                    Download .py
                  </button>
                </div>
              )}
              <pre className="code">{currentResult?.python || 'Converted Python will appear here.'}</pre>
            </section>
          )}
        </div>

        {currentResult?.notes?.length > 0 && (
          <section className="review-notes">
            <h2>Lines to review</h2>
            <ul>
              {currentResult.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          </section>
        )}
        <p className="footnote">
          Conversion runs on the Python backend (`legacylift.converter`). Supported: simple fields,
          DISPLAY, MOVE, ADD, SUBTRACT, STOP RUN. Other lines are marked TODO in the draft.
        </p>
      </main>
    </div>
  )
}
