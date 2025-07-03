// src/components/AssignmentPaperFormatManagement.js
import React, { useState, useEffect, useCallback } from 'react';
import {
    // ... other MUI imports (Container, Paper, Typography, Grid, FormControl, etc.)
    Container, Paper, Typography, Grid, FormControl,
    MenuItem,
    Select,
    ListItemButton,
    ListItemText,
    ListItem,
    Drawer,
    List,
    InputLabel, TextField, Button, Box, Chip, Stack, 
    TableContainer, Table, TableHead, Tooltip, TableBody, TableRow, TableCell,
     IconButton, Dialog, DialogTitle, DialogContent, DialogActions, CircularProgress, Alert, FormHelperText
} from '@mui/material';
import {
    // ... other MUI Icons (Visibility, AddCircleOutline, etc.)
    Visibility, Edit, Delete, AddCircleOutline, RemoveCircleOutline, Close as CloseIcon
} from '@mui/icons-material';
import ArticleIcon from '@mui/icons-material/Article'; // For Sample Papers
import FormatAlignLeftIcon from '@mui/icons-material/FormatAlignLeft'; // For Format Management

// import TeacherDashboardHeader from './teacherDashboardHeader';

// --- Constants & Config (Unchanged) ---
const API_BASE_URL = 'https://lms-backend-931876132356.us-central1.run.app';
const questionDistributionConfig = [ // Ensure apiType matches API expectations
    { uiType: 'Fill in the Blanks', apiType: 'fill_in_blanks', initialCount: 0, lightBg: '#e3f2fd', brightText: '#1976d2' },
    { uiType: 'Short Answer', apiType: 'short_answer', initialCount: 0, lightBg: '#e8f5e9', brightText: '#2e7d32' },
    { uiType: 'Match the Following', apiType: 'match_following', initialCount: 0, lightBg: '#f3e5f5', brightText: '#7b1fa2' },
    { uiType: 'Single Select', apiType: 'single_select', initialCount: 0, lightBg: '#fff8e1', brightText: '#ef6c00' },
    { uiType: 'Multi Select', apiType: 'multi_select', initialCount: 0, lightBg: '#ffebee', brightText: '#d32f2f' },
];

// --- Helper Functions (Unchanged) ---
const formatDate = (isoString) => { /* ... */
    if (!isoString) return ''; try { const d = new Date(isoString); return d.toISOString().split('T')[0]; } catch (e) { return isoString; }
};
const formatQuestionType = (typeString) => { /* ... */
    if (!typeString) return ''; return typeString.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
};
const getAuthToken = () => localStorage.getItem('accessToken');

// --- API Call Helper (Updated to better handle DELETE potentially) ---
const fetchApi = async (url, options = {}) => {
    const token = getAuthToken();
    if (!token) { throw new Error('Authentication token not found.'); }

    const headers = {
        'accept': 'application/json', // Default accept header
        'Authorization': `Bearer ${token}`,
        ...options.headers,
    };
    // Adjust accept header specifically for DELETE if needed, otherwise keep json
    if (options.method === 'DELETE') {
        // headers['accept'] = '*/*'; // Use this ONLY if API strictly requires it
    }


    const response = await fetch(url, { ...options, headers });

    if (!response.ok) {
        let errorMsg = `HTTP error! Status: ${response.status}`;
        // Try reading error details only if content type suggests JSON
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            try {
                const errorData = await response.json();
                errorMsg = errorData.detail || JSON.stringify(errorData) || errorMsg;
            } catch (e) { /* Ignore JSON parse error if body is not JSON */ }
        }
        throw new Error(errorMsg);
    }

    // Handle empty successful responses (like DELETE or maybe some POST/PUT)
    if (response.status === 200 || response.status === 204) { // 204 No Content is common for DELETE/PUT
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            // If JSON is expected and present, parse it
            // Handle potentially empty JSON response body
            const text = await response.text();
            return text ? JSON.parse(text) : { success: true }; // Return JSON or success flag
        } else {
            // If no JSON body expected/returned, indicate success
            return { success: true };
        }
    }
    // Default: Assume JSON response for other successful statuses
    return await response.json();
};
// --- End API Call Helper ---


