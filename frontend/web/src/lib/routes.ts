/**
 * Build the URL of a project screen.
 *
 * Args: screen ("convert" or "export"), the project id, and an optional hash
 * without the leading "#".
 * Returns: a path with the id in the query string.
 * Example: projectUrl("convert", "12", "verification") -> "/convert?project=12#verification"
 */
export function projectUrl(
  screen: "convert" | "export",
  id: string,
  hash?: string,
) {
  return `/${screen}?project=${encodeURIComponent(id)}${hash ? `#${hash}` : ""}`;
}
