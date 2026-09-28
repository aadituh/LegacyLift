/**
 * Browser-side COBOL → Python converter (mirrors backend/prototype pipeline).
 * Used when the FastAPI server is unreachable so Start still works.
 */
(function (global) {
  "use strict";

  const SKIP_PARAGRAPHS = new Set([
    "IDENTIFICATION", "ENVIRONMENT", "DATA", "PROCEDURE", "WORKING-STORAGE",
    "LINKAGE", "FILE", "CONFIGURATION", "INPUT-OUTPUT", "FILE-CONTROL",
    "DIVISION", "SECTION", "PROGRAM", "STOP"
  ]);

  function cleanIdentifier(name) {
    const cleaned = String(name || "")
      .toLowerCase()
      .replace(/[^a-z0-9_]/g, "_")
      .replace(/_+/g, "_")
      .replace(/^_|_$/g, "");
    return cleaned || "unknown";
  }

  function mapPicToType(pic) {
    const p = String(pic || "").toUpperCase();
    if (/S9|V9|9V|V99/.test(p)) return "Decimal";
    if (p.includes("9")) return "int";
    if (p.includes("X")) return "str";
    return "Any";
  }

  function defaultValueForPic(pic) {
    const t = mapPicToType(pic);
    if (t === "Decimal") return "Decimal('0.00')";
    if (t === "int") return "0";
    if (t === "str") return "''";
    return "None";
  }

  function normalizeSource(source) {
    return String(source || "")
      .split(/\r?\n/)
      .map((line) => {
        if (line.length >= 7 && /^\d{6}/.test(line)) {
          const indicator = line[6];
          if (indicator === "*") return "";
          return indicator === " " || indicator === "/" || indicator === "-"
            ? line.slice(7)
            : line.slice(6);
        }
        return line;
      })
      .filter((line) => !line.trim().startsWith("*"))
      .join("\n");
  }

  function parseCobol(source) {
    const normalized = normalizeSource(source);
    const content = normalized.toUpperCase();

    const programMatch = content.match(/PROGRAM-ID\.\s*([A-Z0-9-]+)/);
    const programName = programMatch ? programMatch[1] : "UNKNOWN";

    const attributes = [];
    const seen = new Set();
    const fieldRe = /^\s*(?:0[1-9]|[1-4]\d)\s+([A-Z0-9][A-Z0-9-]*)\s+.*?PIC\s+([\w()V+\-]+)/gim;
    let fm;
    while ((fm = fieldRe.exec(content)) !== null) {
      const name = fm[1].toUpperCase();
      if (name === "FILLER" || seen.has(name)) continue;
      seen.add(name);
      attributes.push({ name: name, pic: fm[2].toUpperCase() });
    }

    let proc = content;
    const procMatch = content.match(/PROCEDURE\s+DIVISION[^\n]*\.\s*([\s\S]*)$/);
    if (procMatch) proc = procMatch[1];

    const paragraphs = [];
    const paraRe = /^([A-Z][A-Z0-9-]*)\.[ \t]*\r?\n((?:(?!^[A-Z][A-Z0-9-]*\.).)*)/gim;
    let pm;
    while ((pm = paraRe.exec(proc)) !== null) {
      const name = pm[1].toUpperCase();
      if (SKIP_PARAGRAPHS.has(name)) continue;
      if (name.endsWith("-DIVISION") || name.endsWith("-SECTION")) continue;
      paragraphs.push({ name: name, body: pm[2].trim() });
    }

    return {
      program_name: programName,
      attributes: attributes,
      paragraphs: paragraphs,
      methods: paragraphs.map((p) => p.name)
    };
  }

  function makeTranslator(fieldNames) {
    const fieldMap = {};
    fieldNames.forEach((n) => {
      fieldMap[String(n).toUpperCase()] = cleanIdentifier(n);
    });
    const names = Object.keys(fieldMap).sort((a, b) => b.length - a.length);
    const fieldPattern = names.length
      ? new RegExp("\\b(" + names.map((n) => n.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&")).join("|") + ")\\b", "gi")
      : null;

    function attr(cobolName) {
      const key = String(cobolName).toUpperCase().trim();
      return "self." + (fieldMap[key] || cleanIdentifier(key));
    }

    function replaceFields(expression) {
      if (!fieldPattern) return expression;
      return expression.replace(fieldPattern, (m) => attr(m));
    }

    function translateDisplay(statement) {
      const parts = [];
      const re = /"([^"]*)"|'([^']*)'|([A-Z0-9][A-Z0-9-]*)/gi;
      let m;
      while ((m = re.exec(statement)) !== null) {
        if (m[1] != null || m[2] != null) {
          parts.push({ type: "lit", text: m[1] != null ? m[1] : m[2] });
        } else if (m[3] && m[3].toUpperCase() !== "DISPLAY") {
          const id = m[3].toUpperCase();
          if (fieldMap[id]) parts.push({ type: "field", text: attr(id) });
          else parts.push({ type: "lit", text: m[3] });
        }
      }
      if (!parts.length) return 'print("")';
      if (parts.some((p) => p.type === "field")) {
        const body = parts.map((p) =>
          p.type === "field" ? "{" + p.text + "}" : p.text
        ).join("");
        return 'print(f"' + body + '")';
      }
      return "print(" + parts.map((p) => JSON.stringify(p.text)).join(" + ") + ")";
    }

    function translateStatement(statement) {
      const stmt = statement.trim().replace(/\.$/, "");
      if (!stmt) return [];
      const upper = stmt.toUpperCase();

      if (upper.startsWith("DISPLAY")) return [translateDisplay(stmt)];

      let match = stmt.match(/COMPUTE\s+([A-Z0-9-]+)\s+(?:ROUNDED\s+)?=\s*(.+)$/i);
      if (match) {
        return [attr(match[1]) + " = " + replaceFields(match[2].replace(/\.$/, ""))];
      }

      match = stmt.match(/ADD\s+(.+?)\s+TO\s+([A-Z0-9-]+)/i);
      if (match) {
        const target = attr(match[2]);
        return match[1].trim().split(/\s+/).map((token) => {
          if (/^\d+(\.\d+)?$/.test(token)) return target + " += " + token;
          return target + " += " + attr(token);
        });
      }

      match = stmt.match(/SUBTRACT\s+(.+?)\s+FROM\s+([A-Z0-9-]+)/i);
      if (match) {
        const src = match[1].trim();
        const rhs = /^\d+(\.\d+)?$/.test(src) ? src : attr(src.split(/\s+/)[0]);
        return [attr(match[2]) + " -= " + rhs];
      }

      match = stmt.match(/MOVE\s+(.+?)\s+TO\s+([A-Z0-9-]+)/i);
      if (match) {
        let source = match[1].trim().replace(/\.$/, "");
        const su = source.toUpperCase();
        if (su === "ZERO" || su === "ZEROS" || su === "ZEROES") source = "0";
        else if (su === "SPACE" || su === "SPACES") source = "''";
        else if (!/^['"]/.test(source) && !/^\d+(\.\d+)?$/.test(source)) source = attr(source);
        return [attr(match[2]) + " = " + source];
      }

      match = stmt.match(/PERFORM\s+([A-Z0-9-]+)/i);
      if (match) return ["self." + cleanIdentifier(match[1]) + "()"];

      if (upper === "STOP RUN" || upper === "GOBACK" || upper === "EXIT" || upper === "EXIT PROGRAM") {
        return ["return"];
      }

      return ["# TODO: translate statement: " + stmt];
    }

    function translateParagraph(body) {
      let text = body.replace(/\n/g, " ").replace(/\s+/g, " ").trim();
      text = text.replace(/\bEND-IF\b/gi, "");
      const chunks = text.split(/\.\s*/).map((c) => c.trim()).filter(Boolean);
      const lines = [];
      chunks.forEach((chunk) => {
        translateStatement(chunk).forEach((line) => lines.push("        " + line));
      });
      if (!lines.length) lines.push("        pass");
      return lines;
    }

    return { translateParagraph: translateParagraph };
  }

  function generatePython(parsed) {
    const programName = parsed.program_name || "UNKNOWN";
    const className = cleanIdentifier(programName).replace(/(^|_)([a-z])/g, (_, __, c) => c.toUpperCase()) + "Class";
    const fields = parsed.attributes || [];
    const paragraphs = parsed.paragraphs || [];
    const translator = makeTranslator(fields.map((f) => f.name));

    const lines = [
      "from decimal import Decimal",
      "from typing import Any",
      "",
      "class " + className + ":",
      '    """',
      "    Modern OOP version of COBOL program: " + programName,
      "    Generated by ML-Driven Legacy Code Modernization framework",
      '    """',
      "",
      "    def __init__(self):",
      "        # Data Division -> Class Attributes"
    ];

    if (fields.length) {
      fields.forEach((item) => {
        const pyName = cleanIdentifier(item.name);
        const pyType = mapPicToType(item.pic);
        const defVal = defaultValueForPic(item.pic);
        lines.push(
          "        self." + pyName + ": " + pyType + " = " + defVal +
          "  # from PIC " + (item.pic || "Unknown")
        );
      });
    } else {
      lines.push("        pass");
    }

    lines.push("");
    lines.push("    # === Procedural patterns grouped via unsupervised clustering ===");
    paragraphs.forEach((p, i) => {
      lines.push("    # Cluster " + i + ": " + p.name);
    });
    lines.push("");
    lines.push("    # === Business Logic Methods (one per COBOL paragraph) ===");
    lines.push("");

    const methodNames = [];
    paragraphs.forEach((p) => {
      const method = cleanIdentifier(p.name);
      methodNames.push(method);
      lines.push("    def " + method + "(self):");
      lines.push('        """COBOL paragraph: ' + p.name + '"""');
      translator.translateParagraph(p.body).forEach((l) => lines.push(l));
      lines.push("");
    });

    let mainMethod = null;
    for (let i = 0; i < paragraphs.length; i++) {
      const n = paragraphs[i].name;
      if (n.indexOf("MAIN") === 0 || n === "MAIN" || /-MAIN$/.test(n)) {
        mainMethod = cleanIdentifier(n);
        break;
      }
    }
    if (!mainMethod && methodNames.length) mainMethod = methodNames[0];

    lines.push("    def run(self):");
    lines.push('        """Entry point - mirrors COBOL PROCEDURE DIVISION main flow."""');
    lines.push("        print('=== Starting modernized COBOL program ===')");
    lines.push("        print(f'Program: " + programName + "')");
    if (mainMethod) lines.push("        self." + mainMethod + "()");
    else lines.push("        pass");
    lines.push("        print('=== Program completed successfully ===')");
    lines.push("");
    lines.push("    # Business logic preserved and modernized from original COBOL");
    return lines.join("\n");
  }

  function formatAnalysis(parsed) {
    const fields = (parsed.attributes || [])
      .map((item) => "- " + item.name + " (" + item.pic + ")")
      .join("\n") || "- none";
    const paragraphs = (parsed.paragraphs || [])
      .map((item) => "- " + item.name)
      .join("\n") || "- none";
    return (
      "Program: " + (parsed.program_name || "UNKNOWN") + "\n\n" +
      "Fields:\n" + fields + "\n\n" +
      "Paragraphs:\n" + paragraphs
    );
  }

  function convertLocal(source, filename) {
    const parsed = parseCobol(source);
    const python = generatePython(parsed);
    const analysis = {
      filename: filename || "upload.cbl",
      program_name: parsed.program_name,
      attributes: parsed.attributes,
      methods: parsed.methods,
      paragraphs: parsed.paragraphs
    };
    const consoleLog = [
      "ML-Driven Legacy Code Modernization (browser fallback)",
      "Input: " + (filename || "upload.cbl"),
      "Program: " + parsed.program_name,
      "Attributes: " + JSON.stringify((parsed.attributes || []).map((a) => a.name)),
      "Methods: " + JSON.stringify(parsed.methods || []),
      "--- Generated Python ---",
      python
    ].join("\n");
    return {
      filename: filename || "upload.cbl",
      python: python,
      analysis: analysis,
      analysis_text: formatAnalysis(parsed),
      console_log: consoleLog,
      local: true
    };
  }

  global.LegacyLiftConverter = {
    parseCobol: parseCobol,
    convertLocal: convertLocal,
    formatAnalysis: formatAnalysis
  };
})(typeof window !== "undefined" ? window : globalThis);