function AssignmentFormat() {
    // --- State for Create Form (mostly unchanged) ---
    const [drawerOpen, setDrawerOpen] = useState(false);

    const [selectedGrade, setSelectedGrade] = useState('');
    const [selectedSubject, setSelectedSubject] = useState('');
    const [selectedSample, setSelectedSample] = useState('');
    const [formatName, setFormatName] = useState('');
    const [showDistribution, setShowDistribution] = useState(false);
    const [gradesList, setGradesList] = useState([]);
    const [subjectsList, setSubjectsList] = useState([]);
    const [samplesList, setSamplesList] = useState([]);
    const [gradesLoading, setGradesLoading] = useState(false);
    const [subjectsLoading, setSubjectsLoading] = useState(false);
    const [samplesLoading, setSamplesLoading] = useState(false);
    const [dropdownError, setDropdownError] = useState(null);
    const [distributionCounts, setDistributionCounts] = useState(
        questionDistributionConfig.map(item => ({ ...item, count: String(item.initialCount) }))
    );
    const [analyzeLoading, setAnalyzeLoading] = useState(false);
    const [analyzeError, setAnalyzeError] = useState(null);
    const [createLoading, setCreateLoading] = useState(false);
    const [createError, setCreateError] = useState(null);
    const [createSuccess, setCreateSuccess] = useState(null);

    // --- State for Formats Table (unchanged) ---
    const [formats, setFormats] = useState([]);
    const [formatsLoading, setFormatsLoading] = useState(false);
    const [formatsError, setFormatsError] = useState(null);

    // --- State for View Modal (unchanged) ---
    const [modalOpen, setModalOpen] = useState(false);
    const [selectedFormatDetails, setSelectedFormatDetails] = useState(null);

    // --- State for Edit Modal ---
    const [editModalOpen, setEditModalOpen] = useState(false);
    const [editingFormat, setEditingFormat] = useState(null); // Holds the full format object being edited {id, name, questions, ...}
    const [editFormatName, setEditFormatName] = useState(''); // Temp state for name input in modal
    const [editDistributionCounts, setEditDistributionCounts] = useState([]); // Temp state for counts in modal
    const [editLoading, setEditLoading] = useState(false);
    const [editError, setEditError] = useState(null);

    // --- State for Delete Operation ---
    const [deleteLoading, setDeleteLoading] = useState(false);
    const [deleteError, setDeleteError] = useState(null);
    const [deletingFormatId, setDeletingFormatId] = useState(null); // Track which ID is being deleted

    // --- State for Delete Confirmation Dialog ---
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
    const [formatToDeleteId, setFormatToDeleteId] = useState(null); // Store the ID to delete

    // --- Fetch Formats List (Bottom Table) ---
    const fetchFormatsList = useCallback(async () => {
        setFormatsLoading(true); setFormatsError(null);
        try {
            const data = await fetchApi(`${API_BASE_URL}/assignment-formats/`);
            setFormats(data || []);
        } catch (err) { console.error("Failed fetch formats:", err); setFormatsError(err.message); }
        finally { setFormatsLoading(false); }
    }, []);
    useEffect(() => { fetchFormatsList(); }, [fetchFormatsList]);

    // --- Fetch Grades, Subjects, Samples (Unchanged) ---
    useEffect(() => {
        const fetchGrades = async () => {
            setGradesLoading(true);
            setDropdownError(null);
            try {
                // Added query params as per curl example
                const data = await fetchApi(`${API_BASE_URL}/grades/?skip=0&limit=100`);
                setGradesList(data || []);
            } catch (err) {
                console.error("Failed to fetch grades:", err);
                setDropdownError(`Grades: ${err.message}`);
                setGradesList([]); // Clear list on error
            } finally {
                setGradesLoading(false);
            }
        };
        fetchGrades();
    }, []);

    // --- Fetch Subjects (when Grade changes) ---
    useEffect(() => {
        // Reset dependent fields when grade changes
        setSelectedSubject('');
        setSubjectsList([]);
        setSelectedSample('');
        setSamplesList([]);
        setShowDistribution(false); // Hide distribution if grade changes

        if (selectedGrade) {
            const fetchSubjects = async () => {
                setSubjectsLoading(true);
                setDropdownError(null);
                try {
                    const data = await fetchApi(`${API_BASE_URL}/subjects/grade/${selectedGrade}`);
                    setSubjectsList(data || []);
                } catch (err) {
                    console.error("Failed to fetch subjects:", err);
                    setDropdownError(`Subjects: ${err.message}`);
                    setSubjectsList([]);
                } finally {
                    setSubjectsLoading(false);
                }
            };
            fetchSubjects();
        }
    }, [selectedGrade]); // Dependency: selectedGrade ID

    // --- Fetch Assignment Samples (when Subject changes) ---
    useEffect(() => {
        // Reset dependent fields when subject changes
        setSelectedSample('');
        setSamplesList([]);
        setShowDistribution(false); // Hide distribution if subject changes

        if (selectedSubject) {
            const fetchSamples = async () => {
                setSamplesLoading(true);
                setDropdownError(null);
                try {
                    const data = await fetchApi(`${API_BASE_URL}/assignment-samples/?subject_id=${selectedSubject}`);
                    setSamplesList(data || []);
                } catch (err) {
                    console.error("Failed to fetch assignment samples:", err);
                    setDropdownError(`Samples: ${err.message}`);
                    setSamplesList([]);
                } finally {
                    setSamplesLoading(false);
                }
            };
            fetchSamples();
        }
    }, [selectedSubject]); // Dependency: selectedSubject ID


    // --- Analyze Assignment Sample (Unchanged) ---
    const handleShowDistributionClick = async () => { /* ... */
        if (!selectedSample) return;
        setAnalyzeLoading(true); setAnalyzeError(null); setShowDistribution(false);
        try {
            const response = await fetchApi(`${API_BASE_URL}/assignment-samples/${selectedSample}/analyze`, 
                { method: 'POST' });
            if (!response || !response.question_counts) { throw new Error("Invalid analyze response."); }
            const countsFromApi = response.question_counts;
            setDistributionCounts(questionDistributionConfig.map(uiItem => {
                const apiData = countsFromApi.find(apiItem => apiItem.type === uiItem.apiType);
                return { ...uiItem, count: String(apiData ? apiData.count : 0) };
            }));
            setShowDistribution(true);
        } catch (err) { console.error("Analyze failed:", err); setAnalyzeError(err.message); setShowDistribution(false); }
        finally { setAnalyzeLoading(false); }
    };

    // --- Create Assignment Format (Unchanged) ---
    const handleCreateFormatClick = async () => { /* ... */
        if (!formatName.trim()) { setCreateError('Format Name required.'); return; }
        setCreateLoading(true); setCreateError(null); setCreateSuccess(null);
        const questionsPayload = distributionCounts.map(item => ({
            type: item.apiType, count: parseInt(item.count || '0', 10)
        }));
        const payload = { name: formatName.trim(), questions: questionsPayload, subject_id: `${selectedSubject}` };
        try {
            const response = await fetchApi(`${API_BASE_URL}/assignment-formats/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, 
                body: JSON.stringify(payload) });
            setCreateSuccess(`Format "${response.name}" created!`);
            setFormatName(''); setSelectedGrade(''); setShowDistribution(false);
            setDistributionCounts(questionDistributionConfig.map(item => ({ ...item, count: String(item.initialCount) })));
            fetchFormatsList(); // Refresh list
        } catch (err) { console.error("Create failed:", err); setCreateError(err.message); }
        finally { setCreateLoading(false); }
    };

    // --- Distribution Count Handlers (for Create form - unchanged) ---
    const handleCountChange = (index, event) => { /* ... (updates distributionCounts) ... */
        const newValue = event.target.value;
        if (newValue === '' || /^[0-9]\d*$/.test(newValue)) {
            setDistributionCounts(currentCounts =>
                currentCounts.map((item, i) => i === index ? { ...item, count: newValue } : item)
            );
        }
    };
    const handleIncrementDecrement = (index, delta) => { /* ... (updates distributionCounts) ... */
        setDistributionCounts(currentCounts =>
            currentCounts.map((item, i) => {
                if (i === index) {
                    const currentVal = parseInt(item.count || '0', 10);
                    let newVal = Math.max(0, currentVal + delta);
                    return { ...item, count: String(newVal) };
                }
                return item;
            })
        );
    };

    // --- Distribution Count Handlers (for EDIT MODAL) ---
    const handleEditCountChange = (index, event) => {
        const newValue = event.target.value;
        if (newValue === '' || /^[0-9]\d*$/.test(newValue)) {
            setEditDistributionCounts(currentCounts =>
                currentCounts.map((item, i) => i === index ? { ...item, count: newValue } : item)
            );
        }
    };
    const handleEditIncrementDecrement = (index, delta) => {
        setEditDistributionCounts(currentCounts =>
            currentCounts.map((item, i) => {
                if (i === index) {
                    const currentVal = parseInt(item.count || '0', 10);
                    let newVal = Math.max(0, currentVal + delta);
                    return { ...item, count: String(newVal) };
                }
                return item;
            })
        );
    };


    // --- View Modal Handlers (Unchanged) ---
    const handleView = (id) => { /* ... */
        const formatToShow = formats.find(format => format.id === id);
        if (formatToShow) { setSelectedFormatDetails(formatToShow); setModalOpen(true); }
        else { console.error("Format not found:", id); setFormatsError("Could not find details."); }
    };
    const handleCloseModal = () => { /* ... */ setModalOpen(false); setSelectedFormatDetails(null); };

    // --- Edit Modal Handlers ---
    const handleEdit = (id) => {
        const formatToEdit = formats.find(format => format.id === id);
        if (formatToEdit) {
            setEditingFormat(formatToEdit);
            setEditFormatName(formatToEdit.name);

            // Initialize editDistributionCounts based on the format's questions
            // Map API data to the UI structure used by the counter component
            const initialEditCounts = questionDistributionConfig.map(uiConfig => {
                const apiQuestion = formatToEdit.questions?.find(q => q.question_type === uiConfig.apiType);
                return {
                    ...uiConfig, // Include uiType, apiType, colors etc.
                    count: String(apiQuestion ? apiQuestion.count : 0) // Get count or default to 0, store as string
                };
            });
            setEditDistributionCounts(initialEditCounts);

            setEditModalOpen(true);
            setEditError(null); // Clear previous errors
        } else {
            console.error("Format to edit not found:", id);
            setFormatsError("Could not find the format to edit.");
        }
    };

    const handleCloseEditModal = () => {
        setEditModalOpen(false);
        setEditingFormat(null);
        setEditFormatName('');
        setEditDistributionCounts([]);
        setEditError(null);
        setEditLoading(false);
    };

    const handleSaveChanges = async () => {
        if (!editingFormat || !editFormatName.trim()) {
            setEditError("Format Name cannot be empty.");
            return;
        }

        setEditLoading(true);
        setEditError(null);

        const questionsPayload = editDistributionCounts.map(item => ({
            type: item.apiType,
            count: parseInt(item.count || '0', 10)
        }));

        // Optional: Filter zero counts if needed
        // const filteredQuestionsPayload = questionsPayload.filter(q => q.count > 0);

        const payload = {
            name: editFormatName.trim(),
            questions: questionsPayload // or filteredQuestionsPayload
        };

        try {
            await fetchApi(
                `${API_BASE_URL}/assignment-formats/${editingFormat.id}`,
                {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                }
            );
            handleCloseEditModal(); // Close modal on success
            fetchFormatsList(); // Refresh the main list
            // Optionally show a success message (e.g., using a Snackbar)
        } catch (err) {
            console.error("Failed to update assignment format:", err);
            setEditError(err.message);
        } finally {
            setEditLoading(false);
        }
    };

    // --- Delete Handler (Opens Confirmation Dialog) ---
    const handleDelete = (id) => {
        setFormatToDeleteId(id); // Store the ID of the format targeted for deletion
        setDeleteConfirmOpen(true); // Open the confirmation dialog
        setDeleteError(null); // Clear previous delete errors when opening dialog
    };

    // --- Closes the Delete Confirmation Dialog ---
    const handleCloseDeleteConfirm = () => {
        setDeleteConfirmOpen(false);
        setFormatToDeleteId(null); // Clear the stored ID
    };

    // --- Performs the Actual Deletion After Confirmation ---
    const handleConfirmDelete = async () => {
        if (!formatToDeleteId) return; // Safety check

        handleCloseDeleteConfirm(); // Close the dialog first

        setDeletingFormatId(formatToDeleteId); // Track which one is being deleted visually
        setDeleteLoading(true);
        setDeleteError(null);

        try {
            await fetchApi(
                `${API_BASE_URL}/assignment-formats/${formatToDeleteId}`,
                { method: 'DELETE' }
            );
            fetchFormatsList(); // Refresh list on success
            // Optionally show success message (e.g., using a Snackbar)

        } catch (err) {
            console.error("Failed to delete assignment format:", err);
            setDeleteError(`Failed to delete format ${formatToDeleteId}: ${err.message}`);
            // Display error near the table or globally
        } finally {
            setDeleteLoading(false);
            setDeletingFormatId(null); // Stop visual tracking
        }
    };

    // --- Render ---
    return (
        <Box sx={{ 
            width: '100%', 
            mt: 4, 
            mb: 4, 
            padding: '0 20px',
            maxWidth: '100%',
            boxSizing: 'border-box'
        }}>
            {/* <TeacherDashboardHeader /> */}
            
            <Stack spacing={4} sx={{ width: '100%' }}>
                {/* --- Create New Assignment Format Section (UI Mostly Unchanged) --- */}
                <Paper elevation={2} sx={{ 
                    p: { xs: 2, md: 3 }, 
                    borderRadius: 2,
                    width: '100%' 
                }}>
                    {/* ... (Create Form Title, Dropdowns, Format Name Input, Distribution Section, Create Button as before) ... */}
                    {/* Make sure loading/disabled states are correctly applied */}
                    <Typography variant="h5" component="h2" gutterBottom sx={{ fontWeight: 'bold', mb: 3 }}> Create New Assignment Format </Typography>
                    {dropdownError && <Alert severity="warning" sx={{ mb: 2 }}>{dropdownError}</Alert>}
                    <Grid container spacing={2} alignItems="flex-start" sx={{ mb: 3, width: '100%' }}>
                        <Grid item xs={12} sm={6} md={6} sx={{ width: '100%' }}> <FormControl fullWidth variant="outlined" size="small" error={!!dropdownError && gradesList.length === 0}> <InputLabel id="grade-select-label">Grade</InputLabel> <Select labelId="grade-select-label" value={selectedGrade} onChange={(e) => setSelectedGrade(e.target.value)} label="Grade" disabled={gradesLoading}> <MenuItem value="" disabled><em>{gradesLoading ? 'Loading...' : 'Select Grade'}</em></MenuItem> {gradesList.map((grade) => <MenuItem key={grade.id} value={grade.id}>{grade.name}</MenuItem>)} </Select> {gradesLoading && <FormHelperText sx={{ ml: 1 }}>Loading...</FormHelperText>} </FormControl> </Grid>
                        <Grid item xs={12} sm={6} md> <FormControl fullWidth variant="outlined" size="small" disabled={!selectedGrade || subjectsLoading} error={!!dropdownError && selectedGrade && subjectsList.length === 0}> <InputLabel id="subject-select-label">Subject</InputLabel> <Select labelId="subject-select-label" value={selectedSubject} onChange={(e) => setSelectedSubject(e.target.value)} label="Subject"> <MenuItem value="" disabled><em>{subjectsLoading ? 'Loading...' : (selectedGrade ? 'Select Subject' : 'Select Grade First')}</em></MenuItem> {subjectsList.map((subject) => <MenuItem key={subject.id} value={subject.id}>{subject.name}</MenuItem>)} </Select> {subjectsLoading && <FormHelperText sx={{ ml: 1 }}>Loading...</FormHelperText>} </FormControl> </Grid>
                        <Grid item xs={12} sm={6} md> <FormControl fullWidth variant="outlined" size="small" disabled={!selectedSubject || samplesLoading} error={!!dropdownError && selectedSubject && samplesList.length === 0}> <InputLabel id="sample-select-label">Assignment Sample</InputLabel> <Select labelId="sample-select-label" value={selectedSample} onChange={(e) => setSelectedSample(e.target.value)} label="Assignment Sample"> <MenuItem value="" disabled><em>{samplesLoading ? 'Loading...' : (selectedSubject ? 'Select Sample' : 'Select Subject First')}</em></MenuItem> {samplesList.map((sample) => <MenuItem key={sample.id} value={sample.id}>{sample.name}</MenuItem>)} </Select> {samplesLoading && <FormHelperText sx={{ ml: 1 }}>Loading...</FormHelperText>} </FormControl> </Grid>
                        <Grid item xs={12} sm={6} md sx={{ width: '100%', textAlign: { xs: 'left', sm: 'right' }, pt: { xs: 2, sm: '3px' } }}> <Button variant="contained" onClick={handleShowDistributionClick} disabled={!selectedGrade || !selectedSubject || !selectedSample || analyzeLoading} size="medium" sx={{ height: '40px', position: 'relative' }} startIcon={analyzeLoading ? <CircularProgress size={20} color="inherit" /> : null} > {analyzeLoading ? 'Analyzing...' : 'Show Question Distribution'} </Button> </Grid>
                    </Grid>
                    {analyzeError && <Alert severity="error" sx={{ mb: 2 }}>Analyze Error: {analyzeError}</Alert>}
                    {showDistribution && (
                        <Box sx={{ mb: 3, width: '100%' }}>
                            <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'medium', mb: 1.5 }}> Question Type Distribution </Typography>
                            <Stack direction="row" spacing={1.5} useFlexGap flexWrap="wrap" sx={{ mb: 1 }}> {distributionCounts.map((item, index) => (<Chip key={item.uiType} variant="outlined" sx={{ p: 0, height: 'auto', minWidth: '150px', '& .MuiChip-label': { px: 1.5, py: 0.8, display: 'flex', alignItems: 'center', width: '100%' } }} label={<Stack direction="row" justifyContent="space-between" alignItems="center" width="100%">
                                <Typography variant="body2" component="span" sx={{ mr: 1, flexGrow: 1 }}> {item.uiType} </Typography>
                                <Stack direction="row" alignItems="center" spacing={0.5}>
                                    <IconButton aria-label={`Decrease ${item.uiType} count`} onClick={() => handleIncrementDecrement(index, -1)} size="small" disabled={parseInt(item.count || '0', 10) <= 0} sx={{ p: 0.2, color: item.brightText }} > <RemoveCircleOutline fontSize="inherit" sx={{ fontSize: '1rem' }} /> </IconButton> <TextField value={item.count} onChange={(e) => handleCountChange(index, e)} variant="standard" inputProps={{ 'aria-label': `${item.uiType} count`, style: { textAlign: 'center', appearance: 'textfield', MozAppearance: 'textfield', padding: 0 }, sx: { width: '24px', height: '24px', boxSizing: 'border-box', borderRadius: '50%', backgroundColor: item.lightBg, color: item.brightText, fontSize: '0.8rem', fontWeight: 'bold', lineHeight: '24px' } }} sx={{ width: '24px', '& .MuiInput-underline:before, & .MuiInput-underline:hover:not(.Mui-disabled):before, & .MuiInput-underline:after': { borderBottom: 'none' }, '& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button': { WebkitAppearance: 'none', margin: 0 } }} /> <IconButton aria-label={`Increase ${item.uiType} count`} onClick={() => handleIncrementDecrement(index, 1)} size="small" sx={{ p: 0.2, color: item.brightText }} > <AddCircleOutline fontSize="inherit" sx={{ fontSize: '1rem' }} /> </IconButton> </Stack> </Stack>} />))} </Stack> <Typography variant="caption" display="block" color="text.secondary"> Modify counts if needed. </Typography>

                            <Grid container spacing={2} sx={{ mb: 3, width: '100%' }}>
                                <Grid item xs={12} sx={{ width: '100%' }}> <TextField fullWidth label="Format Name" variant="outlined" size="small" placeholder="Enter a descriptive name" value={formatName} onChange={(e) => setFormatName(e.target.value)} error={!!createError && !formatName.trim()} helperText={createError && !formatName.trim() ? "Required" : ""} /> </Grid> </Grid>
                            <Grid container justifyContent="flex-end" sx={{ width: '100%' }}>
                                <Grid item sx={{ width: '100%' }}> <Button variant="contained" onClick={handleCreateFormatClick} size="large" disabled={createLoading} startIcon={createLoading ? <CircularProgress size={20} color="inherit" /> : null} > {createLoading ? 'Creating...' : 'Create Format'} </Button> </Grid> </Grid>

                        </Box>

                    )}
                    {createError && <Alert severity="error" sx={{ mb: 2 }}>{createError}</Alert>} {createSuccess && <Alert severity="success" sx={{ mb: 2 }}>{createSuccess}</Alert>}
                    {/* <Grid container justifyContent="flex-end"> <Grid item> <Button variant="contained" onClick={handleCreateFormatClick} size="large" disabled={createLoading} startIcon={createLoading ? <CircularProgress size={20} color="inherit" /> : null} > {createLoading ? 'Creating...' : 'Create Format'} </Button> </Grid> </Grid> */}
                </Paper>

                {/* --- Assignment Paper Formats List Section --- */}
                <Paper elevation={2} sx={{ 
                    p: { xs: 2, md: 3 }, 
                    mt: 4, 
                    borderRadius: 2,
                    width: '100%' 
                }}>
                    <Typography variant="h5" component="h2" gutterBottom sx={{ fontWeight: 'bold' }}> Assignment Paper Formats </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}> Manage your assignment paper formats. </Typography>

                    {/* Loading and Error Display for Table */}
                    {formatsLoading && (<Box sx={{ display: 'flex', justifyContent: 'center', my: 3 }}> <CircularProgress /> </Box>)}
                    {formatsError && (<Alert severity="error" sx={{ my: 2 }}>{formatsError}</Alert>)}
                    {deleteError && (<Alert severity="error" sx={{ my: 2 }}>{deleteError}</Alert>)} {/* Show delete errors here */}


                    {!formatsLoading && !formatsError && (
                        <TableContainer component={Paper} variant="outlined" sx={{ 
                        borderColor: 'grey.200',
                        width: '100%' 
                    }}>
                            <Table sx={{ minWidth: 650 }} aria-label="assignment formats table">
                                <TableHead sx={{ backgroundColor: 'grey.50' }}>
                                    <TableRow>
                                        <TableCell sx={{ fontWeight: 'bold', color: 'text.primary', py: 1 }}>FORMAT NAME</TableCell>
                                        <TableCell sx={{ fontWeight: 'bold', color: 'text.primary', py: 1 }}>CREATED DATE</TableCell>
                                        <TableCell sx={{ fontWeight: 'bold', color: 'text.primary', py: 1 }}>CREATED BY</TableCell>
                                        <TableCell align="center" sx={{ fontWeight: 'bold', color: 'text.primary', py: 1 }}>ACTIONS</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {formats.length > 0 ? (
                                        formats.map((row) => (
                                            <TableRow key={row.id} hover sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
                                                <TableCell sx={{ fontWeight: 'medium', py: 1.5 }}>{row.name}</TableCell>
                                                <TableCell sx={{ py: 1.5 }}>{formatDate(row.created_at)}</TableCell>
                                                <TableCell sx={{ py: 1.5 }}>{row.creator_username}</TableCell>
                                                <TableCell align="center" sx={{ py: 1 }}>
                                                    <Box sx={{ position: 'relative', display: 'inline-block' }}> {/* Wrapper for loading indicator */}
                                                        <IconButton size="small" color="info" onClick={() => handleView(row.id)} aria-label="view format" sx={{ mr: 0.5 }} disabled={deleteLoading && deletingFormatId === row.id}><Visibility fontSize="inherit" /></IconButton>
                                                        <IconButton size="small" color="primary" onClick={() => handleEdit(row.id)} aria-label="edit format" sx={{ mr: 0.5 }} disabled={deleteLoading && deletingFormatId === row.id}><Edit fontSize="inherit" /></IconButton>
                                                        <IconButton size="small" color="error" onClick={() => handleDelete(row.id)} aria-label="delete format" disabled={deleteLoading && deletingFormatId === row.id}><Delete fontSize="inherit" /></IconButton>
                                                        {/* Show loading spinner next to icons for the row being deleted */}
                                                        {deleteLoading && deletingFormatId === row.id && (
                                                            <CircularProgress size={20} sx={{ position: 'absolute', top: '50%', right: -25, marginTop: '-10px' }} />
                                                        )}
                                                    </Box>
                                                </TableCell>
                                            </TableRow>
                                        ))
                                    ) : (
                                        <TableRow><TableCell colSpan={4} align="center" sx={{ py: 3 }}>No assignment formats found.</TableCell></TableRow>
                                    )}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    )}
                </Paper>
            </Stack>

            {/* --- View Details Modal Dialog (Unchanged) --- */}
            <Dialog open={modalOpen} onClose={handleCloseModal} aria-labelledby="format-details-dialog-title" maxWidth="sm" fullWidth >
                <DialogTitle id="format-details-dialog-title"> Assignment Sample Format Details <IconButton aria-label="close" onClick={handleCloseModal} sx={{ position: 'absolute', right: 8, top: 8, color: (theme) => theme.palette.grey[500] }} > <CloseIcon /> </IconButton> </DialogTitle>
                <DialogContent dividers>
                    {selectedFormatDetails ? (
                        <TableContainer component={Paper} variant="outlined">
                            <Table size="small" aria-label="question distribution details">
                                <TableHead> <TableRow sx={{ backgroundColor: 'grey.100' }}> <TableCell sx={{ fontWeight: 'bold' }}>Question Type</TableCell> <TableCell align="right" sx={{ fontWeight: 'bold' }}>No. of Questions</TableCell> </TableRow> </TableHead>
                                <TableBody>
                                    {selectedFormatDetails.questions && selectedFormatDetails.questions.length > 0 ? (
                                        selectedFormatDetails.questions.map((q) => (<TableRow key={q.id || q.question_type}> <TableCell>{formatQuestionType(q.question_type)}</TableCell> <TableCell align="right">{q.count}</TableCell> </TableRow>))
                                    ) : (<TableRow> <TableCell colSpan={2} align="center">No question details available.</TableCell> </TableRow>)}
                                </TableBody>
                            </Table>
                        </TableContainer>
                    ) : (<Typography>Loading details...</Typography>)}
                </DialogContent>
                <DialogActions> <Button onClick={handleCloseModal}>Close</Button> </DialogActions>
            </Dialog>


            {/* --- Edit Format Modal Dialog --- */}
            <Dialog open={editModalOpen} onClose={handleCloseEditModal} aria-labelledby="edit-format-dialog-title" maxWidth="md" fullWidth>
                <DialogTitle id="edit-format-dialog-title">
                    Edit Assignment Format
                    <IconButton aria-label="close" onClick={handleCloseEditModal} sx={{ position: 'absolute', right: 8, top: 8, color: (theme) => theme.palette.grey[500] }} > <CloseIcon /> </IconButton>
                </DialogTitle>
                <DialogContent dividers>
                    {editingFormat ? (
                        <Stack spacing={3} sx={{ pt: 1 }}> {/* Add padding top */}
                            {/* Edit Format Name */}
                            <TextField
                                fullWidth
                                label="Format Name"
                                variant="outlined"
                                size="small"
                                value={editFormatName}
                                onChange={(e) => setEditFormatName(e.target.value)}
                                error={!!editError && !editFormatName.trim()}
                                helperText={editError && !editFormatName.trim() ? "Format Name is required" : ""}
                            />

                            {/* Edit Question Distribution */}
                            <Box>
                                <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'medium', mb: 1.5 }}> Question Type Distribution </Typography>
                                <Stack direction="row" spacing={1.5} useFlexGap flexWrap="wrap" sx={{ mb: 1 }}>
                                    {editDistributionCounts.map((item, index) => (
                                        <Chip key={item.uiType} variant="outlined" sx={{ p: 0, height: 'auto', minWidth: '150px', '& .MuiChip-label': { px: 1.5, py: 0.8, display: 'flex', alignItems: 'center', width: '100%' } }}
                                            label={ /* Reusing the counter component structure, bound to EDIT state */
                                                <Stack direction="row" justifyContent="space-between" alignItems="center" width="100%">
                                                    <Typography variant="body2" component="span" sx={{ mr: 1, flexGrow: 1 }}> {item.uiType} </Typography>
                                                    <Stack direction="row" alignItems="center" spacing={0.5}>
                                                        <IconButton aria-label={`Decrease ${item.uiType} count`} onClick={() => handleEditIncrementDecrement(index, -1)} size="small" disabled={parseInt(item.count || '0', 10) <= 0} sx={{ p: 0.2, color: item.brightText }} > <RemoveCircleOutline fontSize="inherit" sx={{ fontSize: '1rem' }} /> </IconButton>
                                                        <TextField value={item.count} onChange={(e) => handleEditCountChange(index, e)} variant="standard" inputProps={{ 'aria-label': `${item.uiType} count`, style: { textAlign: 'center', appearance: 'textfield', MozAppearance: 'textfield', padding: 0 }, sx: { width: '24px', height: '24px', boxSizing: 'border-box', borderRadius: '50%', backgroundColor: item.lightBg, color: item.brightText, fontSize: '0.8rem', fontWeight: 'bold', lineHeight: '24px' } }} sx={{ width: '24px', '& .MuiInput-underline:before, & .MuiInput-underline:hover:not(.Mui-disabled):before, & .MuiInput-underline:after': { borderBottom: 'none' }, '& input::-webkit-outer-spin-button, & input::-webkit-inner-spin-button': { WebkitAppearance: 'none', margin: 0 } }} />
                                                        <IconButton aria-label={`Increase ${item.uiType} count`} onClick={() => handleEditIncrementDecrement(index, 1)} size="small" sx={{ p: 0.2, color: item.brightText }} > <AddCircleOutline fontSize="inherit" sx={{ fontSize: '1rem' }} /> </IconButton>
                                                    </Stack>
                                                </Stack>
                                            }
                                        />
                                    ))}
                                </Stack>
                            </Box>
                            {/* Edit Error Display */}
                            {editError && <Alert severity="error" sx={{ mt: 2 }}>{editError}</Alert>}
                        </Stack>
                    ) : (
                        <Typography>Loading format data...</Typography> // Fallback
                    )}
                </DialogContent>
                <DialogActions sx={{ px: 3, pb: 2 }}> {/* Add padding */}
                    <Button onClick={handleCloseEditModal} color="inherit">Cancel</Button>
                    <Button
                        onClick={handleSaveChanges}
                        variant="contained"
                        disabled={editLoading}
                        startIcon={editLoading ? <CircularProgress size={20} color="inherit" /> : null}
                    >
                        {editLoading ? 'Saving...' : 'Save Changes'}
                    </Button>
                </DialogActions>
            </Dialog>
            {/* --- Delete Confirmation Dialog --- */}
            <Dialog
                open={deleteConfirmOpen}
                onClose={handleCloseDeleteConfirm} // Allow closing by clicking outside or pressing Esc
                aria-labelledby="delete-confirm-dialog-title"
                aria-describedby="delete-confirm-dialog-description"
            >
                <DialogTitle id="delete-confirm-dialog-title">
                    Confirm Deletion
                </DialogTitle>
                <DialogContent>
                    <Typography variant="body1" id="delete-confirm-dialog-description">
                        Are you sure you want to permanently delete this Assignment Paper Format
                        {/* ID: <strong>{formatToDeleteId}</strong>? */}
                    </Typography>
                    <Typography variant="body2" color="error" sx={{ mt: 1 }}>
                        This action cannot be undone.
                    </Typography>
                </DialogContent>
                <DialogActions sx={{ px: 3, pb: 2 }}>
                    <Button onClick={handleCloseDeleteConfirm} color="inherit" disabled={deleteLoading}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleConfirmDelete}
                        color="error"
                        variant="contained"
                        disabled={deleteLoading} // Disable button while API call is in progress
                        startIcon={deleteLoading ? <CircularProgress size={20} color="inherit" /> : null}
                    >
                        {deleteLoading ? 'Deleting...' : 'Delete'}
                    </Button>
                </DialogActions>
            </Dialog>
        {/* </Container> */}
    </Box>
    );
}

export default AssignmentFormat;