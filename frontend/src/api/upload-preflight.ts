const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const MAX_PDF_PAGES = 50;
const MAX_IMAGE_DIMENSION = 10_000;
const SUPPORTED_EXTENSIONS = new Set(['.pdf', '.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff']);
const extension = (name: string) => name.toLowerCase().slice(name.lastIndexOf('.'));

export async function validateUploadFile(file: File): Promise<string | null> {
  const ext = extension(file.name);
  if (!SUPPORTED_EXTENSIONS.has(ext)) return 'Unsupported file type. Choose a PDF, JPEG, PNG, WEBP, or TIFF.';
  if (file.size > MAX_UPLOAD_BYTES) return 'This file is larger than the 10 MiB limit.';
  if (!file.size) return 'This file is empty.';
  if (ext === '.pdf') {
    try {
      const pdfjs = await import('pdfjs-dist');
      pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString();
      const pdf = await pdfjs.getDocument({ data: await file.arrayBuffer() }).promise;
      const pageCount = pdf.numPages;
      await pdf.destroy();
      if (pageCount > MAX_PDF_PAGES) return 'This PDF has more than the 50-page limit.';
    } catch { return 'This PDF could not be read. Check that the file is valid and try again.'; }
  } else if (ext !== '.tif' && ext !== '.tiff') {
    try {
      const image = await createImageBitmap(file);
      const oversized = image.width > MAX_IMAGE_DIMENSION || image.height > MAX_IMAGE_DIMENSION;
      image.close();
      if (oversized) return 'This image exceeds the 10,000-pixel width or height limit.';
    } catch { return 'This image could not be read. Check that the file is valid and try again.'; }
  }
  return null;
}
