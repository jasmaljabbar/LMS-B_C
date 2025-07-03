import { Box, Button, FormControl, InputLabel, MenuItem, Modal, Select, TextField, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import usegetParentStudent from "../customHooks/usegetParentStudent";
import { AttachFile } from "@mui/icons-material";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const AddHomeworkModal = ({ open, onClose, getHomework }) => {
    const [homeworkTitle, setHomeworkTitle] = useState('');
    const [selectedSubject, setSelectedSubject] = useState('');
    const [selectedLesson, setSelectedLesson] = useState('');
    const [selectedStudent, setSelectedStudent] = useState('');
    const [subjectsData, setSubjectsData] = useState([]);
    const [lessonsData, setLessonsData] = useState([]);
    const [homeworkDescription, setHomeworkDescription] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
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
                console.log(error, "err");
            }
        };

        fetchSubjects();

        return () => {
            isMounted = false;
        };
    }, [selectedStudent]);

    useEffect(() => {
        let isMounted = true;

        const fetchSubjects = async () => {
            if (!selectedSubject) return;

            const token = localStorage.getItem('token');
            try {
                const res = await fetch(`${API_BASE_URL}/lessons/subject/${selectedSubject}`, {
                    headers: {
                        'accept': 'application/json',
                        'Authorization': `Bearer ${token}`,
                    },
                });

                const lessons = await res.json();
                // console.log(subjectData, "subjectData");
                if (isMounted) {
                    setLessonsData(lessons);
                }
            } catch (error) {
                console.log(error, "errrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr");
            }
        };

        fetchSubjects();

        return () => {
            isMounted = false;
        };
    }, [selectedSubject]);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!homeworkTitle || !homeworkDescription || !selectedStudent || !selectedSubject || !selectedLesson) {
            alert("Please fill all required fields.");
            return;
        }

        const formData = new FormData();
        if (selectedFile) {
            formData.append("file", selectedFile);
        }

        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`${API_BASE_URL}/homeworks/?title=${homeworkTitle}&description=${homeworkDescription}&student_id=${selectedStudent}&grade_id=1&subject_id=${selectedSubject}&lesson_id=${selectedLesson}`, {
                method: "POST",
                headers: {
                    'accept': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: formData,
            });

            const result = await response.json();
            if (response.ok) {
                console.log("Homework created successfully:", result);
                getHomework()
                onClose();
            } else {
                console.error("Error creating homework:", result);
                alert("Failed to create homework.");
            }
        } catch (error) {
            console.error("Request error:", error);
            alert("An error occurred while submitting homework.");
        }
    };

    return (
        <Modal
            open={open}
            onClose={onClose}
            aria-labelledby="add-homework-modal-title"
            aria-describedby="add-homework-modal-description"
        >
            <Box
                sx={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    width: 450,
                    maxHeight: '90vh',
                    bgcolor: 'background.paper',
                    boxShadow: 24,
                    borderRadius: 2,
                    display: 'flex',
                    flexDirection: 'column',
                }}
            >
                {/* Header */}
                <Box sx={{ p: 3 }}>
                    <Typography id="add-homework-modal-title" variant="h6" component="h2">
                        Add New Homework
                    </Typography>
                </Box>

                <Box
                    component="form"
                    onSubmit={(e) => {
                        e.preventDefault();
                        handleSubmit(e);
                        // handle form submit here
                    }}
                    sx={{
                        px: 3,
                        overflowY: 'auto',
                        flexGrow: 1,
                        minHeight: 0,
                    }}
                >
                    <TextField
                        margin="normal"
                        required
                        fullWidth
                        id="homework-title"
                        label="Title"
                        name="title"
                        value={homeworkTitle}
                        onChange={(e) => setHomeworkTitle(e.target.value)}
                        autoFocus
                    />
                    <TextField
                        margin="normal"
                        fullWidth
                        id="homework-description"
                        label="Description"
                        name="description"
                        value={homeworkDescription}
                        onChange={(e) => setHomeworkDescription(e.target.value)}
                        multiline
                        rows={4}
                        sx={{ mt: 2 }}
                    />
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
                        <InputLabel id="student-select-label">Select Subject</InputLabel>
                        <Select
                            labelId="student-select-label"
                            id="student-select"
                            name="student"
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
                    <FormControl fullWidth margin="normal">
                        <InputLabel id="student-select-label">Select Lesson</InputLabel>
                        <Select
                            labelId="student-select-label"
                            id="student-select"
                            name="student"
                            value={selectedLesson}
                            onChange={(e) => setSelectedLesson(e.target.value)}
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
                            {lessonsData?.map((lesson) => (
                                <MenuItem key={lesson.id} value={lesson.id}>
                                    {lesson.name}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    {/* <TextField
                        margin="normal"
                        required
                        fullWidth
                        id="homework-due-date"
                        label="Due Date"
                        name="dueDate"
                        type="date"
                        value={homeworkDueDate}
                        onChange={(e) => setHomeworkDueDate(e.target.value)}
                        InputLabelProps={{ shrink: true }}
                    /> */}
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mt: 2 }}>
                        <Button
                            variant="outlined"
                            component="label"
                            startIcon={<AttachFile />}
                            sx={{
                                '&:hover': {
                                    borderColor: 'primary.main',
                                }
                            }}
                        >
                            Upload File
                            <input
                                type="file"
                                hidden
                                accept="application/pdf,image/jpeg,image/png,image/gif"
                                onChange={(e) => {
                                    if (e.target.files && e.target.files[0]) {
                                        setSelectedFile(e.target.files[0]);
                                    }
                                }}
                            />
                        </Button>
                        {selectedFile && (
                            <Typography variant="body2" color="text.secondary">
                                {selectedFile.name}
                            </Typography>
                        )}
                    </Box>
                </Box>

                {/* Footer Buttons */}
                <Box sx={{ p: 3, display: 'flex', flexDirection: 'column', gap: 1 }}>
                    <Button
                        type="submit"
                        variant="contained"
                        fullWidth
                        onClick={(e) => {
                            e.preventDefault();
                            handleSubmit(e);
                        }}
                    >
                        Add Homework
                    </Button>
                    <Button
                        variant="outlined"
                        fullWidth
                        onClick={onClose}
                    >
                        Cancel
                    </Button>
                </Box>
            </Box>
        </Modal>

    )
}

export default AddHomeworkModal
