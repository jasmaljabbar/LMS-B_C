import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import Layout from '../components/Layout';
import ProtectedRoute from '../components/ProtectedRoute';
import Home from '../pages/Home';
import Dashboard from '../pages/Dashboard';
import Login from '../pages/Login';
import ParentDashboard from '../pages/ParentDashboard';
import AssignmentPage from '../pages/Assignments';
import StudentDashboard from '../components/StudentDashboard/studentDashboard';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Login />,
    index: true
  },
  {
    path: '/dashboard',
    element: <ProtectedRoute>
      <Layout>
        <AssignmentPage />
      </Layout>
    </ProtectedRoute>
  },
  {
    path: '/assignments',
    element: <ProtectedRoute>
      <Layout>
        <AssignmentPage />
      </Layout>
    </ProtectedRoute>
  },
  {
    path: '/parent-dashboard',
    element: <ProtectedRoute>
      <Layout>
        <ParentDashboard />
      </Layout>
    </ProtectedRoute>
  },
  {
    path: '/student-dashboard',
    element: <ProtectedRoute>
      <Layout>
        <StudentDashboard />
      </Layout>
    </ProtectedRoute>
  }
]);

export default router;
