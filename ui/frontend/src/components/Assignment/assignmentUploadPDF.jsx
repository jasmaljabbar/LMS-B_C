// src/components/AssignmentPaperSampleManagement.js
import React, { useState, useEffect, useCallback, useRef } from 'react'; // Added useRef
import {
    Container,
    Typography,
    Paper,
    Grid,
    TextField,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Button,
    Box,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    IconButton,
    InputAdornment,
    Dialog,
    DialogActions,
    DialogContent,
    DialogContentText,
    DialogTitle,
    CircularProgress,
    Snackbar,
    Alert, // Keep Alert
    Link,
    LinearProgress,
    FormHelperText,
    List,
    ListItem,
    ListItemButton,
    ListItemIcon,
    ListItemText
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { Dashboard } from '@mui/icons-material';
import ArticleIcon from '@mui/icons-material/Article'; // For Sample Papers
import FormatAlignLeftIcon from '@mui/icons-material/FormatAlignLeft'; // For Format Management
import AutoStoriesIcon from '@mui/icons-material/AutoStories'; // For Paper Generation
// --- Import Icons ---
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import SaveIcon from '@mui/icons-material/Save';
import SearchIcon from '@mui/icons-material/Search';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import DescriptionIcon from '@mui/icons-material/Description';
import VisibilityIcon from '@mui/icons-material/Visibility';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import CloseIcon from '@mui/icons-material/Close';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import MenuIcon from '@mui/icons-material/Menu';
// import { useRouter } from 'next/navigation';
import Drawer from '@mui/material/Drawer';
import Tooltip from '@mui/material/Tooltip';
// import TeacherTabs from './TeacherTabs';

// --- Styled component for the File Upload Area ---
const FileUploadArea = styled('div')(({ theme, disabled }) => ({
    border: `2px dashed ${disabled ? theme.palette.grey[300] : theme.palette.grey[400]}`,
    borderRadius: theme.shape.borderRadius,
    padding: theme.spacing(4),
    textAlign: 'center',
    cursor: disabled ? 'not-allowed' : 'pointer',
    backgroundColor: disabled ? theme.palette.grey[200] : theme.palette.grey[50],
    color: disabled ? theme.palette.text.disabled : 'inherit',
    transition: 'background-color 0.2s ease-in-out, border-color 0.2s ease-in-out',
    '&:hover': {
        backgroundColor: disabled ? theme.palette.grey[200] : theme.palette.grey[100],
    },
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '150px',
}));

// const IP_ADDRESS = process.env.NEXT_PUBLIC_IP_ADDRESS;
const IP_ADDRESS = "";

// --- API Base URL ---
// const API_BASE_URL = `https://${IP_ADDRESS}`;
const API_BASE_URL = ``;

// --- Helper Function to get Token ---
const getAuthToken = () => {
    if (typeof window !== 'undefined') {
        return localStorage.getItem('accessToken');
    }
    return null;
};

// --- Helper to get document icon based on URL ---
const getDocumentIconFromUrl = (url) => {
    if (!url) return null;
    const extension = url.split('.').pop()?.toLowerCase();
    if (extension === 'pdf') {
        return <PictureAsPdfIcon sx={{ color: 'red', verticalAlign: 'middle', mr: 0.5 }} />;
    } else if (extension === 'docx') {
        return <DescriptionIcon sx={{ color: 'blue', verticalAlign: 'middle', mr: 0.5 }} />;
    }
    return <DescriptionIcon sx={{ color: 'grey', verticalAlign: 'middle', mr: 0.5 }} />;
};


// --- Helper function for authenticated API calls ---
const fetchAuthenticated = async (url, options = {}) => {
    const token = getAuthToken();
    // Add a check for token existence early if needed for specific flows
    // if (!token && !url.includes('/login')) { // Example: Allow login routes without token
    //    console.error("Authentication token not found.");
    //    throw new Error("Authentication token not found. Please log in.");
    // }

    const headers = {
        'accept': 'application/json',
        // Conditionally add Authorization header if token exists
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
        ...(options.headers || {}),
    };

    const body = options.body instanceof FormData ? options.body : (options.body ? JSON.stringify(options.body) : undefined);

    try {
        const response = await fetch(url, {
            ...options,
            headers,
            ...(body && { body }), // Only add body if it exists
        });

        if (!response.ok) {
            let errorData = { detail: `Request failed with status ${response.status}` }; // Default error
            try {
                // Try parsing JSON first
                const jsonError = await response.json();
                // Use the detail field if available, otherwise keep the default message
                if (jsonError && jsonError.detail) {
                    errorData.detail = typeof jsonError.detail === 'string' ? jsonError.detail : JSON.stringify(jsonError.detail);
                }
            } catch (e) {
                // If JSON parsing fails, try reading as text
                try {
                    const textError = await response.text();
                    if (textError) {
                        errorData.detail = textError;
                    }
                } catch (textE) {
                    // Ignore error reading text body if response was truly empty
                    console.warn("Could not read error response body as text.");
                }
            }
            console.error(`API Error (${response.status}) for ${url}:`, errorData.detail);
            throw new Error(errorData.detail);
        }

        // Check for empty response body based on status or content-length
        if (response.status === 204 || response.headers.get("content-length") === "0") {
            return null;
        }

        // Assume successful responses have a JSON body
        try {
            return await response.json();
        } catch (e) {
            console.warn(`Successful response from ${url} (status ${response.status}) was not valid JSON.`);
            // Depending on API design, you might want to return null or handle differently
            return null;
        }

    } catch (error) {
        // Catch fetch/network errors or errors thrown from response handling
        console.error(`Fetch failed for ${url}:`, error);
        // Re-throw the original error to maintain stack trace and specific error type if needed
        throw error;
    }
};


function AssignmentUploadPDF() {
    // --- Main Data State ---
    // const router = useRouter();
    const [assignments, setAssignments] = useState([]);
    const [filteredAssignments, setFilteredAssignments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [drawerOpen, setDrawerOpen] = useState(false);

    // --- Form State ---
    const [grade, setGrade] = useState('');
    const [subject, setSubject] = useState('');
    const [assignmentTitle, setAssignmentTitle] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [fileInputKey, setFileInputKey] = useState(Date.now()); // Keep for file input reset

    // --- Dropdown Options State ---
    const [gradesList, setGradesList] = useState([]);
    const [subjectsList, setSubjectsList] = useState([]);
    const [loadingGrades, setLoadingGrades] = useState(false);
    const [loadingSubjects, setLoadingSubjects] = useState(false);
    const [gradesError, setGradesError] = useState(null);
    const [subjectsError, setSubjectsError] = useState(null);


    // --- Edit Dialog State ---
    const [editOpen, setEditOpen] = useState(false);
    const [editingAssignment, setEditingAssignment] = useState(null);
    const [editFormData, setEditFormData] = useState({ grade: '', subject: '', documentName: '' });
    const [newSelectedFile, setNewSelectedFile] = useState(null);

    // --- Delete Dialog State ---
    const [deleteOpen, setDeleteOpen] = useState(false);
    const [deletingAssignmentId, setDeletingAssignmentId] = useState(null);

    // --- Feedback State ---
    const [snackbarOpen, setSnackbarOpen] = useState(false);
    const [snackbarMessage, setSnackbarMessage] = useState('');
    const [snackbarSeverity, setSnackbarSeverity] = useState('success');

    // Ref for the snackbar to potentially help with transitions
    const snackbarRef = useRef(null);

    const [updating, setUpdating] = useState(false); // For Edit Save
    const [deleting, setDeleting] = useState(false); // For Delete Confirm

    // --- Fetch Initial Table Data ---
    const fetchAssignmentData = useCallback(async (showLoadingIndicator = true) => {
        if (showLoadingIndicator) setLoading(true); // Control loading indicator visibility
        // setError(null); // Clear previous errors when refreshing
        console.log("Fetching assignment data...");
        try {
            const assignmentSamples = await fetchAuthenticated(`${API_BASE_URL}/assignment-samples/?skip=0&limit=100`);
            if (!assignmentSamples) { // Handle null/undefined response
                console.warn("Received null or undefined assignment samples from API.");
                setAssignments([]);
                setFilteredAssignments([]);
                if (showLoadingIndicator) setLoading(false);
                setError("Failed to load assignments: Invalid data received."); // Set specific error
                return;
            }
            if (assignmentSamples.length === 0) {
                console.log("No assignment samples found.");
                setAssignments([]);
                setFilteredAssignments([]);
                if (showLoadingIndicator) setLoading(false);
                setError(null); // Clear error if just empty
                return;
            }
            // Make fetching sub-data more robust
            const uniqueSubjectIds = [...new Set(assignmentSamples.map(a => a.subject_id).filter(Boolean))];
            const subjectPromises = uniqueSubjectIds.map(id => fetchAuthenticated(`${API_BASE_URL}/subjects/${id}`).catch(err => { console.warn(`Failed fetch subject ${id}`, err); return null; }));
            const subjectResults = await Promise.all(subjectPromises);
            const subjectsMap = subjectResults.reduce((acc, sub) => { if (sub) acc[sub.id] = sub; return acc; }, {});

            const uniqueGradeIds = [...new Set(Object.values(subjectsMap).map(s => s.grade_id).filter(Boolean))];
            const gradePromises = uniqueGradeIds.map(id => fetchAuthenticated(`${API_BASE_URL}/grades/${id}`).catch(err => { console.warn(`Failed fetch grade ${id}`, err); return null; }));
            const gradeResults = await Promise.all(gradePromises);
            const gradesMap = gradeResults.reduce((acc, gr) => { if (gr) acc[gr.id] = gr; return acc; }, {});

            const combinedData = assignmentSamples.map(sample => {
                // Defensive checks for potentially missing data
                const subj = subjectsMap[sample.subject_id];
                const grad = subj ? gradesMap[subj.grade_id] : null;
                const fileUrlObj = sample.urls?.find(u => u.url_type === 'https');
                return {
                    id: sample.id,
                    gradeName: grad?.name ?? 'Unknown Grade', // Nullish coalescing
                    subjectName: subj?.name ?? 'Unknown Subject',
                    documentName: sample.name ?? 'Untitled',
                    uploadedDate: sample.updated_at ? new Date(sample.updated_at).toLocaleDateString() : 'N/A',
                    uploadedBy: sample.creator_username || 'N/A',
                    fileUrl: fileUrlObj?.url ?? null, // Use optional chaining and nullish coalescing
                    fileSize: sample.file_size, subject_id: sample.subject_id, grade_id: subj?.grade_id,
                };
            }).filter(Boolean); // Ensure no null items in the final array

            setAssignments(combinedData);
            setFilteredAssignments(combinedData); // Initialize filter state
            setError(null); // Clear any previous errors on success

        } catch (err) {
            console.error("Error fetching assignment data:", err);
            // Set error state to display feedback to the user
            setError(err.message || "Failed to load assignment data. Please check connection or login.");
            // Optionally clear data on error or keep stale data
            setAssignments([]);
            setFilteredAssignments([]);
        } finally {
            // Only set loading to false if we showed the indicator
            if (showLoadingIndicator) setLoading(false);
            console.log("Assignment data fetch finished.");
        }
    }, []); // Empty dependency array is okay if it only fetches once or is manually called

    // --- Fetch Grades for Dropdown ---
    const fetchGrades = useCallback(async () => {
        setLoadingGrades(true);
        setGradesError(null);
        try {
            const grades = await fetchAuthenticated(`${API_BASE_URL}/grades/?skip=0&limit=100`);
            setGradesList(grades || []);
        } catch (error) {
            console.error("Failed to fetch grades:", error);
            setGradesError("Could not load grades.");
            setGradesList([]);
        } finally {
            setLoadingGrades(false);
        }
    }, []); // Empty dependency array

    // --- Fetch Subjects for Dropdown based on selected Grade ---
    const fetchSubjects = useCallback(async (selectedGradeId) => {
        if (!selectedGradeId) {
            setSubjectsList([]);
            setSubjectsError(null);
            setSubject(''); // Also clear the subject selection state
            return;
        }
        setLoadingSubjects(true);
        setSubjectsError(null);
        setSubjectsList([]); // Clear previous subjects
        setSubject(''); // Clear subject selection state while loading new ones
        try {
            // Ensure gradeId is valid before fetching
            if (isNaN(parseInt(selectedGradeId))) {
                throw new Error("Invalid Grade ID provided");
            }
            const subjects = await fetchAuthenticated(`${API_BASE_URL}/subjects/grade/${selectedGradeId}`);
            setSubjectsList(subjects || []);
            if (!subjects || subjects.length === 0) {
                setSubjectsError("No subjects found for this grade.");
            }
        } catch (error) {
            console.error(`Failed to fetch subjects for grade ${selectedGradeId}:`, error);
            setSubjectsError(error.message || "Could not load subjects.");
            setSubjectsList([]);
        } finally {
            setLoadingSubjects(false);
        }
    }, []); // Empty dependency array


    // Initial data fetch on component mount
    useEffect(() => {
        fetchAssignmentData();
        fetchGrades();
    }, [fetchAssignmentData, fetchGrades]); // Include callbacks

    // Effect to fetch subjects when grade changes
    useEffect(() => {
        // No need to reset subject state here, fetchSubjects does it now
        fetchSubjects(grade);
    }, [grade, fetchSubjects]);


    // --- Filtering Logic ---
    useEffect(() => {
        const lowerCaseSearchTerm = searchTerm.toLowerCase();
        // Ensure assignment properties exist before calling toLowerCase
        const result = assignments.filter(assignment =>
            (assignment.documentName?.toLowerCase() ?? '').includes(lowerCaseSearchTerm) ||
            (assignment.subjectName?.toLowerCase() ?? '').includes(lowerCaseSearchTerm) ||
            (assignment.gradeName?.toLowerCase() ?? '').includes(lowerCaseSearchTerm) ||
            (assignment.uploadedBy?.toLowerCase() ?? '').includes(lowerCaseSearchTerm)
        );
        setFilteredAssignments(result);
    }, [searchTerm, assignments]);


    // --- Handlers ---

    // Form Field Handlers
    const handleGradeChange = (event) => {
        setGrade(event.target.value); // Value is the grade ID
    };
    const handleSubjectChange = (event) => {
        setSubject(event.target.value); // Value is the subject ID
    };
    const handleTitleChange = (event) => setAssignmentTitle(event.target.value);
    const handleSearchChange = (event) => setSearchTerm(event.target.value);

    const handleFileChange = (event) => {
        if (event.target.files && event.target.files[0]) {
            const file = event.target.files[0];
            if (file.size > 10 * 1024 * 1024) {
                showSnackbar('File size exceeds 10MB limit.', 'error');
                setSelectedFile(null);
                // Reset using key now, no need for event.target.value = ''
                setFileInputKey(Date.now());
                return;
            }
            const allowedTypes = ['application/pdf'];
            if (!allowedTypes.includes(file.type)) {
                showSnackbar('Invalid file type. Only PDF is allowed.', 'error');
                setSelectedFile(null);
                setFileInputKey(Date.now());
                return;
            }
            setSelectedFile(file);
        } else {
            setSelectedFile(null);
        }
    };

    const handleNewFileChange = (event) => { /* ... remains the same ... */ };

    // Snackbar Handler
    const showSnackbar = (message, severity = 'success') => {
        setSnackbarMessage(message);
        setSnackbarSeverity(severity);
        setSnackbarOpen(true); // Open the snackbar
    };
    const handleSnackbarClose = (event, reason) => {
        if (reason === 'clickaway') return;
        setSnackbarOpen(false); // Close the snackbar
    };

    // --- Reset Upload Form ---
    const resetUploadForm = () => {
        setGrade('');
        // setSubject(''); // Not needed, useEffect for grade handles subject reset
        setAssignmentTitle('');
        setSelectedFile(null);
        setFileInputKey(Date.now()); // Reset file input via key change
    }

    // --- Create Operation ---
    const handleSaveAssignment = async () => {
        if (!grade || !subject || !assignmentTitle || !selectedFile) {
            showSnackbar('Please complete all fields: Grade, Subject, Title, and upload a PDF file.', 'warning');
            return;
        }

        setSubmitting(true); // Show loading state on button

        const formData = new FormData();
        formData.append('name', assignmentTitle);
        formData.append('subject_id', subject);
        formData.append('description', assignmentTitle);
        formData.append('pdf_file', selectedFile);

        let success = false;
        try {
            await fetchAuthenticated(`${API_BASE_URL}/assignment-samples/`, {
                method: 'POST',
                body: formData,
            });
            success = true; // Mark as success
            resetUploadForm(); // Reset form fields immediately on success

        } catch (err) {
            console.error("Failed to save assignment:", err);
            showSnackbar(`Error saving assignment: ${err.message}`, 'error');
            // Keep submitting false if error happens during API call itself
        } finally {
            // This block runs whether try succeeded or failed (unless an error was thrown *within* catch)
            setSubmitting(false); // Always stop loading indicator

            // Actions only after successful operation (and after state updates from reset have likely started)
            if (success) {
                // Use setTimeout to decouple Snackbar and data refresh from the submit/reset flow
                setTimeout(() => {
                    showSnackbar('Assignment saved successfully!'); // Show feedback AFTER potential UI reset
                    fetchAssignmentData(false); // Refresh the table data without main loading bar
                }, 100); // Slightly longer delay might be safer
            }
        }
    };


    // --- Edit Operation Handlers ---
    // const handleEditClick = (assignment) => { /* ... remains the same ... */ 
    //     setEditingAssignment(assignment); 
    //     setEditFormData({ grade: assignment.gradeName, subject: assignment.subjectName, documentName: assignment.documentName, }); 
    //     setNewSelectedFile(null); setEditOpen(true); };
    const handleEditClick = (assignment) => {
        if (!assignment) return; // Add a check

        // Store the full assignment object, including original IDs
        setEditingAssignment(assignment);

        // Populate form data ONLY with editable fields
        setEditFormData({
            documentName: assignment.documentName || '', // Use existing document name
            // Grade and Subject are not directly editable via this PUT,
            // so no need to put them in editFormData. We'll use original IDs on save.
        });
        setNewSelectedFile(null); // Reset file selection for edit dialog
        setEditOpen(true); // Open the dialog
    };
    const handleEditClose = () => { /* ... */ setEditOpen(false); setEditingAssignment(null); setNewSelectedFile(null); };
    const handleEditFormChange = (event) => { /* ... */ const { name, value } = event.target; setEditFormData(prev => ({ ...prev, [name]: value })); };
    // const handleEditSave = async () => { /* ... Needs API Integration ... */ showSnackbar('Update functionality requires API integration.', 'info'); console.log("TODO: Implement API call to update assignment"); handleEditClose(); };
    const handleEditSave = async () => {
        // Ensure we have the assignment object and the required name
        if (!editingAssignment || !editFormData.documentName) {
            showSnackbar('Assignment details are missing or document name is empty.', 'warning');
            return;
        }

        setUpdating(true); // Start loading indicator

        const formData = new FormData();
        formData.append('name', editFormData.documentName);
        formData.append('description', editFormData.documentName); // Use name as description or add a field

        // IMPORTANT: Use the original subject_id from the assignment being edited
        if (editingAssignment.subject_id) {
            formData.append('subject_id', editingAssignment.subject_id);
        } else {
            showSnackbar('Original subject ID is missing. Cannot update.', 'error');
            setUpdating(false);
            return; // Stop if critical data is missing
        }

        // Conditionally add the new file if one was selected
        if (newSelectedFile) {
            formData.append('pdf_file', newSelectedFile);
        }
        // Note: If no new file is selected, the API should ideally keep the old one.
        // If the API *requires* a file on PUT, you'd need different handling.

        let success = false;
        try {
            await fetchAuthenticated(`${API_BASE_URL}/assignment-samples/${editingAssignment.id}`, {
                method: 'PUT',
                body: formData,
            });
            success = true; // Mark success
            handleEditClose(); // Close dialog immediately on success

        } catch (err) {
            console.error("Failed to update assignment:", err);
            showSnackbar(`Error updating assignment: ${err.message}`, 'error');
            // Keep dialog open on error for user to retry or cancel
        } finally {
            setUpdating(false); // Stop loading indicator

            if (success) {
                // Use setTimeout to decouple Snackbar and data refresh
                setTimeout(() => {
                    showSnackbar('Assignment updated successfully!');
                    fetchAssignmentData(false); // Refresh table without main loading bar
                }, 100);
            }
        }
    };
    // --- Delete Operation Handlers ---
    const handleDeleteClick = (assignmentId) => { /* ... */ setDeletingAssignmentId(assignmentId); setDeleteOpen(true); };
    const handleDeleteClose = () => { /* ... */ setDeleteOpen(false); setDeletingAssignmentId(null); };
    // const handleDeleteConfirm = async () => { /* ... Needs API Integration ... */ showSnackbar('Delete functionality requires API integration.', 'info'); console.log("TODO: Implement API call to delete assignment"); handleDeleteClose(); };
    const handleDeleteConfirm = async () => {
        if (!deletingAssignmentId) return;

        setDeleting(true); // Start loading indicator

        let success = false;
        try {
            // Call the DELETE API
            await fetchAuthenticated(`${API_BASE_URL}/assignment-samples/${deletingAssignmentId}`, {
                method: 'DELETE',
                // DELETE often doesn't need 'accept' or 'content-type' headers,
                // but fetchAuthenticated adds 'accept: application/json' by default which might be fine.
                // API spec says 'accept: */*', fetchAuthenticated sends 'accept: application/json'
                // If strictly needed: headers: { 'accept': '*/*' }
            });
            success = true; // Mark success
            handleDeleteClose(); // Close dialog immediately on success

        } catch (err) {
            console.error("Failed to delete assignment:", err);
            showSnackbar(`Error deleting assignment: ${err.message}`, 'error');
            // Keep dialog open on error
        } finally {
            setDeleting(false); // Stop loading indicator

            if (success) {
                // Use setTimeout to decouple Snackbar and data refresh
                setTimeout(() => {
                    showSnackbar('Assignment deleted successfully!');
                    fetchAssignmentData(false); // Refresh table without main loading bar
                }, 100);
            }
        }
    };

    // --- Derived State for Disabling ---
    const isSubjectDisabled = !grade;
    const isUploadDisabled = !subject; // Disable Title and Upload if no subject selected
    const isSaveDisabled = !grade || !subject || !assignmentTitle || !selectedFile || submitting;


    // --- Render ---
    return (

        // Use a Box instead of div for top-level to easily apply sx if needed
        <Box sx={{ p: { xs: 2, sm: 3 }, bgcolor: 'grey.50', minHeight: '100vh' }}>
            {/* <TeacherTabs /> */}
            {/* <IconButton onClick={() => setDrawerOpen(true)}>
                <MenuIcon />
            </IconButton> */}

            <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold', mb: 4 }}>
                Assignment Paper Samples Management
            </Typography>

            {/* --- Upload Form Section --- */}
            <Paper elevation={2} sx={{ p: { xs: 2, sm: 3, md: 4 }, mb: 4 }}> {/* Added mb */}
                <Typography variant="h6" component="h2" sx={{ mb: 3, fontWeight: 'medium' }}>
                    Upload New Assignment Paper
                </Typography>
                <Grid container spacing={3}>
                    {/* Grade Select */}
                    <Grid item xs={12} md={6}>
                        <FormControl fullWidth required error={!!gradesError}>
                            <InputLabel id="grade-select-label">Grade</InputLabel>
                            <Select
                                labelId="grade-select-label"
                                id="grade-select"
                                value={grade}
                                label="Grade"
                                onChange={handleGradeChange}
                                disabled={loadingGrades}
                                renderValue={(selected) => { // Handle displaying name when value is ID
                                    if (!selected) { return <em>Select Grade</em>; }
                                    return gradesList.find(g => g.id === selected)?.name ?? selected;
                                }}
                            >
                                <MenuItem value="" disabled><em>Select Grade</em></MenuItem>
                                {loadingGrades && <MenuItem value="" disabled><CircularProgress size={20} sx={{ mr: 1 }} /> Loading...</MenuItem>}
                                {!loadingGrades && gradesList.map((g) => (
                                    <MenuItem key={g.id} value={g.id}>{g.name}</MenuItem>
                                ))}
                                {!loadingGrades && gradesList.length === 0 && !gradesError && <MenuItem value="" disabled>No grades found</MenuItem>}
                            </Select>
                            {gradesError && <FormHelperText error>{gradesError}</FormHelperText>}
                        </FormControl>
                    </Grid>
                    {/* Subject Select */}
                    <Grid item xs={12} md={6}>
                        <FormControl fullWidth required disabled={isSubjectDisabled || loadingSubjects} error={!!subjectsError}>
                            <InputLabel id="subject-select-label" shrink>
                                Subject
                            </InputLabel>
                            <Select
                                labelId="subject-select-label"
                                id="subject-select"
                                value={subject}
                                label="Subject"
                                onChange={handleSubjectChange}
                                displayEmpty // Allow placeholder when disabled
                                renderValue={(selected) => {
                                    if (!selected) { return <em>{isSubjectDisabled ? 'Select grade first':'Select Subject'}</em>; }
                                    return subjectsList.find(s => s.id === selected)?.name ?? selected;
                                }}
                            >
                                <MenuItem value="" disabled><em>{isSubjectDisabled ? 'Select grade first' : 'Select Subject'}</em></MenuItem>
                                {loadingSubjects && <MenuItem value="" disabled><CircularProgress size={20} sx={{ mr: 1 }} /> Loading...</MenuItem>}
                                {!loadingSubjects && subjectsList.map((s) => (
                                    <MenuItem key={s.id} value={s.id}>{s.name}</MenuItem>
                                ))}
                                {!loadingSubjects && grade && subjectsList.length === 0 && !subjectsError && <MenuItem value="" disabled>No subjects found</MenuItem>}
                            </Select>
                            {subjectsError && <FormHelperText error>{subjectsError}</FormHelperText>}
                        </FormControl>
                    </Grid>
                    {/* Upload Document */}
                    <Grid item xs={12} md={6}>
                        <Typography variant="body2" sx={{ mb: 1, fontWeight: 'medium', color: isUploadDisabled ? 'text.disabled' : 'inherit' }}>
                            Upload Document <span style={{ color: isUploadDisabled ? 'grey' : 'red' }}>*</span>
                        </Typography>
                        <input
                            accept=".pdf" // Strictly PDF as per API
                            style={{ display: 'none' }}
                            id="file-upload-input"
                            type="file"
                            onChange={handleFileChange}
                            disabled={isUploadDisabled}
                            key={fileInputKey} // Use key for resetting
                        />
                        <label htmlFor="file-upload-input">
                            {/* Pass disabled state to styled component */}
                            <FileUploadArea disabled={isUploadDisabled}>
                                <CloudUploadIcon sx={{ fontSize: 40, color: isUploadDisabled ? 'disabled' : 'primary.main', mb: 1 }} />
                                <Typography variant="body1" sx={{ color: isUploadDisabled ? 'text.disabled' : 'primary.main', fontWeight: 'medium', mb: 0.5 }}>
                                    Click to upload <span className={isUploadDisabled ? "text-gray-400 font-normal" : "text-gray-600 font-normal"}>or drag and drop</span>
                                </Typography>
                                <Typography variant="caption" sx={{ color: isUploadDisabled ? 'text.disabled' : 'text.secondary' }}> PDF up to 10MB </Typography>
                                {/* Conditionally render selected file text */}
                                {selectedFile && !isUploadDisabled && (
                                    <Typography variant="body2" sx={{ mt: 1, color: 'success.main', fontWeight: 'medium', wordBreak: 'break-all' }}>
                                        Selected: {selectedFile.name}
                                    </Typography>
                                )}
                            </FileUploadArea>
                        </label>
                    </Grid>
                    {/* Assignment Name/Title */}
                    <Grid item xs={12} md={6}>
                        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'flex-start', pt: { xs: 0, md: 3.5 } }}> {/* Adjusted padding instead of margin */}
                            <TextField
                                fullWidth
                                required
                                id="assignment-title"
                                label="Assignment Name/Title"
                                value={assignmentTitle}
                                onChange={handleTitleChange}
                                variant="outlined"
                                disabled={isUploadDisabled}
                            />
                        </Box>
                    </Grid>
                    {/* Save Button */}
                    <Grid item xs={12} sx={{ display: 'flex', justifyContent: 'flex-end', mt: 2 }}>
                        <Button
                            variant="contained"
                            startIcon={submitting ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
                            onClick={handleSaveAssignment}
                            disabled={isSaveDisabled}
                            sx={{
                                bgcolor: '#4f46e5', '&:hover': { bgcolor: '#4338ca' },
                                '&.Mui-disabled': { bgcolor: 'grey.400', cursor: 'not-allowed', pointerEvents: 'auto' } // Ensure disabled style is clear
                            }}
                        >
                            {submitting ? 'Saving...' : 'Save Assignment'}
                        </Button>
                    </Grid>
                </Grid>
            </Paper>

            {/* --- Assignment Samples Table Section --- */}
            <Paper elevation={2} sx={{ p: { xs: 2, sm: 3, md: 4 } }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 2 }}>
                    <Typography variant="h6" component="h2" sx={{ fontWeight: 'medium' }}> Assignment Paper Samples </Typography>
                    <TextField variant="outlined" size="small" placeholder="Search assignments..." value={searchTerm} onChange={handleSearchChange} InputProps={{ startAdornment: (<InputAdornment position="start"><SearchIcon /></InputAdornment>) }} sx={{ width: { xs: '100%', sm: 'auto' }, maxWidth: '300px' }} />
                </Box>
                {/* --- Loading / Error Display for Table --- */}
                {loading && <LinearProgress sx={{ mb: 2 }} />}
                {!loading && error && (<Alert severity="error" icon={<ErrorOutlineIcon fontSize="inherit" />} sx={{ mb: 2 }}> {error} </Alert>)}

                <TableContainer>
                    <Table sx={{ minWidth: 650 }} aria-label="assignment samples table">
                        <TableHead sx={{ bgcolor: 'grey.100' }}>
                            <TableRow>
                                <TableCell sx={{ fontWeight: 'bold', textTransform: 'uppercase' }}>Grade</TableCell>
                                <TableCell sx={{ fontWeight: 'bold', textTransform: 'uppercase' }}>Subject</TableCell>
                                <TableCell sx={{ fontWeight: 'bold', textTransform: 'uppercase' }}>Document Name</TableCell>
                                <TableCell sx={{ fontWeight: 'bold', textTransform: 'uppercase' }}>Uploaded Date</TableCell>
                                <TableCell sx={{ fontWeight: 'bold', textTransform: 'uppercase' }}>Uploaded By</TableCell>
                                <TableCell sx={{ fontWeight: 'bold', textTransform: 'uppercase', textAlign: 'center' }}>Actions</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {/* --- Table Rows --- */}
                            {!loading && !error && filteredAssignments.length > 0 ? (
                                filteredAssignments.map((row) => (
                                    <TableRow key={row.id} hover sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                        <TableCell>{row.gradeName}</TableCell>
                                        <TableCell>{row.subjectName}</TableCell>
                                        <TableCell sx={{ display: 'flex', alignItems: 'center' }}>
                                            {getDocumentIconFromUrl(row.fileUrl)}
                                            {row.fileUrl ? (
                                                <Link href={row.fileUrl} target="_blank" rel="noopener noreferrer" underline="hover" sx={{ ml: 0.5, wordBreak: 'break-word' }}>
                                                    {row.documentName}
                                                </Link>
                                            ) : (
                                                <Typography component="span" sx={{ ml: 0.5, wordBreak: 'break-word' }}>{row.documentName}</Typography>
                                            )}
                                        </TableCell>
                                        <TableCell>{row.uploadedDate}</TableCell>
                                        <TableCell>{row.uploadedBy}</TableCell>
                                        <TableCell align="center">
                                            <IconButton title="View" size="small" sx={{ color: 'primary.main' }} disabled={!row.fileUrl} onClick={() => row.fileUrl && window.open(row.fileUrl, '_blank')}><VisibilityIcon fontSize="inherit" /></IconButton>
                                            {/* Disable Edit/Delete for now as API is not implemented */}
                                            {/* <IconButton title="Edit (Not Implemented)" size="small" sx={{ color: 'warning.main', mx: 0.5 }} onClick={() => handleEditClick(row)} disabled><EditIcon fontSize="inherit" /></IconButton>
                                            <IconButton title="Delete (Not Implemented)" size="small" sx={{ color: 'error.main' }} onClick={() => handleDeleteClick(row.id)} disabled><DeleteIcon fontSize="inherit" /></IconButton> */}
                                            <IconButton title="Edit" size="small" sx={{ color: 'warning.main', mx: 0.5 }} onClick={() => handleEditClick(row)}><EditIcon fontSize="inherit" /></IconButton>
                                            <IconButton title="Delete" size="small" sx={{ color: 'error.main' }} onClick={() => handleDeleteClick(row.id)}><DeleteIcon fontSize="inherit" /></IconButton>

                                        </TableCell>
                                    </TableRow>
                                ))
                            ) : (
                                // --- No Data / Loading / Error Rows ---
                                <TableRow>
                                    <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                                        {loading ? (
                                            <> <CircularProgress size={24} sx={{ mr: 1 }} /> Loading data... </>
                                        ) : error ? (
                                            // Error is shown in the Alert above the table
                                            "Error loading data. See message above."
                                        ) : assignments.length === 0 ? (
                                            "No assignment samples uploaded yet."
                                        ) : (
                                            "No results match your search criteria."
                                        )}
                                    </TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </TableContainer>
            </Paper>

            {/* --- Edit Assignment Dialog (Placeholder) --- */}
            {/* <Dialog open={editOpen} onClose={handleEditClose} maxWidth="sm" fullWidth> ... </Dialog> */}
            {/* --- Edit Assignment Dialog --- */}
            <Dialog open={editOpen} onClose={handleEditClose} maxWidth="sm" fullWidth aria-labelledby="edit-dialog-title">
                <DialogTitle id="edit-dialog-title">
                    Edit Assignment Sample
                    <IconButton aria-label="close" onClick={handleEditClose} sx={{ position: 'absolute', right: 8, top: 8, color: (theme) => theme.palette.grey[500] }} disabled={updating}> <CloseIcon /> </IconButton>
                </DialogTitle>
                <DialogContent dividers>
                    {/* Render content only when editingAssignment is available */}
                    {editingAssignment && (
                        <Grid container spacing={3} sx={{ pt: 1 }}>
                            {/* Display current Grade/Subject (read-only) - Optional */}
                            <Grid item xs={12} sm={6}>
                                <TextField label="Grade (Current)" value={editingAssignment.gradeName || 'N/A'} variant="outlined" fullWidth disabled InputLabelProps={{ shrink: true }} />
                            </Grid>
                            <Grid item xs={12} sm={6}>
                                <TextField label="Subject (Current)" value={editingAssignment.subjectName || 'N/A'} variant="outlined" fullWidth disabled InputLabelProps={{ shrink: true }} />
                            </Grid>

                            {/* Assignment Name/Title (Editable) */}
                            <Grid item xs={12}>
                                <TextField
                                    fullWidth
                                    required
                                    autoFocus // Focus on this field when dialog opens
                                    margin="dense" // Use dense margin in dialogs
                                    name="documentName"
                                    label="Assignment Name/Title"
                                    value={editFormData.documentName}
                                    onChange={handleEditFormChange} // Reuse existing handler
                                    variant="outlined"
                                    disabled={updating} // Disable while updating
                                />
                            </Grid>

                            {/* Replace File */}
                            <Grid item xs={12}>
                                <Typography variant="body2" sx={{ mb: 1 }}>
                                    Current File: {getDocumentIconFromUrl(editingAssignment?.fileUrl)}
                                    {editingAssignment?.fileUrl ? (<Link href={editingAssignment.fileUrl} target="_blank" rel="noopener noreferrer">{editingAssignment?.documentName}</Link>) : (editingAssignment?.documentName || 'None')}
                                </Typography>
                                <Button variant="outlined" component="label" size="small" startIcon={<CloudUploadIcon />} disabled={updating}>
                                    Upload New PDF (Optional)
                                    {/* Ensure ID is unique if main form also has one */}
                                    <input type="file" hidden accept=".pdf" onChange={handleNewFileChange} id="edit-file-input" />
                                </Button>
                                {newSelectedFile && (
                                    <Typography variant="caption" display="block" sx={{ mt: 1, color: 'success.main', wordBreak: 'break-all' }}>
                                        New file selected: {newSelectedFile.name}
                                    </Typography>
                                )}
                                <Typography variant="caption" display="block" sx={{ mt: 0.5, color: 'text.secondary' }}> PDF up to 10MB </Typography>
                            </Grid>
                        </Grid>
                    )}
                    {/* Show loading indicator centrally if needed while fetching initial data */}
                    {/* {!editingAssignment && <CircularProgress />} */}
                </DialogContent>
                <DialogActions sx={{ p: '16px 24px' }}>
                    <Button onClick={handleEditClose} disabled={updating}>Cancel</Button>
                    <Button
                        onClick={handleEditSave}
                        variant="contained"
                        startIcon={updating ? <CircularProgress size={20} color="inherit" /> : <SaveIcon />}
                        disabled={updating || !editFormData.documentName} // Also disable if name is empty
                    >
                        {updating ? 'Saving...' : 'Save Changes'}
                    </Button>
                </DialogActions>
            </Dialog>

            {/* --- Delete Confirmation Dialog (Placeholder) --- */}
            {/* <Dialog open={deleteOpen} onClose={handleDeleteClose} > ... </Dialog> */}
            {/* --- Delete Confirmation Dialog --- */}
            <Dialog
                open={deleteOpen}
                onClose={handleDeleteClose} // Prevent closing while deleting
                aria-labelledby="alert-dialog-title"
                aria-describedby="alert-dialog-description"
            >
                <DialogTitle id="alert-dialog-title">Confirm Deletion</DialogTitle>
                <DialogContent>
                    <DialogContentText id="alert-dialog-description">
                        Are you sure you want to delete the assignment sample titled: <br />
                        <strong>{assignments.find(a => a.id === deletingAssignmentId)?.documentName || 'this assignment'}</strong>? <br />
                        This action cannot be undone.
                    </DialogContentText>
                </DialogContent>
                <DialogActions>
                    {/* Disable Cancel button while delete is in progress */}
                    <Button onClick={handleDeleteClose} disabled={deleting}>Cancel</Button>
                    <Button
                        onClick={handleDeleteConfirm}
                        color="error"
                        variant="contained"
                        disabled={deleting} // Disable button while deleting
                        startIcon={deleting ? <CircularProgress size={20} color="inherit" /> : null} // Show spinner
                        autoFocus
                    >
                        {deleting ? 'Deleting...' : 'Confirm Delete'}
                    </Button>
                </DialogActions>
            </Dialog>
            {/* --- Snackbar for Feedback --- */}
            <Snackbar
                ref={snackbarRef} // Assign ref
                open={snackbarOpen}
                autoHideDuration={6000}
                onClose={handleSnackbarClose}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
            // Consider removing the default Grow transition if it causes issues
            // TransitionComponent={undefined} // Uncomment to disable transition
            >
                {/* Wrap Alert in a Box to potentially help transitions */}
                <Box>
                    <Alert onClose={handleSnackbarClose} severity={snackbarSeverity} variant="filled" sx={{ width: '100%' }}>
                        {snackbarMessage}
                    </Alert>
                </Box>
            </Snackbar>
        </Box>
    );
}

export default AssignmentUploadPDF;