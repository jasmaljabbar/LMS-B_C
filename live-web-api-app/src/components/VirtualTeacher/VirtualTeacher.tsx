// src/components/VirtualTeacher/VirtualTeacher.tsx
'use client';
import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import {
    Box, Typography, Grid, Card, CardContent,
    IconButton, Button, TextField, InputAdornment, Dialog, DialogContent, Grow,
    Drawer, List, ListItem, ListItemIcon, ListItemText, Divider, CircularProgress, Alert, ListItemButton,
    DialogTitle,
    Avatar
} from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import SubjectIcon from '@mui/icons-material/Subject';
import AssessmentIcon from '@mui/icons-material/Assessment';
import TimelineIcon from '@mui/icons-material/Timeline';
import SettingsIcon from '@mui/icons-material/Settings';
import {
    Menu, Search, Settings,
    KeyboardArrowLeft, KeyboardArrowRight,
    PlayCircleOutline, GetApp, Fullscreen, Close, Send,
    MenuBook,
    // Removed media control icons as they are handled by ControlTray
    // Videocam, VideocamOff, ScreenShare, StopScreenShare, MicOn, MicOff, StopCircle
} from '@mui/icons-material';

// --- PDFJS Setup ---
import * as pdfjsLib from 'pdfjs-dist';
// Import worker stuff based on environment (adjust path if your public folder is different)
// --- PDF Viewer ---
import { Worker, Viewer, SpecialZoomLevel } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';

// Import styles for PDF viewer - **IMPORTANT**: Import these globally, e.g., in _app.tsx or layout.tsx
// import '@react-pdf-viewer/core/lib/styles/index.css';
// import '@react-pdf-viewer/default-layout/lib/styles/index.css';

// --- Removed Gemini/Audio specific imports - Handled by LiveAPIContext ---
// import GeminiLiveAPI from '../lib/gemini-live-api'; // Removed
// import { LiveAudioOutputManager } from '../lib/live-media-manager'; // Removed




