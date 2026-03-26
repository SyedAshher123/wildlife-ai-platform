import { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation, useParams, Navigate } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import * as L from 'leaflet';
import { AuthProvider, useAuth } from './auth';
import {
    fetchStats, fetchImages, fetchIndividuals, fetchCollectionStats, fetchCameraStats,
    fetchSpeciesCounts, fetchReport, fetchDetectionDetail, fetchAnnotations, fetchDetections,
    createAnnotation, uploadBatch, fetchJobStatus, fetchUsers, changeUserRole,
    fetchSystemMetrics, register, getExportUrl, getQuollExportUrl, getMetadataExportUrl, fetchImagesBySpecies, fetchImageDetail,
    storageUrl, createMissedDetection,
    type DashboardStats, type ImageData, type IndividualData, type CollectionStat,
    type CameraStat, type SpeciesCount, type PaginatedResponse, type ReportData,
    type DetectionDetail, type AnnotationData, type JobStatus, type UserData, type Detection,
} from './api';
import './index.css';

/* Fix Leaflet default icon paths */
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
    iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
    shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const CHART_COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

function App() {
    return (
        <BrowserRouter>
            <AuthProvider>
                <AppShell />
            </AuthProvider>
        </BrowserRouter>
    );
}

function AppShell() {
    const { user, loading } = useAuth();
    if (loading) return <LoadingState />;
    return (
        <div className="app">
            <HomeHeader />
            <main className="main-content">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/images" element={<ImageBrowser />} />
                    <Route path="/detections" element={<DetectionViewer />} />
                    <Route path="/individuals" element={<SpeciesExplorer />} />
                    <Route path="/individuals/species/:speciesKey" element={<SpeciesDetail />} />
                    <Route path="/individuals/species/:speciesKey/images" element={<SpeciesImages />} />
                    <Route path="/individuals/species/:speciesKey/individuals" element={<SpeciesByIndividual />} />
                    <Route path="/individuals/species/:speciesKey/individuals/:individualId" element={<IndividualImages />} />
                    <Route path="/upload" element={<RequireAuth><BatchUpload /></RequireAuth>} />
                    <Route path="/reports" element={<Reports />} />
                    <Route path="/pending-review" element={<RequireAuth><PendingReviewPage /></RequireAuth>} />
                    <Route path="/help" element={<HelpPage />} />
                    <Route path="/review/:detectionId" element={<RequireAuth><ImageReview /></RequireAuth>} />
                    <Route path="/review-empty/:imageId" element={<RequireAuth><ReviewEmptyImage /></RequireAuth>} />
                    <Route path="/review-image/:imageId" element={<RequireAuth><ReviewImage /></RequireAuth>} />
                    <Route path="/admin" element={<RequireAuth role="admin"><AdminPanel /></RequireAuth>} />
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="*" element={<Navigate to="/" />} />
                </Routes>
            </main>
            <Footer />
        </div>
    );
}

function RequireAuth({ children, role }: { children: React.ReactNode; role?: string }) {
    const { user } = useAuth();
    if (!user) return <Navigate to="/login" />;
    if (role && user.role !== role) return <div className="empty-state"><h3>Access denied</h3><p>Requires {role} role</p></div>;
    return <>{children}</>;
}

/* ============================================================
   HEADER (WildlifeTracker approved design)
   ============================================================ */
function HomeHeader() {
    const loc = useLocation();
    const { user, logout } = useAuth();
    const navItems = [
        { path: '/', label: 'Home' },
        { path: '/upload', label: 'Upload' },
        { path: '/individuals', label: 'Profiles' },
        { path: '/pending-review', label: 'Pending Review' },
        { path: '/reports', label: 'Reports' },
        { path: '/help', label: 'Help' },
    ];

    return (
        <header className="site-header">
            <Link to="/" className="logo">
                <LeafLogo />
                <span>WildlifeTracker</span>
            </Link>
            <nav className="nav-center">
                {navItems.map((item) => (
                    <Link
                        key={item.path}
                        to={item.path}
                        className={`nav-link ${loc.pathname === item.path || (item.path === '/pending-review' && loc.pathname.startsWith('/review')) ? 'active' : ''}`}
                    >
                        {item.label}
                    </Link>
                ))}
            </nav>
            <div className="nav-icons">
                <button type="button" className="nav-icon-btn" aria-label="Notifications">🔔</button>
                <button type="button" className="nav-icon-btn" aria-label="Help">❓</button>
                {user ? (
                    <button
                        type="button"
                        className="nav-icon-btn"
                        onClick={logout}
                        aria-label="User"
                        title={user.email}
                    >
                        👤
                    </button>
                ) : (
                    <Link to="/login" className="nav-icon-btn" aria-label="Sign in">👤</Link>
                )}
            </div>
        </header>
    );
}

function LeafLogo() {
    return (
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden>
            <path d="M17 8C8 10 5.9 16.17 3.82 21.34L5.71 22L6.66 19.7C7.14 18.66 7.5 17.59 7.77 16.5C8.5 18 9.5 19.5 10.5 20.5C11.5 21.5 13 22 15 22C19 22 22 19 22 15C22 12 20.5 9.5 18 8C17 8 17 8 17 8Z" />
        </svg>
    );
}

/* ============================================================
   FOOTER (WildlifeTracker approved design)
   ============================================================ */
function Footer() {
    return (
        <footer className="site-footer">
            <div className="footer-inner">
                <div className="footer-brand">
                    <Link to="/" className="logo"><LeafLogo /><span>WildlifeTracker</span></Link>
                    <p className="footer-tagline">Advanced wildlife monitoring and conservation technology</p>
                </div>
                <div className="footer-col">
                    <h4>Features</h4>
                    <Link to="/detections">AI Recognition</Link>
                    <Link to="/individuals">Movement Tracking</Link>
                    <Link to="/reports">Data Analytics</Link>
                </div>
                <div className="footer-col">
                    <h4>Support</h4>
                    <a href="#docs">Documentation</a>
                    <Link to="/help">Help Center</Link>
                    <a href="#contact">Contact Us</a>
                </div>
                <div className="footer-col">
                    <h4>Connect</h4>
                    <div className="footer-connect">
                        <a href="#twitter" aria-label="Twitter">𝕏</a>
                        <a href="#youtube" aria-label="YouTube">▶</a>
                        <a href="#linkedin" aria-label="LinkedIn">in</a>
                    </div>
                </div>
            </div>
            <div className="footer-bottom">© 2025 WildlifeTracker. All rights reserved.</div>
        </footer>
    );
}

/* ============================================================
   HELP (placeholder)
   ============================================================ */
function HelpPage() {
    return (
        <div className="page-header">
            <h2>Help</h2>
            <p>Documentation and support — coming soon.</p>
        </div>
    );
}

/* ============================================================
   PENDING REVIEW (design: metrics, category cards, review list)
   ============================================================ */
