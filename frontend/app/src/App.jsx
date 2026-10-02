import { useEffect, useMemo, useState } from 'react'
import {
  apiConfigured,
  checkBackend,
  convertFiles,
  convertProject,
  createDemoProject,
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
  const [screen, setScreen] = useState('upload')
  const [uploadMode, setUploadMode] = useState('project')
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
          setStatus('Backend is not reachable. Check the API connection, then refresh this page.')
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
    setProject(null)
    setResults([])
    setError('')
    setStatus(`${chosen.length} file(s) ready for batch conversion via /api/convert.`)
    setScreen('convert')
    showFile(chosen[0], 0)
  }

  function loadSample() {
    const sample = new File([sampleCobol], 'hello_team.cbl', { type: 'text/plain' })
    setFiles([sample])
    setProject(null)
    setResults([])
    setError('')
    setStatus('Sample loaded. Click Convert files to run the Python backend.')
    setScreen('convert')
    showFile(sample, 0)
  }

  async function handleConvert() {
    if (!backendReady) {
      setError('Backend is offline. Check the API connection, then try again.')
      return
    }

    setIsConverting(true)
    setError('')
    try {
      // File-picker selections use the batch route. Open projects use their own route.
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

  function openProject(nextProject) {
    setProject(nextProject)
    setProjectName(nextProject.name)
    setFiles([])
    setResults([])
    setSelectedFile(0)
    setSourceText(programFilesFromProject(nextProject)[0]?.content || '')
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


  const hasPrograms= files.length > 0 || projectPrograms.length > 0
  const hasOnlyOtherFiles = Boolean(project?.files?.length) && projectPrograms.length === 0 && files.length === 0
  const progressStep = results.length > 0 ? 2 : hasPrograms ? 1 : 0
  const ringRadius = 32
  const ringLength = 2 * Math.PI * ringRadius
  const progressNote = 
    progressStep === 0
      ? hasOnlyOtherFiles
        ? 'Upload a COBOL program before converting.'
        : 'Add files before converting.'
      : progressStep === 1
        ? files.length > 0
          ? 'Convert these files before verification.'
          : 'Convert this project before verification.'
        : 'Converted. Verification is not available yet.'
  const progressSteps = [
    { name: 'Upload', state: progressStep > 0 ? 'done' : 'current' },
    {
      name: 'Convert',
      state: progressStep > 1 ? 'done' : progressStep === 1 ? 'current' : 'waiting',
    },
    { name: 'Verify', state: progressStep > 1 ? 'current' : 'locked'},
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
          <strong>{project ? project.name : files.length ? 'Batch conversion' : 'No project yet'}</strong>
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

                  <p className="file-limit">Projects: up to 10 files via /api/projects, then /convert.</p>
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
                    : files.length
                      ? 'Convert files'
                      : projectPrograms.length
                        ? 'Convert project'
                        : 'Convert'}
                </button>
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
                        : 'Choose files, load a sample, or upload programs to a project.'}
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
              {results.length === 0 ? (
                <p className="file-limit">Convert a program first. The Python files will show up here.</p>
              ) : (
                <ul className="export-list">
                  {results.map((result, index) => (
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
