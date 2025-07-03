import React from 'react';
import { Box, Button, TextField, Typography, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import { Modal } from '@mui/material';
import { useState } from 'react';
import usegetParentStudent from '../customHooks/usegetParentStudent';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const AddSubjectModal = ({ open, onClose }) => {
  const [subjectName, setSubjectName] = React.useState('');
  const [selectedStudent, setSelectedStudent] = React.useState('');
  const [error, setError] = React.useState('');

  const { studentsData ,fetchSubjectsForAll} = usegetParentStudent();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const subjectName = formData.get('subjectName');
    const studentId = formData.get('student');
    const token = localStorage.getItem('token');

    try {
      const response = await fetch(`${API_BASE_URL}/subjects/`, {
        method: 'POST',
        headers: {
          'accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          "name": subjectName,
          "student_id": studentId
        }),
      });

      if(response.ok){
        fetchSubjectsForAll(token);
      }

      onClose();
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
          Add New Subject
        </Typography>
        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 2 }}>
          <TextField
            margin="normal"
            required
            fullWidth
            id="subject-name"
            label="Subject Name"
            name="subjectName"
            value={subjectName}
            onChange={(e) => setSubjectName(e.target.value)}
            autoFocus
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
              <MenuItem value="">
                <em>Select a student</em>
              </MenuItem>
              {studentsData?.map((student) => (
                <MenuItem key={student.student_id} value={student.student_id}>
                  {student.student_name} - {student.grade_name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            type="submit"
            fullWidth
            variant="contained"
            sx={{ mt: 3, mb: 2 }}
          >
            Add Subject
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

export default AddSubjectModal;
