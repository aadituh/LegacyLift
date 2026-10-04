import { useEffect, useMemo, useRef, useState } from 'react'
import {
  apiConfigured,
  checkBackend,
  convertFiles,
  convertProject,
  createDemoProject,
  createProject,
  downloadPythonFile,
  uploadProjectFiles,
  deleteProject,
  getProject,
  getRun,
  getRuns,
  listProjects,
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

/** Read a file as UTF-8. Browsers' file.text() replaces bad bytes instead of failing. */
async function utf8Text(file) {
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer())
  } catch {
    throw new Error(`${file.name} must be UTF-8 text.`)
  }
}

function programFilesFromProject(project) {
  if (!project?.files?.length) return []
  return project.files.filter((file) => file.kind === 'program')
}

const maxProjectFiles = 10
const savedProjectKey = 'legacylift-project-id'
const savedBatchKey = 'legacylift-batch'
const savedScreenKey = 'legacylift-screen'
const savedUploadModeKey = 'legacylift-upload-mode'
const savedViewKey = 'legacylift-view'

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function fillConversionProgress(setConversionProgress) {
  setConversionProgress(0)
  for (let step = 1; step <= 100; step += 1) {
    await delay(50)
    setConversionProgress(step)
  }
}

function clearSavedBatch() {
  sessionStorage.removeItem(savedBatchKey)
}

async function rememberBatch(fileList, converted, downloadId) {
  const sources = []
  for (const file of fileList) {
    sources.push({ name: file.name, text: await file.text() })
  }
  sessionStorage.setItem(
    savedBatchKey,
    JSON.stringify({ sources, results: converted, downloadId: downloadId || '' }),
  )
}

function readSavedBatch() {
  if (sessionStorage.getItem(savedProjectKey)) return null
  const raw = sessionStorage.getItem(savedBatchKey)
  if (!raw) return null
  try {
    const saved = JSON.parse(raw)
    const sources = saved.sources || []
    if (!sources.length) return null
    const results = saved.results || []
    return {
      files: sources.map((source) => new File([source.text], source.name, { type: 'text/plain' })),
      results,
      downloadId: saved.downloadId || '',
      sourceText: sources[0]?.text || '',
      status: results.length
        ? 'Opened the batch conversion from this tab.'
        : 'Opened the batch files from this tab. Click Convert files.',
    }
  } catch {
    clearSavedBatch()
    return null
  }
}

function runLabel(kind) {
  if (kind === 'convert') return 'Convert'
  if (kind === 'analyze') return 'Analyze'
  if (kind === 'verify') return 'Verify'
  return kind
}

function runStatusLabel(status) {
  if (status === 'draft') return 'Draft'
  if (status === 'review_required') return 'Review required'
  if (status === 'inventory_only') return 'File count only'
  if (status === 'not_verified') return 'Not compared'
    return status
}

function runTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString()
}

