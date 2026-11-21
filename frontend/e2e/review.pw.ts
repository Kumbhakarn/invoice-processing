import { expect, test } from '@playwright/test';

const minimalPdf = () => Buffer.from('JVBERi0xLjMKJeLjz9MKMSAwIG9iago8PAovUHJvZHVjZXIgKHB5cGRmKQo+PgplbmRvYmoKMiAwIG9iago8PAovVHlwZSAvUGFnZXMKL0NvdW50IDEKL0tpZHMgWyA0IDAgUiBdCj4+CmVuZG9iagozIDAgb2JqCjw8Ci9UeXBlIC9DYXRhbG9nCi9QYWdlcyAyIDAgUgo+PgplbmRvYmoKNCAwIG9iago8PAovVHlwZSAvUGFnZQovUmVzb3VyY2VzIDw8Cj4+Ci9NZWRpYUJveCBbIDAuMCAwLjAgNjEyIDc5MiBdCi9QYXJlbnQgMiAwIFIKPj4KZW5kb2JqCnhyZWYKMCA1CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDAxNSAwMDAwMCBuIAowMDAwMDAwMDU0IDAwMDAwIG4gCjAwMDAwMDAxMTMgMDAwMDAgbiAKMDAwMDAwMDE2MiAwMDAwMCBuIAp0cmFpbGVyCjw8Ci9TaXplIDUKL1Jvb3QgMyAwIFIKL0luZm8gMSAwIFIKPj4Kc3RhcnR4cmVmCjI1NgolJUVPRgo=', 'base64');

async function uploadDocument(page: import('@playwright/test').Page, name = 'digital-invoice.pdf') {
  await page.goto('/');
  await page.getByLabel('Choose invoice documents').setInputFiles({ name: name.replace(/\.png$/i, '.pdf'), mimeType: 'application/pdf', buffer: minimalPdf() });
  await page.getByRole('button', { name: /start review/i }).click();
}

test('upload a document, review extracted fields, edit locally and export', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /clearer view of every invoice/i })).toBeVisible();
  await page.getByLabel('Choose invoice documents').setInputFiles({ name: 'digital-invoice.pdf', mimeType: 'application/pdf', buffer: minimalPdf() });
  await page.getByRole('button', { name: /start review/i }).click();
  await expect(page.getByRole('heading', { name: /invoice fields/i })).toBeVisible({ timeout: 10_000 });
  const invoiceNumber = page.getByRole('textbox', { name: 'Invoice number' }); await expect(invoiceNumber).toHaveValue('CI-2048-17');
  const invoiceBox = page.getByRole('button', { name: 'Focus Invoice number' });
  await page.locator('[data-field-path="invoice_number"]').hover();
  await expect(invoiceBox).toBeVisible();
  await invoiceBox.evaluate((button) => (button as HTMLButtonElement).click()); await expect(invoiceNumber).toBeFocused();
  await invoiceNumber.fill('CI-LOCAL-EDIT');
  await expect(page.getByText(/edited locally, not saved/i)).toBeVisible();
  await page.getByText('Export', { exact: true }).click();
  await expect(page.getByText(/export json/i)).toBeVisible();
});

test('shows the mock safe notice and local development notice', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText(/no ai provider requests are made/i)).toBeVisible();
  await expect(page.getByRole('contentinfo')).toContainText(/local development only/i);
});

test('cancels an in-flight mock upload', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Choose invoice documents').setInputFiles({ name: 'slow-invoice.pdf', mimeType: 'application/pdf', buffer: minimalPdf() });
  await page.getByRole('button', { name: /start review/i }).click();
  await page.getByRole('button', { name: /cancel upload/i }).click();
  await expect(page.getByLabel('Upload queue').getByText('The request was cancelled.')).toBeVisible();
});

test('shows a safe timeout message and rejects unsupported file types', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Choose invoice documents').setInputFiles({ name: 'oversized.png', mimeType: 'image/png', buffer: Buffer.alloc(10 * 1024 * 1024 + 1) });
  await expect(page.getByText(/larger than the 10 MiB limit/i)).toBeVisible();
  await page.getByLabel('Choose invoice documents').setInputFiles({ name: 'unsupported.exe', mimeType: 'application/octet-stream', buffer: Buffer.from('not a document') });
  await expect(page.getByText(/unsupported file type/i)).toBeVisible();
  await page.getByLabel('Choose invoice documents').setInputFiles({ name: 'timeout-invoice.pdf', mimeType: 'application/pdf', buffer: minimalPdf() });
  await page.getByRole('button', { name: /start review/i }).click();
  await expect(page.getByRole('alert')).toContainText(/ai provider request timed out/i, { timeout: 5_000 });
  await expect(page.getByRole('alert')).not.toContainText(/provider exception|secret|backend/i);
});

