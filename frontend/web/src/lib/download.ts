export function saveBlob(blob: Blob, name: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function saveText(
  text: string,
  name: string,
  type = "text/plain;charset=utf-8",
) {
  saveBlob(new Blob([text], { type }), name);
}
