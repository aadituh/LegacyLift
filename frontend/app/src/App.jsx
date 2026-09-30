import { useState } from 'react'
import { backendIsReady, convertFiles } from './api'
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

export default function App() {
  const [files, setFiles] = useState([])
  const [sourceText, setSourceText] = useState('')
  const [selectedFile, setSelectedFile] = useState(0)
  const [results, setResults] = useState([])
  const [error, setError] = useState('')
  const [isConverting, setIsConverting] = useState(false)
  const [viewMode, setViewMode] = useState("split")

  async function showFile(file, index) {
    setSelectedFile(index)
    try {
      setSourceText(await file.text())
    } catch {
      setSourceText('Could not read this file.')
    }
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
    showFile(chosen[0], 0)
  }

  function loadSample() {
    const sample = new File([sampleCobol], 'hello_team.cbl', { type: 'text/plain' })
    setFiles([sample])
    setResults([])
    setError('')
    showFile(sample, 0)
  }

  async function handleConvert() {
    setIsConverting(true)
    setError('')
    try {
      setResults(await convertFiles(files))
    } catch (cause) {
      setResults([])
      setError(cause.message)
    } finally {
      setIsConverting(false)
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

  return (
    <div className="page">
      <header className="site-header">
        <span className="logo">L</span>
        <div>
          <strong>LegacyLift</strong>
          <span>COBOL to Python demo</span>
        </div>
      </header>

      <main className="workspace">
        <div className="intro">
          <p className="eyebrow">SIMPLE TEAM STARTER</p>
          <h1>Turn COBOL files into Python drafts.</h1>
          <p>Select a few small programs, convert them, then review and download each Python file.</p>
        </div>

        {!backendIsReady && (
          <p className="message" role="status">
            The frontend is ready. Connect the backend to enable conversion.
          </p>
        )}
        {error && <p className="message error" role="alert">{error}</p>}

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
            disabled={!backendIsReady || !files.length || isConverting}
          >
            {isConverting ? 'Converting…' : 'Convert files'}
          </button>
        </div>

        <p className="file-limit">Up to 5 UTF-8 files, 100 KB each. Supported extensions: .cbl and .cob.</p>

        <div>
          <button
            className={viewMode === "split" ? "button dark" : "button secondary"}
            type="button"
            onClick={() => setViewMode("split")}
          >
            Both
          </button>
          <button
            className={viewMode === "cobol" ? "button dark" : "button secondary"}
            type="button"
            onClick={() => setViewMode("cobol")}
          >
            COBOL only
          </button>
          <button
            className={viewMode === "python" ? "button dark" : "button secondary"}
            type="button"
            onClick={() => setViewMode("python")}
          >
            Python only
          </button>
        </div>

        <div className={viewMode === "split" ? "panels" : "panels single"}>
          {(viewMode === "split" || viewMode === "cobol") && ( 
          <section className="panel" aria-labelledby="source-title">
            <div className="panel-heading">
              <span>INPUT</span>
              <h2 id="source-title">COBOL files</h2>
            </div>
            {files.length > 0 && (
              <div className="file-tabs">
                {files.map((file, index) => (
                  <button
                    key={`${file.name}-${index}`}
                    type="button"
                    className={selectedFile === index ? 'active' : ''}
                    onClick={() => showFile(file, index)}
                  >
                    {file.name}
                  </button>
                ))}
              </div>
            )}
            <pre className="code">{files.length ? sourceText : 'Choose files or load the sample to begin.'}</pre>
          </section>
        )}
        
        {(viewMode === "split" || viewMode === "python") && ( 
          <section className="panel" aria-labelledby="output-title">
            <div className="panel-heading">
              <span>OUTPUT</span>
              <h2 id="output-title">Python files</h2>
            </div>
            {currentResult && (
              <div className="output-toolbar">
                <span>{currentResult.python_name}</span>
                <button className="download" type="button" onClick={() => downloadPython(currentResult)}>
                  Download .py
                </button>
              </div>
            )}
            <pre className="code">{currentResult?.python || 'Converted Python will appear here.'}</pre>
          </section>
        )}
        </div>

        {currentResult?.notes.length > 0 && (
          <section className="review-notes">
            <h2>Lines to review</h2>
            <ul>
              {currentResult.notes.map((note) => <li key={note}>{note}</li>)}
            </ul>
          </section>
        )}
        <p className="footnote">
          The converter handles simple fields, DISPLAY, MOVE, ADD, and SUBTRACT. Other lines are marked TODO in the draft.
        </p>
      </main>
    </div>
  )
}
