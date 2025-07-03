import React from 'react';
import { CircularProgress, Box, Typography, Paper, useTheme } from '@mui/material';
import { green, red, yellow, blue } from '@mui/material/colors';

const WeeklyPerformanceChart = ({ data }) => {
    // Calculate average score for the week
    const totalScore = data.reduce((acc, item) => acc + (item.score_percentage || 0), 0);
    const averageScore = totalScore / data.length;
    
    // Determine color based on score
    const getColor = (score) => {
        if (score >= 80) return green[500];
        if (score >= 60) return yellow[500];
        return red[500];
    };

    return (
        <Paper sx={{ p: 3, mb: 3 , mt: 2}}>
            <Typography variant="h6" gutterBottom>
                Weekly Performance
            </Typography>
            
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 2 }}>
                <Box sx={{ position: 'relative', display: 'inline-flex' }}>
                    <CircularProgress
                        variant="determinate"
                        value={averageScore}
                        size={120}
                        sx={{
                            color: getColor(averageScore),
                            position: 'absolute',
                            left: 0,
                            top: 0,
                        }}
                    />
                    <Box
                        sx={{
                            top: 0,
                            left: 0,
                            bottom: 0,
                            right: 0,
                            position: 'absolute',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '1.5rem',
                            fontWeight: 'bold',
                            color: getColor(averageScore),
                        }}
                    >
                        {Math.round(averageScore)}%
                    </Box>
                </Box>
                
                <Typography variant="body2" color="text.secondary" align="center">
                    {averageScore >= 80 ? 'Excellent Progress!' :
                     averageScore >= 60 ? 'Good Progress' :
                     'Needs Improvement'}
                </Typography>
            </Box>
        </Paper>
    );
};

export default WeeklyPerformanceChart;
