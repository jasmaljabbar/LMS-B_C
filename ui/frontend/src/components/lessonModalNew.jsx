import { Box, Button, Modal, Typography, TextField } from "@mui/material";
import AssignmentIcon from '@mui/icons-material/Assignment';

const LessonModal = ({ open, onClose, selectedLesson }) => {
  const [pdfName, setPdfName] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
  };

  const handleFileClick = () => {
    const fileInput = document.getElementById('raised-button-file');
    fileInput.click();
  };

  const handleUpload = () => {
    if (!selectedFile || !pdfName) {
      alert('Please select a file and enter a PDF name');
      return;
    }
    console.log('Uploading file:', selectedFile, 'with name:', pdfName);
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      aria-labelledby="lesson-modal-title"
      aria-describedby="lesson-modal-description"
    >
      <Box
        sx={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 400,
          bgcolor: 'background.paper',
          borderRadius: 2,
          boxShadow: 24,
          p: 4,
        }}
      >
        <Typography id="lesson-modal-title" variant="h6" component="h2" sx={{ mb: 2 }}>
          {selectedLesson?.name}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          {selectedLesson?.description}
        </Typography>
        <Box sx={{ mb: 2 }}>
          <input
            accept="*"
            style={{ display: 'none' }}
            id="raised-button-file"
            type="file"
            onChange={handleFileChange}
          />
          <label htmlFor="raised-button-file">
            <Button
              variant="contained"
              component="span"
              fullWidth
              startIcon={<AssignmentIcon />}
              onClick={handleFileClick}
            >
              Upload File
            </Button>
          </label>
        </Box>
        {selectedFile && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Selected file: {selectedFile.name}
          </Typography>
        )}
        <Box sx={{ mb: 2 }}>
          <TextField
            fullWidth
            label="PDF Name"
            value={pdfName}
            onChange={(e) => setPdfName(e.target.value)}
            sx={{ mt: 2 }}
          />
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 2 }}>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleUpload}
            disabled={!selectedFile || !pdfName}
          >
            Upload
          </Button>
        </Box>
      </Box>
    </Modal>
  );
};

export default LessonModal;
