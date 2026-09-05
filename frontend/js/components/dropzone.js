export function setupFileDropzone({
  dropzone,
  input,
  onFile,
  onError,
  validate,
  maxSize = 500 * 1024 * 1024,
}) {
  if (!dropzone || !input || dropzone.dataset.setup === 'true') return;
  dropzone.dataset.setup = 'true';

  const acceptFile = file => {
    if (!file) return;
    if (file.size > maxSize) {
      onError?.(`File is too large. Maximum size is ${Math.round(maxSize / 1024 / 1024)} MB.`);
      return;
    }
    const validationMessage = validate?.(file);
    if (validationMessage) {
      onError?.(validationMessage);
      return;
    }
    onFile(file);
  };

  dropzone.addEventListener('click', () => input.click());
  dropzone.addEventListener('dragover', event => {
    event.preventDefault();
    dropzone.classList.add('dragover');
  });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
  dropzone.addEventListener('drop', event => {
    event.preventDefault();
    dropzone.classList.remove('dragover');
    acceptFile(event.dataTransfer?.files?.[0]);
  });
  input.addEventListener('change', () => acceptFile(input.files?.[0]));

  return { acceptFile };
}
