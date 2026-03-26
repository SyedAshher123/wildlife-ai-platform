const API_BASE = '/api';
const STORAGE_BASE = '/storage';

// ---- Auth token management ------------------------------------------------

let _token: string | null = localStorage.getItem('token');

export function setToken(token: string | null) {
    _token = token;
    if (token) localStorage.setItem('token', token);
    else localStorage.removeItem('token');
}

export function getToken(): string | null {
    return _token;
}

function authHeaders(): Record<string, string> {
    return _token ? { Authorization: `Bearer ${_token}` } : {};
}

async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
    const res = await fetch(url, {
        ...init,
        headers: { ...authHeaders(), ...(init?.headers || {}) },
    });
    return res;
}

// ---- Types ----------------------------------------------------------------

export interface DashboardStats {
    total_images: number;
    processed_images: number;
    unprocessed_images: number;
    total_detections: number;
    total_animals: number;
    quoll_detections: number;
    total_individuals: number;
    total_cameras: number;
    total_collections: number;
    processing_percent: number;
    pending_review: number;
}

export interface ImageData {
    id: number;
    filename: string;
    file_path: string;
    camera_id: number | null;
    collection_id: number | null;
    captured_at: string | null;
    width: number | null;
    height: number | null;
    processed: boolean;
    has_animal: boolean | null;
    thumbnail_path: string | null;
}

export interface Detection {
    id: number;
    image_id: number;
    bbox_x: number;
    bbox_y: number;
    bbox_w: number;
    bbox_h: number;
    detection_confidence: number;
    category: string | null;
    species: string | null;
    classification_confidence: number | null;
    model_version: string | null;
    crop_path: string | null;
    created_at: string | null;
}

export interface DetectionDetail extends Detection {
    image: ImageData | null;
    camera: CameraStat | null;
    annotations: AnnotationData[];
}

export interface AnnotationData {
    id: number;
    detection_id: number;
    annotator: string | null;
    corrected_species: string | null;
    is_correct: boolean | null;
    notes: string | null;
    created_at: string | null;
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    per_page: number;
    pages: number;
}

export interface IndividualData {
    individual_id: string;
    species: string;
    first_seen: string | null;
    last_seen: string | null;
    total_sightings: number;
}

export interface SpeciesCount {
    species: string;
    count: number;
}

export interface CameraStat {
    id: number;
    name: string;
    latitude: number | null;
    longitude: number | null;
    image_count: number;
    detection_count: number;
    last_upload: string | null;
}

export interface CollectionStat {
    name: string;
    image_count: number;
}

export interface UserData {
    id: number;
    email: string;
    full_name: string | null;
    role: string;
    is_active: boolean;
}

export interface JobStatus {
    id: number;
    batch_name: string | null;
    status: string;
    total_images: number;
    processed_images: number;
    failed_images: number;
    percent: number;
    error_message?: string | null;
    started_at: string | null;
    completed_at: string | null;
}

export interface ReportData {
    total_images: number;
    processed_images: number;
    empty_images: number;
    total_detections: number;
    total_species: number;
    quoll_detections: number;
    mean_detection_confidence: number | null;
    mean_classification_confidence: number | null;
    species_distribution: { species: string; count: number }[];
    camera_counts: { camera: string; detections: number }[];
    hourly_activity: { hour: number; detections: number }[];
}

// ---- Auth -----------------------------------------------------------------

export async function login(email: string, password: string): Promise<UserData> {
    const form = new URLSearchParams();
    form.set('username', email);
    form.set('password', password);
    const res = await fetch(`${API_BASE}/auth/login`, { method: 'POST', body: form });
    if (!res.ok) throw new Error('Invalid credentials');
    const data = await res.json();
    setToken(data.access_token);
    return fetchMe();
}

export async function register(email: string, password: string, fullName: string, role: string): Promise<UserData> {
    const res = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: fullName, role }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Registration failed');
    }
    return res.json();
}

export async function fetchMe(): Promise<UserData> {
    const res = await apiFetch(`${API_BASE}/auth/me`);
    if (!res.ok) throw new Error('Not authenticated');
    return res.json();
}

export function logout() {
    setToken(null);
}

