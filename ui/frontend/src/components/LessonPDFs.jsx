import React, { useEffect, useState } from 'react';
import { Box, Button, Typography, IconButton, Modal, Paper, CircularProgress } from '@mui/material';
import { Download as DownloadIcon, Delete as DeleteIcon } from '@mui/icons-material';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const LessonPDFs = ({ lessonId, fetchLessons }) => {
    const [pdfs, setPdfs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const fetchLessonPDFs = async () => {
        try {
            setLoading(true);
            const token = localStorage.getItem('token');
            const response = await fetch(`${API_BASE_URL}/pdfs/lesson/${lessonId}`, {
                headers: {
                    'accept': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (response.ok) {
                const data = await response.json();
                setPdfs(data);
                onc
            } else {
                throw new Error('Failed to fetch PDFs');
            }
        } catch (err) {
            console.error('Error fetching PDFs:', err);
            setError('Failed to load PDFs');
        } finally {
            setLoading(false);
        }
    };

    const handleDeletePDF = async (pdfId) => {
        console.log(pdfId, "pdfId");
        if (window.confirm('Are you sure you want to delete this PDF?')) {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch(`${API_BASE_URL}/pdfs/${pdfId}`, {
                    method: 'DELETE',
                    headers: {
                        'accept': 'application/json',
                        'Authorization': `Bearer ${token}`,
                    },
                });

                if (response.ok) {
                    fetchLessonPDFs();
                } else {
                    throw new Error('Failed to delete PDF');
                }
            } catch (err) {
                console.error('Error deleting PDF:', err);
                setError('Failed to delete PDF');
            }
        }
    };

    const handleDownloadPDF = async (pdfUrl) => {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(pdfUrl, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = pdfUrl.split('/').pop();
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
            } else {
                throw new Error('Failed to download PDF');
            }
        } catch (err) {
            console.error('Error downloading PDF:', err);
            setError('Failed to download PDF');
        }
    };

    useEffect(() => {
        fetchLessonPDFs();
    }, [lessonId]);

    return (
        <Box sx={{ mt: 2 }}>
            {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                    <CircularProgress />
                </Box>
            ) : (
                <>
                    {/* {error && (
            <Typography color="error" sx={{ mb: 2 }}>
              {error}
            </Typography>
          )} */}
                    {pdfs.length > 0 ? (
                        <Box>
                            <Typography variant="subtitle1" sx={{ mb: 1 }}>
                                Lesson Materials
                            </Typography>
                            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                                {pdfs.map((pdf) => (
                                    <Paper
                                        key={pdf.id}
                                        sx={{
                                            display: 'flex',
                                            p: 0.5,
                                            justifyContent: 'space-between',
                                            alignItems: 'center',
                                        }}
                                    >
                                        <Typography>{pdf.name}</Typography>
                                        <Box>

                                            <IconButton
                                                onClick={() => handleDeletePDF(pdf.id)}
                                                size="small"
                                                sx={{ color: 'error.main' }}
                                            >
                                                <DeleteIcon />
                                            </IconButton>
                                        </Box>
                                    </Paper>
                                ))}
                            </Box>
                        </Box>
                    ) : (
                        <Typography variant="body2" color="text.secondary">
                            No materials uploaded for this lesson
                        </Typography>
                    )}
                </>
            )}
        </Box>
    );
};

export default LessonPDFs;
