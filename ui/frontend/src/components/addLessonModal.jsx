import React, { useEffect } from 'react';
import { Box, Button, TextField, Typography, Select, MenuItem, FormControl, InputLabel, IconButton } from '@mui/material';
import { AttachFile } from '@mui/icons-material';
import { Modal } from '@mui/material';
import { useState } from 'react';
import usegetParentStudent from '../customHooks/usegetParentStudent';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const AddLessonModal = ({ open, onClose, fetchSubjectsForAll }) => {
    const [lessonName, setLessonName] = useState('');
    const [selectedStudent, setSelectedStudent] = useState('');
    const [selectedSubject, setSelectedSubject] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
    const [subjectsData, setSubjectsData] = useState([]);
    const { studentsData } = usegetParentStudent();

    useEffect(() => {
        let isMounted = true;

        const fetchSubjects = async () => {
            if (!selectedStudent) return;

            const token = localStorage.getItem('token');
            try {
                const res = await fetch(`${API_BASE_URL}/subjects/student/${selectedStudent}?skip=0&limit=100`, {
                    headers: {
                        'accept': 'application/json',
                        'Authorization': `Bearer ${token}`,
                    },
                });

                const subjectData = await res.json();
                // console.log(subjectData, "subjectData");
                if (isMounted) {
                    setSubjectsData(subjectData);
                }
            } catch (error) {
                console.log(error, "errrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr");
            }
        };

        fetchSubjects();

        return () => {
            isMounted = false;
        };
    }, [selectedStudent]);

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/gif'];
            if (!allowedTypes.includes(file.type)) {
                alert('Please upload a PDF or image file only');
                return;
            }
            setSelectedFile(file);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const formData = new FormData(e.currentTarget);
        // const studentId = formData.get('student');
        const subjectName = formData.get('subjectName');
        const lessonName = formData.get('lessonName');
        const token = localStorage.getItem('token')

        try {
            const response = await fetch(`${API_BASE_URL}/lessons/`, {
                method: 'POST',
                headers: {
                    'accept': 'application/json',
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    "name": lessonName,
                    "subject_id": subjectName
                }),
            });

            if (response.ok) {
                onClose();
                fetchSubjectsForAll(token);
            }
        } catch (error) {
            console.log(error, "errrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr");
        }

    };

    return (
        <Modal
            open={open}
            onClose={onClose}
            aria-labelledby="add-subject-modal-title"
            aria-describedby="add-subject-modal-description"
        >
            <Box sx={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: 400,
                bgcolor: 'background.paper',
                boxShadow: 24,
                p: 4,
                borderRadius: 2,
            }}>
                <Typography id="add-subject-modal-title" variant="h6" component="h2">
                    Add New Lesson
                </Typography>
                <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
                    <FormControl fullWidth margin="normal">
                        <InputLabel id="student-select-label">Select Student</InputLabel>
                        <Select
                            labelId="student-select-label"
                            id="student-select"
                            name="student"
                            value={selectedStudent}
                            onChange={(e) => setSelectedStudent(e.target.value)}
                            label="Select Student"
                            required
                            sx={{
                                '& .MuiOutlinedInput-root': {
                                    '& fieldset': {
                                        borderColor: 'rgba(0, 0, 0, 0.23)',
                                    },
                                    '&:hover fieldset': {
                                        borderColor: 'rgba(0, 0, 0, 0.23)',
                                    },
                                    '&.Mui-focused fieldset': {
                                        borderColor: 'rgba(0, 0, 0, 0.23)',
                                    },
                                },
                            }}
                        >
                            {/* <MenuItem value="">
                                <em>Select a student</em>
                            </MenuItem> */}
                            {studentsData?.map((student) => (
                                <MenuItem key={student.student_id} value={student.student_id}>
                                    {student.student_name} - {student.grade_name}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    <FormControl fullWidth margin="normal">
                        <InputLabel id="subject-select-label">Select Subject</InputLabel>
                        <Select
                            labelId="subject-select-label"
                            id="subject-select"
                            name="subjectName"
                            value={selectedSubject}
                            onChange={(e) => setSelectedSubject(e.target.value)}
                            label="Select Subject"
                            required
                            sx={{
                                '& .MuiOutlinedInput-root': {
                                    '& fieldset': {
                                        borderColor: 'rgba(0, 0, 0, 0.23)',
                                    },
                                    '&:hover fieldset': {
                                        borderColor: 'rgba(0, 0, 0, 0.23)',
                                    },
                                    '&.Mui-focused fieldset': {
                                        borderColor: 'rgba(0, 0, 0, 0.23)',
                                    },
                                },
                            }}
                        >

                            {subjectsData?.map((subject) => (
                                <MenuItem key={subject.id} value={subject.id}>
                                    {subject.name}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    <TextField
                        margin="normal"
                        required
                        fullWidth
                        id="lesson-name"
                        label="Lesson Name"
                        name="lessonName"
                        value={lessonName}
                        onChange={(e) => setLessonName(e.target.value)}
                        autoFocus
                    />
                    <Button
                        type="submit"
                        fullWidth
                        variant="contained"
                        sx={{ mt: 3, mb: 2 }}
                    >
                        Add Lesson
                    </Button>
                    <Button
                        fullWidth
                        variant="outlined"
                        onClick={onClose}
                    >
                        Cancel
                    </Button>
                </Box>
            </Box>
        </Modal>
    );
};

export default AddLessonModal;
