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

/**
 * One header row, then one row per output line.
 * `error` is filled on the first row of each program. A program with no
 * output still gets one row so the status and error are in the file.
 */
export function buildAuditReportCsv(verification) {
  const rows = [['program', 'status', 'error', 'line', 'cobol', 'python']]
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
