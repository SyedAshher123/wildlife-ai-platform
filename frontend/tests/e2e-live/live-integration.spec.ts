import { expect, test } from '@playwright/test';
import os from 'node:os';
import path from 'node:path';
import { mkdtemp, writeFile } from 'node:fs/promises';

async function createSampleUploadFolder() {
  const folder = await mkdtemp(path.join(os.tmpdir(), 'wildlife-live-upload-'));
  const png1 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Zx7cAAAAASUVORK5CYII=';
  const png2 = 'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAQAAABFaP0WAAAADElEQVR42mP8z8AARAAA//8D3v7oNwAAAABJRU5ErkJggg==';
  await writeFile(path.join(folder, 'sample_1.png'), Buffer.from(png1, 'base64'));
  await writeFile(path.join(folder, 'sample_2.png'), Buffer.from(png2, 'base64'));
  return folder;
}

test('live flow: register/login, upload folder, and view results pages', async ({ page }) => {
  const uniq = Date.now();
  const email = `live-user-${uniq}@example.com`;
  const password = 'Password123!';

  await page.goto('/login');
  await page.getByRole('button', { name: 'Register' }).click();
  await page.locator('input').nth(0).fill('Live Tester');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: 'Create Account' }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

  await page.goto('/upload');
  const folder = await createSampleUploadFolder();
  await page.locator('input[webkitdirectory]').first().setInputFiles(folder);
  await page.getByRole('button', { name: 'Upload & Process' }).click();
  await expect(page.getByText(/Job #/)).toBeVisible();

  await page.goto('/images');
  await expect(page.getByRole('heading', { name: 'Image Browser' })).toBeVisible();
  await expect(page.getByText(/images/)).toBeVisible();

  await page.goto('/detections');
  await expect(page.getByRole('heading', { name: 'Detections', exact: true })).toBeVisible();

  await page.goto('/reports');
  await expect(page.getByRole('heading', { name: 'Reports' })).toBeVisible();
});
