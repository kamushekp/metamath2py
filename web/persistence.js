(function (global) {
  async function downloadFromServer(onMessage) {
    try {
      const response = await fetch("/session/export");
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const blob = await response.blob();
      const filename = extractFilename(response.headers.get("Content-Disposition")) || buildFilename();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      onMessage && onMessage(`Граф сохранен в ${filename}`);
    } catch (err) {
      console.error(err);
      onMessage && onMessage("Не удалось сохранить: " + err.message);
    }
  }

  async function uploadToServer(file, onLoad, onMessage) {
    if (!file) return;
    const form = new FormData();
    form.append("file", file, file.name);
    try {
      const response = await fetch("/session/import", {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!response.ok) {
        onMessage && onMessage(payload.error || "Ошибка загрузки файла");
        return;
      }
      onLoad && onLoad(payload);
      onMessage && onMessage(`Граф загружен из ${file.name}`);
    } catch (err) {
      console.error(err);
      onMessage && onMessage("Не удалось загрузить файл");
    }
  }

  function extractFilename(contentDisposition) {
    if (!contentDisposition) return null;
    const match = /filename=\"?([^\";]+)\"?/i.exec(contentDisposition);
    return match ? match[1] : null;
  }

  function buildFilename() {
    const now = new Date();
    const pad = (num) => num.toString().padStart(2, "0");
    const timestamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    return `saplings_graph_${timestamp}.json`;
  }

  function initPersistence({ onLoad, saveButton, loadButton, fileInput, onMessage }) {
    if (!saveButton || !loadButton || !fileInput) return;
    saveButton.addEventListener("click", () => {
      downloadFromServer(onMessage);
    });
    loadButton.addEventListener("click", () => {
      fileInput.click();
    });
    fileInput.addEventListener("change", (event) => {
      const [file] = event.target.files || [];
      if (!file) return;
      uploadToServer(file, onLoad, onMessage);
      fileInput.value = "";
    });
  }

  global.Persistence = { initPersistence };
})(window);
