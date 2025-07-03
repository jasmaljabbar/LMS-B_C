import { Box, Button, Modal, Typography, TextField, CircularProgress } from "@mui/material"
import { useEffect, useState } from "react"
import AssignmentIcon from '@mui/icons-material/Assignment';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const LessonModal = ({ open, onClose, selectedLesson }) => {
    const [selectedFile, setSelectedFile] = useState(null);
    const [pdfName, setPdfName] = useState('');
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        if (open) {
            console.log(selectedLesson, "selectedLesson");

            const token = localStorage.getItem('token');
            const fetchData = async (token) => {
                try {
                    const childrenResponse = await fetch(`${API_BASE_URL}/lessons/${selectedLesson?.id}/files/https`, {
                        headers: {
                            'accept': 'application/json',
                            'Authorization': `Bearer ${token}`,
                        },
                    });
                    const childrenData = await childrenResponse.json();
                    console.log(childrenData, "childrenData");
                } catch (error) {
                    console.error("Error fetching children data:", error);
                }
            };
            fetchData(token);
        }
    }, [open]);

    // const handleFileClick = () => {
    //     const input = document.getElementById('raised-button-file');
    //     if (input) {
    //         input.click();
    //     }
    // };

    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file) {
            setSelectedFile(file);
            setPdfName(file.name);
            setError('');
            console.log('File selected:', file.name);
        }
    };

    const handleSubmit = async () => {
        try {
            setUploading(true);
            setError('');

            const token = localStorage.getItem('token');
            const formData = new FormData();
            formData.append('pdf_file', selectedFile);
            formData.append('pdf_name', pdfName);
            formData.append('lesson_id', selectedLesson.id);

            const response = await fetch(`${API_BASE_URL}/pdfs/`, {
                method: 'POST',
                headers: {
                    'accept': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }
            const data = await response.json();
            console.log('File uploaded successfully:', data);
            onClose();

        } catch (err) {
            console.error('Error uploading file:', err);
            setError('Failed to upload file. Please try again.');
        } finally {
            setUploading(false);
        }
    };


    return (
        <Modal
            open={open}
            onClose={onClose}
            aria-labelledby="lesson-modal-title"
            aria-describedby="lesson-modal-description"
        >
            <Box
                sx={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    width: 400,
                    bgcolor: 'background.paper',
                    borderRadius: 2,
                    boxShadow: 24,
                    p: 4,
                }}
            >
                <Typography id="lesson-modal-title" variant="h6" component="h2" sx={{ mb: 2 }}>
                    {selectedLesson?.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                    {selectedLesson?.description}
                </Typography>

                <Box sx={{ mb: 2 }}>
                    <Typography variant="h6" component="h2" sx={{ mb: 1 }}>
                        Upload File
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Choose a file to upload for this lesson
                    </Typography>
                    {selectedFile && (
                        <Typography variant="body2" color="success.main" sx={{ mb: 2 }}>
                            ✅ Selected: {selectedFile.name}
                        </Typography>
                    )}
                    {error && (
                        <Typography variant="body2" color="error" sx={{ mb: 2 }}>
                            ❌ {error}
                        </Typography>
                    )}
                    <TextField
                        fullWidth
                        label="File Name"
                        placeholder="Enter file name"
                        value={pdfName}
                        onChange={(event) => setPdfName(event.target.value)}
                        sx={{ mb: 2 }}
                    />
                </Box>
                <Box sx={{ mb: 2 }}>
                    <input
                        accept="*"
                        style={{ display: 'none' }}
                        id="raised-button-file"
                        type="file"
                        onChange={handleFileChange}
                    />
                    <label htmlFor="raised-button-file">
                        <Button
                            variant="contained"
                            component="span"
                            fullWidth
                            startIcon={<AssignmentIcon />}
                            sx={{
                                bgcolor: 'primary.main',
                                '&:hover': {
                                    bgcolor: 'primary.dark'
                                }
                            }}
                        >
                            {selectedFile ? 'Change File' : 'Select File'}
                        </Button>
                    </label>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 2 }}>
                    <Button onClick={onClose}>Cancel</Button>
                    <Button
                        variant="contained"
                        onClick={handleSubmit}
                        disabled={!selectedFile || !pdfName || uploading}
                        sx={{
                            bgcolor: 'success.main',
                            '&:hover': {
                                bgcolor: 'success.dark'
                            }
                        }}
                    >
                        {uploading ? (
                            <>
                                <CircularProgress size={20} sx={{ mr: 1 }} />
                                Uploading...
                            </>
                        ) : (
                            'Upload File'
                        )}
                    </Button>
                </Box>
            </Box>
        </Modal>
    )
}

export default LessonModal
