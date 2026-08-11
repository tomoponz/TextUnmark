import { analyzeText, inspectText } from "./engine.mjs";

self.addEventListener("message", (event) => {
  const message = event.data || {};
  try {
    if (message.type === "analyze") {
      const report = analyzeText(String(message.text ?? ""), message.profile || "inspect");
      self.postMessage({ id: message.id, ok: true, type: "analyze", report });
      return;
    }

    if (message.type === "scan-files") {
      const files = Array.isArray(message.files) ? message.files : [];
      const results = files.map((file) => ({
        name: file.name,
        size: file.size,
        report: inspectText(String(file.text ?? "")),
      }));
      self.postMessage({ id: message.id, ok: true, type: "scan-files", results });
      return;
    }

    throw new Error(`Unknown worker message type: ${message.type}`);
  } catch (error) {
    self.postMessage({
      id: message.id,
      ok: false,
      type: message.type,
      error: error instanceof Error ? error.message : String(error),
    });
  }
});
