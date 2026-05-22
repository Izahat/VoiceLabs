export function setupDropzone(dropzoneEl, inputEl, fileInfoHandlers, onFileSelected, opts = {}) {
  const { accept = '*', maxSize = 500 * 1024 * 1024 } = opts;

  function handleFile(file) {
    if (file.size > maxSize) {
      alert(`File too large. Max ${maxSize / 1024 / 1024}MB`);
      return;
    }
    onFileSelected(file);
    const sizeStr = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
    if (fileInfoHandlers.show) fileInfoHandlers.show(file.name, sizeStr);
  }

  dropzoneEl.addEventListener('click', () => inputEl.click());

  dropzoneEl.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzoneEl.classList.add('dragover');
  });

  dropzoneEl.addEventListener('dragleave', () => {
    dropzoneEl.classList.remove('dragover');
  });

  dropzoneEl.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzoneEl.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });

  inputEl.addEventListener('change', () => {
    if (inputEl.files[0]) {
      handleFile(inputEl.files[0]);
    }
  });

  return { handleFile };
}