// ---- Stats ----------------------------------------------------------------

export async function fetchStats(): Promise<DashboardStats> {
    const res = await fetch(`${API_BASE}/stats/`);
    if (!res.ok) throw new Error('Failed to fetch stats');
    return res.json();
}

export async function fetchCameraStats(): Promise<CameraStat[]> {
    const res = await fetch(`${API_BASE}/stats/cameras`);
    if (!res.ok) throw new Error('Failed to fetch camera stats');
    return res.json();
}

export async function fetchCollectionStats(): Promise<CollectionStat[]> {
    const res = await fetch(`${API_BASE}/stats/collections`);
    if (!res.ok) throw new Error('Failed to fetch collection stats');
    return res.json();
}

export async function fetchIndividuals(): Promise<IndividualData[]> {
    const res = await fetch(`${API_BASE}/stats/individuals`);
    if (!res.ok) throw new Error('Failed to fetch individuals');
    return res.json();
}

// ---- Images ---------------------------------------------------------------

export async function fetchImages(params: {
    page?: number; per_page?: number; camera_id?: number;
    collection_id?: number; processed?: boolean; has_animal?: boolean;
}): Promise<PaginatedResponse<ImageData>> {
    const sp = new URLSearchParams();
    if (params.page) sp.set('page', String(params.page));
    if (params.per_page) sp.set('per_page', String(params.per_page));
    if (params.camera_id !== undefined) sp.set('camera_id', String(params.camera_id));
    if (params.collection_id !== undefined) sp.set('collection_id', String(params.collection_id));
    if (params.processed !== undefined) sp.set('processed', String(params.processed));
    if (params.has_animal !== undefined) sp.set('has_animal', String(params.has_animal));
    const res = await fetch(`${API_BASE}/images/?${sp}`);
    if (!res.ok) throw new Error('Failed to fetch images');
    return res.json();
}

export async function fetchImagesBySpecies(
    species: string,
    params: { page?: number; per_page?: number } = {},
): Promise<PaginatedResponse<ImageData>> {
    const sp = new URLSearchParams();
    if (params.page) sp.set('page', String(params.page));
    if (params.per_page) sp.set('per_page', String(params.per_page));
    const res = await fetch(`${API_BASE}/images/by-species/${encodeURIComponent(species)}?${sp}`);
    if (!res.ok) throw new Error('Failed to fetch images by species');
    return res.json();
}

export async function fetchImageDetail(id: number) {
    const res = await fetch(`${API_BASE}/images/${id}`);
    if (!res.ok) throw new Error('Failed to fetch image');
    return res.json();
}

export async function uploadBatch(
    files: File[],
    collectionName?: string,
): Promise<{ job_id: number; files_received: number }> {
    const CHUNK_SIZE = 200;
    let jobId: number | null = null;
    let received = 0;

    for (let i = 0; i < files.length; i += CHUNK_SIZE) {
        const chunk = files.slice(i, i + CHUNK_SIZE);
        const form = new FormData();
        for (const f of chunk) form.append('files', f);

        const relativePaths = chunk.map((f) => (f as any).webkitRelativePath || f.name);
        form.append('relative_paths', JSON.stringify(relativePaths));
        if (collectionName) form.append('collection_name', collectionName);

        const query = new URLSearchParams();
        if (jobId != null) query.set('job_id', String(jobId));
        const url = query.toString()
            ? `${API_BASE}/images/upload-batch?${query.toString()}`
            : `${API_BASE}/images/upload-batch`;

        const res = await apiFetch(url, { method: 'POST', body: form });
        if (!res.ok) throw new Error('Upload failed');
        const data = await res.json();
        jobId = data.job_id;
        received += data.files_received ?? chunk.length;
    }

    if (jobId == null) {
        throw new Error('No files to upload');
    }

    return { job_id: jobId, files_received: received };
}

export async function fetchJobStatus(jobId: number): Promise<JobStatus> {
    const res = await fetch(`${API_BASE}/images/jobs/${jobId}`);
    if (!res.ok) throw new Error('Failed to fetch job');
    return res.json();
}

// ---- Detections -----------------------------------------------------------

