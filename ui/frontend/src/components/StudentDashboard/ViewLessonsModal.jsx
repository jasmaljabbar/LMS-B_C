import React, { useEffect } from 'react';
import { Modal, Box, Typography, Button, IconButton, List, ListItem, ListItemText, ListItemIcon, Grid } from '@mui/material';
import { Book, Close, Download, OpenInNew } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const ViewLessonsModal = ({ open, onClose, subject }) => {
    const [lessons, setLessons] = React.useState([]);
    const navigate = useNavigate()
    const modalStyle = {
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: 400,
        bgcolor: 'background.paper',
        borderRadius: 1,
        boxShadow: 24,
        p: 3,
    };

    useEffect(() => {
        const token = localStorage.getItem('token');
        const fetchLessons = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/lessons/subject/${subject.id}`, {
                    headers: {
                        'accept': 'application/json',
                        'Authorization': `Bearer ${token}`,
                    },
                });
                const data = await response.json();
                setLessons(data);
            } catch (error) {
                console.error('Error fetching lessons:', error);
            }
        };
        fetchLessons();
    }, [subject]);

const handleView = async (lessonId) => {
    const token = localStorage.getItem('token');
    const studentId = localStorage.getItem('entity_id');
    let urlId = null; // Declare urlId in outer scope

    try {
        const response = await fetch(`${API_BASE_URL}/pdfs/lesson/${lessonId}`, {
            headers: {
                'accept': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();

        if (Array.isArray(data) && data.length > 0 && data[0].urls.length > 0) {
            urlId = data[0].id;
            console.log('URL ID:', urlId);
        } else {
            console.warn('Unexpected response structure or no URLs found');
            return;
        }
    } catch (error) {
        console.error('Fetch error:', error);
        return;
    }

    // Now use urlId safely
    window.location.href = `https://51b2-117-211-236-210.ngrok-free.app?token=${token}&pdf_id=${urlId}&student_id=${studentId}&student_id=${subject.id}&lesson_id=${lessonId}`;
    console.log('Viewing lesson:', lessonId);
};


    return (
        <Modal
            open={open}
            onClose={onClose}
            aria-labelledby="view-lessons-modal-title"
            aria-describedby="view-lessons-modal-description"
            sx={{
                '& .MuiModal-backdrop': {
                    backgroundColor: 'transparent',
                }
            }}
        >
            <Box sx={modalStyle}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography id="view-lessons-modal-title" variant="h6" component="h2">
                        View Lessons
                    </Typography>
                    <IconButton onClick={onClose} sx={{ color: 'grey.500' }}>
                        <Close />
                    </IconButton>
                </Box>
                <Grid container spacing={2}>
                    {lessons && lessons.length > 0 ? lessons.map((lesson) => (
                        <Grid item xs={12} sm={6} key={lesson.id}>
                            <Box
                                sx={{
                                    p: 2,
                                    borderRadius: 1,
                                    bgcolor: 'background.paper',
                                    boxShadow: 1,
                                    transition: 'transform 0.2s',
                                    height: '100%',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    '&:hover': {
                                        transform: 'translateY(-2px)',
                                        boxShadow: 2,
                                    }
                                }}
                            >
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                                        {lesson.name}
                                    </Typography>
                                    <IconButton onClick={() => handleView(lesson.id)}>
                                        <OpenInNew />
                                    </IconButton>
                                </Box>
                                <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                                    {lesson.description}
                                </Typography>
                            </Box>
                        </Grid>
                    )) : (
                        <Box
                            sx={{
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                justifyContent: 'center',
                                height: '100%',
                                p: 4
                            }}
                        >
                            <Box
                                sx={{
                                    width: 64,
                                    height: 64,
                                    bgcolor: 'grey.200',
                                    borderRadius: '50%',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    mb: 2
                                }}
                            >
                                <Book sx={{ fontSize: 32, color: 'grey.500' }} />
                            </Box>
                            <Typography variant="h6" sx={{ mb: 1, color: 'text.secondary' }}>
                                No Lessons Available
                            </Typography>
                            <Typography variant="body2" sx={{ textAlign: 'center', color: 'text.secondary' }}>
                                There are no lessons available for this subject yet.
                            </Typography>
                        </Box>
                    )}
                </Grid>
                <Button
                    variant="contained"
                    onClick={onClose}
                    sx={{ ml: 'auto', display: 'block', mt: 2 }}
                >
                    Close
                </Button>
            </Box>
        </Modal>
    );
};

export default ViewLessonsModal;
