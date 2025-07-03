import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  TextField,
  Button,
  Checkbox,
  FormControlLabel,
  Link as MuiLink,
  Avatar,
  Paper,
  Grid,
  useMediaQuery,
  useTheme,
  styled,
  ThemeProvider,
  CssBaseline,
  IconButton,
  InputAdornment
} from '@mui/material';
import {
  School as SchoolIcon,
  EmojiPeopleOutlined as EmojiPeople,
  EmojiEventsOutlined as EmojiEvents,
  EmojiObjectsOutlined as EmojiObjects,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon
} from '@mui/icons-material';
import { theme } from '../theme/theme';
import { themeColors } from '../theme/theme';

const BackgroundBox = styled(Box)(({ theme }) => ({
  backgroundColor: themeColors.background,
  height: '100vh',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexDirection: 'column',
  backgroundImage: 'linear-gradient(135deg, #f0f7ff 0%, #e3f2fd 100%)',
  overflow: 'hidden',
}));

const FeatureBox = styled(Box)(({ theme }) => ({
  backgroundColor: 'white',
  borderRadius: '20px',
  padding: theme.spacing(4),
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
  transition: 'transform 0.3s ease',
  '&:hover': {
    transform: 'translateY(-5px)',
  },
}));

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

const Login = () => {
  const navigate = useNavigate();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [showPassword, setShowPassword] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const handlePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    if (!username || !password) {
      setError('Please fill in both username and password');
      return;
    }

    setIsLoading(true);
    try {
      const urlEncodedData = new URLSearchParams();
      urlEncodedData.append('grant_type', 'password');
      urlEncodedData.append('username', username);
      urlEncodedData.append('password', password);

      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded',
        },

        body: urlEncodedData

      });

      if (!response.ok) {
        throw new Error('Invalid credentials');
      }

      const data = await response.json();
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user_id', JSON.stringify(data.user_id));
      localStorage.setItem('user_type', JSON.stringify(data.user_type));
      localStorage.setItem('entity_id', JSON.stringify(data.entity_id));

      console.log(data ,"data");
      switch (data.user_type) {
        case 'Parent':
          navigate('/parent-dashboard');
          break;
        case 'Student':
          navigate('/student-dashboard');
          break;
        default:
          setError('Access denied: Invalid user type');
          localStorage.removeItem('token');
          localStorage.removeItem('user_id');
          localStorage.removeItem('user_type');
      }
    } catch (error) {
      setError('Invalid username or password');
      console.error('Login error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BackgroundBox>
        <Box sx={{
          display: 'flex',
          flexDirection: 'column',
          width: '100%',
          height: '100vh',
          overflow: 'hidden',
          alignItems: 'center',
          justifyContent: 'center',
          p: 0,
          position: 'relative'
        }}>
          <Grid container spacing={2} sx={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>

            {isMobile ? <></> : <Grid item xs={12} md={6}>
              <Box
                sx={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: { xs: 'flex-start', md: 'center' },
                  height: '100vh',
                  p: 3,
                  textAlign: 'center',
                  width: '100%'
                }}
              >
                <Typography
                  variant="h4"
                  sx={{
                    fontWeight: 700,
                    color: themeColors.textPrimary,
                    mb: 4,
                    textAlign: 'center',
                    fontSize: { xs: '1.5rem', md: '2rem' }
                  }}
                >
                  Welcome to Our Learning Community
                </Typography>
                <Typography
                  variant="body1"
                  sx={{
                    textAlign: 'center',
                    color: themeColors.textSecondary,
                    opacity: 0.8,
                    mb: 6,
                    maxWidth: { xs: '100%', md: '600px' },
                    fontSize: { xs: '0.9rem', md: '1rem' }
                  }}
                >
                  Join our community of learners and educators.
                  Access interactive lessons, track progress, and
                  connect with teachers and students worldwide.
                </Typography>
                <Box
                  sx={{
                    display: 'grid',
                    gridTemplateColumns: { xs: '1fr', md: 'repeat(3, 1fr)' },
                    gap: 3,
                    width: '100%',
                    maxWidth: { xs: '100%', md: '800px' }
                  }}
                >
                  <FeatureBox>
                    <EmojiPeople sx={{ fontSize: 40, mb: 2 }} />
                    <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
                      Student-Friendly
                    </Typography>
                    <Typography variant="body2" sx={{ color: themeColors.textSecondary, opacity: 0.8 }}>
                      Designed for students of all ages
                    </Typography>
                  </FeatureBox>
                  <FeatureBox>
                    <EmojiEvents sx={{ fontSize: 40, mb: 2 }} />
                    <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
                      Interactive Learning
                    </Typography>
                    <Typography variant="body2" sx={{ color: themeColors.textSecondary, opacity: 0.8 }}>
                      Engaging lessons and activities
                    </Typography>
                  </FeatureBox>
                  <FeatureBox>
                    <EmojiObjects sx={{ fontSize: 40, mb: 2 }} />
                    <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
                      Modern Tools
                    </Typography>
                    <Typography variant="body2" sx={{ color: themeColors.textSecondary, opacity: 0.8 }}>
                      Latest educational technology
                    </Typography>
                  </FeatureBox>
                </Box>
                <Box
                  sx={{
                    display: 'flex',
                    gap: 2,
                    mt: 4,
                    justifyContent: 'center',
                    width: '100%',
                    maxWidth: '400px'
                  }}
                >
                </Box>
              </Box>
            </Grid>}
            <Grid item xs={12} md={6} sx={{
              width: '100%',
              height: '100%',
              display: { xs: 'flex', md: 'none' },
              alignItems: 'center',
              justifyContent: 'center',
              p: 2,
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)'
            }}>
              <Paper
                elevation={4}
                sx={{
                  p: { xs: 2, md: 3 },
                  borderRadius: { xs: '15px', md: '20px' },
                  backgroundColor: 'white',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '100%',
                  maxWidth: { xs: '100%', md: '500px' },
                  minWidth: { xs: '100%', md: '300px' },
                  maxHeight: { xs: 'auto', md: '600px' },
                  minHeight: { xs: 'auto', md: '400px' },
                  overflow: 'visible',
                  margin: { xs: 1, md: 2 },
                  flex: 1,
                  height: { xs: 'auto', md: '100%' },
                  alignSelf: 'center'
                }}
              >
                <Box
                  sx={{
                    width: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    textAlign: 'center',
                    gap: 1
                  }}
                >
                  <Box
                    sx={{
                      width: '100%',
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      // mb: 3
                    }}
                  >
                    <Avatar
                      sx={{
                        bgcolor: themeColors.primary,
                        width: isMobile ? 100 : 120,
                        height: isMobile ? 100 : 120,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}
                    >
                      <SchoolIcon sx={{ fontSize: isMobile ? 60 : 80 }} />
                    </Avatar>
                  </Box>
                  <Typography
                    component="h1"
                    variant="h3"
                    sx={{
                      fontWeight: 700,
                      color: themeColors.textPrimary,
                      textAlign: 'center',
                      fontSize: { xs: '2rem', md: '2.5rem' },
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      mb: 0
                    }}
                  >
                    Welcome to Learning Hub
                  </Typography>

                  <Box
                    component="form"
                    onSubmit={handleSubmit}
                    noValidate
                    sx={{ mt: 1, width: '100%' }}
                  >
                    <TextField
                      margin="normal"
                      required
                      fullWidth
                      id="username"
                      onChange={(e) => setUsername(e.target.value)}
                      label="username"
                      name="username"
                      autoComplete="username"
                      autoFocus
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          borderRadius: '10px',
                          mb: 2,
                          backgroundColor: '#f8f9fa',
                          '& fieldset': {
                            borderColor: '#e0e0e0',
                          },
                          '&:hover fieldset': {
                            borderColor: '#4361ee',
                          },
                          '&.Mui-focused fieldset': {
                            borderColor: '#4361ee',
                          },
                        }
                      }}
                    />
                    <TextField
                      margin="normal"
                      required
                      fullWidth
                      name="password"
                      onChange={(e) => setPassword(e.target.value)}
                      label="Password"
                      type={showPassword ? 'text' : 'password'}
                      id="password"
                      autoComplete="current-password"
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          borderRadius: '10px',
                          mb: 2,
                          backgroundColor: '#f8f9fa',
                          '& fieldset': {
                            borderColor: '#e0e0e0',
                          },
                          '&:hover fieldset': {
                            borderColor: '#4361ee',
                          },
                          '&.Mui-focused fieldset': {
                            borderColor: '#4361ee',
                          },
                        }
                      }}
                      InputProps={{
                        endAdornment: (
                          <InputAdornment position="end">
                            <IconButton
                              onClick={handlePasswordVisibility}
                              edge="end"
                            >
                              {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                            </IconButton>
                          </InputAdornment>
                        )
                      }}
                    />
                    <Button
                      type="submit"
                      fullWidth
                      variant="contained"
                      sx={{
                        mt: 3,
                        borderRadius: '10px',
                        height: { xs: 45, md: 50 },
                        bgcolor: themeColors.primary,
                        color: 'white',
                        fontWeight: 600,
                        textTransform: 'none',
                        fontSize: { xs: '1rem', md: '1.1rem' },
                        '&:hover': {
                          bgcolor: themeColors.primaryDark,
                          transform: 'translateY(-2px)',
                        },
                        transition: 'all 0.3s ease'
                      }}
                    >
                      Sign In
                    </Button>
                    {error && (
                      <Typography
                        variant="body2"
                        color="error"
                        sx={{
                          mt: 1,
                          textAlign: 'center',
                          fontSize: '0.875rem'
                        }}
                      >
                        {error}
                      </Typography>
                    )}
                  </Box>

                </Box>
              </Paper>
            </Grid>
            <Grid item xs={0} md={6} sx={{
              width: '100%',
              height: '100%',
              display: { xs: 'none', md: 'flex' },
              alignItems: 'center',
              justifyContent: 'center',
              p: 2
            }}>
              <Paper
                elevation={4}
                sx={{
                  p: { xs: 2, md: 3 },
                  borderRadius: { xs: '15px', md: '20px' },
                  backgroundColor: 'white',
                  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '100%',
                  maxWidth: { xs: '100%', md: '500px' },
                  minWidth: { xs: '100%', md: '300px' },
                  maxHeight: { xs: 'auto', md: '600px' },
                  minHeight: { xs: 'auto', md: '400px' },
                  overflow: 'visible',
                  margin: { xs: 1, md: 2 },
                  flex: 1,
                  height: { xs: 'auto', md: '100%' },
                  alignSelf: 'center'
                }}
              >
                <Box
                  sx={{
                    width: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    textAlign: 'center',
                    gap: 2
                  }}
                >
                  <Box
                    sx={{
                      width: '100%',
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      mb: 3
                    }}
                  >
                    <Avatar
                      sx={{
                        bgcolor: themeColors.primary,
                        width: isMobile ? 100 : 120,
                        height: isMobile ? 100 : 120,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}
                    >
                      <SchoolIcon sx={{ fontSize: isMobile ? 60 : 80 }} />
                    </Avatar>
                  </Box>
                  <Typography
                    component="h1"
                    variant="h3"
                    sx={{
                      fontWeight: 700,
                      mb: 3,
                      color: themeColors.textPrimary,
                      textAlign: 'center',
                      fontSize: { xs: '2rem', md: '2.5rem' },
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    Welcome to Learning Hub
                  </Typography>

                  <Box
                    component="form"
                    onSubmit={handleSubmit}
                    noValidate
                    sx={{ mt: 1, width: '100%' }}
                  >
                    <TextField
                      margin="normal"
                      required
                      fullWidth
                      id="username"
                      label="username"
                      name="username"
                      autoComplete="username"
                      value={username}  // Add this
                      onChange={(e) => setUsername(e.target.value)}  // Add this
                      autoFocus
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          borderRadius: '10px',
                          mb: 2,
                          backgroundColor: '#f8f9fa',
                          '& fieldset': {
                            borderColor: '#e0e0e0',
                          },
                          '&:hover fieldset': {
                            borderColor: '#4361ee',
                          },
                          '&.Mui-focused fieldset': {
                            borderColor: '#4361ee',
                          },
                        }
                      }}
                    />
                    <TextField
                      margin="normal"
                      required
                      fullWidth
                      name="password"
                      label="Password"
                      type={showPassword ? 'text' : 'password'}
                      id="password"
                      autoComplete="current-password"
                      value={password}  // Add this
                      onChange={(e) => setPassword(e.target.value)}
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          borderRadius: '10px',
                          mb: 2,
                          backgroundColor: '#f8f9fa',
                          '& fieldset': {
                            borderColor: '#e0e0e0',
                          },
                          '&:hover fieldset': {
                            borderColor: '#4361ee',
                          },
                          '&.Mui-focused fieldset': {
                            borderColor: '#4361ee',
                          },
                        }
                      }}
                      InputProps={{
                        endAdornment: (
                          <InputAdornment position="end">
                            <IconButton
                              onClick={handlePasswordVisibility}
                              edge="end"
                            >
                              {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                            </IconButton>
                          </InputAdornment>
                        )
                      }}
                    />
                    <Button
                      type="submit"
                      fullWidth
                      variant="contained"
                      sx={{
                        mt: 3,
                        borderRadius: '10px',
                        height: { xs: 45, md: 50 },
                        bgcolor: themeColors.primary,
                        color: 'white',
                        fontWeight: 600,
                        textTransform: 'none',
                        fontSize: { xs: '1rem', md: '1.1rem' },
                        '&:hover': {
                          bgcolor: themeColors.primaryDark,
                          transform: 'translateY(-2px)',
                        },
                        transition: 'all 0.3s ease'
                      }}
                    >
                      {isLoading ? "Loading..." : "Sign In"}
                    </Button>
                  </Box>
                </Box>
              </Paper>
            </Grid>
          </Grid>
        </Box>
      </BackgroundBox>
    </ThemeProvider>
  );
};

export default Login;