function PendingReviewPage() {
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [report, setReport] = useState<ReportData | null>(null);
    const [detections, setDetections] = useState<Detection[]>([]);
    const [emptyImages, setEmptyImages] = useState<PaginatedResponse<ImageData> | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [filter, setFilter] = useState<string | null>(null);
    const [search, setSearch] = useState('');
    const [focusSpecies, setFocusSpecies] = useState<'quoll' | 'all'>('quoll');

    useEffect(() => {
        let alive = true;
        const load = async () => {
            setLoading(true);
            try {
                const [s, r, detRes, emptyRes] = await Promise.all([
                    fetchStats(),
                    fetchReport(),
                    fetchDetections({ per_page: 200, min_confidence: 0 }),
                    fetchImages({ has_animal: false, per_page: 50 }),
                ]);
                if (!alive) return;
                setStats(s);
                setReport(r);
                setDetections(detRes.items || []);
                setEmptyImages(emptyRes);
                setError(null);
            } catch (e: any) {
                setError(e.message);
            } finally {
                if (alive) setLoading(false);
            }
        };
        load();
    }, []);

    const lowConf = detections.filter((d) => (d.detection_confidence < 0.7) || (d.classification_confidence != null && d.classification_confidence < 0.7));
    const highConf = detections.filter((d) => d.detection_confidence >= 0.7 && (d.classification_confidence == null || d.classification_confidence >= 0.7));
    const noAnimalCount = emptyImages?.total ?? report?.empty_images ?? 0;

    const metrics = {
        lowConf: lowConf.length,
        conflict: 0,
        noAnimal: noAnimalCount,
        newIndividual: Math.min(highConf.length, 50),
    };

    if (loading) return <LoadingState />;
    if (error) return <ErrorState message={error} />;

    return (
        <div className="pending-review-page">
            <nav className="breadcrumb">
                <Link to="/">Home</Link>
                <span className="sep">›</span>
                <span>Pending Review</span>
            </nav>
            <div className="page-header">
                <h1 className="pending-review-title">Pending Reviews for Verification</h1>
                <p className="pending-review-subtitle">Review and verify AI-detected images for Spotted-tail Quolls.</p>
            </div>

            <div className="review-metrics">
                <div className="review-metric-card warning">
                    <span className="dot yellow" /><span className="icon">⚠</span>
                    <div><strong>{fmt(metrics.lowConf)}</strong> Low Confidence Identifications</div>
                </div>
                <div className="review-metric-card danger">
                    <span className="dot red" /><span className="icon">✕</span>
                    <div><strong>{fmt(metrics.conflict)}</strong> Conflict Detections</div>
                </div>
                <div className="review-metric-card muted">
                    <span className="dot gray" /><span className="icon">↻</span>
                    <div><strong>{fmt(metrics.noAnimal)}</strong> No Animal Detected</div>
                </div>
                <div className="review-metric-card success">
                    <span className="dot green" /><span className="icon">+</span>
                    <div><strong>{fmt(metrics.newIndividual)}</strong> New Individuals Potential</div>
                </div>
            </div>

            <div className="review-toolbar">
                <input type="search" className="review-search" placeholder="Search by filename, camera trap, or date" value={search} onChange={(e) => setSearch(e.target.value)} />
                <select className="filter-select"><option>Spotted-tail Quoll</option><option>All Species</option></select>
                <select className="filter-select"><option>Date Range</option></select>
                <select className="filter-select"><option>Camera Location</option></select>
                <select className="filter-select"><option>Sort by Date</option></select>
            </div>

            {!filter ? (
                <div className="review-category-grid">
                    <ReviewCategoryCard title="Low confidence" tag={`${lowConf.length > 0 ? Math.round((lowConf[0].detection_confidence || 0) * 100) : 0}% - Low Confidence`} tagClass="warning" imageCount={lowConf.length} onReview={() => setFilter('low-confidence')} />
                    <ReviewCategoryCard title="Conflict" tag="Conflict" tagClass="danger" imageCount={metrics.conflict} onReview={() => setFilter('conflict')} />
                    <ReviewCategoryCard title="New Individual" tag="89% - High" tagClass="success" imageCount={metrics.newIndividual} onReview={() => setFilter('new-individual')} />
                    <ReviewCategoryCard title="No Animal (Miss fire)" tag="No Detection" tagClass="muted" imageCount={metrics.noAnimal} onReview={() => setFilter('no-animal')} />
                </div>
            ) : (
                <div className="review-list-view">
                    <button type="button" className="btn btn-outline" style={{ marginBottom: '1rem' }} onClick={() => setFilter(null)}>← Back to categories</button>
                    {filter === 'low-confidence' && (
                        <div className="review-item-grid">
                            {lowConf.slice(0, 20).map((d) => (
                                <div key={d.id} className="review-item-card">
                                    <div className="review-item-tags">
                                        <span className={`tag tag-${(d.detection_confidence || 0) >= 0.7 ? 'primary' : 'accent'}`}>{Math.round((d.detection_confidence || 0) * 100)}%</span>
                                        <span className="tag tag-muted">Low Confidence</span>
                                    </div>
                                    <div>Image Count — 1</div>
                                    <div className="review-item-model">Model: YOLOV8</div>
                                    <Link to={`/review/${d.id}`} className="btn btn-primary" style={{ marginTop: '0.75rem' }}>Review</Link>
                                </div>
                            ))}
                        </div>
                    )}
                    {filter === 'no-animal' && emptyImages && (
                        <div className="review-item-grid">
                            {emptyImages.items.map((img) => (
                                <div key={img.id} className="review-item-card">
                                    <div className="review-item-tags"><span className="tag tag-muted">No Animal</span></div>
                                    <div>{img.filename}</div>
                                    <Link to={`/review-empty/${img.id}`} className="btn btn-primary" style={{ marginTop: '0.75rem' }}>Annotate (add animal)</Link>
                                </div>
                            ))}
                        </div>
                    )}
                    {(filter === 'conflict' || filter === 'new-individual') && (
                        <div className="review-item-grid">
                            {(filter === 'new-individual' ? highConf : detections).slice(0, 20).map((d) => (
                                <div key={d.id} className="review-item-card">
                                    <div className="review-item-tags">
                                        <span className="tag tag-primary">{Math.round((d.detection_confidence || 0) * 100)}%</span>
                                    </div>
                                    <Link to={`/review/${d.id}`} className="btn btn-primary" style={{ marginTop: '0.75rem' }}>Review</Link>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            <div className="review-side-panels">
                <div className="review-panel card">
                    <h4>Analytics Overview</h4>
                    <p>Reviews Completed This Week: <strong>{report?.processed_images ?? 0}</strong></p>
                    <p>Average Model Confidence: <strong>76%</strong></p>
                    <p>Most Common Pending: <span className="tag tag-accent">Low Confidence</span></p>
                </div>
                <div className="review-panel card">
                    <h4>Focus Species</h4>
                    <label><input type="radio" checked={focusSpecies === 'quoll'} onChange={() => setFocusSpecies('quoll')} /> Spotted-tail Quoll</label>
                    <label><input type="radio" checked={focusSpecies === 'all'} onChange={() => setFocusSpecies('all')} /> All Species</label>
                    <a href={getExportUrl('csv', focusSpecies === 'quoll' ? 'quoll' : undefined)} className="btn btn-outline" style={{ marginTop: '0.75rem', display: 'inline-flex' }}>Export Summary</a>
                </div>
            </div>
        </div>
    );
}

function ReviewCategoryCard({ title, tag, tagClass, imageCount, onReview }: { title: string; tag: string; tagClass: string; imageCount: number; onReview: () => void }) {
    return (
        <div className="review-category-card card">
            <div className="review-category-tags">
                <span className={`tag tag-${tagClass}`}>{tag}</span>
                <span className={`tag tag-${tagClass}`}>{tag.split(' ')[0]}</span>
            </div>
            <div className="review-category-title">{title}</div>
            <div className="review-category-meta">Image Count - {fmt(imageCount)}</div>
            <div className="review-category-model">Model: YOLOV8</div>
            <button type="button" className="btn btn-primary" onClick={onReview}>Review</button>
        </div>
    );
}

/* ============================================================
   DASHBOARD (Home — WildlifeTracker approved design)
   ============================================================ */
function Dashboard() {
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [report, setReport] = useState<ReportData | null>(null);
    const [cameras, setCameras] = useState<CameraStat[]>([]);
    const [species, setSpecies] = useState<SpeciesCount[]>([]);
    const [recentDetections, setRecentDetections] = useState<Detection[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [mapView, setMapView] = useState<'cluster' | 'region'>('region');

    useEffect(() => {
        let alive = true;
        const loadAll = async (showSpinner = false) => {
            if (showSpinner) setLoading(true);
            try {
                const [s, r, cam, sp, det] = await Promise.all([
                    fetchStats(),
                    fetchReport(),
                    fetchCameraStats(),
                    fetchSpeciesCounts(),
                    fetchDetections({ per_page: 5 }),
                ]);
                if (!alive) return;
                setStats(s);
                setReport(r);
                setCameras(cam);
                setSpecies(sp);
                setRecentDetections(det.items || []);
                setError(null);
            } catch (e: any) {
                if (!alive) return;
                setError(e.message);
            } finally {
                if (alive) setLoading(false);
            }
        };
        loadAll(true);
        const pollId = window.setInterval(() => loadAll(false), 5000);
        return () => { alive = false; window.clearInterval(pollId); };
    }, []);

    if (loading) return <LoadingState />;
    if (error) return <ErrorState message={error} />;
    if (!stats) return null;

    const camsWithCoords = cameras.filter((c) => c.latitude && c.longitude);
    const mapCenter: [number, number] = camsWithCoords.length > 0
        ? [camsWithCoords[0].latitude!, camsWithCoords[0].longitude!]
        : [-34.4, 150.3];

    // Activity by time of day: group hourly_activity into Dawn/Morning/Afternoon/Evening/Night
    const hourGroups = [
        { name: 'Dawn', hours: [5, 6, 7] },
        { name: 'Morning', hours: [8, 9, 10, 11] },
        { name: 'Afternoon', hours: [12, 13, 14, 15, 16] },
        { name: 'Evening', hours: [17, 18, 19, 20] },
        { name: 'Night', hours: [21, 22, 23, 0, 1, 2, 3, 4] },
    ];
    const hourlyMap = new Map<number, number>();
    if (report?.hourly_activity) {
        report.hourly_activity.forEach(({ hour, detections }) => hourlyMap.set(hour, detections));
    }
    const activityByTimeOfDay = hourGroups.map((g) => ({
        name: g.name,
        count: g.hours.reduce((sum, h) => sum + (hourlyMap.get(h) || 0), 0),
    }));

    // Observation trends: 6 months (use report total or mock)
    const totalDet = report?.total_detections ?? stats.total_detections;
    const observationTrends = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'].map((name, i) => ({
        name,
        count: Math.round(totalDet * (0.6 + (i * 0.1)) + Math.random() * 20),
    }));

    // Species abundance: Species, Individuals, Density, Trend (design uses Koala/Quoll/Kangaroo; we use API species + mock density/trend)
    const speciesAbundance = species.slice(0, 8).map((s, i) => ({
        species: s.species,
        individuals: s.count,
        density: (s.count / (i + 2)).toFixed(1),
        trend: (i % 3 === 0 ? -5 : i % 3 === 1 ? 15 : 8),
    }));

    return (
        <>
            <div className="home-stats">
                <div className="home-stat-card">
                    <div className="stat-icon-wrap green">📷</div>
                    <div>
                        <div className="stat-value">{fmt(stats.total_detections || stats.total_images)}</div>
                        <div className="stat-label">Total Observations</div>
                    </div>
                </div>
                <div className="home-stat-card">
                    <div className="stat-icon-wrap blue">🐾</div>
                    <div>
                        <div className="stat-value">{species.length}</div>
                        <div className="stat-label">Active Species</div>
                    </div>
                </div>
                <div className="home-stat-card">
                    <div className="stat-icon-wrap green">✓</div>
                    <div>
                        <div className="stat-value">{fmt(stats.total_individuals)}</div>
                        <div className="stat-label">Identified Individuals</div>
                    </div>
                </div>
                <div className="home-stat-card">
                    <div className="stat-icon-wrap orange">📋</div>
                    <div>
                        <div className="stat-value">{fmt(stats.pending_review)}</div>
                        <div className="stat-label">Pending Review</div>
                    </div>
                </div>
            </div>

            <div className="home-map-section">
                <div className="section-header">
                    <h3>CameraTrap Locations</h3>
                    <div className="view-toggle">
                        <button type="button" className={mapView === 'cluster' ? 'active' : ''} onClick={() => setMapView('cluster')}>Cluster View</button>
                        <span style={{ color: 'var(--border)' }}>|</span>
                        <button type="button" className={mapView === 'region' ? 'active' : ''} onClick={() => setMapView('region')}>Region View ▾</button>
                    </div>
                </div>
                <div className="map-wrap">
                    <MapContainer center={mapCenter} zoom={camsWithCoords.length ? 12 : 10} style={{ height: '100%', width: '100%' }}>
                        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="OSM" />
                        {camsWithCoords.map((c) => (
                            <Marker key={c.id} position={[c.latitude!, c.longitude!]}>
                                <Popup>
                                    <strong>{c.name}</strong><br />
                                    Images: {c.image_count} · Detections: {c.detection_count}
                                    {c.last_upload && <><br />Last: {new Date(c.last_upload).toLocaleDateString()}</>}
                                </Popup>
                            </Marker>
                        ))}
                    </MapContainer>
                </div>
            </div>

            <div className="home-charts">
                <div className="home-chart-card">
                    <div className="card-header"><h3>Activity by Time of Day</h3></div>
                    <div className="card-body">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={activityByTimeOfDay} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                                <YAxis tick={{ fontSize: 11 }} />
                                <Tooltip />
                                <Bar dataKey="count" fill="var(--primary)" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
                <div className="home-chart-card">
                    <div className="card-header"><h3>Observation Trends</h3></div>
                    <div className="card-body">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={observationTrends} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                                <YAxis tick={{ fontSize: 11 }} />
                                <Tooltip />
                                <Line type="monotone" dataKey="count" stroke="var(--info)" strokeWidth={2} dot={{ r: 4 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            <div className="species-abundance-section">
                <div className="section-header"><h3>Species Abundance</h3></div>
                <div className="table-container">
                    <table>
                        <thead>
                            <tr><th>Species</th><th>Individuals</th><th>Density (/km²)</th><th>Trend</th></tr>
                        </thead>
                        <tbody>
                            {speciesAbundance.length === 0 ? (
                                <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No species data yet</td></tr>
                            ) : (
                                speciesAbundance.map((row) => (
                                    <tr key={row.species}>
                                        <td>{row.species}</td>
                                        <td>{row.individuals}</td>
                                        <td>{row.density}</td>
                                        <td className={row.trend >= 0 ? 'trend-up' : 'trend-down'}>
                                            {row.trend >= 0 ? '+' : ''}{row.trend}%
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="recent-activity-section">
                <div className="section-header"><h3>Recent Activity</h3></div>
                <div className="recent-activity-list">
                    {recentDetections.length === 0 ? (
                        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>No recent activity</div>
                    ) : (
                        recentDetections.map((d) => (
                            <Link key={d.id} to={`/review/${d.id}`} className="recent-activity-item">
                                <div className="thumb">
                                    {d.crop_path ? <img src={storageUrl(d.crop_path)} alt="" /> : '📷'}
                                </div>
                                <div className="content">
                                    <div className="title">{d.species || 'Unknown'} — {d.id}</div>
                                    <div className="subtitle">Detection #{d.id} · {d.created_at ? new Date(d.created_at).toLocaleString() : 'Recent'}</div>
                                </div>
                                <span className={`badge ${(d.detection_confidence || 0) >= 0.7 ? 'confirmed' : 'low-confidence'}`}>
                                    {(d.detection_confidence || 0) >= 0.7 ? 'Confirmed' : 'Low Confidence'}
                                </span>
                            </Link>
                        ))
                    )}
                </div>
            </div>
        </>
    );
}

/* ============================================================
   IMAGE BROWSER
   ============================================================ */
function ImageBrowser() {
    const [images, setImages] = useState<PaginatedResponse<ImageData> | null>(null);
    const [page, setPage] = useState(1);
    const [filterProcessed, setFilterProcessed] = useState('all');
    const [filterAnimal, setFilterAnimal] = useState('all');
    const [filterSpecies, setFilterSpecies] = useState('all');
    const [selectedImage, setSelectedImage] = useState<ImageData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const sortedItems = images
        ? [...images.items].sort((a, b) => a.filename.localeCompare(b.filename, undefined, { numeric: true, sensitivity: 'base' }))
        : [];

    useEffect(() => {
        setLoading(true);
        setError(null);
        const params: any = { page, per_page: 48 };
        if (filterProcessed !== 'all') params.processed = filterProcessed === 'yes';
        if (filterAnimal !== 'all') params.has_animal = filterAnimal === 'yes';
        const request = filterSpecies === 'quoll' ? fetchImagesBySpecies('quoll', params) : fetchImages(params);
        request.then(setImages).catch((e) => setError(e.message)).finally(() => setLoading(false));
    }, [page, filterProcessed, filterAnimal, filterSpecies]);

    const selectedIndex = selectedImage
        ? sortedItems.findIndex((img) => img.id === selectedImage.id)
        : -1;

    const showPrevImage = useCallback(() => {
        if (selectedIndex <= 0) return;
        setSelectedImage(sortedItems[selectedIndex - 1]);
    }, [selectedIndex, sortedItems]);

    const showNextImage = useCallback(() => {
        if (selectedIndex < 0 || selectedIndex >= sortedItems.length - 1) return;
        setSelectedImage(sortedItems[selectedIndex + 1]);
    }, [selectedIndex, sortedItems]);

    useEffect(() => {
        if (!selectedImage) return;
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'ArrowLeft') showPrevImage();
            if (e.key === 'ArrowRight') showNextImage();
            if (e.key === 'Escape') setSelectedImage(null);
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [selectedImage, showPrevImage, showNextImage]);

    return (
        <>
            <div className="page-header"><h2>Image Browser</h2><p>Browse and filter camera trap images</p></div>
            <div className="filters-bar">
                <select className="filter-select" value={filterProcessed} onChange={(e) => { setFilterProcessed(e.target.value); setPage(1); }}>
                    <option value="all">All Images</option><option value="yes">Processed</option><option value="no">Unprocessed</option>
                </select>
                <select className="filter-select" value={filterAnimal} onChange={(e) => { setFilterAnimal(e.target.value); setPage(1); }}>
                    <option value="all">All Results</option><option value="yes">Has Animal</option><option value="no">Empty</option>
                </select>
                <select className="filter-select" value={filterSpecies} onChange={(e) => { setFilterSpecies(e.target.value); setPage(1); }}>
                    <option value="all">All Species</option><option value="quoll">Quoll Only</option>
                </select>
                {images && <span className="tag tag-muted">{fmt(images.total)} images</span>}
            </div>
            {loading ? <LoadingState /> : error ? <ErrorState message={error} /> : !images || images.items.length === 0 ? (
                <div className="empty-state"><div className="icon">📷</div><h3>No images found</h3></div>
            ) : (
                <>
                    <div className="image-grid">
                        {sortedItems.map((img) => (
                            <div key={img.id} className="image-card" onClick={() => setSelectedImage(img)} style={{ cursor: 'pointer' }}>
                                <div className="image-thumb">
                                    {(img.thumbnail_path || img.file_path) ? <img src={storageUrl(img.thumbnail_path || img.file_path)} alt={img.filename} /> : '📷'}
                                    {img.has_animal && <div style={{ position: 'absolute', top: 8, right: 8, background: 'rgba(16,185,129,0.9)', borderRadius: '6px', padding: '2px 6px', fontSize: '0.65rem', fontWeight: 700, color: 'white' }}>ANIMAL</div>}
                                </div>
                                <div className="image-info">
                                    <div className="image-filename">{img.filename}</div>
                                    <div className="image-meta">
                                        {img.processed ? <span className="tag tag-primary">Processed</span> : <span className="tag tag-muted">Pending</span>}
                                        {img.camera_id && <span className="tag tag-info">Cam {img.camera_id}</span>}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                    {images.pages > 1 && (
                        <div className="pagination">
                            <button className="page-btn" onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1}>Prev</button>
                            <span className="page-info">Page {page} of {images.pages}</span>
                            <button className="page-btn" onClick={() => setPage(Math.min(images.pages, page + 1))} disabled={page === images.pages}>Next</button>
                        </div>
                    )}
                </>
            )}
            {selectedImage && (
                <div onClick={() => setSelectedImage(null)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'grid', placeItems: 'center', zIndex: 1000, padding: '1rem' }}>
                    <div className="card" onClick={(e) => e.stopPropagation()} style={{ width: 'min(900px, 100%)', maxHeight: '90vh', overflow: 'auto' }}>
                        <div className="card-header" style={{ justifyContent: 'space-between' }}>
                            <h3>{selectedImage.filename}</h3>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button className="btn btn-outline" onClick={showPrevImage} disabled={selectedIndex <= 0}>← Prev</button>
                                <button className="btn btn-outline" onClick={showNextImage} disabled={selectedIndex >= sortedItems.length - 1}>Next →</button>
                                <button className="btn btn-outline" onClick={() => setSelectedImage(null)}>Close</button>
                            </div>
                        </div>
                        <div className="card-body">
                            <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
                                <img
                                    src={storageUrl(selectedImage.file_path)}
                                    alt={selectedImage.filename}
                                    style={{ maxWidth: '100%', maxHeight: '70vh', borderRadius: 8 }}
                                />
                            </div>
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: '0.75rem' }}>
                                Use keyboard: Left/Right arrows to navigate, Esc to close
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                <span className="tag tag-muted">Image #{selectedImage.id}</span>
                                {selectedImage.processed ? <span className="tag tag-primary">Processed</span> : <span className="tag tag-muted">Pending</span>}
                                {selectedImage.has_animal === true && <span className="tag tag-info">Has Animal</span>}
                                {selectedImage.has_animal === false && <span className="tag tag-muted">Empty</span>}
                                {selectedImage.camera_id && <span className="tag tag-info">Cam {selectedImage.camera_id}</span>}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}

/* ============================================================
   DETECTION VIEWER
   ============================================================ */
function DetectionViewer() {
    const [species, setSpecies] = useState<SpeciesCount[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => { fetchSpeciesCounts().then(setSpecies).catch((e) => setError(e.message)).finally(() => setLoading(false)); }, []);
    if (loading) return <LoadingState />;
    if (error) return <ErrorState message={error} />;
    const total = species.reduce((s, x) => s + x.count, 0);

    return (
        <>
            <div className="page-header"><h2>Detections</h2><p>Species classification results from MegaDetector + AWC135</p></div>
            {species.length === 0 ? <div className="empty-state"><div className="icon">🔍</div><h3>No detections yet</h3></div> : (
                <>
                    <div className="stats-grid" style={{ marginBottom: '2rem' }}>
                        <StatCard icon="🔍" value={fmt(total)} label="Total Detections" />
                        <StatCard icon="🏷️" value={fmt(species.length)} label="Species Found" />
                        <StatCard icon="🐾" value={fmt(species.find((s) => s.species.toLowerCase().includes('quoll'))?.count || 0)} label="Quoll Detections" />
                    </div>
                    <div className="card">
                        <div className="card-header"><h3>Species Distribution</h3></div>
                        <div className="card-body">
                            {species.map((s) => {
                                const pct = total > 0 ? (s.count / total) * 100 : 0;
                                const isQ = s.species.toLowerCase().includes('quoll');
                                return (
                                    <div key={s.species} style={{ marginBottom: '1rem' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                                            <span style={{ fontWeight: isQ ? 700 : 500, color: isQ ? 'var(--accent)' : 'var(--text-primary)' }}>{isQ && '🐾 '}{s.species}</span>
                                            <span style={{ color: 'var(--text-muted)' }}>{fmt(s.count)} ({pct.toFixed(1)}%)</span>
                                        </div>
                                        <div className="progress-bar-bg"><div className="progress-bar-fill" style={{ width: `${pct}%`, background: isQ ? 'linear-gradient(90deg,var(--accent),var(--accent-dark))' : undefined }} /></div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </>
            )}
        </>
    );
}

/* ============================================================
   INDIVIDUAL QUOLLS
   ============================================================ */
function Individuals() {
    const [individuals, setIndividuals] = useState<IndividualData[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => { fetchIndividuals().then(setIndividuals).catch((e) => setError(e.message)).finally(() => setLoading(false)); }, []);
    if (loading) return <LoadingState />;
    if (error) return <ErrorState message={error} />;

    return (
        <>
            <div className="page-header"><h2>Quoll Profiles</h2><p>Known individual Spotted-tailed Quolls</p></div>
            {individuals.length === 0 ? <div className="empty-state"><div className="icon">🐾</div><h3>No individuals imported yet</h3></div> : (
                <>
                    <div className="stats-grid" style={{ marginBottom: '2rem' }}>
                        <StatCard icon="🐾" value={fmt(individuals.length)} label="Known Individuals" />
                        <StatCard icon="👁️" value={fmt(individuals.reduce((s, i) => s + i.total_sightings, 0))} label="Total Sightings" />
                    </div>
                    <div className="quoll-grid">
                        {individuals.map((ind) => (
                            <div key={ind.individual_id} className="quoll-card">
                                <div className="quoll-id">🐾 {ind.individual_id}</div>
                                <div className="quoll-species">{ind.species}</div>
                                <div className="quoll-stats">
                                    <div className="quoll-stat"><div className="label">Sightings</div><div className="value">{ind.total_sightings}</div></div>
                                    <div className="quoll-stat"><div className="label">First Seen</div><div className="value">{ind.first_seen ? new Date(ind.first_seen).toLocaleDateString() : '—'}</div></div>
                                    <div className="quoll-stat"><div className="label">Last Seen</div><div className="value">{ind.last_seen ? new Date(ind.last_seen).toLocaleDateString() : '—'}</div></div>
                                    <div className="quoll-stat"><div className="label">Active</div><div className="value">{ind.first_seen && ind.last_seen ? `${Math.ceil((new Date(ind.last_seen).getTime() - new Date(ind.first_seen).getTime()) / 86400000)}d` : '—'}</div></div>
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </>
    );
}

/* ============================================================
   BATCH UPLOAD
   ============================================================ */
function parseFolderStructure(files: File[]) {
    const cameras = new Map<string, number>();
    let collectionName = '';
    for (const f of files) {
        const relPath = (f as any).webkitRelativePath || '';
        const parts = relPath.split('/').filter(Boolean);
        if (parts.length >= 2 && !collectionName) collectionName = parts[0];
        if (parts.length >= 3) {
            const cam = parts[1];
            cameras.set(cam, (cameras.get(cam) || 0) + 1);
        }
    }
    return { collectionName, cameras };
}

function BatchUpload() {
    const [job, setJob] = useState<JobStatus | null>(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [dragOver, setDragOver] = useState(false);
    const [collectionName, setCollectionName] = useState('');
    const folderRef = useRef<HTMLInputElement>(null);

    const folderInfo = selectedFiles.length > 0 ? parseFolderStructure(selectedFiles) : null;

    useEffect(() => {
        if (folderInfo?.collectionName && !collectionName) setCollectionName(folderInfo.collectionName);
    }, [folderInfo?.collectionName]);

    const addFiles = (files: FileList | File[]) => {
        const arr = Array.from(files).filter((f) => /\.(jpe?g|png)$/i.test(f.name));
        setSelectedFiles(arr);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(false);
        if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
    };

    const handleUpload = async () => {
        if (selectedFiles.length === 0) return;
        setUploading(true);
        setError(null);
        try {
            const res = await uploadBatch(selectedFiles, collectionName || undefined);
            pollJob(res.job_id);
        } catch (e: any) {
            const msg = e?.message?.includes('fetch')
                ? 'Upload connection dropped. Try smaller batches or retry.'
                : e.message;
            setError(msg);
            setUploading(false);
        }
    };

    const pollJob = useCallback(async (jobId: number) => {
        try {
            const s = await fetchJobStatus(jobId);
            setJob(s);
            setUploading(false);
            if (s.status === 'queued' || s.status === 'processing') {
                setTimeout(() => pollJob(jobId), 2000);
            }
        } catch {
            setUploading(false);
        }
    }, []);

    return (
        <>
            <div className="page-header"><h2>Upload Images</h2><p>Select a collection folder containing camera trap subfolders.</p></div>

            <div
                className={`dropzone ${dragOver ? 'dragover' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => folderRef.current?.click()}
            >
                <input
                    ref={folderRef}
                    type="file"
                    multiple
                    accept=".jpg,.jpeg,.png"
                    style={{ display: 'none' }}
                    {...({ webkitdirectory: '', directory: '' } as any)}
                    onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = ''; }}
                />
                <div className="dropzone-icon">
                    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
                    </svg>
                </div>
                <p className="dropzone-text">Drop folder here or click to browse</p>
                <p className="dropzone-hint">Select the collection folder (e.g. MortonNP_June2025/) containing camera subfolders</p>
                <div className="dropzone-buttons">
                    <button type="button" className="btn btn-primary" onClick={(e) => { e.stopPropagation(); folderRef.current?.click(); }}>Choose Folder</button>
                </div>
            </div>

            {/* Folder summary: collection + cameras detected */}
            {folderInfo && selectedFiles.length > 0 && !job && (
                <div className="upload-summary card">
                    <div className="card-header"><h3>Folder Summary</h3></div>
                    <div className="card-body">
                        <div className="upload-summary-field">
                            <label>Collection Name</label>
                            <input className="filter-select" style={{ width: '100%' }} value={collectionName} onChange={(e) => setCollectionName(e.target.value)} placeholder="e.g. MortonNP_June2025" />
                        </div>
                        <div className="upload-summary-stats">
                            <div className="upload-summary-stat">
                                <span className="num">{selectedFiles.length}</span>
                                <span className="label">Total Images</span>
                            </div>
                            <div className="upload-summary-stat">
                                <span className="num">{folderInfo.cameras.size}</span>
                                <span className="label">Camera Traps Detected</span>
                            </div>
                        </div>
                        {folderInfo.cameras.size > 0 && (
                            <div className="upload-camera-list">
                                <h4>Cameras</h4>
                                <div className="upload-camera-grid">
                                    {Array.from(folderInfo.cameras.entries()).sort(([a], [b]) => a.localeCompare(b, undefined, { numeric: true })).map(([cam, count]) => (
                                        <div key={cam} className="upload-camera-chip">
                                            <span className="cam-name">{cam}</span>
                                            <span className="cam-count">{count} images</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        {folderInfo.cameras.size === 0 && (
                            <p style={{ color: 'var(--warning)', fontSize: '0.85rem', marginTop: '0.75rem' }}>
                                No camera subfolders detected. Images will be uploaded without camera assignment. Expected structure: Collection/CameraName/image.jpg
                            </p>
                        )}
                        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.25rem' }}>
                            <button className="btn btn-primary" onClick={handleUpload} disabled={uploading}>{uploading ? 'Uploading...' : `Upload & Process (${selectedFiles.length} images)`}</button>
                            <button className="btn btn-outline" onClick={() => { setSelectedFiles([]); setCollectionName(''); }}>Clear</button>
                        </div>
                        {error && <p style={{ color: 'var(--danger)', marginTop: '0.5rem', fontSize: '0.85rem' }}>{error}</p>}
                    </div>
                </div>
            )}

            {/* Batch processing progress */}
            {job && (
                <div className="upload-batch-progress card">
                    <div className="card-header">
                        <h3>Batch Processing — {job.batch_name || `Job #${job.id}`}</h3>
                        <span className={`tag ${job.status === 'completed' ? 'tag-primary' : job.status === 'failed' ? 'tag-danger' : 'tag-accent'}`}>{job.status}</span>
                    </div>
                    <div className="card-body">
                        <div className="progress-bar-bg"><div className="progress-bar-fill" style={{ width: `${job.percent}%` }} /></div>
                        <div className="progress-label"><span>{job.processed_images} / {job.total_images} processed</span><span>{job.percent.toFixed(1)}%</span></div>
                        {job.failed_images > 0 && <p style={{ color: 'var(--danger)', marginTop: '0.5rem', fontSize: '0.85rem' }}>{job.failed_images} failed</p>}
                        {job.status === 'failed' && job.error_message && <p style={{ color: 'var(--danger)', marginTop: '0.5rem', fontSize: '0.85rem' }}>{job.error_message}</p>}
                        {job.status === 'completed' && <p style={{ color: 'var(--success)', marginTop: '0.5rem', fontSize: '0.85rem' }}>All images processed successfully.</p>}
                    </div>
                </div>
            )}
        </>
    );
}

/* ============================================================
   REPORTS
   ============================================================ */
function Reports() {
    const [report, setReport] = useState<ReportData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => { fetchReport().then(setReport).catch((e) => setError(e.message)).finally(() => setLoading(false)); }, []);
    if (loading) return <LoadingState />;
    if (error) return <ErrorState message={error} />;
    if (!report) return null;

    const downloadFile = async (url: string, filename: string) => {
        try {
            const res = await fetch(url);
            if (!res.ok) throw new Error(`Download failed (${res.status})`);
            const blob = await res.blob();
            const objectUrl = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = objectUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(objectUrl);
        } catch (e: any) {
            setError(e.message || 'Download failed');
        }
    };

    return (
        <>
            <div className="page-header"><h2>Reports</h2><p>Batch processing results and data visualizations</p></div>
            <div className="stats-grid">
                <StatCard icon="📷" value={fmt(report.total_images)} label="Total Images" />
                <StatCard icon="✅" value={fmt(report.processed_images)} label="Processed" />
                <StatCard icon="🔲" value={fmt(report.empty_images)} label="Empty" />
                <StatCard icon="🔍" value={fmt(report.total_detections)} label="Detections" />
                <StatCard icon="🏷️" value={fmt(report.total_species)} label="Species" />
                <StatCard icon="🐾" value={fmt(report.quoll_detections)} label="Quolls" />
            </div>

            {report.mean_detection_confidence != null && (
                <div className="card" style={{ marginBottom: '1.5rem' }}>
                    <div className="card-header"><h3>Confidence Statistics</h3></div>
                    <div className="card-body" style={{ display: 'flex', gap: '2rem' }}>
                        <div>Detection avg: <strong>{report.mean_detection_confidence.toFixed(3)}</strong></div>
                        <div>Classification avg: <strong>{(report.mean_classification_confidence ?? 0).toFixed(3)}</strong></div>
                    </div>
                </div>
            )}

            <div className="chart-grid">
                {report.species_distribution.length > 0 && (
                    <div className="card">
                        <div className="card-header"><h3>Species Distribution</h3></div>
                        <div className="card-body" style={{ height: 300 }}>
                            <ResponsiveContainer>
                                <PieChart>
                                    <Pie data={report.species_distribution} dataKey="count" nameKey="species" cx="50%" cy="50%" outerRadius={100} label={({ species, percent }) => `${species.split('|').pop()?.trim()} ${(percent * 100).toFixed(0)}%`}>
                                        {report.species_distribution.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                                    </Pie>
                                    <Tooltip />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}
                {report.hourly_activity.length > 0 && (
                    <div className="card">
                        <div className="card-header"><h3>Hourly Activity</h3></div>
                        <div className="card-body" style={{ height: 300 }}>
                            <ResponsiveContainer>
                                <BarChart data={report.hourly_activity}>
                                    <XAxis dataKey="hour" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                                    <YAxis tick={{ fill: '#9ca3af', fontSize: 12 }} />
                                    <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid rgba(255,255,255,0.1)' }} />
                                    <Bar dataKey="detections" fill="#10b981" radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}
                {report.camera_counts.length > 0 && (
                    <div className="card">
                        <div className="card-header"><h3>Detections by Camera</h3></div>
                        <div className="card-body" style={{ height: 300 }}>
                            <ResponsiveContainer>
                                <BarChart data={report.camera_counts} layout="vertical">
                                    <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 12 }} />
                                    <YAxis dataKey="camera" type="category" tick={{ fill: '#9ca3af', fontSize: 11 }} width={50} />
                                    <Tooltip contentStyle={{ background: '#1f2937', border: '1px solid rgba(255,255,255,0.1)' }} />
                                    <Bar dataKey="detections" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                )}
            </div>

            <div className="card">
                <div className="card-header"><h3>Export</h3></div>
                <div className="card-body" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <button className="btn btn-outline" onClick={() => downloadFile(getExportUrl('csv'), 'wildlife_report.csv')}>Report CSV</button>
                    <button className="btn btn-outline" onClick={() => downloadFile(getExportUrl('json'), 'wildlife_report.json')}>Report JSON</button>
                    <button className="btn btn-primary" onClick={() => downloadFile(getQuollExportUrl('csv'), 'quoll_detections.csv')}>Quoll Detections CSV</button>
                    <button className="btn btn-outline" onClick={() => downloadFile(getMetadataExportUrl('csv'), 'full_metadata.csv')}>Full Metadata CSV</button>
                </div>
            </div>
        </>
    );
}

/* ============================================================
   IMAGE REVIEW (annotation workflow)
   ============================================================ */
function ImageReview() {
    const params = useParams();
    const id = parseInt(params.detectionId || '0');
    const [det, setDet] = useState<DetectionDetail | null>(null);
    const [anns, setAnns] = useState<AnnotationData[]>([]);
    const [form, setForm] = useState<{ is_correct: boolean; corrected_species: string; notes: string; individual_id: string; flag_for_retraining: boolean; bbox?: { x: number; y: number; w: number; h: number } }>({ is_correct: true, corrected_species: '', notes: '', individual_id: '', flag_for_retraining: false });
    const [saving, setSaving] = useState(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!id) return;
        Promise.all([fetchDetectionDetail(id), fetchAnnotations(id)])
            .then(([d, a]) => { setDet(d); setAnns(a); }).finally(() => setLoading(false));
    }, [id]);

    const submit = async () => {
        if (!det) return;
        setSaving(true);
        try {
            const notes = form.bbox ? JSON.stringify({ bbox: form.bbox, type: 'user_drawn' }) : form.notes;
            const ann = await createAnnotation({
                detection_id: det.id,
                is_correct: form.is_correct,
                corrected_species: form.corrected_species || undefined,
                notes: notes || undefined,
                individual_id: form.individual_id || undefined,
                flag_for_retraining: form.flag_for_retraining,
            });
            setAnns([ann, ...anns]);
            setForm({ is_correct: true, corrected_species: '', notes: '', individual_id: '', flag_for_retraining: false, bbox: undefined });
        } catch { }
        setSaving(false);
    };

    if (loading) return <LoadingState />;
    if (!det) return <div className="empty-state"><h3>Detection not found</h3></div>;

    return (
        <>
            <div className="page-header"><h2>Review Detection #{det.id}</h2><p>{det.image?.filename} — {det.species}</p></div>
            <div className="chart-grid">
                <div className="card">
                    <div className="card-header"><h3>Image</h3></div>
                    <div className="card-body" style={{ textAlign: 'center' }}>
                        {det.crop_path && <img src={storageUrl(det.crop_path)} alt="crop" style={{ maxWidth: '100%', borderRadius: 8 }} />}
                        <div style={{ marginTop: '1rem', fontSize: '0.85rem' }}>
                            <div><strong>Species:</strong> {det.species || 'Unknown'}</div>
                            <div><strong>Confidence:</strong> {det.classification_confidence?.toFixed(3)}</div>
                            <div><strong>Detection conf:</strong> {det.detection_confidence.toFixed(3)}</div>
                            <div><strong>Model:</strong> {det.model_version}</div>
                            <div><strong>Camera:</strong> {det.camera?.name || '—'}</div>
                            <div><strong>Timestamp:</strong> {det.image?.captured_at || '—'}</div>
                            <div><strong>Bbox:</strong> [{det.bbox_x.toFixed(3)}, {det.bbox_y.toFixed(3)}, {det.bbox_w.toFixed(3)}, {det.bbox_h.toFixed(3)}]</div>
                        </div>
                    </div>
                </div>
                <div className="card">
                    <div className="card-header"><h3>Annotate</h3></div>
                    <div className="card-body">
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ fontSize: '0.8rem', display: 'block', marginBottom: '0.25rem' }}>ML prediction correct?</label>
                            <select className="filter-select" value={String(form.is_correct)} onChange={(e) => setForm({ ...form, is_correct: e.target.value === 'true' })}>
                                <option value="true">Yes, correct</option><option value="false">No, incorrect</option>
                            </select>
                        </div>
                        {!form.is_correct && (
                            <div style={{ marginBottom: '1rem' }}>
                                <label style={{ fontSize: '0.8rem', display: 'block', marginBottom: '0.25rem' }}>Corrected species</label>
                                <input className="filter-select" style={{ width: '100%' }} value={form.corrected_species} onChange={(e) => setForm({ ...form, corrected_species: e.target.value })} placeholder="e.g. Trichosurus sp | Brushtail Possum sp" />
                            </div>
                        )}
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ fontSize: '0.8rem', display: 'block', marginBottom: '0.25rem' }}>Individual ID (e.g. 02Q2)</label>
                            <input className="filter-select" style={{ width: '100%' }} value={form.individual_id} onChange={(e) => setForm({ ...form, individual_id: e.target.value })} />
                        </div>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ fontSize: '0.8rem', display: 'block', marginBottom: '0.25rem' }}>Notes</label>
                            <textarea className="filter-select" style={{ width: '100%', minHeight: 60, resize: 'vertical' }} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
                        </div>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ fontSize: '0.8rem', cursor: 'pointer' }}>
                                <input type="checkbox" checked={form.flag_for_retraining} onChange={(e) => setForm({ ...form, flag_for_retraining: e.target.checked })} style={{ marginRight: '0.5rem' }} />
                                Flag for retraining dataset
                            </label>
                        </div>
                        {!form.is_correct && (
                            <div style={{ marginBottom: '1rem' }}>
                                <label style={{ fontSize: '0.8rem', display: 'block', marginBottom: '0.25rem' }}>Draw box around animal (feedback for model)</label>
                                {det.image?.file_path && (
                                    <BboxDrawer
                                        imageUrl={storageUrl(det.image.file_path)}
                                        onDraw={(bbox) => setForm((f) => ({ ...f, bbox }))}
                                    />
                                )}
                            </div>
                        )}
                        <button className="btn btn-primary" onClick={submit} disabled={saving}>{saving ? 'Saving...' : 'Save Annotation'}</button>

                        {anns.length > 0 && (
                            <div style={{ marginTop: '1.5rem' }}>
                                <h4 style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>Previous Annotations</h4>
                                {anns.map((a) => (
                                    <div key={a.id} style={{ background: 'var(--bg-primary)', borderRadius: 8, padding: '0.75rem', marginBottom: '0.5rem', fontSize: '0.8rem' }}>
                                        <div>{a.is_correct ? '✅ Correct' : '❌ Incorrect'}{a.corrected_species && ` → ${a.corrected_species}`}</div>
                                        {a.notes && <div style={{ color: 'var(--text-muted)' }}>{a.notes}</div>}
                                        <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>{a.annotator} — {a.created_at}</div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </>
    );
}

/* Draw bbox on image for annotation / missed-detection feedback */
function BboxDrawer({ imageUrl, onDraw }: { imageUrl: string; onDraw: (bbox: { x: number; y: number; w: number; h: number }) => void }) {
    const imgRef = useRef<HTMLImageElement>(null);
    const drawingRef = useRef(false);
    const startRef = useRef<{ x: number; y: number } | null>(null);
    const [liveBox, setLiveBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
    const [savedBox, setSavedBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);

    const toRelative = useCallback((clientX: number, clientY: number) => {
        const img = imgRef.current;
        if (!img) return { x: 0, y: 0 };
        const rect = img.getBoundingClientRect();
        return {
            x: Math.max(0, Math.min(1, (clientX - rect.left) / rect.width)),
            y: Math.max(0, Math.min(1, (clientY - rect.top) / rect.height)),
        };
    }, []);

    const handlePointerDown = useCallback((e: React.PointerEvent) => {
        e.preventDefault();
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
        const pt = toRelative(e.clientX, e.clientY);
        startRef.current = pt;
        drawingRef.current = true;
        setLiveBox({ x: pt.x, y: pt.y, w: 0, h: 0 });
        setSavedBox(null);
    }, [toRelative]);

    const handlePointerMove = useCallback((e: React.PointerEvent) => {
        if (!drawingRef.current || !startRef.current) return;
        const pt = toRelative(e.clientX, e.clientY);
        const s = startRef.current;
        setLiveBox({
            x: Math.min(s.x, pt.x),
            y: Math.min(s.y, pt.y),
            w: Math.abs(pt.x - s.x),
            h: Math.abs(pt.y - s.y),
        });
    }, [toRelative]);

    const handlePointerUp = useCallback((e: React.PointerEvent) => {
        if (!drawingRef.current || !startRef.current) return;
        drawingRef.current = false;
        const pt = toRelative(e.clientX, e.clientY);
        const s = startRef.current;
        const box = {
            x: Math.min(s.x, pt.x),
            y: Math.min(s.y, pt.y),
            w: Math.max(Math.abs(pt.x - s.x), 0.02),
            h: Math.max(Math.abs(pt.y - s.y), 0.02),
        };
        startRef.current = null;
        setLiveBox(null);
        setSavedBox(box);
        onDraw(box);
    }, [toRelative, onDraw]);

    const box = liveBox || savedBox;

    return (
        <div style={{ userSelect: 'none' }}>
            <div
                style={{ position: 'relative', display: 'inline-block', cursor: 'crosshair', maxWidth: '100%', touchAction: 'none' }}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
            >
                <img ref={imgRef} src={imageUrl} alt="Draw box" draggable={false} style={{ maxWidth: '100%', height: 'auto', display: 'block', borderRadius: 8 }} />
                {box && box.w > 0.005 && box.h > 0.005 && (
                    <div
                        style={{
                            position: 'absolute',
                            left: `${box.x * 100}%`,
                            top: `${box.y * 100}%`,
                            width: `${box.w * 100}%`,
                            height: `${box.h * 100}%`,
                            border: '3px solid #10b981',
                            background: 'rgba(16, 185, 129, 0.15)',
                            borderRadius: 4,
                            pointerEvents: 'none',
                        }}
                    />
                )}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 6 }}>
                {savedBox ? '✓ Box drawn — drag again to redraw' : 'Click and drag on the image to draw a box around the animal'}
            </div>
        </div>
    );
}

/* ============================================================
   REVIEW IMAGE — step-based review from any image context
   Step 1: What action?  (Confirm empty / Has animal)
   Step 2 (if has animal): Species? → Draw bbox → Save
   ============================================================ */
function ReviewImage() {
    const { imageId } = useParams();
    const id = parseInt(imageId || '0');
    const [image, setImage] = useState<ImageData | null>(null);
    const [loading, setLoading] = useState(true);
    const [step, setStep] = useState<'choose' | 'annotate' | 'done'>('choose');
    const [bbox, setBbox] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
    const [species, setSpecies] = useState('Spotted-tailed Quoll');
    const [individualId, setIndividualId] = useState('');
    const [notes, setNotes] = useState('');
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (!id) return;
        fetchImageDetail(id).then((data: any) => setImage(data)).catch(() => {}).finally(() => setLoading(false));
    }, [id]);

    const confirmEmpty = async () => {
        if (!image) return;
        setSaving(true);
        try {
            await createMissedDetection(image.id, { bbox_x: 0, bbox_y: 0, bbox_w: 0, bbox_h: 0, species: '__confirmed_empty__', flag_for_retraining: false });
            setStep('done');
        } catch { }
        setSaving(false);
    };

    const submitAnimal = async () => {
        if (!image || !bbox) return;
        setSaving(true);
        try {
            await createMissedDetection(image.id, { bbox_x: bbox.x, bbox_y: bbox.y, bbox_w: bbox.w, bbox_h: bbox.h, species, flag_for_retraining: true });
            setStep('done');
        } catch { }
        setSaving(false);
    };

    if (loading) return <LoadingState />;
    if (!image) return <div className="empty-state"><h3>Image not found</h3></div>;

    if (step === 'done') return (
        <div className="review-done">
            <div className="review-done-icon">✓</div>
            <h2>Review saved</h2>
            <p>Thank you — this feedback will help improve the model.</p>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', marginTop: '1rem' }}>
                <Link to="/pending-review" className="btn btn-primary">Back to Pending Review</Link>
                <button type="button" className="btn btn-outline" onClick={() => window.history.back()}>Go Back</button>
            </div>
        </div>
    );

    return (
        <div>
            <nav className="breadcrumb"><Link to="/">Home</Link><span className="sep">›</span><span>Review Image</span></nav>
            <div className="page-header"><h2>Review — {image.filename}</h2><p>Decide how to classify this image.</p></div>

            <div className="review-image-layout">
                <div className="review-image-left card">
                    <div className="card-body" style={{ textAlign: 'center' }}>
                        {step === 'choose' && <img src={storageUrl(image.file_path)} alt={image.filename} style={{ maxWidth: '100%', maxHeight: '65vh', borderRadius: 8 }} />}
                        {step === 'annotate' && (
                            <BboxDrawer imageUrl={storageUrl(image.file_path)} onDraw={setBbox} />
                        )}
                    </div>
                    <div className="card-body" style={{ paddingTop: 0, display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                        <span className="tag tag-muted">Image #{image.id}</span>
                        {image.processed ? <span className="tag tag-primary">Processed</span> : <span className="tag tag-muted">Pending</span>}
                        {image.has_animal === true && <span className="tag tag-info">Has Animal</span>}
                        {image.has_animal === false && <span className="tag tag-muted">Marked Empty</span>}
                        {image.camera_id && <span className="tag tag-info">Cam {image.camera_id}</span>}
                    </div>
                </div>

                <div className="review-image-right">
                    {step === 'choose' && (
                        <div className="card">
                            <div className="card-header"><h3>What do you see?</h3></div>
                            <div className="card-body review-action-choices">
                                <button type="button" className="review-action-btn empty" onClick={confirmEmpty} disabled={saving}>
                                    <span className="review-action-icon">⬜</span>
                                    <span>Image is empty</span>
                                    <span className="review-action-hint">Confirm no animal present</span>
                                </button>
                                <button type="button" className="review-action-btn has-animal" onClick={() => setStep('annotate')}>
                                    <span className="review-action-icon">🐾</span>
                                    <span>Has animal</span>
                                    <span className="review-action-hint">Draw a box around the animal</span>
                                </button>
                            </div>
                        </div>
                    )}

                    {step === 'annotate' && (
                        <div className="card">
                            <div className="card-header"><h3>Annotate Animal</h3></div>
                            <div className="card-body">
                                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>Draw a box around the animal on the image, then fill in the details below.</p>
                                {bbox && <div className="tag tag-primary" style={{ marginBottom: '1rem' }}>Box drawn ✓</div>}
                                <div className="review-field">
                                    <label>Species</label>
                                    <select className="filter-select" value={species} onChange={(e) => setSpecies(e.target.value)}>
                                        <option>Spotted-tailed Quoll</option>
                                        <option>Quoll (unknown sp)</option>
                                        <option>Red Kangaroo</option>
                                        <option>Common Wombat</option>
                                        <option>Short-beaked Echidna</option>
                                        <option>Tasmanian Devil</option>
                                        <option>Bennett's Wallaby</option>
                                        <option>Common Brushtail Possum</option>
                                        <option>Unknown</option>
                                        <option>Other</option>
                                    </select>
                                </div>
                                <div className="review-field">
                                    <label>Individual ID (optional, e.g. 02Q2)</label>
                                    <input className="filter-select" style={{ width: '100%' }} value={individualId} onChange={(e) => setIndividualId(e.target.value)} placeholder="Leave blank if unknown" />
                                </div>
                                <div className="review-field">
                                    <label>Notes (optional)</label>
                                    <textarea className="filter-select" style={{ width: '100%', minHeight: 50, resize: 'vertical' }} value={notes} onChange={(e) => setNotes(e.target.value)} />
                                </div>
                                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                                    <button className="btn btn-primary" onClick={submitAnimal} disabled={!bbox || saving}>{saving ? 'Saving...' : 'Save Annotation'}</button>
                                    <button className="btn btn-outline" onClick={() => setStep('choose')}>Back</button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function ReviewEmptyImage() {
    const { imageId } = useParams();
    return <Navigate to={`/review-image/${imageId}`} replace />;
}

/* ============================================================
   PROFILES — Species & Individuals Explorer (hierarchy)
   ============================================================ */
function SpeciesExplorer() {
    const [species, setSpecies] = useState<SpeciesCount[]>([]);
    const [individuals, setIndividuals] = useState<IndividualData[]>([]);
    const [thumbs, setThumbs] = useState<Record<string, string>>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [view, setView] = useState<'grid' | 'list'>('grid');
    const [search, setSearch] = useState('');

    useEffect(() => {
        Promise.all([fetchSpeciesCounts(), fetchIndividuals()]).then(([s, i]) => { setSpecies(s); setIndividuals(i); }).catch((e) => setError(e.message)).finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        if (species.length === 0) return;
        const pending: Record<string, string> = {};
        Promise.all(
            species.map((s) =>
                fetchImagesBySpecies(s.species, { per_page: 1 })
                    .then((res) => {
                        const img = res.items[0];
                        if (img) pending[s.species] = storageUrl(img.thumbnail_path || img.file_path);
                    })
                    .catch(() => {})
            )
        ).then(() => setThumbs(pending));
    }, [species]);

    const slug = (name: string) => encodeURIComponent(name.toLowerCase().replace(/\s+/g, '-'));
    const bySpecies = species.map((s) => {
        const inds = individuals.filter((i) => i.species.toLowerCase().includes(s.species.toLowerCase()) || s.species.toLowerCase().includes(i.species.toLowerCase()));
        return { ...s, individuals: inds.length, individualList: inds };
    }).filter((s) => !search || s.species.toLowerCase().includes(search.toLowerCase()));

    if (loading) return <LoadingState />;
    if (error) return <ErrorState message={error} />;

    return (
        <div className="species-explorer-page">
            <nav className="breadcrumb"><Link to="/">Home</Link><span className="sep">›</span><span className="active">Profiles</span><span className="sep">›</span><span>Species Overview</span></nav>
            <div className="page-header">
                <h1 className="species-explorer-title">Species & Individuals Explorer</h1>
                <p className="species-explorer-subtitle">Explore and manage all species and individual animals recorded in the system.</p>
            </div>
            <div className="species-toolbar">
                <input type="search" className="review-search" placeholder="Search species..." value={search} onChange={(e) => setSearch(e.target.value)} />
                <select className="filter-select"><option>Sort by: Alphabetical</option></select>
                <div className="view-toggle">
                    <button type="button" className={view === 'grid' ? 'active' : ''} onClick={() => setView('grid')} aria-label="Grid">▦</button>
                    <button type="button" className={view === 'list' ? 'active' : ''} onClick={() => setView('list')} aria-label="List">≡</button>
                </div>
            </div>
            <div className={view === 'grid' ? 'species-card-grid' : 'species-list'}>
                {bySpecies.map((s) => (
                    <Link key={s.species} to={`/individuals/species/${slug(s.species)}`} className="species-card card">
                        <div className="species-card-image">
                            {thumbs[s.species] ? <img src={thumbs[s.species]} alt={s.species} style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : '🐾'}
                        </div>
                        <span className="species-card-status">Common</span>
                        <div className="species-card-name">{s.species}</div>
                        <div className="species-card-scientific">{s.species}</div>
                        <div className="species-card-stats">🐾 {s.individuals} individuals · 👁 {fmt(s.count)} obs.</div>
                    </Link>
                ))}
            </div>
            <div className="system-overview">
                <div className="system-overview-stat"><span className="num green">{species.length}</span> Total Species</div>
                <div className="system-overview-stat"><span className="num blue">{individuals.length}</span> Individual Animals</div>
                <div className="system-overview-stat"><span className="num orange">{fmt(species.reduce((a, b) => a + b.count, 0))}</span> Total Observations</div>
            </div>
        </div>
    );
}

function SpeciesDetail() {
    const { speciesKey } = useParams();
    const decoded = speciesKey ? decodeURIComponent(speciesKey).replace(/-/g, ' ') : '';
    const isQuoll = /quoll/i.test(decoded);

    return (
        <div>
            <nav className="breadcrumb"><Link to="/">Home</Link><span className="sep">›</span><Link to="/individuals">Profiles</Link><span className="sep">›</span><span>Species: {decoded}</span></nav>
            <div className="page-header">
                <h2>{decoded}</h2>
                <p>View images or browse by individual.</p>
            </div>
            <div className="species-choice-cards">
                <Link to={`/individuals/species/${speciesKey}/images`} className="card species-choice-card">
                    <h3>View all images</h3>
                    <p>All images containing this species</p>
                </Link>
                {isQuoll && (
                    <Link to={`/individuals/species/${speciesKey}/individuals`} className="card species-choice-card">
                        <h3>View by individual (ID)</h3>
                        <p>Browse quoll folders by individual ID</p>
                    </Link>
                )}
            </div>
        </div>
    );
}

function SpeciesImages() {
    const { speciesKey } = useParams();
    const decoded = speciesKey ? decodeURIComponent(speciesKey).replace(/-/g, ' ') : '';
    const [images, setImages] = useState<PaginatedResponse<ImageData> | null>(null);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [selected, setSelected] = useState<ImageData | null>(null);
    const [detections, setDetections] = useState<Detection[]>([]);
    const [showBoxes, setShowBoxes] = useState(true);

    useEffect(() => {
        if (!decoded) return;
        setLoading(true);
        fetchImagesBySpecies(decoded, { page, per_page: 30 }).then(setImages).catch(() => {}).finally(() => setLoading(false));
    }, [decoded, page]);

    useEffect(() => {
        if (!selected) { setDetections([]); return; }
        fetchImageDetail(selected.id).then((detail: any) => {
            setDetections(detail.detections || []);
        }).catch(() => setDetections([]));
    }, [selected?.id]);

    const sortedItems = images ? [...images.items].sort((a, b) => a.filename.localeCompare(b.filename, undefined, { numeric: true, sensitivity: 'base' })) : [];
    const selectedIdx = selected ? sortedItems.findIndex((i) => i.id === selected.id) : -1;
    const goPrev = () => { if (selectedIdx > 0) setSelected(sortedItems[selectedIdx - 1]); };
    const goNext = () => { if (selectedIdx >= 0 && selectedIdx < sortedItems.length - 1) setSelected(sortedItems[selectedIdx + 1]); };

    useEffect(() => {
        if (!selected) return;
        const onKey = (e: KeyboardEvent) => { if (e.key === 'ArrowLeft') goPrev(); if (e.key === 'ArrowRight') goNext(); if (e.key === 'Escape') setSelected(null); };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    });

    if (loading) return <LoadingState />;
    return (
        <div>
            <nav className="breadcrumb"><Link to="/">Home</Link><span className="sep">›</span><Link to="/individuals">Profiles</Link><span className="sep">›</span><Link to={`/individuals/species/${speciesKey}`}>{decoded}</Link><span className="sep">›</span><span>Images</span></nav>
            <div className="page-header"><h2>All images — {decoded}</h2><span className="tag tag-muted" style={{ marginLeft: '0.5rem' }}>{images?.total ?? 0} images</span></div>
            {!images || images.items.length === 0 ? <div className="empty-state">No images for this species.</div> : (
                <>
                    <div className="image-grid">
                        {sortedItems.map((img) => (
                            <div key={img.id} className="image-card" onClick={() => setSelected(img)} style={{ cursor: 'pointer' }}>
                                <div className="image-thumb">
                                    {(img.thumbnail_path || img.file_path) ? <img src={storageUrl(img.thumbnail_path || img.file_path)} alt={img.filename} /> : '📷'}
                                    {img.has_animal && <div className="image-animal-badge">ANIMAL</div>}
                                </div>
                                <div className="image-info">
                                    <div className="image-filename">{img.filename}</div>
                                    <div className="image-meta">
                                        {img.processed ? <span className="tag tag-primary">Processed</span> : <span className="tag tag-muted">Pending</span>}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                    {images.pages > 1 && <div className="pagination"><button className="page-btn" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>Prev</button><span className="page-info">Page {page} of {images.pages}</span><button className="page-btn" onClick={() => setPage((p) => Math.min(images.pages, p + 1))} disabled={page === images.pages}>Next</button></div>}
                </>
            )}
            {selected && (
                <div className="lightbox-overlay" onClick={() => setSelected(null)}>
                    <div className="lightbox-content card" onClick={(e) => e.stopPropagation()}>
                        <div className="card-header" style={{ justifyContent: 'space-between' }}>
                            <h3>{selected.filename}</h3>
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                <label style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.3rem', cursor: 'pointer' }}>
                                    <input type="checkbox" checked={showBoxes} onChange={(e) => setShowBoxes(e.target.checked)} /> Boxes
                                </label>
                                <button className="btn btn-outline" onClick={goPrev} disabled={selectedIdx <= 0}>← Prev</button>
                                <button className="btn btn-outline" onClick={goNext} disabled={selectedIdx >= sortedItems.length - 1}>Next →</button>
                                <button className="btn btn-outline" onClick={() => setSelected(null)}>Close</button>
                            </div>
                        </div>
                        <div className="card-body">
                            <div style={{ position: 'relative', display: 'inline-block', marginBottom: '1rem', width: '100%', textAlign: 'center' }}>
                                <img src={storageUrl(selected.file_path)} alt={selected.filename} style={{ maxWidth: '100%', maxHeight: '65vh', borderRadius: 8, display: 'block', margin: '0 auto' }}
                                    onLoad={(e) => {
                                        const img = e.currentTarget;
                                        const wrapper = img.parentElement;
                                        if (wrapper) {
                                            wrapper.style.width = img.offsetWidth + 'px';
                                            wrapper.style.margin = '0 auto';
                                        }
                                    }}
                                />
                                {showBoxes && detections.map((det) => (
                                    <div key={det.id} className="detection-bbox-overlay" style={{
                                        position: 'absolute',
                                        left: `${det.bbox_x * 100}%`,
                                        top: `${det.bbox_y * 100}%`,
                                        width: `${det.bbox_w * 100}%`,
                                        height: `${det.bbox_h * 100}%`,
                                        border: '2px solid #00ff88',
                                        borderRadius: 3,
                                        pointerEvents: 'none',
                                    }}>
                                        <span className="detection-bbox-label" style={{
                                            position: 'absolute',
                                            top: -22,
                                            left: -2,
                                            background: 'rgba(0,255,136,0.85)',
                                            color: '#000',
                                            fontSize: '0.65rem',
                                            fontWeight: 700,
                                            padding: '1px 5px',
                                            borderRadius: '3px 3px 0 0',
                                            whiteSpace: 'nowrap',
                                            lineHeight: '18px',
                                        }}>
                                            {det.species || det.category || 'animal'} — AWC135: {det.classification_confidence != null ? (det.classification_confidence * 100).toFixed(1) + '%' : 'N/A'}
                                        </span>
                                    </div>
                                ))}
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
                                <span className="tag tag-muted">Image #{selected.id}</span>
                                {selected.processed ? <span className="tag tag-primary">Processed</span> : <span className="tag tag-muted">Pending</span>}
                                {selected.has_animal === true && <span className="tag tag-info">Has Animal</span>}
                                {selected.has_animal === false && <span className="tag tag-muted">Empty</span>}
                                {selected.camera_id && <span className="tag tag-info">Cam {selected.camera_id}</span>}
                            </div>
                            {detections.length > 0 && (
                                <div style={{ marginBottom: '1rem' }}>
                                    <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.4rem' }}>Detections ({detections.length})</div>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                                        {detections.map((det) => (
                                            <span key={det.id} className="tag tag-primary" style={{ fontSize: '0.7rem' }}>
                                                {det.species || 'unknown'} — {det.classification_confidence != null ? (det.classification_confidence * 100).toFixed(1) + '%' : 'N/A'} conf
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <Link to={`/review-image/${selected.id}`} className="btn btn-primary">Review Image</Link>
                            </div>
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.75rem' }}>Use ←/→ to navigate, Esc to close</div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function SpeciesByIndividual() {
    const { speciesKey } = useParams();
    const decoded = speciesKey ? decodeURIComponent(speciesKey).replace(/-/g, ' ') : '';
    const [individuals, setIndividuals] = useState<IndividualData[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => { fetchIndividuals().then((list) => setIndividuals(list.filter((i) => i.species.toLowerCase().includes(decoded.toLowerCase())))).finally(() => setLoading(false)); }, [decoded]);

    if (loading) return <LoadingState />;
    return (
        <div>
            <nav className="breadcrumb"><Link to="/">Home</Link><span className="sep">›</span><Link to="/individuals">Profiles</Link><span className="sep">›</span><Link to={`/individuals/species/${speciesKey}`}>{decoded}</Link><span className="sep">›</span><span>By individual</span></nav>
            <div className="page-header"><h2>Individuals — {decoded}</h2></div>
            <div className="quoll-grid">
                {individuals.map((ind) => (
                    <Link key={ind.individual_id} to={`/individuals/species/${speciesKey}/individuals/${encodeURIComponent(ind.individual_id)}`} className="quoll-card">
                        <div className="quoll-id">🐾 {ind.individual_id}</div>
                        <div className="quoll-species">{ind.species}</div>
                        <div className="quoll-stats"><div className="quoll-stat"><div className="label">Sightings</div><div className="value">{ind.total_sightings}</div></div></div>
                    </Link>
                ))}
            </div>
        </div>
    );
}

function IndividualImages() {
    const { speciesKey, individualId } = useParams();
    const decoded = individualId ? decodeURIComponent(individualId) : '';

    return (
        <div>
            <nav className="breadcrumb"><Link to="/">Home</Link><span className="sep">›</span><Link to="/individuals">Profiles</Link><span className="sep">›</span><Link to={`/individuals/species/${speciesKey}`}>{speciesKey}</Link><span className="sep">›</span><Link to={`/individuals/species/${speciesKey}/individuals`}>Individuals</Link><span className="sep">›</span><span>{decoded}</span></nav>
            <div className="page-header"><h2>Individual {decoded}</h2><p>Sightings and images for this individual (list requires backend support)</p></div>
        </div>
    );
}

/* ============================================================
   ADMIN PANEL
   ============================================================ */
function AdminPanel() {
    const [users, setUsers] = useState<UserData[]>([]);
    const [metrics, setMetrics] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([fetchUsers(), fetchSystemMetrics()])
            .then(([u, m]) => { setUsers(u); setMetrics(m); })
            .catch(() => {}).finally(() => setLoading(false));
    }, []);

    const onRoleChange = async (userId: number, role: string) => {
        const updated = await changeUserRole(userId, role);
        setUsers(users.map((u) => (u.id === userId ? updated : u)));
    };

    if (loading) return <LoadingState />;

    return (
        <>
            <div className="page-header"><h2>Admin Panel</h2><p>System management and user administration</p></div>
            {metrics && (
                <div className="stats-grid">
                    <StatCard icon="📷" value={fmt(metrics.total_images)} label="Images" />
                    <StatCard icon="🔍" value={fmt(metrics.total_detections)} label="Detections" />
                    <StatCard icon="👤" value={fmt(metrics.total_users)} label="Users" />
                    <StatCard icon="⏳" value={fmt(metrics.pending_jobs)} label="Pending Jobs" />
                    <StatCard icon="💾" value={`${metrics.db_size_mb} MB`} label="DB Size" />
                    <StatCard icon="📁" value={`${metrics.storage_size_mb} MB`} label="Storage" />
                </div>
            )}
            <div className="card">
                <div className="card-header"><h3>Users</h3></div>
                <div className="card-body">
                    <div className="table-container">
                        <table>
                            <thead><tr><th>Email</th><th>Name</th><th>Role</th><th>Active</th><th>Action</th></tr></thead>
                            <tbody>
                                {users.map((u) => (
                                    <tr key={u.id}>
                                        <td>{u.email}</td>
                                        <td>{u.full_name || '—'}</td>
                                        <td><span className="tag tag-primary">{u.role}</span></td>
                                        <td>{u.is_active ? '✅' : '❌'}</td>
                                        <td>
                                            <select className="filter-select" value={u.role} onChange={(e) => onRoleChange(u.id, e.target.value)} style={{ fontSize: '0.75rem' }}>
                                                <option value="admin">admin</option><option value="researcher">researcher</option><option value="reviewer">reviewer</option>
                                            </select>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div className="card" style={{ marginTop: '1.5rem' }}>
                <div className="card-header"><h3>Dataset Exports</h3></div>
                <div className="card-body" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <a href={getQuollExportUrl('csv')} className="btn btn-primary" download>Export Quoll Detections</a>
                    <a href={getMetadataExportUrl('csv')} className="btn btn-outline" download>Export Full Metadata</a>
                    <a href={getExportUrl('json')} className="btn btn-outline" download>Export Report JSON</a>
                </div>
            </div>
        </>
    );
}

/* ============================================================
   LOGIN PAGE
   ============================================================ */
function LoginPage() {
    const { user, login } = useAuth();
    const [tab, setTab] = useState<'login' | 'register'>('login');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [fullName, setFullName] = useState('');
    const [role, setRole] = useState('reviewer');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    if (user) return <Navigate to="/" />;

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault(); setError(''); setLoading(true);
        try { await login(email, password); } catch { setError('Invalid credentials'); }
        setLoading(false);
    };

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault(); setError(''); setLoading(true);
        try {
            await register(email, password, fullName, role);
            await login(email, password);
        } catch (err: any) { setError(err.message); }
        setLoading(false);
    };

    return (
        <div style={{ maxWidth: 400, margin: '4rem auto' }}>
            <div className="page-header" style={{ textAlign: 'center' }}><h2>🌿 Wildlife AI Platform</h2><p>Sign in to continue</p></div>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
                <button className={`btn ${tab === 'login' ? 'btn-primary' : 'btn-outline'}`} onClick={() => setTab('login')} style={{ flex: 1 }}>Login</button>
                <button className={`btn ${tab === 'register' ? 'btn-primary' : 'btn-outline'}`} onClick={() => setTab('register')} style={{ flex: 1 }}>Register</button>
            </div>
            <div className="card">
                <div className="card-body">
                    <form onSubmit={tab === 'login' ? handleLogin : handleRegister}>
                        {tab === 'register' && (
                            <div style={{ marginBottom: '1rem' }}>
                                <label style={{ fontSize: '0.8rem', display: 'block', marginBottom: '0.25rem' }}>Full Name</label>
                                <input className="filter-select" style={{ width: '100%' }} value={fullName} onChange={(e) => setFullName(e.target.value)} />
                            </div>
                        )}
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ fontSize: '0.8rem', display: 'block', marginBottom: '0.25rem' }}>Email</label>
                            <input className="filter-select" style={{ width: '100%' }} type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                        </div>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ fontSize: '0.8rem', display: 'block', marginBottom: '0.25rem' }}>Password</label>
                            <input className="filter-select" style={{ width: '100%' }} type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
                        </div>
                        {tab === 'register' && (
                            <div style={{ marginBottom: '1rem' }}>
                                <label style={{ fontSize: '0.8rem', display: 'block', marginBottom: '0.25rem' }}>Role</label>
                                <select className="filter-select" value={role} onChange={(e) => setRole(e.target.value)}>
                                    <option value="reviewer">Reviewer</option><option value="researcher">Researcher</option><option value="admin">Admin</option>
                                </select>
                            </div>
                        )}
                        {error && <p style={{ color: 'var(--danger)', fontSize: '0.85rem', marginBottom: '0.5rem' }}>{error}</p>}
                        <button className="btn btn-primary" type="submit" disabled={loading} style={{ width: '100%', justifyContent: 'center' }}>
                            {loading ? 'Please wait...' : tab === 'login' ? 'Sign In' : 'Create Account'}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
}

/* ============================================================
   SHARED COMPONENTS
   ============================================================ */
function StatCard({ icon, value, label }: { icon: string; value: string; label: string }) {
    return <div className="stat-card"><div className="stat-icon">{icon}</div><div className="stat-value">{value}</div><div className="stat-label">{label}</div></div>;
}

function LoadingState() {
    return <div className="loading-container"><div className="spinner" /><span>Loading...</span></div>;
}

function ErrorState({ message }: { message: string }) {
    return <div className="empty-state"><div className="icon">⚠️</div><h3>Connection Error</h3><p>{message}</p></div>;
}

function EmptyMsg({ text }: { text: string }) {
    return <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>{text}</div>;
}

function fmt(n: number): string {
    return n.toLocaleString();
}

export default App;
