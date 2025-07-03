import { Box, Typography } from '@mui/material';

const HomeworkEmptyState = () => {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        p: 4
      }}
    >
      <Typography
        variant="h6"
        color="text.secondary"
        sx={{ mb: 2 }}
      >
        No homework assigned yet
      </Typography>
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ opacity: 0.7 }}
      >
        Click the "Add Homework" button to assign homework
      </Typography>
    </Box>
  );
};

export default HomeworkEmptyState;
