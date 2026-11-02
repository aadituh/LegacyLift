/** Build the Export download `audit-report.csv` from a verify response. */

function reportFileStatus(verification, file) {
  if (verification?.status === 'not_verified') return 'not_verified'
  if (file?.equivalent) return 'verified'
  return 'mismatch'
}

function outputLines(text) {
  if (typeof text !== 'string' || !text) return []
  const normalized = text.replace(/\r\n/g, '\n').replace(/\n$/, '')
  return normalized ? normalized.split('\n') : []
}

function csvCell(value) {
  const text = value == null ? '' : String(value)
  if (/[",\n\r]/.test(text) || /^[=+\-@]/.test(text)) {
    return `"${text.replaceAll('"', '""')}"`
  }
  return text
}

function callerDisplayName(source) {
  const file = String(source || '').split(':')[0]
  return file.replace(/\.(cbl|cob)$/i, '')
}

/**
 * Programs another program calls, and that verify did not run on their own.
 * Hidden while the whole run is `not_verified`, matching the verification card.
 */
export function calledProgramReports(verification, dependencies) {
  if (!verification || verification.status === 'not_verified') return []
  const reported = new Set((verification.files || []).map((file) => file.source_name))
  const seen = new Set()
  const reports = []
  for (const link of dependencies || []) {
    if (link.kind !== 'call' || !link.target || reported.has(link.target) || seen.has(link.target)) {
      continue
    }
    seen.add(link.target)
    reports.push({ program: link.target, caller: callerDisplayName(link.source) })
  }
  return reports
}

/**
 * One header row, then one row per output line.
 * `error` is filled on the first row of each program. A program with no
 * output still gets one row so the status and error are in the file.
 */
export function buildAuditReportCsv(verification, calledPrograms = []) {
  const rows = [['program', 'status', 'error', 'line', 'cobol', 'python']]
  for (const called of calledPrograms) {
    rows.push([called.program, `runs inside ${called.caller}`, '', '', '', ''])
  }
  for (const file of verification?.files || []) {
    const status = reportFileStatus(verification, file)
    const error = file.error || ''
    const cobol = outputLines(file.cobol_stdout)
    const python = outputLines(file.python_stdout)
    const count = Math.max(cobol.length, python.length)
    if (count === 0) {
      rows.push([file.source_name || '', status, error, '', '', ''])
      continue
    }
    for (let index = 0; index < count; index += 1) {
      rows.push([
        file.source_name || '',
        status,
        index === 0 ? error : '',
        String(index + 1),
        cobol[index] ?? '',
        python[index] ?? '',
      ])
    }
  }
  return rows.map((row) => row.map(csvCell).join(',')).join('\r\n')
}