test('edits a value, reverts it and supports undo', async ({ page }) => {
  await uploadDocument(page);
  const field = page.getByRole('textbox', { name: 'Invoice number' });
  await expect(field).toHaveValue('CI-2048-17', { timeout: 10_000 });
  await field.fill('CI-LOCAL-EDIT');
  await page.getByRole('button', { name: /undo edit/i }).click();
  await expect(field).toHaveValue('CI-2048-17');
  await field.fill('CI-LOCAL-EDIT');
  await expect(page.getByText(/edited locally, not saved/i)).toBeVisible();
  await page.getByRole('button', { name: /revert/i }).click();
  await expect(field).toHaveValue('CI-2048-17');
  await expect(page.getByText(/edited locally, not saved/i)).toHaveCount(0);
});

test('cycles ambiguous evidence candidates and filters fields needing review', async ({ page }) => {
  await uploadDocument(page, 'ambiguous-invoice.pdf');
  await expect(page.getByText('2 possible locations')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText('1 / 2')).toBeVisible();
  await page.getByRole('button', { name: 'Next location candidate' }).click();
  await expect(page.getByText('2 / 2')).toBeVisible();
  await page.getByRole('button', { name: 'Needs review' }).click();
  await expect(page.getByRole('textbox', { name: 'Invoice number' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Exporter name' })).toHaveCount(0);
});

test('opens validation findings and keeps history browsing useful when enabled', async ({ page }) => {
  await uploadDocument(page);
  await page.getByRole('button', { name: /line items\[1\]\.amount/i }).click();
  await expect(page.getByRole('heading', { name: /invoice fields/i })).toBeVisible({ timeout: 10_000 });
  await page.getByRole('button', { name: /history/i }).last().click();
  await expect(page.getByRole('heading', { name: /invoice history/i })).toBeVisible();
  await expect(page.getByText('Page 1 · 23 records')).toBeVisible();
  await page.getByRole('button', { name: 'Next' }).click();
  await expect(page.getByText('Page 2 · 23 records')).toBeVisible();
  await page.getByLabel('Status').selectOption('failed');
  await expect(page.getByText('Page 1 · 1 records')).toBeVisible();
});

test('shows history disabled state and keeps an entry after deleting its original', async ({ page }) => {
  await page.goto('/');
  await page.evaluate(() => localStorage.setItem('docextract:mock-history-disabled', 'true'));
  await page.getByRole('button', { name: /browse history/i }).click();
  await expect(page.getByRole('heading', { name: /history is disabled on this server/i })).toBeVisible();
  await page.evaluate(() => localStorage.removeItem('docextract:mock-history-disabled'));
  await page.getByRole('button', { name: /back to upload/i }).click();
  await page.getByRole('button', { name: /browse history/i }).click();
  await expect(page.getByRole('heading', { name: /invoice history/i })).toBeVisible();
  const deleteButton = page.getByRole('button', { name: /delete original for/i }).first();
  await deleteButton.click();
  await page.getByRole('dialog').getByRole('button', { name: 'Delete original' }).click();
  await expect(page.getByRole('status')).toContainText(/history record and extraction result remain/i);
  await page.getByRole('button', { name: /northstar-commercial-invoice\.pdf/i }).first().click();
  await expect(page.getByText(/original document was deleted/i).first()).toBeVisible();
});

test('offers JSON and CSV exports', async ({ page }) => {
  await uploadDocument(page);
  await expect(page.getByRole('heading', { name: /invoice fields/i })).toBeVisible({ timeout: 10_000 });
  await page.getByText('Export', { exact: true }).click();
  await expect(page.getByText(/export json/i)).toBeVisible();
  await expect(page.getByText(/export csv/i)).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByText(/export json/i).click();
  await expect(download).resolves.toBeTruthy();
  const csvDownload = page.waitForEvent('download');
  await page.getByText(/export csv/i).click();
  await expect(csvDownload).resolves.toBeTruthy();
});
