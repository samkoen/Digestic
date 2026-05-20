import { createTheme, alpha } from '@mui/material/styles'

const primaryMain = '#0B7B6A'
const primaryDark = '#065A4D'
const primaryLight = '#14A892'

export const digesticTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: primaryMain,
      dark: primaryDark,
      light: primaryLight,
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#3D4F7C',
      dark: '#2A3658',
      light: '#5C6F9E',
    },
    success: { main: '#2E7D4F' },
    warning: { main: '#E67E22' },
    error: { main: '#C62828' },
    background: {
      default: '#F0F4F3',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1A2332',
      secondary: '#5C6B7A',
    },
    divider: alpha('#1A2332', 0.08),
  },
  typography: {
    fontFamily: '"Plus Jakarta Sans", "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    h4: { fontWeight: 700, letterSpacing: '-0.02em' },
    h5: { fontWeight: 700, letterSpacing: '-0.01em' },
    h6: { fontWeight: 600 },
    subtitle1: { fontWeight: 500 },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#F0F4F3',
          backgroundImage:
            'radial-gradient(ellipse 80% 50% at 50% -20%, rgba(11, 123, 106, 0.08), transparent)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 10, padding: '10px 20px' },
        contained: {
          boxShadow: '0 4px 14px rgba(11, 123, 106, 0.25)',
          '&:hover': { boxShadow: '0 6px 20px rgba(11, 123, 106, 0.35)' },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          border: `1px solid ${alpha('#1A2332', 0.06)}`,
          boxShadow: '0 4px 20px rgba(26, 35, 50, 0.06)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        rounded: { borderRadius: 16 },
      },
    },
    MuiTextField: {
      defaultProps: { variant: 'outlined' },
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': { borderRadius: 10 },
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          minHeight: 48,
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: {
          height: 3,
          borderRadius: '3px 3px 0 0',
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-head': {
            fontWeight: 600,
            backgroundColor: alpha(primaryMain, 0.04),
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 500 },
      },
    },
  },
})

export const sidebarWidth = 268
