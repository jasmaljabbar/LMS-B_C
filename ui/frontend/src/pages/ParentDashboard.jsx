import React, { useEffect, useState } from 'react';
import {
  Box, Container, Typography, Grid, Card, CardContent, Button, IconButton,
  Modal, TextField, Chip, LinearProgress, Avatar
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import {
  Add as AddIcon, Subject as SubjectIcon,
  Delete as DeleteIcon,
  Assignment as AssignmentIcon, School as SchoolIcon, Group
} from '@mui/icons-material';
import AddSubjectModal from '../components/addSubjectModal';
import AddHomeworkModal from '../components/addHomeworkModal';
import usegetParentStudent from '../customHooks/usegetParentStudent';
import AddLessonModal from '../components/addLessonModal';
import LessonModal from '../components/lessonModal';
import HomeWorkSection from '../components/homeWorkSection';
import LessonPDFs from '../components/LessonPDFs';
import Notifications from '../components/Notifications';
// import AddLessonModal from '../components/addLessonModal';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const ParentDashboard = () => {

  const theme = useTheme();
  const [openAddSubject, setOpenAddSubject] = useState(false);
  const [openAddHomework, setOpenAddHomework] = useState(false);
  const [openAddLesson, setOpenAddLesson] = useState(false);
  const [openLessonModal, setOpenLessonModal] = useState(false);
  const [selectedLesson, setSelectedLesson] = useState(null);
  const [homeworkData, setHomeworkData] = useState([]);
  const { studentsData, subjectsMap, lessonsMap, fetchSubjectsForAll, fetchLessons,fetchSubjects } = usegetParentStudent();

  const handleOpenAddSubject = () => setOpenAddSubject(true);
  const handleCloseAddSubject = () => setOpenAddSubject(false);
  const handleOpen = (lesson) => {
    setOpenLessonModal(true);
    setSelectedLesson(lesson);
  };

  const handleDeleteLesson = async (lessonId) => {
    if (window.confirm('Are you sure you want to delete this lesson?')) {
      console.log(lessonId, "lessonId");
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE_URL}/lessons/${lessonId}`, {
        method: 'DELETE',
        headers: {
          'accept': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        console.log('Lesson deleted successfully');
        fetchSubjectsForAll(token);
      } else {
        console.error('Failed to delete lesson');
      }
    }
  };

  const handleGetHomework = async () => {
    const token = localStorage.getItem('token');
    const userId = localStorage.getItem('user_id');
    const response = await fetch(`${API_BASE_URL}/homeworks/by-parent/${userId}`, {
      headers: {
        'accept': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
    });
    const data = await response.json();
    setHomeworkData(data);
  };

  const handleOpenAddHomework = () => {
    setOpenAddHomework(true);
  };
  const handleCloseAddHomework = () => {
    setOpenAddHomework(false);
  };

  const handleOpenAddLesson = () => {
    setOpenAddLesson(true);
  };
  const handleCloseAddLesson = () => {
    setOpenAddLesson(false);
  };

  const subjectMappings = {
    'English': { gradient: 'linear-gradient(to right, #2196f3, #64b5f6)' },
    'Physics': { gradient: 'linear-gradient(to right, #9c27b0, #ba68c8)' },
    'Chemistry': { gradient: 'linear-gradient(to right, #4caf50, #81c784)' },
    'Biology': { gradient: 'linear-gradient(to right, #f44336, #ef9a9a)' },
    'Mathematics': { gradient: 'linear-gradient(to right, #ff9800, #ffb74d)' },
    'default': { gradient: 'linear-gradient(to right, #607d8b, #90a4ae)' }
  };
  const getSubjectStyling = (subjectName) => {
    return subjectMappings[subjectName] || subjectMappings['default'];
  };

  useEffect(() => {
    // Lessons are now fetched automatically in the usegetParentStudent hook
    // No need to call fetchLessons here
  }, [studentsData, subjectsMap]);

  return (
    <Box sx={{
      minHeight: '100vh',
      bgcolor: theme.palette.background.default,
      display: 'flex',
      flexDirection: 'column'
    }}>
      <Box sx={{
        mt: 4,
        px: 2
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h4" gutterBottom>
            My Children
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <Button
              variant="contained"
              startIcon={<SubjectIcon />}
              onClick={handleOpenAddSubject}
              sx={{
                bgcolor: 'primary.main',
                '&:hover': {
                  bgcolor: 'primary.dark'
                }
              }}
            >
              Add Subject
            </Button>
            <Button
              variant="contained"
              startIcon={<SchoolIcon />}
              onClick={handleOpenAddLesson}
              sx={{
                bgcolor: '#8B5CF6',
                '&:hover': {
                  bgcolor: '#7C3AED'
                }
              }}
            >
              Add Lesson
            </Button>
            <Button
              variant="contained"
              startIcon={<AssignmentIcon />}
              onClick={handleOpenAddHomework}
              sx={{
                bgcolor: 'success.main',
                '&:hover': {
                  bgcolor: 'success.dark'
                }
              }}
            >
              Add Homework
            </Button>
            <Notifications />
          </Box>
        </Box>

        <AddSubjectModal open={openAddSubject} onClose={handleCloseAddSubject} fetchSubjects={fetchSubjects} />
        <AddHomeworkModal
          open={openAddHomework}
          onClose={handleCloseAddHomework}
          getHomework={handleGetHomework}
        />
        <AddLessonModal open={openAddLesson} onClose={handleCloseAddLesson} fetchSubjectsForAll={fetchSubjectsForAll} />
        <LessonModal
          open={openLessonModal}
          onClose={() => setOpenLessonModal(false)}
          selectedLesson={selectedLesson}
        />

        <Grid container spacing={4} sx={{
          '& .MuiGrid-item': {
            flex: '0 1 calc(50% - 20px)',
            maxWidth: 'calc(50% - 20px)',
            [theme.breakpoints.down('sm')]: {
              flex: '0 1 100%',
              maxWidth: '100%'
            }
          },
          '& .MuiCard-root': {
            p: 2,
            [theme.breakpoints.down('sm')]: {
              p: 1
            }
          }
        }}>
          {studentsData && studentsData?.length > 0 ? studentsData.map((student) => {
            const subjectsAccordingtoStuednts = subjectsMap[student.student_id] || [];
            return (
              <Grid item xs={12} sm={6} key={student.student_id}>
                <Card sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column'
                }}>
                  <Box sx={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: {
                      xs: 1,
                      sm: 2
                    },
                    p: 2,
                    borderBottom: 1,
                    borderColor: 'divider'
                  }}>
                    <Avatar
                      alt={student.student_name}
                      src={student.user_photo}
                      sx={{
                        ...(!student.user_photo
                          ? {
                            fontSize: {
                              xs: '48px',
                              sm: '72px',
                            },
                            fontWeight: 'bold',
                            textTransform: 'uppercase',
                          }
                          : {}),
                        width: {
                          xs: 80,
                          sm: 120,
                        },
                        height: {
                          xs: 80,
                          sm: 120,
                        },
                        borderRadius: {
                          xs: '8px',
                          sm: '16px',
                        },
                        transition: 'transform 0.3s ease',
                        '&:hover': {
                          transform: 'scale(1.05)',
                        },
                      }}
                    >
                      {!student.user_photo && (student.student_name?.charAt(0).toUpperCase() || '?')}
                    </Avatar>
                    <Box sx={{
                      flex: 1
                    }}>
                      <Typography variant="h5" component="h2">
                        {student.student_name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                        Grade: {student.grade_name}
                      </Typography>
                      <Typography variant="body2" color="primary" sx={{ mt: 0.5 }}>
                        Section: {student.section_name}
                      </Typography>
                    </Box>
                  </Box>
                  <Box sx={{
                    p: 3,
                    flexGrow: 1
                  }}>
                    <Typography variant="h6" gutterBottom>
                      Subjects Progress
                    </Typography>
                    <Grid container spacing={2}>
                      {subjectsAccordingtoStuednts && subjectsAccordingtoStuednts.length > 0 ?
                        [...subjectsAccordingtoStuednts]
                          .sort((a, b) => a.subject_name.localeCompare(b.subject_name))
                          .map((subject) => {
                            const { gradient } = getSubjectStyling(subject.subject_name);
                          return (
                            <Grid item xs={12} sm={6} key={subject.subject_id}>
                              <Card sx={{
                                background: gradient, color: 'white',
                                '&:hover': { boxShadow: 6, transform: 'translateY(-4px)', transition: 'transform 0.3s, box-shadow 0.3s' }
                              }}>
                                <CardContent>
                                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <Avatar alt={subject.subject_name} src={subject.subject_name}
                                      sx={{ width: 32, height: 32, mr: 1 }} />
                                    <Chip label={`${subject.average_score === null ? 0 : subject.average_score}%`} color="primary" size="small" sx={{ color: 'white', fontWeight: 'bold', backgroundColor: 'rgba(0,0,0,0.2)' }} />
                                  </Box>
                                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mt: 1 }}>
                                    {subject.subject_name}
                                  </Typography>
                                  <LinearProgress
                                    variant="determinate"
                                    value={subject.average_scorev === null ? 0 : subject.average_score}
                                    sx={{ height: 8, borderRadius: 4, my: 1, backgroundColor: 'rgba(255,255,255,0.3)' }}
                                  />
                                  <Box sx={{ mt: 2 }}>
                                    {lessonsMap[subject.subject_id]?.length > 0 && <Typography variant="caption" color="inherit" sx={{ mb: 1, fontWeight: 'bold' }}>
                                      Lessons
                                    </Typography>}
                                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                                      {lessonsMap[subject.subject_id]?.map((lesson, index) => (
                                        <>
                                          <Button
                                            variant="contained"
                                            size="small"
                                            onClick={() => handleOpen(lesson)}
                                            sx={{
                                              mt: 1,
                                              width: '100%',
                                              display: 'flex',
                                              justifyContent: 'space-between',
                                              alignItems: 'center',
                                              backgroundColor: theme.palette.grey[100],
                                              color: theme.palette.text.primary,
                                              '&:hover': {
                                                backgroundColor: theme.palette.grey[200],
                                              }
                                            }}
                                          >
                                            <Typography>{lesson.name}</Typography>
                                            <IconButton
                                              onClick={(e) => {
                                                e.stopPropagation();
                                                handleDeleteLesson(lesson.id);
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
                                          </Button>
                                          <LessonPDFs lessonId={lesson.id} fetchLessons={fetchLessons} />
                                        </>

                                      ))}

                                    </Box>
                                  </Box>
                                </CardContent>
                              </Card>
                            </Grid>
                          )
                        }) : (
                          <Box sx={{ p: 2 }}>
                            <Typography variant="h6" gutterBottom>
                              No Subjects Found
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              No subjects found for this student.
                            </Typography>
                          </Box>
                        )}
                    </Grid>
                  </Box>
                  <HomeWorkSection
                    student={student}
                    homeworkData={homeworkData}
                    handleGetHomework={handleGetHomework}
                  />
                </Card>
              </Grid>
            )
          }) : (
            <Grid item xs={12} sm={6}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  p: 4,
                  bgcolor: 'background.paper',
                  boxShadow: 2,
                  borderRadius: 2,
                }}
              >
                <Avatar
                  sx={{
                    width: 64,
                    height: 64,
                    bgcolor: 'grey.200',
                    mb: 2,
                  }}
                >
                  <Group sx={{ fontSize: 32 }} />
                </Avatar>
                <Typography
                  variant="h6"
                  component="h2"
                  sx={{
                    color: 'text.secondary',
                    mb: 1,
                    fontWeight: 500,
                  }}
                >
                  No Students Found
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    textAlign: 'center',
                    color: 'text.secondary',
                    opacity: 0.8,
                  }}
                >
                  No students are currently registered under your account.
                </Typography>
              </Card>
            </Grid>
          )}
        </Grid>
      </Box>
    </Box>
  );
}

export default ParentDashboard;
