import React from "react";
import { Box, Grid, Card, CardContent, Typography, Avatar, Button } from '@mui/material';
import { Assignment, Book } from '@mui/icons-material';
import useGetStudentbyID from "../../customHooks/useGetStudentbyID";
import usegetSubjectbyhStudent from "../../customHooks/usegetSubjectbyhStudent";
import ViewLessonsModal from "./ViewLessonsModal";
import ViewHomeworkModal from "./ViewHomeworkModal";
import WeeklyPerformanceChart from "./WeeklyPerformanceChart";
import SubjectRadarChart from "./SubjectRadarChart";

const StudentDashboard = () => {
  const [selectedSubject, setSelectedSubject] = React.useState(null);
  const [openLessonModal, setOpenLessonModal] = React.useState(false);
  const [openHomeworkModal, setOpenHomeworkModal] = React.useState(false);
  // const theme = useTheme();
  // const location = useLocation();

  // const subjects = dummySubjects;
  const { student, loading } = useGetStudentbyID();
  const { subjects, isLoading, error } = usegetSubjectbyhStudent();

  // Weekly performance data
  const weeklyPerformanceData = [
    { day: "Tue", score_percentage: null },
    { day: "Wed", score_percentage: null },
    { day: "Thu", score_percentage: null },
    { day: "Fri", score_percentage: null },
    { day: "Sat", score_percentage: null },
    { day: "Sun", score_percentage: null },
    { day: "Mon", score_percentage: null }
  ];

  const handleViewLessons = (subject) => {
    setSelectedSubject(subject);
    setOpenLessonModal(true);
  };

  const handleViewHomework = (subject) => {
    setSelectedSubject(subject);
    setOpenHomeworkModal(true);
  };

  const subjectMappings = {
    'English': { gradient: 'linear-gradient(to right, #2196f3, #64b5f6)' },
    'Physics': { gradient: 'linear-gradient(to right, #9c27b0, #ba68c8)' },
    'Mathematics': { gradient: 'linear-gradient(to right, #ff9800, #ffb74d)' },
    'Chemistry': { gradient: 'linear-gradient(to right, #4caf50, #81c784)' },
    'Biology': { gradient: 'linear-gradient(to right, #f44336, #ef9a9a)' },
    'default': { gradient: 'linear-gradient(to right, #607d8b, #90a4ae)' }
  };

  const buttonColors = {
    'View Lessons': {
      background: 'linear-gradient(to right, #4caf50, #81c784)',
      hover: 'linear-gradient(to right, #4caf50, #81c784, #4caf50)'
    },
    'View Homework': {
      background: 'linear-gradient(to right, #2196f3, #64b5f6)',
      hover: 'linear-gradient(to right, #2196f3, #64b5f6, #2196f3)'
    }
  };

  const getButtonStyling = (buttonType) => {
    return buttonColors[buttonType] || {
      background: 'linear-gradient(to right, #607d8b, #90a4ae)',
      hover: 'linear-gradient(to right, #607d8b, #90a4ae, #607d8b)'
    };
  };

  const getSubjectStyling = (subjectName) => {
    return subjectMappings[subjectName] || subjectMappings['default'];
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        {student?.name}'s Subjects
      </Typography>
      <Grid container spacing={3}>
        {subjects.map((subject) => (
          <Grid item xs={12} sm={6} md={4} key={subject.id}>
            <Card
              sx={{
                height: '100%',
                background: getSubjectStyling(subject.name).gradient,
                color: 'white',
                '&:hover': {
                  boxShadow: 6,
                  transform: 'translateY(-4px)',
                  transition: 'transform 0.3s, box-shadow 0.3s'
                }
              }}
            >
              <CardContent sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                  <Avatar
                    alt={subject.name}
                    src={subject.name}
                    sx={{ width: 32, height: 32, mr: 1 }}
                  />
                  {/* <Chip 
                    label={`${subject.average_score === null ? 0 : subject.average_score}%`} 
                    color="primary" 
                    size="small" 
                    sx={{ 
                      color: 'white', 
                      fontWeight: 'bold', 
                      backgroundColor: 'rgba(0,0,0,0.2)'
                    }} 
                  /> */}
                </Box>
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mt: 1 }}>
                  {subject.name}
                </Typography>
                <Box sx={{ width: '100%', mb: 1 }}>
                  <Box sx={{ width: '100%', height: 8, backgroundColor: 'rgba(255,255,255,0.3)' }}>
                    {/* <Box 
                      sx={{ 
                        width: `${subject.average_score === null ? 0 : subject.average_score}%`, 
                        height: '100%', 
                        backgroundColor: 'white', 
                        borderRadius: 2,
                        transition: 'width 0.3s'
                      }} 
                    /> */}
                  </Box>
                </Box>
              </CardContent>

              <Box sx={{ display: 'flex', justifyContent: 'space-between', p: 2, borderTop: 1, borderColor: 'rgba(255,255,255,0.1)' }}>
                <Button
                  variant="contained"
                  size="small"
                  startIcon={<Book />}
                  onClick={() => handleViewLessons(subject)}
                  sx={{
                    bgcolor: 'transparent',
                    background: getButtonStyling('View Lessons').background,
                    color: 'white',
                    '&:hover': {
                      background: getButtonStyling('View Lessons').hover,
                      boxShadow: 'none'
                    },
                    '&:active': {
                      transform: 'scale(0.98)'
                    }
                  }}
                >
                  View Lessons
                </Button>
                <Button
                  variant="contained"
                  size="small"
                  onClick={() => handleViewHomework(subject)}
                  startIcon={<Assignment />}
                  sx={{
                    bgcolor: 'transparent',
                    background: getButtonStyling('View Homework').background,
                    color: 'white',
                    '&:hover': {
                      background: getButtonStyling('View Homework').hover,
                      boxShadow: 'none'
                    },
                    '&:active': {
                      transform: 'scale(0.98)'
                    }
                  }}
                >
                  View Homework
                </Button>
              </Box>
            </Card>
          </Grid>
        ))}
      </Grid>
      <Typography variant="h5" component="h2" sx={{ mt: 3, mb: 1 }}>
        Performance Analysis
      </Typography>
      <Grid container spacing={4} >
        <Grid item xs={12} md={6}>
          <SubjectRadarChart subjects={subjects} />
        </Grid>
        <Grid item xs={12} md={6}>
          <WeeklyPerformanceChart data={weeklyPerformanceData} />
        </Grid>
      </Grid>

      <ViewLessonsModal
        open={openLessonModal}
        onClose={() => setOpenLessonModal(false)}
        subject={selectedSubject}
      />
      <ViewHomeworkModal
        open={openHomeworkModal}
        onClose={() => setOpenHomeworkModal(false)}
        subject={selectedSubject}
      />
    </Box>
  );
};

export default StudentDashboard;
