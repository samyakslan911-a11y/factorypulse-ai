# 🔐 Implementando Auth — FactoryPulse AI

> Abre este archivo con `Ctrl+Shift+V` para ver el preview de Markdown en VS Code

---

## Flujo de auth que estamos construyendo

```
Browser → /login → Supabase Auth → JWT token
                                       ↓
                              FastAPI (Railway)
                                       ↓
                           get_current_user(token)
                                       ↓
                           Supabase verifica JWT
                                       ↓
                           user_id real → DB queries
```

---

## Progreso actual

### Backend ✅

| Archivo | Qué cambia | Estado |
|---|---|---|
| `backend/auth/__init__.py` | Nuevo módulo | ✅ Listo |
| `backend/auth/dependencies.py` | `get_current_user` — valida JWT de Supabase | ✅ Listo |
| `backend/api/suppliers.py` | Reemplaza `DEMO_USER_ID` por `Depends(get_current_user)` | ✅ Listo |
| `backend/api/analyses.py` | Mismo cambio — user_id del token | ✅ Listo |

### Frontend 🔄

| Archivo | Qué cambia | Estado |
|---|---|---|
| `npm @supabase/supabase-js` | Cliente Supabase | ✅ Instalado |
| `src/lib/supabase.ts` | Cliente Supabase compartido | ✅ Listo |
| `src/lib/api.ts` | `apiFetch()` inyecta `Authorization: Bearer token` | ✅ Listo |
| `src/components/AuthProvider.tsx` | Context — mantiene sesión, redirige si no hay token | ✅ Listo |
| `src/app/login/page.tsx` | Página login/signup con email+password | ✅ Listo |
| `src/components/LogoutButton.tsx` | Botón salir + email del usuario en el header | ✅ Listo |
| `src/app/layout.tsx` | Envuelve con AuthProvider, agrega LogoutButton | ✅ Listo |
| `src/app/page.tsx` | `fetch` → `apiFetch` | ✅ Listo |
| `src/components/SupplierCard.tsx` | `fetch` → `apiFetch` | 🔄 Haciendo... |
| `src/components/NewSupplierModal.tsx` | `fetch` → `apiFetch` | ⏳ Pendiente |
| `src/app/suppliers/[id]/page.tsx` | `fetch` → `apiFetch` | ⏳ Pendiente |

### Variables de entorno ⏳

| Variable | Dónde agregar | Valor |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Vercel | Tu Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Vercel | Tu Supabase anon key |

---

## El cambio clave (backend)

```python
# ANTES — hardcodeado
DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"

def list_suppliers():
    return db.list_suppliers(DEMO_USER_ID)  # ✗

# DESPUÉS — del token JWT
from backend.auth.dependencies import get_current_user

def list_suppliers(user_id: str = Depends(get_current_user)):
    return db.list_suppliers(user_id)  # ✓
```

## El cambio clave (frontend)

```typescript
// ANTES
const res = await fetch(apiUrl("/suppliers/"));

// DESPUÉS — incluye el Bearer token automáticamente
const res = await apiFetch("/suppliers/");
```

---

## Pasos restantes

- [x] Backend auth dependency
- [x] Routers actualizados
- [x] Supabase client frontend
- [x] AuthProvider + login page
- [x] LogoutButton + layout
- [x] page.tsx migrado
- [x] SupplierCard migrado
- [x] NewSupplierModal migrado
- [x] suppliers/[id]/page.tsx migrado
- [ ] Variables de entorno en Vercel ← **TÚ haces esto**
- [ ] Commit + deploy

---

*Actualizo este archivo a medida que avanzo*
