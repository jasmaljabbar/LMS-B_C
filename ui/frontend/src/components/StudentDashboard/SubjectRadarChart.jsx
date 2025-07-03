import React from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Box, Typography, Paper, useTheme, styled } from '@mui/material';
import {
  blue,
  green,
  red,
  yellow,
  purple,
  orange,
  pink,
  teal,
  indigo,
  brown
} from '@mui/material/colors';

const CustomTooltip = styled(Tooltip)({
  '& .recharts-default-tooltip': {
    backgroundColor: 'rgba(0,0,0,0.9)',
    borderRadius: 8,
    padding: '12px',
    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
  },
  '& .recharts-tooltip-item': {
    color: 'white',
    fontSize: '0.9rem',
    fontWeight: 500,
  },
});

const SubjectRadarChart = ({ subjects }) => {
  // Format data with dummy values for Recharts
  const chartData = [
    {
      subject: 'Maths',
      score: 85, // Excellent
      color: blue[500]
    },
    {
      subject: 'English',
      score: 78, // Good
      color: green[500]
    },
    {
      subject: 'Geography',
      score: 68, // Fair
      color: purple[500]
    },
    {
      subject: 'Biology',
      score: 92, // Excellent
      color: orange[500]
    },
    {
      subject: 'Grammar',
      score: 74, // Good
      color: pink[500]
    }
  ];

  // Calculate average score
  const totalScore = chartData.reduce((acc, item) => acc + item.score, 0);
  const averageScore = totalScore / chartData.length;

  // Get theme for colors
  const theme = useTheme();

  return (
    <Paper sx={{ p: 3, mb: 3, mt: 2, boxShadow: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ color: theme.palette.primary.main }}>
        Subject Performance
      </Typography>
      
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 2 }}>
        <Box sx={{ width: '100%', maxWidth: 400 }}>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                outerRadius={120}
                fill="#8884d8"
                paddingAngle={5}
                dataKey="score"
              >
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.color}
                    stroke={entry.color}
                  />
                ))}
              </Pie>
              <Tooltip />
              <Legend 
                verticalAlign="bottom" 
                align="center" 
                layout="horizontal"
                iconSize={10}
                iconType="circle"
                wrapperStyle={{ marginTop: 20 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </Box>
        
        <Typography variant="body2" color="text.secondary" align="center">
          Average Performance: {averageScore.toFixed(1)}%
        </Typography>
      </Box>
    </Paper>
  );
};

export default SubjectRadarChart;
