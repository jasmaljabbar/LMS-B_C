import React, { useEffect } from 'react';
import { Modal, Box, Typography, Button, IconButton, List, ListItem, ListItemText, ListItemIcon, Grid } from '@mui/material';
import { Assignment, Close, Download, OpenInNew } from '@mui/icons-material';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const ViewHomeworkModal = ({ open, onClose, subject }) => {
    const [homework, setHomework] = React.useState([]);
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
        const userId = localStorage.getItem('entity_id');

        const fetchHomework = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/homeworks/by-student-subject/?student_id=${userId}&subject_id=${subject.id}`, {
                    headers: {
                        'accept': 'application/json',
                        'Authorization': `Bearer ${token}`,
                    },
                });
                const data = await response.json();
                console.log(data,'sssssssssssssssssssssssss');
                setHomework(data);
            } catch (error) {
                console.error('Error fetching homework:', error);
            }
        };
        fetchHomework();
    }, [subject]);

    const handleView = (homeworkId) => {
        console.log('Viewing homework:', homeworkId);
    };

    return (
        <Modal
            open={open}
            onClose={onClose}
            aria-labelledby="view-homework-modal-title"
            aria-describedby="view-homework-modal-description"
            sx={{
                '& .MuiModal-backdrop': {
                    backgroundColor: 'transparent',
                }
            }}
        >
            <Box sx={modalStyle}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography id="view-homework-modal-title" variant="h6" component="h2">
                        View Homework
                    </Typography>
                    <IconButton onClick={onClose} sx={{ color: 'grey.500' }}>
                        <Close />
                    </IconButton>
                </Box>
                <Grid container spacing={2}>
                    {homework && homework.length > 0 ? homework.map((hw) => (
                        <Grid item xs={12} sm={6} key={hw.id}>
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
                                        {hw.title}
                                    </Typography>
                                    <IconButton onClick={() => handleView(hw.id)}>
                                        <OpenInNew />
                                    </IconButton>
                                </Box>
                                <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
                                    {hw.description}
                                </Typography>
                                <Typography variant="caption" sx={{ mt: 1, color: 'text.secondary' }}>
                                    Subject: {hw.subject.name}
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
                                <Assignment sx={{ fontSize: 32, color: 'grey.500' }} />
                            </Box>
                            <Typography variant="h6" sx={{ mb: 1, color: 'text.secondary' }}>
                                No Homework Available
                            </Typography>
                            <Typography variant="body2" sx={{ textAlign: 'center', color: 'text.secondary' }}>
                                There are no homework assignments for this subject yet.
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

export default ViewHomeworkModal;
