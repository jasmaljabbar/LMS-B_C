import { createTheme } from '@mui/material/styles';

// Global CSS Variables
export const themeColors = {
  primary: '#7b1fa2',
  secondary: '#FF4081',
  background: '#F5F5F5',
  textPrimary: '#333333',
  textSecondary: '#666666',
  error: '#FF5252',
  success: '#4CAF50',
  warning: '#FFC107',
  info: '#7b1fa2',
};

export const theme = createTheme({
  palette: {
    primary: {
      main: themeColors.primary,
      light: '#a142f4',
      dark: '#512da8',
    },
    secondary: {
      main: themeColors.secondary,
      light: '#FF6E97',
      dark: '#D81B60',
    },
    background: {
      default: themeColors.background,
      paper: '#FFFFFF',
    },
    text: {
      primary: themeColors.textPrimary,
      secondary: themeColors.textSecondary,
    },
    error: {
      main: themeColors.error,
    },
    success: {
      main: themeColors.success,
    },
    warning: {
      main: themeColors.warning,
    },
    info: {
      main: themeColors.info,
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 500,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 500,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 500,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 500,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 500,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 500,
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.5,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.5,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          padding: '8px 24px',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
          },
        },
      },
    },
  },
});
