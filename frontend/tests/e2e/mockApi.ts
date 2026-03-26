import type { Page, Route } from '@playwright/test';

function json(route: Route, payload: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(payload),
  });
}

const baseDashboard = {
  total_images: 120,
  processed_images: 90,
  unprocessed_images: 30,
  total_detections: 42,
  total_animals: 30,
  quoll_detections: 12,
  total_individuals: 4,
  total_cameras: 3,
  total_collections: 2,
  processing_percent: 75,
  pending_review: 5,
};

const imagePage = {
  items: [
    {
      id: 1,
      filename: 'cam1_001.jpg',
      file_path: 'uploads/cam1_001.jpg',
      camera_id: 1,
      collection_id: 1,
      captured_at: null,
      width: 1920,
      height: 1080,
      processed: true,
      has_animal: true,
      thumbnail_path: null,
    },
    {
      id: 2,
      filename: 'cam1_002.jpg',
      file_path: 'uploads/cam1_002.jpg',
      camera_id: 1,
      collection_id: 1,
      captured_at: null,
      width: 1920,
      height: 1080,
      processed: false,
      has_animal: false,
      thumbnail_path: null,
    },
  ],
  total: 2,
  page: 1,
  per_page: 48,
  pages: 1,
};

const quollImagePage = {
  ...imagePage,
  items: [imagePage.items[0]],
  total: 1,
};

const speciesCounts = [
  { species: 'Dasyurus maculatus | Spotted-tailed Quoll', count: 12 },
  { species: 'Macropus giganteus | Eastern Grey Kangaroo', count: 8 },
];

const report = {
  total_images: 120,
  processed_images: 90,
  empty_images: 25,
  total_detections: 42,
  total_species: 2,
  quoll_detections: 12,
  mean_detection_confidence: 0.91,
  mean_classification_confidence: 0.87,
  species_distribution: speciesCounts,
  camera_counts: [
    { camera: '1', detections: 20 },
    { camera: '2', detections: 22 },
  ],
  hourly_activity: [
    { hour: 0, detections: 1 },
    { hour: 1, detections: 3 },
  ],
};

const users = [
  { id: 1, email: 'admin@example.com', full_name: 'Admin', role: 'admin', is_active: true },
  { id: 2, email: 'reviewer@example.com', full_name: 'Reviewer', role: 'reviewer', is_active: true },
];

const metrics = {
  total_images: 120,
  total_detections: 42,
  total_users: 2,
  pending_jobs: 1,
  db_size_mb: 10,
  storage_size_mb: 250,
};

export async function installMockApi(page: Page, role: 'reviewer' | 'admin' = 'reviewer') {
  await page.route('**/api/**', async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const { pathname } = url;

    if (pathname.endsWith('/api/auth/login')) {
      return json(route, { access_token: 'mock-token', token_type: 'bearer', role });
    }
    if (pathname.endsWith('/api/auth/me')) {
      return json(route, {
        id: role === 'admin' ? 1 : 2,
        email: role === 'admin' ? 'admin@example.com' : 'reviewer@example.com',
        full_name: role === 'admin' ? 'Admin' : 'Reviewer',
        role,
        is_active: true,
      });
    }
    if (pathname.endsWith('/api/stats/')) return json(route, baseDashboard);
    if (pathname.endsWith('/api/stats/collections')) return json(route, [{ name: 'C1', image_count: 120 }]);
    if (pathname.endsWith('/api/stats/cameras')) {
      return json(route, [{ id: 1, name: 'Cam 1', latitude: -35.2, longitude: 150.1, image_count: 120, detection_count: 42, last_upload: null }]);
    }
    if (pathname.endsWith('/api/detections/species-counts')) return json(route, speciesCounts);
    if (pathname.includes('/api/images/by-species/quoll')) return json(route, quollImagePage);
    if (pathname.endsWith('/api/images/')) return json(route, imagePage);
    if (pathname.endsWith('/api/reports/summary')) return json(route, report);
    if (pathname.endsWith('/api/images/upload-batch')) return json(route, { job_id: 55, files_received: 2, status: 'queued' });
    if (pathname.endsWith('/api/images/jobs/55')) {
      return json(route, {
        id: 55,
        batch_name: 'batch-upload-2-files',
        status: 'completed',
        total_images: 2,
        processed_images: 2,
        failed_images: 0,
        percent: 100,
        started_at: null,
        completed_at: null,
      });
    }
    if (pathname.endsWith('/api/admin/users')) return json(route, users);
    if (pathname.endsWith('/api/admin/system-metrics')) return json(route, metrics);
    if (pathname.includes('/api/admin/users/') && pathname.endsWith('/role')) {
      return json(route, { ...users[1], role: 'researcher' });
    }

    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });
}

export async function withAuthToken(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('token', 'mock-token');
  });
}