if (typeof window !== 'undefined') {
    // Option 1: If you copied the worker file to /public
    // pdfjsLib.GlobalWorkerOptions.workerSrc = `/pdf.worker.min.mjs`;

    // Option 2: If using the one from node_modules (might require bundler setup)
    pdfjsLib.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.js`;
}


const defaultThumbnail = '/video_placeholder.jpg'; // Ensure this exists in /public

// --- Interfaces for API Data ---
interface SubjectData {
    id: string;
    name: string;
    grade_id: string;
    // Add other fields if needed
}

interface GradeData {
    id: string;
    name: string;
    // Add other fields if needed
}

interface LessonData {
    id: string;
    name: string;
    term_id: string;
    subject_id: string;
    // Add other fields if needed
}

interface FormattedLesson {
    id: string;
    title: string;
    color: string;
}

interface PdfUrlData {
    id: number;
    url: {
        id: number;
        url: string;
        url_type: 'http' | 'https' | string; // Be more specific if possible
        pdf_id: number;
    };
    url_type: 'http' | 'https' | string;
}
interface PdfData {
    id: string;
    name: string;
    lesson_id: string;
    urls: PdfUrlData[];
    // Add other fields if needed
}

interface FormattedPdf {
    id: string;
    title: string;
    url: string;
    lessonId: string;
}

interface VideoData {
    id: string;
    name: string;
    url: string;
    lesson_id: string;
    // Add other fields if needed
}

interface FormattedVideo {
    id: string;
    title: string;
    url: string;
    lessonId: string;
}

interface Student {
    name: string;
    year: string;
    avatar: string;
}
type Params = {
    accessToken: string;
    subjectId: string;
    studentId: string;
};



const VirtualTeacher: React.FC = () => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('accessToken')
    const subjctId = params.get('subjectId')
    const studentId = params.get('studentId')
    const termId = params.get('termId')
    // const token = query.get('token');
    // --- State Variables ---
    // Header States
    const [student, setStudent] = useState<Student>({
        name: 'Loading...',
        year: '',
        avatar: '',

    });

    useEffect(() => {
        const fetchInitialData = async () => {
            try {
                const response = await fetch(`https://lms-backend-931876132356.us-central1.run.app/students/${studentId}`, {
                    headers: {
                        Authorization: `Bearer ${token}`,
                        'Content-Type': 'application/json',
                    },
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const studentData = await response.json();
                console.log(studentData, "student data")

                if (studentData) {
                    setStudent({
                        name: studentData.name || 'N/A',
                        year: studentData.year ? `Academic Year ${studentData.year}` : 'N/A',
                        avatar: studentData.user?.photo || '',
                    });
                } else {
                    throw new Error('Received no student data.');
                }
            } catch (err) {
                console.error('Error fetching student data:', err);
            }
        };
        fetchInitialData();


    }, [])




    const [subjectName, setSubjectName] = useState<string | null>(null);
    const [gradeName, setGradeName] = useState<string | null>(null);
    const [headerLoading, setHeaderLoading] = useState<boolean>(true);
    const [headerError, setHeaderError] = useState<string | null>(null);

    // Lesson States
    const [dynamicLessons, setDynamicLessons] = useState<FormattedLesson[]>([]);
    const [lessonsLoading, setLessonsLoading] = useState<boolean>(true);
    const [lessonsError, setLessonsError] = useState<string | null>(null);
    const [selectedLessonId, setSelectedLessonId] = useState<string | null>(null);

    // PDF Data
    const [fetchedPdfs, setFetchedPdfs] = useState<FormattedPdf[]>([]);
    const [pdfsLoading, setPdfsLoading] = useState<boolean>(false);
    const [pdfsError, setPdfsError] = useState<string | null>(null);
    const [pdfIndex, setPdfIndex] = useState<number>(0);
    const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
    const [isThumbnailLoading, setIsThumbnailLoading] = useState<boolean>(false);
    const [fullScreenPdf, setFullScreenPdf] = useState<boolean>(false);

    // --- NEW State for PDF Page Navigation ---
    const [currentPageNumber, setCurrentPageNumber] = useState<number>(1);
    const [numPages, setNumPages] = useState<number>(0);
    
    // Video Data
    const [fetchedVideos, setFetchedVideos] = useState<FormattedVideo[]>([]);
    const [videosLoading, setVideosLoading] = useState<boolean>(false);
    const [videosError, setVideosError] = useState<string | null>(null);
    const [selectedVideo, setSelectedVideo] = useState<string | null>(null); // Store URL directly
    const [videoDurations, setVideoDurations] = useState<Record<string, number>>({});

    // UI
    const [drawerOpen, setDrawerOpen] = useState<boolean>(false);

    // Removed chat state - Handled by SidePanel
    // const [userQuestion, setUserQuestion] = useState('');
    // const [chatHistory, setChatHistory] = useState([]);

    // Removed Media Toggle States - Handled by ControlTray
    // const [isCameraOn, setIsCameraOn] = useState(false);
    // const [isScreenSharing, setIsScreenSharing] = useState(false);
    // const [isMicListening, setIsMicListening] = useState(false);
    // const [mediaError, setMediaError] = useState('');

    // --- Refs ---
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const renderTaskRef = useRef<pdfjsLib.RenderTask | null>(null);
    const loadedThumbnailUrlRef = useRef<string | null>(null);

    // Removed Media Refs - Handled by ControlTray/useLiveAPI
    // const mediaStreamRef = useRef<MediaStream | null>(null);
    // const micStreamRef = useRef<MediaStream | null>(null);
    // const videoPreviewRef = useRef<HTMLVideoElement | null>(null);
    // const geminiApiRef = useRef(null); // Removed
    // const audioOutputManagerRef = useRef(null); // Removed

    // --- Data ---
    const lessonColors = ['#e91e63', '#9c27b0', '#3f51b5', '#2196f3', '#009688', '#ff9800', '#795548', '#607d8b'];
    const getLessonColor = (index: number) => lessonColors[index % lessonColors.length];

    // --- Utility Function to Stop PDF Render Task ---
    // Simplified - only need to stop PDF render now
    const stopPdfRenderTask = useCallback(() => {
        if (renderTaskRef.current) {
            renderTaskRef.current.cancel();
            renderTaskRef.current = null;
        }
    }, []);


    // --- PDF Handling ---
    const loadPdfDocument = useCallback(async (url: string): Promise<pdfjsLib.PDFDocumentProxy | null> => {
        // No need to check for window, pdfjsLib should be available if workerSrc is set
        if (!pdfjsLib) return null;
        setIsThumbnailLoading(true);
        //setPdfDoc(null); // Reset doc before loading
        stopPdfRenderTask(); // Cancel any ongoing render

        try {
            const loadingTask = pdfjsLib.getDocument(url);
            const pdf = await loadingTask.promise;
            if (!pdf) throw new Error("PDF load failed");
            setPdfDoc(pdf);
            setNumPages(pdf.numPages);
            setCurrentPageNumber(1); // Reset to first page whenever a new document is loaded
            loadedThumbnailUrlRef.current = url; // Track the URL of this successfully loaded doc

            // setIsThumbnailLoading(false); // Set loading false in renderPage or on error
            return pdf;
        } catch (error: any) {
            console.error("Error loading PDF:", error);
            setPdfDoc(null);
            setNumPages(0);
            setCurrentPageNumber(1);
            loadedThumbnailUrlRef.current = null;

            //setIsThumbnailLoading(false);
            return null;
        }
    }, [stopPdfRenderTask]); // Add stopPdfRenderTask dependency


    const renderPage = useCallback(async (pdfDocument: pdfjsLib.PDFDocumentProxy, pageNumToRender: number, canvas: HTMLCanvasElement, scaleMultiplier = 1.5) => {
        if (!pdfDocument?.getPage || !canvas?.getContext) {
            setIsThumbnailLoading(false);
            return;
        }
        stopPdfRenderTask(); // Cancel any ongoing render
        try {
            const page = await pdfDocument.getPage(pageNumToRender);
            const containerWidth = canvas.parentElement?.clientWidth || 300;
            let viewport = page.getViewport({ scale: 1.0 });
            const scale = (containerWidth / viewport.width) * scaleMultiplier;
            viewport = page.getViewport({ scale });
            const context = canvas.getContext('2d');
            if (!context) {
                throw new Error("Could not get 2D context from canvas");
            }
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            canvas.style.width = '100%';
            canvas.style.height = 'auto';
            const renderContext = { canvasContext: context, viewport }; // Let TypeScript infer the type

            renderTaskRef.current = page.render(renderContext);
            await renderTaskRef.current.promise;
            renderTaskRef.current = null;
            setIsThumbnailLoading(false);
        } catch (error: any) {
            renderTaskRef.current = null;
            setIsThumbnailLoading(false);
            if (error?.name !== 'RenderingCancelledException') {
                console.error("Error rendering PDF page:", error);
            }
        }
    }, [stopPdfRenderTask]); // Add stopPdfRenderTask dependency

    // --- Memoized Filtered Content ---
    const filteredPdfs = useMemo(() => {
        if (!selectedLessonId || pdfsLoading || pdfsError) return [];
        // Ensure fetchedPdfs is always an array before filtering
        return (fetchedPdfs || []).filter(pdf => pdf.lessonId === selectedLessonId);
    }, [selectedLessonId, fetchedPdfs, pdfsLoading, pdfsError]);

    useEffect(() => {
        setCurrentPageNumber(1);
        // setPdfDoc(null); // Let the main rendering effect handle reloading if necessary
        // loadedThumbnailUrlRef.current = null; // Also handled by main rendering effect logic
    }, [pdfIndex, filteredPdfs]); // Only when the file selection changes


    const filteredVideos = useMemo(() => {
        if (!selectedLessonId || videosLoading || videosError) return [];
        // Ensure fetchedVideos is always an array
        return (fetchedVideos || []).filter(video => video.lessonId === selectedLessonId);
    }, [selectedLessonId, fetchedVideos, videosLoading, videosError]);

    // --- Memoized Selected Lesson Name ---
    const selectedLessonName = useMemo(() => {
        if (!selectedLessonId || lessonsLoading || lessonsError) return null;
        const selected = dynamicLessons.find(lesson => lesson.id === selectedLessonId);
        return selected ? selected.title : null;
    }, [selectedLessonId, dynamicLessons, lessonsLoading, lessonsError]);

    // Effect to fetch header data (Subject and Grade) on mount
    useEffect(() => {
        const fetchHeaderData = async () => {
            setHeaderLoading(true);
            setHeaderError(null);
            let fetchedSubjectName: string | null = null;
            let fetchedGradeName: string | null = null;

            try {
                // const token = localStorage.getItem('accessToken');
                const subjectId = localStorage.getItem('subjectId');

                if (!token) throw new Error('Access token not found in localStorage.');
                if (!subjctId) throw new Error('Subject ID not found in localStorage.');

                const headers = {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json',
                };

                // 1. Fetch Subject Details
                const subjectApiUrl = `https://lms-backend-931876132356.us-central1.run.app/subjects/${subjctId}`;
                const subjectResponse = await fetch(subjectApiUrl, { headers });

                if (!subjectResponse.ok) throw new Error(`Failed to fetch subject: ${subjectResponse.status} ${subjectResponse.statusText}`);
                const subjectData: SubjectData = await subjectResponse.json();
                fetchedSubjectName = subjectData.name;
                const gradeId = subjectData.grade_id;
                if (!gradeId) throw new Error('Grade ID not found in subject response.');

                // 2. Fetch Grade Details
                const gradeApiUrl = `https://lms-backend-931876132356.us-central1.run.app/grades/${gradeId}`;
                const gradeResponse = await fetch(gradeApiUrl, { headers });

                if (!gradeResponse.ok) throw new Error(`Failed to fetch grade: ${gradeResponse.status} ${gradeResponse.statusText}`);
                const gradeData: GradeData = await gradeResponse.json();
                fetchedGradeName = gradeData.name;

                setSubjectName(fetchedSubjectName);
                setGradeName(fetchedGradeName);

            } catch (error: any) {
                console.error("Error fetching header data:", error);
                setHeaderError(error.message);
                setSubjectName(null);
                setGradeName(null);
            } finally {
                setHeaderLoading(false);
            }
        };

        if (typeof window !== 'undefined') {
            fetchHeaderData();
        } else {
            setHeaderLoading(false);
            setHeaderError("Cannot fetch data outside of browser environment.");
        }

    }, []);

    // Effect to fetch Lessons data
    useEffect(() => {
        const fetchLessons = async () => {
            setLessonsLoading(true);
            setLessonsError(null);
            setSelectedLessonId(null);
            setDynamicLessons([]);    

            try {

                if (!token || !termId || !subjctId) {
                    throw new Error('Missing required items (token, termId, or subjectId) in localStorage.');
                }

                const headers = {
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json',
                };

                const lessonsApiUrl = `https://lms-backend-931876132356.us-central1.run.app/lessons/by-term-subject/?term_id=${termId}&subject_id=${subjctId}`;
                const response = await fetch(lessonsApiUrl, { headers });

                if (!response.ok) {
                    throw new Error(`Failed to fetch lessons: ${response.status} ${response.statusText}`);
                }

                const data: LessonData[] = await response.json();

                const formattedLessons: FormattedLesson[] = data.map((lesson, index) => ({
                    id: lesson.id,
                    title: lesson.name,
                    color: getLessonColor(index),
                }));

                setDynamicLessons(formattedLessons);

                if (formattedLessons.length > 0) {
                    setSelectedLessonId(formattedLessons[0].id); // Select the first lesson by default
                }

            } catch (error: any) {
                console.error("Error fetching lessons:", error);
                setLessonsError(error.message);
                setDynamicLessons([]);
                setSelectedLessonId(null);
            } finally {
                setLessonsLoading(false);
            }
        };

        if (typeof window !== 'undefined') {
            fetchLessons();
        } else {
            setLessonsLoading(false);
            setLessonsError("Cannot fetch lessons outside of browser environment.");
        }

    }, []);

    // Effect to fetch PDFs and Videos based on loaded lessons
    useEffect(() => {
        const fetchContentForLessons = async () => {
            if (lessonsLoading || lessonsError || pdfsLoading || videosLoading || dynamicLessons.length === 0) {
                if (!lessonsLoading && dynamicLessons.length === 0) {
                    setFetchedPdfs([]);
                    setFetchedVideos([]);
                    setPdfIndex(0);
                    setVideoDurations({});
                }
                return;
            }

            setPdfsLoading(true);
            setVideosLoading(true);
            setPdfsError(null);
            setVideosError(null);
            setFetchedPdfs([]);
            setFetchedVideos([]);
            setPdfIndex(0);
            setVideoDurations({});

            try {
                // const token = localStorage.getItem('accessToken');
                if (!token) throw new Error('Access token not found.');

                const headers = { 'Authorization': `Bearer ${token}`, 'Accept': 'application/json' };
                const lessonIds = dynamicLessons.map(lesson => lesson.id);
                if (lessonIds.length === 0) {
                    setPdfsLoading(false); setVideosLoading(false); return;
                }

                // --- Fetch PDFs ---
                const pdfPromises = lessonIds.map(lessonId =>
                    fetch(`https://lms-backend-931876132356.us-central1.run.app/pdfs/lesson/${lessonId}`, { headers })
                        .then(res => res.ok ? res.json() as Promise<PdfData[]> : Promise.reject(`PDF fetch failed for lesson ${lessonId}: ${res.status}`))
                        .catch(err => { console.error(`Error fetching PDF for lesson ${lessonId}:`, err); return []; })
                );

                // --- Fetch Videos ---
                const videoPromises = lessonIds.map(lessonId =>
                    fetch(`https://lms-backend-931876132356.us-central1.run.app/videos/lesson/${lessonId}`, { headers })
                        .then(res => res.ok ? res.json() as Promise<VideoData[]> : Promise.reject(`Video fetch failed for lesson ${lessonId}: ${res.status}`))
                        .catch(err => { console.error(`Error fetching Video for lesson ${lessonId}:`, err); return []; })
                );

                const [pdfResults, videoResults] = await Promise.all([Promise.all(pdfPromises), Promise.all(videoPromises)]);

                // --- Process PDFs ---
                const allPdfs: PdfData[] = pdfResults.flat();
                const formattedPdfs: FormattedPdf[] = allPdfs
                    .map(pdfData => {
                        // Ensure urls is an array before finding
                        const httpsUrlObj = (pdfData.urls || []).find(u => u?.url?.url_type === 'https');
                        return httpsUrlObj ? {
                            id: pdfData.id,
                            title: pdfData.name,
                            url: httpsUrlObj.url.url,
                            lessonId: pdfData.lesson_id
                        } : null;
                    })
                    .filter((pdf): pdf is FormattedPdf => pdf !== null); // Type guard filter

                setFetchedPdfs(formattedPdfs);
                if (formattedPdfs.length === 0 && allPdfs.length > 0) {
                    console.warn("PDFs found, but none had an HTTPS URL.");
                    setPdfsError("No viewable PDFs found (missing HTTPS URL).");
                }

                // --- Process Videos ---
                const allVideos: VideoData[] = videoResults.flat();
                const formattedVideos: FormattedVideo[] = allVideos.map(videoData => ({
                    id: videoData.id,
                    title: videoData.name,
                    url: videoData.url, // Assuming URL is directly available
                    lessonId: videoData.lesson_id
                }));

                setFetchedVideos(formattedVideos);
                if (formattedVideos.length === 0 && allVideos.length > 0) {
                    console.warn("Videos found, but processing failed.");
                    setVideosError("Could not process video data.");
                }

            } catch (error: any) {
                console.error("Error fetching PDFs/Videos:", error);
                setPdfsError(error.message || 'Failed to load PDFs.');
                setVideosError(error.message || 'Failed to load Videos.');
                setFetchedPdfs([]);
                setFetchedVideos([]);
            } finally {
                setPdfsLoading(false);
                setVideosLoading(false);
            }
        };

        if (typeof window !== 'undefined') {
            fetchContentForLessons();
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [dynamicLessons, lessonsLoading, lessonsError]); // Only depends on lessons state

    // Effect to reset PDF index when selected lesson changes
    useEffect(() => {
        setPdfIndex(0);
    }, [selectedLessonId]);

     // --- MODIFIED Effect to Load/Render PDF Thumbnail (Handles both file and page changes) ---
     useEffect(() => {
        let isMounted = true;

        const loadAndRenderCurrentPdfPage = async () => {
            const currentFile = filteredPdfs?.[pdfIndex];

            if (!currentFile || !canvasRef.current) {
                if (isMounted) {
                    if (canvasRef.current) {
                        const ctx = canvasRef.current.getContext('2d');
                        if (ctx) ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
                    }
                    setIsThumbnailLoading(false);
                    setPdfDoc(null);
                    setNumPages(0);
                    // currentPageNumber is reset by its own dedicated effect on pdfIndex change
                }
                return;
            }

            // Always set loading true when this effect runs for a new render
            setIsThumbnailLoading(true);
            if (canvasRef.current) { // Clear canvas before new render attempt
                const ctx = canvasRef.current.getContext('2d');
                if (ctx) ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
            }

            let docToRender = pdfDoc;

            // Condition to load a new document:
            // 1. pdfDoc is null (no doc loaded yet for this selection)
            // 2. The URL of the current file is different from the URL of the already loaded pdfDoc
            if (!docToRender || loadedThumbnailUrlRef.current !== currentFile.url) {
                // console.log(`Attempting to load new PDF document: ${currentFile.title}`);
                docToRender = await loadPdfDocument(currentFile.url);
                // loadPdfDocument now sets pdfDoc, numPages, and resets currentPageNumber to 1,
                // and updates loadedThumbnailUrlRef.current
            }

            if (isMounted && docToRender && canvasRef.current) {
                // console.log(`Rendering page ${currentPageNumber} of ${docToRender.numPages} for ${currentFile.title}`);
                await renderPage(docToRender, currentPageNumber, canvasRef.current, 1.5);
            } else if (isMounted) {
                // This path means docToRender is null (load failed) or canvas is gone
                setIsThumbnailLoading(false);
                if (!docToRender) { // Ensure states are reset if loading failed
                    setPdfDoc(null);
                    setNumPages(0);
                    loadedThumbnailUrlRef.current = null;
                }
            }
        };

        if (!pdfsLoading && selectedLessonId && filteredPdfs.length > 0) {
            loadAndRenderCurrentPdfPage();
        } else {
            // Conditions where we don't render (e.g., initial content loading, no lesson)
            if (isMounted) {
                if (canvasRef.current) {
                    const ctx = canvasRef.current.getContext('2d');
                    if (ctx) ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
                }
                setIsThumbnailLoading(false);
                setPdfDoc(null);
                setNumPages(0);
                loadedThumbnailUrlRef.current = null;
            }
        }

        return () => {
            isMounted = false;
            stopPdfRenderTask();
        };
    }, [
        pdfIndex,         // When the selected PDF file changes
        filteredPdfs,     // When the list of PDFs for the lesson changes
        currentPageNumber,// When the page number for the current PDF changes
        pdfsLoading,      // To wait for initial content fetch
        selectedLessonId, // To ensure a lesson is active
        loadPdfDocument,  // Callback
        renderPage,       // Callback
        stopPdfRenderTask,// Callback
        pdfDoc            // Re-added: important to re-render if pdfDoc changes due to external reasons (though less likely here)
                          // or if we want to ensure renderPage is called if pdfDoc is already set but currentPageNumber hasn't changed (initial load scenario)
    ]);

    const handleNextPdf = () => {
        if (filteredPdfs.length > 0) {
            setPdfIndex((prev) => (prev + 1) % filteredPdfs.length);
        }
    };
    const handlePreviousPdf = () => {
        if (filteredPdfs.length > 0) {
            setPdfIndex((prev) => (prev - 1 + filteredPdfs.length) % filteredPdfs.length);
        }
    };
    const handleCloseFullScreen = () => setFullScreenPdf(false);
    const defaultLayoutPluginInstance = defaultLayoutPlugin();
    // --- NEW PDF *Page* Navigation Handlers ---
    const handleNextPage = () => {
        if (pdfDoc && currentPageNumber < numPages) {
            setCurrentPageNumber(prev => prev + 1);
        }
    };

    const handlePreviousPage = () => {
        if (pdfDoc && currentPageNumber > 1) {
            setCurrentPageNumber(prev => prev - 1);
        }
    };


    // --- Video Handling ---
    const getVideoDuration = useCallback(async (url: string): Promise<number | null> => {
        if (typeof window === 'undefined') return null;
        return new Promise((resolve) => {
            const v = document.createElement('video');
            v.preload = 'metadata';
            v.onloadedmetadata = () => resolve(v.duration);
            v.onerror = () => resolve(null);
            v.src = url;
        });
    }, []);

    useEffect(() => {
        if (typeof window === 'undefined') return;
        let isMounted = true;
        const fetchDurations = async () => {
            const durations: Record<string, number> = {};
            // Use filteredVideos here
            const promises = filteredVideos.map(v =>
                getVideoDuration(v.url).then(d => ({ url: v.url, duration: d }))
            );
            const results = await Promise.all(promises);
            if (isMounted) {
                results.forEach(({ url, duration }) => {
                    if (duration) durations[url] = duration;
                });
                setVideoDurations(durations);
            }
        };

        if (filteredVideos?.length > 0 && !videosLoading) {
            fetchDurations();
        } else {
            setVideoDurations({});
        }
        return () => { isMounted = false; };
    }, [getVideoDuration, filteredVideos, videosLoading]);


    // --- Chat Handling ---
    // Removed handleSendMessage and related state/effects. Chat handled by SidePanel.

    // --- UI Handling ---
    const toggleDrawer = () => setDrawerOpen(!drawerOpen);

    // --- Media Stream Toggles ---
    // Removed all media toggle handlers (handleVideoToggle, etc.) and related state/effects.
    // Media is controlled via ControlTray.

    // --- Cleanup Effect ---
    // Simplified cleanup: only need to cancel PDF render task now.
    useEffect(() => {
        return () => {
            // console.log("VirtualTeacher Cleanup: Stopping PDF render task");
            stopPdfRenderTask();
        };
    }, [stopPdfRenderTask]);

    // Escape Key Listener (only handles fullscreen pdf, video player now)
    useEffect(() => {
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                if (fullScreenPdf) handleCloseFullScreen();
                else if (selectedVideo) setSelectedVideo(null);
            }
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [fullScreenPdf, selectedVideo]); // Removed media state dependencies


    const handleLogout = () => {
        window.location.replace('https://ai-powered-lms.web.app/');
    }

    // Removed WebSocket connection useEffect

    // --- Render ---
    return (
        // Use a fragment or a Box as the top-level element returned by the component
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
            {/* Top Bar - Inherited from App.tsx structure, but adding elements here */}
            {/* <Box sx={{
                 background: 'linear-gradient(to right, #4e54c8, #8f94fb)',
                 p: 1.5,
                 display: 'flex',
                 justifyContent: 'space-between',
                 alignItems: 'center',
                 color: 'white',
                 flexShrink: 0 // Prevent shrinking
             }}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <IconButton color="inherit" edge="start" onClick={toggleDrawer} aria-label="Open lessons menu"><Menu /></IconButton>
                    <Typography variant="h6" sx={{ ml: 1, fontSize: { xs: '1rem', sm: '1.25rem' }, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {headerLoading ? 'Loading...' : headerError ? `Error` : (subjectName && gradeName) ? `${subjectName} - ${gradeName}` : 'Subject - Grade'}
                    </Typography>
                </Box>
                <Box>
                     <IconButton color="inherit" aria-label="Search (VT)"><Search /></IconButton>
                     <IconButton color="inherit" aria-label="Settings (VT)"><Settings /></IconButton>
                </Box>
            </Box> */}

            <Box
                sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    p: 2,
                    mb: 2,
                    bgcolor: 'white',
                    borderRadius: 1,
                    boxShadow: 1,
                }}
            >
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Avatar src={student.avatar} sx={{ width: 48, height: 48, mr: 2 }} />
                    <Box>
                        <Typography variant="h6" component="h1" fontWeight="bold" color="text.primary">
                            {student.name}
                        </Typography>
                        <Typography variant="subtitle1" color="text.secondary">
                            {student.year}
                        </Typography>
                    </Box>
                </Box>
                {/* Header Links - Static */}
                <Box sx={{ display: { xs: 'none', md: 'flex' }, alignItems: 'center' }}>
                    {/* ... existing header links ... */}
                    {/* <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
                        <IconButton sx={{ color: 'rgba(0, 0, 0, 0.54)' }}> <HomeIcon /> </IconButton>
                        <Typography variant="body2" color="text.secondary"> Home </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
                        <IconButton sx={{ color: 'rgba(0, 0, 0, 0.54)' }}> <SubjectIcon /> </IconButton>
                        <Typography variant="body2" color="text.secondary"> Subjects </Typography>
                    </Box> */}
                    {/* <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
                        <IconButton sx={{ color: 'rgba(0, 0, 0, 0.54)' }}> <AssessmentIcon /> </IconButton>
                        <Typography variant="body2" color="text.secondary"> Assessments </Typography>
                    </Box> */}

                    <Box sx={{ display: 'flex', alignItems: 'center', cursor: "pointer" }} onClick={handleLogout}>
                        <IconButton sx={{ color: 'rgba(0, 0, 0, 0.54)' }}> <SettingsIcon /> </IconButton>
                        <Typography variant="body2" color="text.secondary"> Logout </Typography>
                    </Box>
                </Box>
            </Box>

            {/* Drawer for Lessons */}
            <Drawer variant="temporary" open={drawerOpen} onClose={toggleDrawer} ModalProps={{ keepMounted: true }} sx={{ '& .MuiDrawer-paper': { boxSizing: 'border-box', width: 240 } }}>
                <Box sx={{ width: '100%', bgcolor: '#4e54c8' }}><Typography variant="h6" gutterBottom sx={{ color: 'white', p: 2 }}>Lessons</Typography></Box><Divider />
                <List>
                    {lessonsLoading ? (
                        <ListItem><CircularProgress size={24} sx={{ mx: 'auto', my: 2 }} /></ListItem>
                    ) : lessonsError ? (
                        <ListItem><ListItemText primary={`Error: ${lessonsError}`} sx={{ color: 'error.main', textAlign: 'center' }} /></ListItem>
                    ) : dynamicLessons.length > 0 ? (
                        dynamicLessons.map((lesson, index) => {
                            const isSelected = lesson.id === selectedLessonId;
                            return (
                                <ListItemButton
                                    key={lesson.id || index}
                                    onClick={() => { setSelectedLessonId(lesson.id); toggleDrawer(); }}
                                    selected={isSelected} // Use selected prop
                                    sx={{
                                        //cursor: 'pointer',
                                        '&:hover': { bgcolor: 'rgba(0, 0, 0, 0.04)' },
                                        // MUI handles selected style, but can override
                                        // bgcolor: isSelected ? 'action.selected' : 'transparent',
                                        '& .MuiListItemText-primary': { fontWeight: isSelected ? 'fontWeightBold' : 'fontWeightRegular' },
                                    }}
                                >
                                    <ListItemIcon><MenuBook sx={{ color: lesson.color }} /></ListItemIcon>
                                    <ListItemText primary={lesson.title} sx={{ color: lesson.color }} />
                                </ListItemButton>
                            )
                        })
                    ) : (
                        <ListItem><ListItemText primary="No lessons found." sx={{ color: 'text.secondary', textAlign: 'center' }} /></ListItem>
                    )}
                </List>
            </Drawer>

            {/* Main Content Area for Virtual Teacher */}
            {/* Adjusted padding and layout to fit within the main area */}
            <Box sx={{
                flexGrow: 1, // Take remaining vertical space
                p: { xs: 1, sm: 2 }, // Reduced padding
                display: 'flex',
                flexDirection: 'column', // Stack PDF and Video vertically
                gap: { xs: 1.5, md: 2 }, // Reduced gap
                overflowY: 'auto', // Allow scrolling within this Box
                // Max height calculation might not be needed if parent controls height
            }}>

                {/* PDF Thumbnail Card */}
                <Card sx={{ borderRadius: '12px', boxShadow: 3, flexShrink: 0 }}>
                    <CardContent sx={{ p: { xs: 1.5, sm: 2 } }}>
                        <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold', fontSize: { xs: '1rem', sm: '1.1rem' } }}>
                            {lessonsLoading ? 'Loading Lesson...' : selectedLessonName ? selectedLessonName : 'Select a Lesson'}
                        </Typography>
                        <Box sx={{ position: 'relative', width: '100%', overflow: 'hidden', borderRadius: '8px', backgroundColor: '#e0e0e0', border: '1px solid #ccc', minHeight: '150px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {(pdfsLoading || isThumbnailLoading) && <CircularProgress size={40} sx={{ position: 'absolute', color: '#8f94fb' }} />}
                            {!pdfsLoading && pdfsError && !isThumbnailLoading && (<Alert severity="error" sx={{ width: '100%' }}>{pdfsError}</Alert>)}

                            {/* Canvas - ensure it's displayed correctly */}
                            <canvas ref={canvasRef} style={{
                                width: '100%',
                                height: 'auto',
                                borderRadius: '8px',
                                // Conditionally display based on loading/error states AND pdfDoc presence
                                display: (pdfsLoading || pdfsError || isThumbnailLoading || !pdfDoc) ? 'none' : 'block'
                            }} />


                            {/* Fullscreen Button */}
                            {!pdfsLoading && !pdfsError && !isThumbnailLoading && pdfDoc && filteredPdfs.length > 0 && (
                                <IconButton size="small" sx={{ position: 'absolute', top: 8, right: 8, color: 'white', backgroundColor: 'rgba(0, 0, 0, 0.5)', '&:hover': { backgroundColor: 'rgba(0, 0, 0, 0.7)' } }} onClick={() => setFullScreenPdf(true)} aria-label="View PDF Fullscreen"><Fullscreen fontSize="small" /></IconButton>
                            )}

                            {/* Empty/Placeholder States */}
                            {!pdfsLoading && !pdfsError && !isThumbnailLoading && !pdfDoc && !selectedLessonId && (<Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center', p: 2 }}>Select a lesson to view PDFs.</Typography>)}
                            {!pdfsLoading && !pdfsError && !isThumbnailLoading && !pdfDoc && selectedLessonId && filteredPdfs.length === 0 && (<Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center', p: 2 }}>No PDFs for this lesson.</Typography>)}
                            {!pdfsLoading && !pdfsError && !isThumbnailLoading && !pdfDoc && selectedLessonId && filteredPdfs.length > 0 && (<Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center', p: 2 }}>PDF preview unavailable.</Typography>)}

                        </Box>
                                                {/* --- PDF PAGE Navigation Controls --- */}
                                                {pdfDoc && numPages > 0 && !isThumbnailLoading && (
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1.5, mb: 0.5 }}>
                                <Button
                                    size="small"
                                    startIcon={<KeyboardArrowLeft />}
                                    onClick={handlePreviousPage}
                                    disabled={currentPageNumber <= 1}
                                    variant="outlined" // Using outlined for distinction
                                >
                                    Prev Page
                                </Button>
                                <Typography variant="caption" sx={{ textAlign: 'center', color: 'text.secondary' }}>
                                    Page {currentPageNumber} / {numPages}
                                </Typography>
                                <Button
                                    size="small"
                                    endIcon={<KeyboardArrowRight />}
                                    onClick={handleNextPage}
                                    disabled={currentPageNumber >= numPages}
                                    variant="outlined"
                                >
                                    Next Page
                                </Button>
                            </Box>
                        )}
                        {/* --- End PDF PAGE Navigation --- */}

                        {/* PDF Navigation */}
                        {filteredPdfs.length > 1 && !pdfsLoading && !pdfsError && (
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1 }}>
                                <Button size="small" startIcon={<KeyboardArrowLeft />} variant='text' sx={{ color: '#9c27b0' }} onClick={handlePreviousPdf} disabled={isThumbnailLoading || pdfsLoading}>
                                    Prev Doc {/* Changed text */}
                                </Button>
                                <Typography variant="caption" sx={{ textAlign: 'center' }}>
                                    Doc {filteredPdfs.length > 0 ? pdfIndex + 1 : 0} / {filteredPdfs.length}
                                </Typography>
                                <Button size="small" endIcon={<KeyboardArrowRight />} variant='text' sx={{ color: '#9c27b0' }} onClick={handleNextPdf} disabled={isThumbnailLoading || pdfsLoading}>
                                    Next Doc {/* Changed text */}
                                </Button>
                            </Box>
                        )}
                    </CardContent>
                </Card>


                {/* Video Lessons Card */}
                <Card sx={{ borderRadius: '12px', boxShadow: 3, flexShrink: 0 }}>
                    <CardContent sx={{ p: { xs: 1.5, sm: 2 } }}>
                        <Typography variant="h6" gutterBottom sx={{ fontWeight: 'medium', fontSize: { xs: '1rem', sm: '1.1rem' } }}>Related Videos</Typography>

                        {videosLoading && (<Box sx={{ display: 'flex', justifyContent: 'center', my: 2 }}><CircularProgress size={30} sx={{ color: '#8f94fb' }} /></Box>)}
                        {!videosLoading && videosError && (<Alert severity="error" sx={{ width: '100%', my: 1 }}>{videosError}</Alert>)}
                        {!videosLoading && !videosError && !selectedLessonId && (<Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center', my: 2 }}>Select a lesson to view videos.</Typography>)}
                        {!videosLoading && !videosError && selectedLessonId && filteredVideos.length === 0 && (<Typography variant="body2" sx={{ color: 'text.secondary', textAlign: 'center', my: 2 }}>No videos available for this lesson.</Typography>)}

                        {/* Video List - Use filteredVideos */}
                        {!videosLoading && !videosError && selectedLessonId && filteredVideos.length > 0 && (
                            filteredVideos.map((video, index) => (
                                <Box key={video.id || index} sx={{ display: 'flex', alignItems: 'center', my: 1.5, gap: 1.5 }}>
                                    <Box
                                        sx={{ position: 'relative', width: '100px', height: '56.25px', borderRadius: '6px', overflow: 'hidden', cursor: 'pointer', flexShrink: 0, backgroundColor: '#e0e0e0', '&:hover .playIcon': { opacity: 1, color: 'white' } }}
                                        onClick={() => setSelectedVideo(video.url)}
                                    >
                                        <img src={defaultThumbnail} alt={`Thumbnail for ${video.title}`} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                                        <PlayCircleOutline className="playIcon" sx={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: 'rgba(255, 255, 255, 0.8)', fontSize: 32, transition: 'opacity 0.3s ease, color 0.3s ease', opacity: 0.8 }} />
                                    </Box>
                                    <Box sx={{ minWidth: 0 }}>
                                        <Typography variant="body2" sx={{ fontWeight: 'medium' }} noWrap={false}>{video.title}</Typography>
                                        <Typography variant="caption" color="text.secondary">
                                            {videoDurations[video.url] ? `${Math.floor(videoDurations[video.url] / 60)}:${String(Math.floor(videoDurations[video.url] % 60)).padStart(2, '0')}` : '...'}
                                        </Typography>
                                    </Box>
                                </Box>
                            ))
                        )}
                    </CardContent>
                </Card>

            </Box> {/* End Main Content Area for VT */}

            {/* --- Dialogs --- */}

            {/* Full Screen PDF Dialog */}
            <Dialog open={fullScreenPdf} onClose={handleCloseFullScreen} fullScreen PaperProps={{ sx: { bgcolor: '#555' } }} TransitionComponent={Grow}>
                <DialogContent sx={{ p: 0, display: 'flex', flexDirection: 'column', width: '100vw', height: '100vh', overflow: 'hidden' }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', p: 1, bgcolor: 'rgba(0, 0, 0, 0.7)', color: 'white', flexShrink: 0 }}>
                        <Typography variant="body1" sx={{ mr: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', flexGrow: 1 }}>
                            {/* Ensure filteredPdfs exists and has item at pdfIndex */}
                            {filteredPdfs?.[pdfIndex]?.title || `Document`}
                        </Typography>
                        <Typography variant="caption" sx={{ color: 'lightgrey', display: { xs: 'none', sm: 'block' }, mx: 2 }}>(Press Esc to exit)</Typography>
                        <IconButton edge="end" color="inherit" onClick={handleCloseFullScreen} aria-label="Close PDF viewer"><Close /></IconButton>
                    </Box>
                    <Box sx={{ flexGrow: 1, width: '100%', height: 'calc(100% - 48px)', overflow: 'hidden' }}>
                        {/* Ensure filteredPdfs exists and has item at pdfIndex */}
                        {filteredPdfs?.[pdfIndex]?.url ? (
                            <Worker workerUrl={pdfjsLib.GlobalWorkerOptions.workerSrc}>
                                <Viewer fileUrl={filteredPdfs[pdfIndex].url} plugins={[defaultLayoutPluginInstance]} defaultScale={SpecialZoomLevel.PageFit} />
                            </Worker>
                        ) : (
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}><Typography color="white">No PDF to display.</Typography></Box>
                        )}
                    </Box>
                </DialogContent>
            </Dialog>

            {/* Video Playback Dialog */}
            <Dialog open={!!selectedVideo} onClose={() => setSelectedVideo(null)} maxWidth="lg" fullWidth PaperProps={{ sx: { backgroundColor: 'black', boxShadow: 'none', maxHeight: '95vh' } }} TransitionComponent={Grow}>
                <IconButton aria-label="close video player" onClick={() => setSelectedVideo(null)} sx={{ position: 'absolute', right: 8, top: 8, color: 'white', zIndex: 1, bgcolor: 'rgba(0,0,0,0.5)', '&:hover': { bgcolor: 'rgba(0,0,0,0.7)' } }}><Close /></IconButton>
                <DialogContent sx={{ p: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', overflow: 'hidden' }}>
                    {selectedVideo && (
                        <Box sx={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <video controls autoPlay style={{ maxWidth: '100%', maxHeight: '100%', display: 'block' }} onEnded={() => setSelectedVideo(null)}>
                                <source src={selectedVideo} type="video/mp4" />
                                Your browser does not support the video tag.
                            </video>
                        </Box>
                    )}
                </DialogContent>
            </Dialog>

            {/* Removed Camera/Screen Share Preview Modal Dialog - Handled by ControlTray/App's video element */}

        </Box>
    );
};

export default VirtualTeacher;