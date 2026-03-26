# Front-End Capability Tests

This project includes Playwright tests for key front-end capabilities:

- Dashboard
- Image Browser (including `Quoll Only` filtering)
- Detections
- Batch Upload (folder-based selection)
- Reports
- Admin

## Run Tests

From `frontend/`:

```bash
npm install
npx playwright install
npm run test:e2e
```

To run the interactive UI runner:

```bash
npm run test:e2e:ui
```

## Live Integration Mode (real backend)

This mode runs without API mocking and validates the full path through your local backend + frontend.

From project root, make sure Python dependencies are installed first, then from `frontend/` run:

```bash
npm run test:e2e:live
```

What this mode does:

- Starts backend (`uvicorn`) and frontend (`vite`) automatically
- Registers a real user
- Uploads a folder via the front-end folder picker
- Verifies results are visible across Dashboard/Image Browser/Detections/Reports

## Create Sample Upload Folder

From project root:

```bash
python -m scripts.create_sample_upload_folder
```

This creates:

- `storage/sample_uploads/sample_1.png`
- `storage/sample_uploads/sample_2.png`

## Notes

- Tests mock API responses, so they validate front-end behavior without requiring backend services.
- Quoll Profiles are intentionally not included, per current feature scope.