export async function fetchDetections(params: {
    page?: number; per_page?: number; species?: string; min_confidence?: number; image_id?: number;
}): Promise<PaginatedResponse<Detection>> {
    const sp = new URLSearchParams();
    if (params.page) sp.set('page', String(params.page));
    if (params.per_page) sp.set('per_page', String(params.per_page));
    if (params.species) sp.set('species', params.species);
    if (params.min_confidence) sp.set('min_confidence', String(params.min_confidence));
    if (params.image_id) sp.set('image_id', String(params.image_id));
    const res = await fetch(`${API_BASE}/detections/?${sp}`);
    if (!res.ok) throw new Error('Failed to fetch detections');
    return res.json();
}

export async function fetchDetectionDetail(id: number): Promise<DetectionDetail> {
    const res = await fetch(`${API_BASE}/detections/${id}`);
    if (!res.ok) throw new Error('Failed to fetch detection');
    return res.json();
}

export async function fetchSpeciesCounts(): Promise<SpeciesCount[]> {
    const res = await fetch(`${API_BASE}/detections/species-counts`);
    if (!res.ok) throw new Error('Failed to fetch species counts');
    return res.json();
}

// ---- Annotations ----------------------------------------------------------

export async function createAnnotation(payload: {
    detection_id: number; corrected_species?: string; is_correct?: boolean;
    notes?: string; individual_id?: string; flag_for_retraining?: boolean;
}): Promise<AnnotationData> {
    const res = await apiFetch(`${API_BASE}/annotations/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to create annotation');
    return res.json();
}

export async function fetchAnnotations(detectionId: number): Promise<AnnotationData[]> {
    const res = await fetch(`${API_BASE}/annotations/by-detection/${detectionId}`);
    if (!res.ok) throw new Error('Failed to fetch annotations');
    return res.json();
}

// ---- Reports --------------------------------------------------------------

export async function fetchReport(species?: string): Promise<ReportData> {
    const sp = new URLSearchParams();
    if (species) sp.set('species', species);
    const res = await fetch(`${API_BASE}/reports/summary?${sp}`);
    if (!res.ok) throw new Error('Failed to fetch report');
    return res.json();
}

export function getExportUrl(format: 'csv' | 'json', species?: string): string {
    const sp = new URLSearchParams({ format });
    if (species) sp.set('species', species);
    return `${API_BASE}/reports/export?${sp}`;
}

export function getQuollExportUrl(format: 'csv' | 'json'): string {
    return `${API_BASE}/exports/quoll-detections?format=${format}`;
}

export function getMetadataExportUrl(format: 'csv' | 'json'): string {
    return `${API_BASE}/exports/metadata?format=${format}`;
}

// ---- Admin ----------------------------------------------------------------

export async function fetchUsers(): Promise<UserData[]> {
    const res = await apiFetch(`${API_BASE}/admin/users`);
    if (!res.ok) throw new Error('Failed to fetch users');
    return res.json();
}

export async function changeUserRole(userId: number, role: string): Promise<UserData> {
    const res = await apiFetch(`${API_BASE}/admin/users/${userId}/role?role=${role}`, { method: 'PATCH' });
    if (!res.ok) throw new Error('Failed to change role');
    return res.json();
}

export async function fetchSystemMetrics() {
    const res = await apiFetch(`${API_BASE}/admin/system-metrics`);
    if (!res.ok) throw new Error('Failed to fetch metrics');
    return res.json();
}

// ---- Helpers --------------------------------------------------------------

export function storageUrl(path: string): string {
    return `${STORAGE_BASE}/${path}`;
}

// ---- Missed detection (user correction: "model said no animal but there is one")
export async function createMissedDetection(
    imageId: number,
    payload: { bbox_x: number; bbox_y: number; bbox_w: number; bbox_h: number; species: string; flag_for_retraining?: boolean },
): Promise<{ id: number; image_id: number; species: string; created_at: string | null }> {
    const res = await apiFetch(`${API_BASE}/images/${imageId}/missed-detection`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, flag_for_retraining: payload.flag_for_retraining ?? true }),
    });
    if (!res.ok) throw new Error('Failed to submit correction');
    return res.json();
}
