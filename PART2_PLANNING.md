# 📋 Part 2 — SaaS Multi-Tenant Solution Planning

## 🎯 Overview

Part 2 transforms the single-user MVP into a multi-tenant SaaS platform where:
- Multiple clients can sign up and manage their own AI assistants
- Each client can have multiple end-users
- Usage analytics and billing tracking
- API key management for client integrations
- Admin panel for system management

---

## 🗄️ Database Schema Design

### Tables

#### 1. `clients`
- `id` (UUID, PK)
- `name` (VARCHAR)
- `email` (VARCHAR, UNIQUE)
- `password_hash` (VARCHAR)
- `api_key` (VARCHAR, UNIQUE)
- `tier` (ENUM: free, pro, enterprise)
- `status` (ENUM: active, suspended, deleted)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

#### 2. `users`
- `id` (UUID, PK)
- `client_id` (UUID, FK → clients.id)
- `username` (VARCHAR)
- `email` (VARCHAR)
- `role` (ENUM: admin, user)
- `created_at` (TIMESTAMP)
- `last_active` (TIMESTAMP)

#### 3. `documents`
- `id` (UUID, PK)
- `client_id` (UUID, FK → clients.id)
- `user_id` (UUID, FK → users.id, nullable)
- `filename` (VARCHAR)
- `file_path` (VARCHAR)
- `index_path` (VARCHAR)
- `file_size` (BIGINT)
- `chunk_count` (INT)
- `status` (ENUM: processing, ready, error)
- `uploaded_at` (TIMESTAMP)

#### 4. `conversations`
- `id` (UUID, PK)
- `client_id` (UUID, FK → clients.id)
- `user_id` (UUID, FK → users.id, nullable)
- `document_id` (UUID, FK → documents.id)
- `started_at` (TIMESTAMP)
- `ended_at` (TIMESTAMP, nullable)

#### 5. `messages`
- `id` (UUID, PK)
- `conversation_id` (UUID, FK → conversations.id)
- `role` (ENUM: user, assistant)
- `content` (TEXT)
- `message_type` (ENUM: text, voice)
- `created_at` (TIMESTAMP)

#### 6. `usage_analytics`
- `id` (UUID, PK)
- `client_id` (UUID, FK → clients.id)
- `date` (DATE)
- `text_queries` (INT)
- `voice_queries` (INT)
- `voice_minutes` (FLOAT)
- `documents_processed` (INT)
- `total_tokens` (BIGINT)

---

## 🔐 Authentication Flow

### JWT Token Structure
```json
{
  "sub": "client_id",
  "role": "client|admin",
  "exp": 1234567890
}
```

### Endpoints
- `POST /auth/register` - Client registration
- `POST /auth/login` - Login (returns JWT)
- `POST /auth/refresh` - Refresh token
- `POST /auth/logout` - Invalidate token
- `GET /auth/me` - Get current user info

---

## 🏗️ Implementation Phases

### Phase 2.1 — Database & Authentication (Week 1)

**Tasks:**
1. Set up PostgreSQL database (local + Docker)
2. Create SQLAlchemy models for all tables
3. Set up Alembic for migrations
4. Implement JWT authentication middleware
5. Create auth endpoints (register, login, refresh)
6. Add role-based access control decorators
7. Update document service to use per-client FAISS indices

**Files to Create:**
- `backend/app/db/database.py` - Database connection
- `backend/app/db/models.py` - SQLAlchemy models
- `backend/app/db/crud.py` - CRUD operations
- `backend/app/core/security.py` - JWT & password hashing
- `backend/app/api/auth.py` - Auth endpoints
- `backend/app/middleware/auth.py` - Auth middleware
- `backend/alembic/` - Migration files

**Dependencies to Add:**
```
sqlalchemy==2.0.23
alembic==1.13.1
psycopg2-binary==2.9.9
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
```

### Phase 2.2 — Client Portal (Week 2)

**Tasks:**
1. Create client dashboard API endpoints
2. Implement usage analytics aggregation
3. Build API key generation & management
4. Create embeddable widget code generator
5. Add rate limiting per client tier
6. Build client dashboard UI (React)

**Files to Create:**
- `backend/app/api/client.py` - Client management endpoints
- `backend/app/api/analytics.py` - Analytics endpoints
- `backend/app/services/analytics_service.py` - Analytics logic
- `backend/app/middleware/rate_limit.py` - Rate limiting
- `frontend/src/pages/ClientDashboard.jsx` - Dashboard UI
- `frontend/src/pages/ApiKeys.jsx` - API key management UI

### Phase 2.3 — End-User Management (Week 3)

**Tasks:**
1. Implement session tracking
2. Add conversation history persistence
3. Create user-specific document management
4. Build user management UI for clients
5. Add usage quotas per tier

**Files to Create:**
- `backend/app/api/users.py` - User management endpoints
- `backend/app/services/session_service.py` - Session tracking
- `frontend/src/pages/UserManagement.jsx` - User management UI

### Phase 2.4 — Admin Panel (Week 4)

**Tasks:**
1. Create admin dashboard with system metrics
2. Build client management interface (CRUD)
3. Add system health monitoring
4. Create billing/subscription placeholder UI
5. Add audit logging

**Files to Create:**
- `backend/app/api/admin.py` - Admin endpoints
- `backend/app/services/monitoring_service.py` - System monitoring
- `frontend/src/pages/AdminDashboard.jsx` - Admin UI
- `frontend/src/pages/ClientManagement.jsx` - Client management UI

---

## 🔄 Migration Strategy

### From Single-User to Multi-Tenant

1. **Backward Compatibility:**
   - Keep existing endpoints working for testing
   - Add new `/v2/` endpoints with auth required
   - Gradually migrate frontend to use v2 endpoints

2. **Data Migration:**
   - Create a "default" client for existing data
   - Move existing documents to default client's namespace
   - Preserve existing FAISS indices

3. **Testing Strategy:**
   - Unit tests for all new endpoints
   - Integration tests for auth flow
   - Load testing for multi-tenant isolation

---

## 📊 Tier Limits

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| Documents | 1 | 10 | Unlimited |
| Queries/day | 100 | 1,000 | Unlimited |
| Voice minutes/month | 10 | 100 | Unlimited |
| Users | 1 | 5 | Unlimited |
| API Access | ❌ | ✅ | ✅ |
| Custom branding | ❌ | ❌ | ✅ |

---

## 🚀 Getting Started with Part 2

### Prerequisites
- Part 1 MVP fully tested and working
- PostgreSQL installed locally or via Docker
- Understanding of JWT authentication
- Familiarity with SQLAlchemy ORM

### First Steps
1. Install PostgreSQL
2. Create a new database: `voice_rag_saas`
3. Update `.env` with database connection string
4. Install new dependencies
5. Create initial database schema
6. Test authentication flow

### Docker Setup (Recommended)
```bash
docker run --name voice-rag-postgres \
  -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_DB=voice_rag_saas \
  -p 5432:5432 \
  -d postgres:15
```

---

## 📝 Notes

- Keep the MVP endpoints working during development
- Use feature flags to gradually roll out SaaS features
- Document all API changes in OpenAPI/Swagger
- Consider using Redis for session management and rate limiting
- Plan for horizontal scaling from the start

---

**Ready to start?** Begin with Phase 2.1 by setting up the database and authentication system.
