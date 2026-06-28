import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AdminLayout } from './layouts/AdminLayout'
import { AuthLayout } from './layouts/AuthLayout'
import { AdminHomePage } from '../features/admin/pages/AdminHomePage'
import { AuditLogsPage } from '../features/admin/pages/AuditLogsPage'
import { RolesPage } from '../features/admin/pages/RolesPage'
import { UsersPage } from '../features/admin/pages/UsersPage'
import { ModuleHubPage } from '../features/app/pages/ModuleHubPage'
import { LlmPage } from '../features/llm/pages/LlmPage'
import { AuthCallbackPage } from '../features/auth/pages/AuthCallbackPage'
import { LoginPage } from '../features/auth/pages/LoginPage'
import { RequireAuth, RequirePermission } from '../features/auth/guards'
import { KnowledgeBasesPage } from '../features/knowledge/pages/KnowledgeBasesPage'
import { ForbiddenPage } from '../shared/components/ForbiddenPage'

export const router = createBrowserRouter([
  {
    element: <AuthLayout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/auth/callback', element: <AuthCallbackPage /> },
      { path: '/403', element: <ForbiddenPage /> },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      {
        path: '/app',
        element: <ModuleHubPage />,
      },
      {
        element: <RequirePermission permission="llm.chat.use" />,
        children: [{ path: '/app/llm', element: <LlmPage /> }],
      },
      {
        element: <RequirePermission permission="kb.knowledge_base.read" />,
        children: [{ path: '/app/knowledge', element: <KnowledgeBasesPage /> }],
      },
      {
        element: <RequirePermission permission="platform.admin.access" />,
        children: [
          {
            path: '/admin',
            element: <AdminLayout />,
            children: [
              { index: true, element: <AdminHomePage /> },
              {
                element: <RequirePermission permission="iam.user.read" />,
                children: [{ path: 'users', element: <UsersPage /> }],
              },
              {
                element: <RequirePermission permission="iam.role.read" />,
                children: [{ path: 'roles', element: <RolesPage /> }],
              },
              {
                element: <RequirePermission permission="audit.log.read" />,
                children: [{ path: 'audit-logs', element: <AuditLogsPage /> }],
              },
            ],
          },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/app" replace /> },
])
