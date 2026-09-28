const API_CANDIDATES = ["http://127.0.0.1:8000", "http://localhost:8000"];

export async function postFile(path, file) {
    const body = new FormData();
    body.append("file", file);
    let lastError = null;

    for (const origin of API_CANDIDATES) {
        try {
            const response = await fetch(origin + path, {
                method: "POST",
                body,
                cache: "no-store",
            });
            const text = await response.text();
            let data;
            try {
                data = JSON.parse(text);
            }   catch {
                const snippet = text.replace(/\s+/g, " ").trim().slice(0, 180);
                throw new Error(
                    snippet
                    ? "The server did not return JSON. " + snippet
                    : "The server returned an empty response.",
                );
            }
            if (!response.ok) {
                const detail = data && data.detail;
                throw new Error(typeof detail === "string" ? detail : JSON.stringify(data));
            }
            return data;
        } catch (err) {
            lastError = err;
        }
    }

    throw lastError || new Error("Could not reach the API on port 8000.");
}