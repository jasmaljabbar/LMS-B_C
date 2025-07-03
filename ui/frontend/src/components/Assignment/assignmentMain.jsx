import React, { useState } from 'react';
import { Box, Container, Typography, Grid, Card, CardContent, Button, IconButton, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Chip, Tabs, Tab } from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import AssignmentUploadPDF from './assignmentUploadPDF';
import AssignmentFormat from './assignmentFormat';

const Assignments = () => {
    const [value, setValue] = useState(0);

    //   const assignments = [
    //     {
    //       id: 1,
    //       title: 'Math Assignment 1',
    //       subject: 'Mathematics',
    //       dueDate: '2025-06-30',
    //       status: 'pending',
    //       description: 'Complete exercises 1-10 from chapter 3'
    //     },
    //     {
    //       id: 2,
    //       title: 'Science Project',
    //       subject: 'Science',
    //       dueDate: '2025-07-05',
    //       status: 'in-progress',
    //       description: 'Submit the plant growth experiment report'
    //     },
    //     {
    //       id: 3,
    //       title: 'English Essay',
    //       subject: 'English',
    //       dueDate: '2025-06-28',
    //       status: 'completed',
    //       description: 'Write an essay on environmental conservation'
    //     },
    //     {
    //       id: 4,
    //       title: 'Physics Lab Report',
    //       subject: 'Physics',
    //       dueDate: '2025-06-25',
    //       status: 'overdue',
    //       description: 'Submit the electricity experiment report'
    //     }
    //   ];

    const statusColors = {
        pending: 'warning',
        'in-progress': 'info',
        completed: 'success'
    };

    const handleChange = (event, newValue) => {
        setValue(newValue);
    };

    return (
        <Box sx={{ width: '100%', mt: 4 }}>
            <Typography variant="h4" gutterBottom>
                Assignments
            </Typography>

            <Box sx={{ 
                width: '100%', 
                borderBottom: 1, 
                borderColor: 'divider'
            }}>
                <Tabs 
                    value={value} 
                    onChange={handleChange} 
                    aria-label="assignments tabs"
                    sx={{ width: '100%' }}
                >
                    <Tab label="Assignment PDF Upload" />
                    <Tab label="Assignment Format Creation" />
                    <Tab label="Assignment QP Generation" />
                    <Tab label="Assignment Distribution" />
                </Tabs>
            </Box>

            <Box sx={{ width: '100%', p: 2 }}>
                    {value === 0 && (
                        <AssignmentUploadPDF />
                    )}
                    {value === 1 && (
                        <AssignmentFormat />
                    )}
                    {value === 2 && (
                        <Typography variant="body1" sx={{ width: '100%' }}>
                            Hello World - Completed Assignments tab
                        </Typography>
                    )}
                    {value === 3 && (
                        <Typography variant="body1" sx={{ width: '100%' }}>
                            Hello World - Overdue Assignments tab
                        </Typography>
                    )}
            </Box>
        </Box>
    );
};

export default Assignments;
