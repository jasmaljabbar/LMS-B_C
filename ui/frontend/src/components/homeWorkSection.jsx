import { Box, Card, Grid, IconButton, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import {
    Delete as DeleteIcon
} from '@mui/icons-material';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const HomeWorkSection = ({
    student,
    homeworkData,
    handleGetHomework
}) => {
    useEffect(() => {
        handleGetHomework();
    }, []);

    const handleDeleteHomework = async (homeworkId) => {
        if (window.confirm('Are you sure you want to delete this homework?')) {
            console.log(homeworkId, "homeworkId");
            const token = localStorage.getItem('token');
            const response = await fetch(`${API_BASE_URL}/homeworks/${homeworkId}`, {
                method: 'DELETE',
                headers: {
                    'accept': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (response.ok) {
                console.log('Homework deleted successfully');
                handleGetHomework();
            } else {
                console.error('Failed to delete homework');
            }
        }
    };


    return (
        <Box
            sx={{
                p: 3,
                flexGrow: 1,
                overflow: 'auto',
                bgcolor: 'background.paper',
                borderRadius: 2,
                border: '1px solid',
                borderColor: 'divider'
            }}>
            <Typography variant="h6" gutterBottom>
                Homework
            </Typography>
            <Grid container spacing={2}>
                {homeworkData && (() => {
                    const studentHomeworks = homeworkData.filter(
                        (homework) => homework.student_id === student.student_id
                    );

                    if (studentHomeworks.length === 0) {
                        return (
                            <Grid item xs={12}>
                                <Typography variant="h6" gutterBottom>
                                    No Homework Found
                                </Typography>
                                <Typography variant="body2" color="text.secondary">
                                    No homework found for this student.
                                </Typography>
                            </Grid>
                        );
                    }

                    return studentHomeworks.map((homework) => (
                        <Grid item xs={12} key={homework.id}>
                            <Card
                                sx={{
                                    p: 2,
                                    bgcolor: 'background.default',
                                    boxShadow: 2,
                                    transition: 'transform 0.2s ease-in-out',
                                    '&:hover': {
                                        transform: 'translateY(-2px)',
                                        boxShadow: 4,
                                    },
                                }}
                            >
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                                    <Typography
                                        variant="subtitle1"
                                        gutterBottom
                                        sx={{
                                            fontWeight: 'bold',
                                            color: 'text.primary',
                                        }}
                                    >
                                        {homework.title}
                                    </Typography>
                                    <IconButton
                                        onClick={(e) => {
                                            e.stopPropagation();
                                            handleDeleteHomework(homework.id);
                                        }}
                                        size="small"
                                        sx={{
                                            ml: 1,
                                            p: 0,
                                            '&:hover': {
                                                backgroundColor: 'transparent',
                                            }
                                        }}
                                    >
                                        <DeleteIcon sx={{ color: 'error.main' }} />
                                    </IconButton>
                                </Box>
                                <Box
                                    sx={{
                                        display: 'flex',
                                        flexDirection: 'column',
                                        // gap: 1,
                                        p: 1,
                                    }}
                                >
                                    <Typography
                                        variant="body2"
                                        color="text.secondary"
                                        sx={{
                                            // whiteSpace: 'pre-line',
                                            maxHeight: '100px',
                                            overflow: 'hidden',
                                            textOverflow: 'ellipsis',
                                            display: '-webkit-box',
                                            WebkitLineClamp: 3,
                                            WebkitBoxOrient: 'vertical',
                                        }}
                                    >
                                        {homework.description}
                                    </Typography>

                                    <Typography
                                        variant="body2"
                                        color="text.secondary"
                                        sx={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 1,
                                        }}
                                    >
                                        <Typography
                                            variant="caption"
                                            sx={{
                                                fontWeight: 'bold',
                                                color: 'primary.main',
                                            }}
                                        >
                                            Subject:
                                        </Typography>
                                        <Typography
                                            variant="body2"
                                            sx={{
                                                fontWeight: 500,
                                                color: 'text.primary',
                                            }}
                                        >
                                            {homework.subject.name}
                                        </Typography>
                                    </Typography>



                                    <Typography
                                        variant="body2"
                                        color="text.secondary"
                                        sx={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 1,
                                        }}
                                    >
                                        <Typography
                                            variant="caption"
                                            sx={{
                                                fontWeight: 'bold',
                                                color: 'primary.main',
                                            }}
                                        >
                                            Status:
                                        </Typography>
                                        <Typography
                                            variant="body2"
                                            sx={{
                                                fontWeight: 500,
                                                color: 'text.primary',
                                            }}
                                        >
                                            {homework.completed ? 'Completed' : 'Not Completed'}
                                        </Typography>
                                    </Typography>
                                </Box>
                            </Card>
                        </Grid>
                    ));
                })()}
            </Grid>
        </Box>
    );
};

export default HomeWorkSection;