export default function App() {
  const [savedBatch] = useState(readSavedBatch)
  const [files, setFiles] = useState(() => savedBatch?.files ?? [])
  const [sourceText, setSourceText] = useState(() => savedBatch?.sourceText ?? '')
  const [selectedFile, setSelectedFile] = useState(0)
  const [results, setResults] = useState(() => savedBatch?.results ?? [])
  const [error, setError] = useState('')
  const [status, setStatus] = useState(() => savedBatch?.status ?? '')
  const [isConverting, setIsConverting] = useState(false)
  const [conversionProgress, setConversionProgress] = useState(0)
 
  const [viewMode, setViewMode] = useState(() => {
    const saved = sessionStorage.getItem(savedViewKey)
    if (saved === 'split' || saved === 'cobol' || saved === 'python') return saved
    return 'split'
  })
  
  const [screen, setScreen] = useState(() => {
    const saved = sessionStorage.getItem(savedScreenKey)
    if (saved === 'upload' || saved === 'convert' || saved === 'export') return saved
    return 'upload'
  })

  const [uploadMode, setUploadMode] = useState(() => {
    const saved = sessionStorage.getItem(savedUploadModeKey)
    if (saved === 'project' || saved === 'batch') return saved
    return 'project'
  })

  const [projectName, setProjectName] = useState('')
  const [project, setProject] = useState(null)
  const [backendReady, setBackendReady] = useState(false)
  const [backendChecked, setBackendChecked] = useState(false)
  const [runs, setRuns] = useState([])
  const [savedProjects, setSavedProjects] = useState([])
  const [downloadRunId, setDownloadRunId] = useState('')
  const [batchDownloadId, setBatchDownloadId] = useState(() => savedBatch?.downloadId ?? '')
  const sourceRead = useRef(0)

  const projectPrograms = useMemo(() => programFilesFromProject(project), [project])
  const batchReady = uploadMode === 'batch' && files.length > 0
  const projectReady = uploadMode === 'project' && projectPrograms.length > 0
  const canConvert = backendReady && (batchReady || projectReady) && !isConverting

  useEffect(() => {
    sessionStorage.setItem(savedScreenKey, screen)
  }, [screen])

  useEffect(() => {
    sessionStorage.setItem(savedUploadModeKey, uploadMode)
  }, [uploadMode])

  useEffect(() => {
    sessionStorage.setItem(savedViewKey, viewMode)
  }, [viewMode]) 

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
          setStatus('Backend is not reachable. Check the API connection, then refresh this page.')
        } else if (!savedBatch) {
          setStatus('Connected to LegacyLift API. Choose COBOL files or a project, then Convert.')
        }
      }
    }
    probe()
    return () => {
      cancelled = true
    }
  }, [savedBatch])

  useEffect(() => {
    const id = sessionStorage.getItem(savedProjectKey)
    
    if(!backendReady || !id) return
    let cancelled = false
    async function restore() {
      try {
        const saved = await getProject(id)
        if (cancelled) return
        openProject(saved)
        const runs = await getRuns(id)
        const convertRun = [...runs.runs].reverse().find((run) => run.kind === 'convert')
        if (!convertRun) {
          setStatus(`Opened "${saved.name}". Convert it to see the Python again.`)
          return
        }
        const run = await getRun(id, convertRun.id)
        if (cancelled) return
        setDownloadRunId(convertRun.id)
        setBatchDownloadId('')
        setResults(run.files || [])
        setStatus(`Opened "${saved.name}" with the saved Python. `)
      } catch (cause) {
        sessionStorage.removeItem(savedProjectKey)
        if (!cancelled) setError(cause.message)
      }
    }
    restore()
    return () => {
      cancelled = true
    }
  }, [backendReady])

  useEffect(() => {
    if (screen !== 'export' || !project?.id || !backendReady) return
    let cancelled = false
    async function  loadRuns() {
      try {
        const data = await getRuns(project.id)
        if (!cancelled) setRuns(data.runs || [])
      } catch (cause) {
        if (!cancelled) setError(cause.message)
      }
    }
    loadRuns()
    return () => {
      cancelled = true
    }
  }, [screen, project, backendReady])

  useEffect(() => {
    if (screen !== 'upload' || uploadMode !== 'project' || !backendReady) return
    let cancelled = false
    async function loadSavedProjects() {
      try {
        const data = await listProjects() 
        if (!cancelled) setSavedProjects(data.projects || [])
      } catch (cause) {
        if (!cancelled) setError(cause.message)
      }
    }
    loadSavedProjects()
    return () => {
      cancelled = true
    }
  }, [screen, uploadMode, backendReady, project])

  async function showFile(file, index) {
    const readId = ++sourceRead.current
    setSelectedFile(index)
    try {
      const text = await utf8Text(file)
      if (readId !== sourceRead.current) return
      setSourceText(text)
    } catch {
      if (readId !== sourceRead.current) return
      setSourceText('Could not read this file.')
    }
  }

  function showProjectProgram(program, index) {
    sourceRead.current += 1
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

  async function chooseFiles(event) {
    const chosen = Array.from(event.target.files || [])
    event.target.value = ''
    if (!chosen.length) return
    if (chosen.length > 5) {
      rejectFiles('Choose up to 5 files.')
      return
    }
    const tooBig = chosen.filter((file) => file.size > 100_000)
    if (tooBig.length) {
      const names = tooBig.map((file) => file.name).join(', ')
      rejectFiles(`${names} must be 100 KB or less.`)
      return
    }
    const wrongType = chosen.filter((file) => !/\.(cbl|cob)$/i.test(file.name))
    if (wrongType.length) {
      const names = wrongType.map((file) => file.name).join(', ')
      rejectFiles(`${names} must be a .cbl or .cob file.`)
      return
    }
    try {
      for (const file of chosen) await utf8Text(file)
    } catch (cause) {
      rejectFiles(cause.message)
      return
    }

    setFiles(chosen)
    setProject(null)
    setDownloadRunId('')
    setBatchDownloadId('')
    sessionStorage.removeItem(savedProjectKey)
    clearSavedBatch()
    setResults([])
    setError('')
    setStatus(`${chosen.length} file(s) ready for batch conversion via /api/convert.`)
    showFile(chosen[0], 0)
    await rememberBatch(chosen, [], '')
  }

  async function loadSample() {
    const sample = new File([sampleCobol], 'hello_team.cbl', { type: 'text/plain' })
    setFiles([sample])
    setProject(null)
    setDownloadRunId('')
    setBatchDownloadId('')
    sessionStorage.removeItem(savedProjectKey)
    clearSavedBatch()
    setResults([])
    setError('')
    setStatus(
      backendReady
        ? 'Sample loaded. Click Convert files to run the Python backend.'
        : 'Sample loaded. Convert files not ready until the API is online.'
    )
    showFile(sample, 0)
    await rememberBatch([sample], [], '')
  }

  async function handleConvert() {
    if (!backendReady) {
      setError('Backend is offline. Check the API connection, then try again.')
      return
    }

    setIsConverting(true)
    setError('')
    try {
      // The Upload screen's Project / Batch files choice decides the route.
      if (uploadMode === 'batch') {
        if (files.length === 0) {
          setError('Choose COBOL files or load a sample before converting.')
          return
        }
        await fillConversionProgress(setConversionProgress)
        const converted = await convertFiles(files)
        setResults(converted.files)
        setDownloadRunId('')
        setBatchDownloadId(converted.download_id)
        await rememberBatch(files, converted.files, converted.download_id)
        setStatus(`Converted ${converted.files.length} file(s) through /api/convert.`)
        if (selectedFile >= converted.files.length) setSelectedFile(0)
        return
      }
      if (!project || projectPrograms.length === 0) {
        setError(
          project
            ? 'Upload a COBOL program before converting this project.'
            : 'Create a project and upload a COBOL program before converting.',
        )
        return
      }
      await fillConversionProgress(setConversionProgress)
      const conversion = await convertProject(project.id)
      setResults(conversion.files)
      setDownloadRunId(conversion.run_id)
      setBatchDownloadId('')
      setStatus(
        `Converted project "${project.name}" (${conversion.files.length} program(s), status: ${conversion.status}).`,
      )
      setSelectedFile(0)
      setSourceText(projectPrograms[0].content || '')
    } catch (cause) {
      setResults([])
      setDownloadRunId('')
      setBatchDownloadId('')
      setError(cause.message)
      if (files.length > 0) await rememberBatch(files, [], '')
      setError(cause.message)
    } finally {
      setIsConverting(false)
      setConversionProgress(0)
    }
  }

  function openProject(nextProject) {
    sessionStorage.setItem(savedProjectKey, nextProject.id)
    clearSavedBatch()
    setProject(nextProject)
    setProjectName(nextProject.name)
    setDownloadRunId('')
    setBatchDownloadId('')
    setFiles([])
    setResults([])
    setSelectedFile(0)
    setSourceText(programFilesFromProject(nextProject)[0]?.content || '')
  }

  function closeProjectIfDeleted(projectId) {
    if (project?.id !== projectId) return
    sessionStorage.removeItem(savedProjectKey)
    setProject(null)
    setResults([])
    setDownloadRunId('')
    setSourceText('')
    setSelectedFile(0)
  }

  async function handleOpenSavedProject(projectId) {
    if (!backendReady) return
    setError('')
    try {
      const saved = await getProject(projectId)
      openProject(saved)
      const runs = await getRuns(projectId)
      const convertRun = [...runs.runs].reverse().find((run) => run.kind === 'convert')
      if (!convertRun) {
        setStatus(`Opened "${saved.name}". Convert it to see the Python again.`)
        return
      }
      const run = await getRun(projectId, convertRun.id)
      setDownloadRunId(convertRun.id)
      setResults(run.files || [])
      setScreen('convert')
      setStatus(`Opened "${saved.name}" with the saved Python.`)
    } catch (cause) {
      setError(cause.message)
    }
  }

  async function handleRemoveSavedProject(projectId) {
    if (!backendReady) return
    setError('')
    try {
      await deleteProject(projectId)
      closeProjectIfDeleted(projectId)
      setSavedProjects((current) => current.filter((item) => item.id !== projectId))
      setStatus('Removed the saved project.')
    } catch (cause) {
      setError(cause.message)
    }
  }

  async function handleClearSavedProjects() {
    if (!backendReady || savedProjects.length === 0) return
    setError('')
    const ids = savedProjects.map((item) => item.id)
    try {
      for (const projectId of ids) {
        await deleteProject(projectId)
      }
      if (ids.includes(project?.id)) closeProjectIfDeleted(project.id)
      setSavedProjects([])
      setStatus('Cleared saved projects')
    } catch (cause) {
      setError(cause.message)
      const data = await listProjects().catch(() => null)
      if (data) setSavedProjects(data.projects || [])
    }
  }

  async function handleCreateProject() {
    const name = projectName.trim()
    if (!name) {
      setError('Enter a project name.')
      return
    }
    if (!backendReady) {
      setError('Backend is offline. Check the API connection, then try again.')
      return
    }
    setError('')
    try {
      const created = await createProject(name)
      openProject(created)
      setStatus(`Project "${created.name}" created. Upload .cbl/.cob files, then Convert.`)
    } catch (cause) {
      setError(cause.message)
    }
  }

  async function handleLoadDemoProject() {
    if (!backendReady) return
    setError('')
    try {
      const demo = await createDemoProject()
      openProject(demo)
      setStatus(`Loaded "${demo.name}" with ${demo.files.length} sample files. Click Convert project.`)
    } catch (cause) {
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
      setError('Backend is offline. Check the API connection, then try again.')
      return
    }
    const fileCount = project.files.length + chosen.length
    if (fileCount > maxProjectFiles) {
      const room = maxProjectFiles - project.files.length
      const roomText =
        room > 0
          ? `This project already has ${project.files.length}, so ${room} more can be added.`
          : `This project already has ${project.files.length}.`
      setError(`A project can take up to ${maxProjectFiles} files. ${roomText}`)
      return
    } 
    const tooBig = chosen.filter((file) => file.size > 100_000)
    if (tooBig.length) {
      const names = tooBig.map((file) => file.name).join(', ')
      setError(`${names} must be 100 KB or less.`)
      return
    }
    try {
      for (const file of chosen) await utf8Text(file)
    } catch (cause) {
      setError(cause.message)
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
      setFiles([])
      setResults([])
      const programs = programFilesFromProject(next)
      setStatus(
        `Uploaded ${uploaded.files.length} file(s). ${programs.length} program(s) ready to convert.`
      )
      if (programs.length) {
        setSourceText(programs[0].content || '')
        setSelectedFile(0)
      }
    } catch (cause) {
      setError(cause.message)
    }
  }

  async function downloadPython(result) {
    const path = downloadRunId && project
      ? `/api/projects/${encodeURIComponent(project.id)}/runs/${encodeURIComponent(downloadRunId)}/files/${encodeURIComponent(result.python_name)}`
      : batchDownloadId
        ? `/api/convert/${encodeURIComponent(batchDownloadId)}/files/${encodeURIComponent(result.python_name)}`
        : ''
    if (!path) {
      setError('Convert the files again before downloading. This copy is not on the API.')
      return
    }
    setError('')
    try {
      await downloadPythonFile(path, result.python_name)
    } catch (cause) {
      setError(cause.message)
    }
  }

  const showingBatch = uploadMode === 'batch'
  const shownResults = showingBatch ? (batchDownloadId ? results : []) : downloadRunId ? results : []
  const currentResult = shownResults[selectedFile]
  const sourceTabs = showingBatch
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


  const modeReady = showingBatch ? files.length > 0 : projectPrograms.length > 0
  const modeConverted = shownResults.length > 0
  const hasOnlyOtherFiles =
    !showingBatch && Boolean(project?.files?.length) && projectPrograms.length === 0
  const progressStep = modeConverted ? 2 : modeReady ? 1 : 0
  const ringRadius = 32
  const ringLength = 2 * Math.PI * ringRadius
  const progressNote = 
    progressStep === 0
      ? hasOnlyOtherFiles
        ? 'Upload a COBOL program before converting.'
        : 'Add files before converting.'
      : progressStep === 1
        ? showingBatch
          ? 'Convert these files before verification.'
          : 'Convert this project before verification.'
        : 'Converted. Verification is coming soon.'
  const progressSteps = [
    { name: 'Upload', state: progressStep > 0 ? 'done' : 'current' },
    {
      name: 'Convert',
      state: progressStep > 1 ? 'done' : progressStep === 1 ? 'current' : 'waiting',
    },
    { name: 'Verify', state: progressStep > 1 ? 'soon' : 'locked' },
  ]

  return (
    <div className="page app-shell">
      <aside className="side-nav">
        <div className="nav-brand">
          <span className="logo">L</span>
          <strong>LegacyLift</strong>
        </div>
        <button
          className={screen === 'upload' ? 'nav-button active' : "nav-button"}
          type="button"
          onClick={() => setScreen('upload')}
        >
          Upload
        </button>
        <button
          className={screen === 'convert' ? 'nav-button active' : 'nav-button'}
          type="button"
          onClick={() => setScreen('convert')}
        >
          Convert
        </button>
        <button
          className={screen === 'export' ? 'nav-button active' : 'nav-button'}
          type="button"
          onClick={() => setScreen('export')}
        >
          Export
        </button>
      </aside>

      <div className="shell-main">
        <header className="site-header">
          <strong>
            {showingBatch ? 'Batch conversion' : project ? project.name : 'No project yet'}
          </strong>
          {backendChecked && (
            <span className={backendReady ? 'api-badge ok' : 'api-badge down'} role="status">
              {backendReady ? 'API connected' : 'API offline'}
            </span>
          )}
        </header>

        <section className="progress-status" aria-label={`Progress ${progressStep} of 3. ${progressNote}`}>
          <div className="status-ring-wrap">
            <svg className="status-ring" viewBox="0 0 88 88" aria-hidden="true">
              <circle className="status-ring-track" cx="44" cy="44" r={ringRadius} />
              {progressStep > 0 && (
                <circle
                  className="status-ring-value"
                  cx="44"
                  cy="44"
                  r={ringRadius}
                  strokeDasharray={`${(progressStep / 3) * ringLength} ${ringLength}`}
                />
              )}
            </svg>
            <span className="status-ring-count">{progressStep}/3</span>
          </div>
          <div className="progress-steps">
            {progressSteps.map((step) => (
              <p key={step.name} className={`progress-step ${step.state}`}>
                {step.state === 'done' ? '✓ ' : ''}
                {step.name}
                {step.state === 'locked' ? ' Locked' : ''}
                {step.state === 'soon' ? ' — coming soon' : ''}
              </p>
            ))}
            <p className="progress-note">{progressNote}</p>
          </div>
        </section>

        <main className="workspace">
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

          {screen === 'upload' && (
            <>
              <div className="actions project-row">
                <button
                  className={uploadMode === 'project' ? 'button dark' : 'button secondary'}
                  type="button"
                  onClick={() => setUploadMode('project')}
                >
                  Project
                </button>
                <button
                  className={uploadMode === 'batch' ? 'button dark' : 'button secondary'}
                  type="button"
                  onClick={() => setUploadMode('batch')}
                >
                  Batch files
                </button>
              </div>

              {uploadMode === 'project' && (
                <>
                  <div className="actions project-row">
                    <input
                      value={projectName}
                      onChange={(event) => setProjectName(event.target.value)}
                      placeholder="Project name"
                    />
                    <button
                      className="button primary"
                      type="button"
                      onClick={handleCreateProject}
                      disabled={!backendReady || isConverting}
                    >
                      Create project
                    </button>
                    <button
                      className="button secondary"
                      type="button"
                      onClick={handleLoadDemoProject}
                      disabled={!backendReady || isConverting}
                    >
                      Load demo project
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

                  <p className="file-limit">
                    Projects: up to {maxProjectFiles} files via /api/projects, then /convert.
                  </p>
                  <div className="saved-projects">
                    <h2 className="history-title">Saved projects</h2>
                    <button
                      className="button secondary"
                      type="button"
                      onClick={handleClearSavedProjects}
                      disabled={!backendReady || isConverting || savedProjects.length === 0}
                    >
                      Clear saved projects
                    </button>
                    {savedProjects.length === 0 ? (
                    <p className="file-limit">No saved projects yet.</p>
                  ) : (
                    <ul className="export-list">
                      {savedProjects.map((item) => (
                        <li key={item.id} className="export-row">
                          <span>
                            {item.name}
                            <span className="run-time">{runTime(item.created_at)}</span>
                          </span>
                          <span className="actions">
                            <button
                            className="button secondary"
                            type="button"
                            onClick={() => handleOpenSavedProject(item.id)}
                            disabled={isConverting}
                          >
                            Open
                          </button>
                          <button
                            className="button secondary"
                            type="button"
                            onClick={() => handleRemoveSavedProject(item.id)}
                            disabled={isConverting}
                          >
                            Remove
                          </button>
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                  </div>
                </>
              )}

              {uploadMode === 'batch' && (
                <>
                  <p className="file-limit">
                    These files are converted on their own and are not added to a project.
                  </p>
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
                      Load small sample
                    </button>
                  </div>
                  <p className="file-limit">Batch: up to 5 UTF-8 .cbl/.cob files (100 KB each) via /api/convert.</p>
                </>
              )}
            </>  
          )}

          {screen === 'convert' && (
            <>
              <div className="actions project-row">
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
                  type = "button"
                  onClick={() => setViewMode('python')}
                >
                  Python only
                </button>
                <button
                  className="button dark"
                  type="button"
                  onClick={handleConvert}
                  disabled={!canConvert}
                >
                  {isConverting
                    ? 'Converting...'
                    : showingBatch
                      ? 'Convert files'
                      : 'Convert project'}
                </button>
              </div>

              {isConverting && (
                <section className="conversion-progress" aria-label="Preparing conversion">
                  <div className="conversion-progress-header">
                    <span>Preparing conversion...</span>
                    <span>{conversionProgress}%</span>
                  </div>
                  <div
                    className="conversion-progress-track"
                    role="progressbar"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={conversionProgress}
                    aria-label={`Conversion preparation ${conversionProgress}%`}
                  >
                    <div
                      className="conversion-progress-value"
                      style={{ width: `${conversionProgress}%` }}
                    />
                  </div>
                  <p className="conversion-progress-note">
                    Preparing the COBOL source for conversion.
                  </p>
                </section>
              )}

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
                    
              <div className={viewMode === 'split' ? 'panels' : 'panels single'}>
                {(viewMode === 'split' || viewMode === 'cobol') && (
                  <section className="panel" aria-labelledby="source-title">
                    <div className="panel-heading">
                      <span>INPUT</span>
                      <h2 id="source-title">COBOL files</h2>
                    </div>
                    <pre className="code">
                      {sourceTabs.length
                        ? sourceText
                        : showingBatch
                          ? 'Choose COBOL files or load a sample.'
                          : 'Upload programs to a project.'}
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
                          {currentResult.status ? ` . ${currentResult.status}` : ''}
                        </span>
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
            </>
          )}

        {screen === 'export' && (
          <>
            <h2 className="history-title">Run history</h2>
            {showingBatch ? (
              <p className="file-limit">
                Batch conversion is not saved, so there is no run history.
              </p>
            ) : !project ? (
              <p className="file-limit">Open a project to see its runs.</p>
            ) : runs.length === 0 ? (
              <p className="file-limit">No runs yet. Convert the project to add one.</p>
            ) : (
              <ul className="export-list">
                {[...runs].reverse().map((run) => (
                  <li key={run.id} className="export-row">
                    <span>{runLabel(run.kind)}</span>
                    <span className="run-status">{runStatusLabel(run.status)}</span>
                    <span className="run-time">{runTime(run.created_at)}</span>
                  </li>
                ))}
              </ul>
            )}

            <h2 className="history-title">Downloads</h2>
            {shownResults.length === 0 ? (
              <p className="file-limit">Convert a program first. The Python files will show up here.</p>
            ) : (
              <ul className="export-list">
                {shownResults.map((result, index) => (
                  <li
                    key={result.python_name}
                    className={index === selectedFile ? 'export-row selected' : 'export-row'}
                  >
                    <span>{result.python_name}</span>
                    <button className="download" type="button" onClick={() => downloadPython(result)}>
                      Download .py
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </>
          )} 
        </main>
      </div>
    </div>
  )
}
