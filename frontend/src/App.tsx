import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Login } from './pages/Login';
import { Home } from './pages/Home';
import { Checkin } from './pages/Checkin';
import { Chat } from './pages/Chat';
import { Trends } from './pages/Trends';
import { Crew } from './pages/Crew';
import { Emergency } from './pages/Emergency';
import { Booklet } from './pages/Booklet';
import { Recover } from './pages/Recover';
import { ScenarioLab } from './pages/ScenarioLab';
import { Ground } from './pages/Ground';
import { Profile } from './pages/Profile';
import { useDemo } from './hooks/useDemo';
import { useAuth } from './hooks/useAuth';
import { roleHome } from './utils/roles';

const ROLE_ROUTES: Record<string, string[]> = {
  '/': ['astronaut'],
  '/checkin': ['astronaut'],
  '/chat': ['astronaut', 'cmo'],
  '/trends': ['astronaut', 'cmo'],
  '/crew': ['cmo', 'ground', 'admin'],
  '/emergency': ['astronaut', 'cmo'],
  '/booklet': ['astronaut', 'cmo', 'ground', 'admin'],
  '/recover': ['astronaut'],
  '/scenario-lab': ['ground', 'admin'],
  '/ground': ['ground', 'admin'],
  '/profile': ['astronaut', 'cmo', 'ground', 'admin'],
};

function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="animate-spin rounded-full h-12 w-12 border-4 border-teal-500 border-t-transparent" />
    </div>
  );
}

function RequireRole({ children, roles }: { children: React.ReactNode; roles: string[] }) {
  const { user, hasRole, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Loading />;

  if (!user) {
    return <Navigate to={`/login${location.search}`} replace />;
  }

  if (!hasRole(roles)) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center">
          <p className="text-gray-500 text-lg">Access denied</p>
          <p className="text-gray-400 mt-2">Your role ({user.role}) cannot access this page</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

function HomeRoute() {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) return <Navigate to={`/login${location.search}`} replace />;
  if (user.role !== 'astronaut') {
    return <Navigate to={`${roleHome(user.role)}${location.search}`} replace />;
  }
  return (
    <RequireRole roles={ROLE_ROUTES['/']}>
      <Home />
    </RequireRole>
  );
}

function AppRoutes() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Loading />;

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to={`${roleHome(user.role)}${location.search}`} replace /> : <Login />}
      />
      <Route element={<Layout />}>
        <Route path="/" element={<HomeRoute />} />
        <Route
          path="/checkin"
          element={
            <RequireRole roles={ROLE_ROUTES['/checkin']}>
              <Checkin />
            </RequireRole>
          }
        />
        <Route
          path="/chat"
          element={
            <RequireRole roles={ROLE_ROUTES['/chat']}>
              <Chat />
            </RequireRole>
          }
        />
        <Route
          path="/trends"
          element={
            <RequireRole roles={ROLE_ROUTES['/trends']}>
              <Trends />
            </RequireRole>
          }
        />
        <Route
          path="/crew"
          element={
            <RequireRole roles={ROLE_ROUTES['/crew']}>
              <Crew />
            </RequireRole>
          }
        />
        <Route
          path="/emergency"
          element={
            <RequireRole roles={ROLE_ROUTES['/emergency']}>
              <Emergency />
            </RequireRole>
          }
        />
        <Route
          path="/booklet"
          element={
            <RequireRole roles={ROLE_ROUTES['/booklet']}>
              <Booklet />
            </RequireRole>
          }
        />
        <Route
          path="/recover"
          element={
            <RequireRole roles={ROLE_ROUTES['/recover']}>
              <Recover />
            </RequireRole>
          }
        />
        <Route
          path="/scenario-lab"
          element={
            <RequireRole roles={ROLE_ROUTES['/scenario-lab']}>
              <ScenarioLab />
            </RequireRole>
          }
        />
        <Route
          path="/ground"
          element={
            <RequireRole roles={ROLE_ROUTES['/ground']}>
              <Ground />
            </RequireRole>
          }
        />
        <Route
          path="/profile"
          element={
            <RequireRole roles={ROLE_ROUTES['/profile']}>
              <Profile />
            </RequireRole>
          }
        />
        <Route
          path="*"
          element={<Navigate to={user ? roleHome(user.role) : `/login${location.search}`} replace />}
        />
      </Route>
    </Routes>
  );
}

function App() {
  useDemo();
  return <AppRoutes />;
}

export default App;
