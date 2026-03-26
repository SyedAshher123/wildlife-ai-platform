import { expect, test } from '@playwright/test';
import os from 'node:os';
import path from 'node:path';
import { mkdtemp, writeFile } from 'node:fs/promises';
import { installMockApi, withAuthToken } from './mockApi';

test('dashboard renders key stats', async ({ page }) => {
  await installMockApi(page);
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  await expect(page.getByText('Total Images')).toBeVisible();
  await expect(page.getByText('Quoll Detections')).toBeVisible();
});

test('image browser supports quoll-only filter', async ({ page }) => {
  await installMockApi(page);
  await page.goto('/images');

  await expect(page.getByRole('heading', { name: 'Image Browser' })).toBeVisible();
  await page.getByRole('combobox').nth(2).selectOption('quoll');
  await expect(page.getByText('1 images')).toBeVisible();
});

test('detections page shows species distribution', async ({ page }) => {
  await installMockApi(page);
  await page.goto('/detections');

  await expect(page.getByRole('heading', { name: 'Detections' })).toBeVisible();
  await expect(page.getByText('Species Distribution')).toBeVisible();
  await expect(page.getByText('Spotted-tailed Quoll')).toBeVisible();
});

test('reports page renders export actions', async ({ page }) => {
  await installMockApi(page);
  await page.goto('/reports');

  await expect(page.getByRole('heading', { name: 'Reports' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Report CSV' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Quoll Detections CSV' })).toBeVisible();
});

test('batch upload works from folder input', async ({ page }) => {
  await withAuthToken(page);
  await installMockApi(page);
  await page.goto('/upload');

  const tempDir = await mkdtemp(path.join(os.tmpdir(), 'wildlife-upload-'));
  await writeFile(path.join(tempDir, 'cam1_001.jpg'), 'a');
  await writeFile(path.join(tempDir, 'cam1_002.jpg'), 'b');

  const folderInput = page.locator('input[webkitdirectory]').first();
  await folderInput.setInputFiles(tempDir);

  await page.getByRole('button', { name: 'Upload & Process' }).click();
  await expect(page.getByText(/Job #55/)).toBeVisible();
  await expect(page.getByText('2 / 2 processed')).toBeVisible();
});

test('admin panel is accessible for admin role', async ({ page }) => {
  await withAuthToken(page);
  await installMockApi(page, 'admin');
  await page.goto('/admin');

  await expect(page.getByRole('heading', { name: 'Admin Panel' })).toBeVisible();
  await expect(page.getByText('System management and user administration')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Users' })).toBeVisible();
});
