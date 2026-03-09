(() => {
  // ---- Element refs ----
  const dropSource    = document.getElementById("dropSource");
  const dropTarget    = document.getElementById("dropTarget");
  const sourceInput   = document.getElementById("sourceInput");
  const targetInput   = document.getElementById("targetInput");
  const sourcePreview = document.getElementById("sourcePreview");
  const targetPreview = document.getElementById("targetPreview");
  const sourceContent = document.getElementById("sourceContent");
  const targetContent = document.getElementById("targetContent");
  const clearSource   = document.getElementById("clearSource");
  const clearTarget   = document.getElementById("clearTarget");
  const goBtn         = document.getElementById("goBtn");
  const statusEl      = document.getElementById("status");
  const resultArea    = document.getElementById("resultArea");
  const resultImage   = document.getElementById("resultImage");
  const downloadBtn   = document.getElementById("downloadBtn");

  let sourceFile = null;
  let targetFile = null;

  // ---- Helpers ----
  function setStatus(msg, type = "info") {
    statusEl.textContent = msg;
    statusEl.className = `status ${type}`;
    statusEl.classList.remove("hidden");
  }

  function clearStatus() {
    statusEl.className = "status hidden";
    statusEl.textContent = "";
  }

  function updateGoBtn() {
    goBtn.disabled = !(sourceFile && targetFile);
  }

  function setPreview(imgEl, contentEl, clearBtn, file) {
    const url = URL.createObjectURL(file);
    imgEl.src = url;
    imgEl.classList.remove("hidden");
    contentEl.classList.add("hidden");
    clearBtn.classList.remove("hidden");
  }

  function clearPreview(imgEl, contentEl, clearBtn) {
    if (imgEl.src) URL.revokeObjectURL(imgEl.src);
    imgEl.src = "";
    imgEl.classList.add("hidden");
    contentEl.classList.remove("hidden");
    clearBtn.classList.add("hidden");
  }

  function handleFile(file, slot) {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setStatus("Please upload a valid image file (JPEG, PNG, or WEBP).", "error");
      return;
    }
    clearStatus();

    if (slot === "source") {
      sourceFile = file;
      setPreview(sourcePreview, sourceContent, clearSource, file);
    } else {
      targetFile = file;
      setPreview(targetPreview, targetContent, clearTarget, file);
    }
    updateGoBtn();
  }

  // ---- Drop zone setup ----
  function setupDropZone(zone, input, slot) {
    // Click to open file picker
    zone.addEventListener("click", () => input.click());
    zone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") input.click();
    });

    // File input change
    input.addEventListener("change", () => {
      if (input.files[0]) handleFile(input.files[0], slot);
      input.value = ""; // reset so same file can be re-selected
    });

    // Drag events
    zone.addEventListener("dragover", (e) => {
      e.preventDefault();
      zone.classList.add("drag-over");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
    zone.addEventListener("drop", (e) => {
      e.preventDefault();
      zone.classList.remove("drag-over");
      const file = e.dataTransfer.files[0];
      handleFile(file, slot);
    });
  }

  setupDropZone(dropSource, sourceInput, "source");
  setupDropZone(dropTarget, targetInput, "target");

  // ---- Clear buttons ----
  clearSource.addEventListener("click", (e) => {
    e.stopPropagation();
    sourceFile = null;
    clearPreview(sourcePreview, sourceContent, clearSource);
    updateGoBtn();
    clearStatus();
  });

  clearTarget.addEventListener("click", (e) => {
    e.stopPropagation();
    targetFile = null;
    clearPreview(targetPreview, targetContent, clearTarget);
    updateGoBtn();
    clearStatus();
  });

  // ---- Go button ----
  goBtn.addEventListener("click", async () => {
    if (!sourceFile || !targetFile) return;

    // UI: loading state
    goBtn.classList.add("loading");
    goBtn.disabled = true;
    resultArea.classList.add("hidden");
    setStatus("Swapping faces... this may take 15–30 seconds on CPU.", "info");

    const formData = new FormData();
    formData.append("source_image", sourceFile);
    formData.append("target_image", targetFile);

    try {
      const response = await fetch("/swap", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        const msg = data.detail || "Unknown server error.";
        setStatus(`Error: ${msg}`, "error");
        return;
      }

      // Show result
      const resultUrl = data.result_url + "?t=" + Date.now(); // cache-bust
      resultImage.src = resultUrl;
      downloadBtn.href = resultUrl;
      resultArea.classList.remove("hidden");
      setStatus("Done! Your swapped image is ready.", "success");

    } catch (err) {
      setStatus(`Network error: ${err.message}`, "error");
    } finally {
      goBtn.classList.remove("loading");
      goBtn.disabled = false;
      updateGoBtn();
    }
  });
})();
