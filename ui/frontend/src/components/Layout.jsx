import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useLocation } from 'react-router-dom';
import { ThemeProvider, AppBar, Toolbar, Typography, Button, Box, CssBaseline } from '@mui/material';
import { theme } from '../theme/theme';
import {
  Dashboard as DashboardIcon,
  Assignment as AssignmentIcon,
  Person as PersonIcon,
  ExitToApp as ExitToAppIcon
} from '@mui/icons-material';

const Layout = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/');
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        {location.pathname === '/' ? (
          <>{children}</>
        ) : (
          <>
            <AppBar position="static">
              <Toolbar>
                <Typography variant="h6" component={Link} to="/"
                  sx={{ flexGrow: 1, textDecoration: 'none', color: 'inherit' }}
                >
                  LMS
                </Typography>
                {/* <Button color="inherit" component={Link} to="/parent-dashboard" startIcon={<DashboardIcon />}>
                  Dashboard
                </Button> */}
                <Button color="inherit" onClick={handleLogout} startIcon={<ExitToAppIcon />}>
                  Logout
                </Button>
              </Toolbar>
            </AppBar>
            <Box sx={{ p: 3, flexGrow: 1 }}>
              {children}
            </Box>
          </>
        )}
      </Box>
    </ThemeProvider>
  );
};

export default Layout;
