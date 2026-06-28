# Changelog

## [2026-06-28] Correcciones en parser, buscador y UX

### Realizado
- **Parser**: tabla de encabezados mejorada — normaliza espacios múltiples antes de buscar palabras clave, agrega "carga", "horaria", "semanal", "total", "código" y otras palabras de encabezado para evitar filtraciones en nombres de materias
- **Parser**: filtro de palabras de encabezado en la ruta de continuación (líneas entre filas de datos) para que no se agreguen a nombres de materias
- **Parser**: umbral `_is_continuation_line` cambiado de `< 12` a `<= 12` para capturar palabras como "Programación" (12 caracteres)
- **Parser**: `looks_like_faculty_table` — regex corregido para no consumir "Anual"/"Cuatrimestral" con `\S+`
- **Parser**: `detect_faculty_name` — filtra líneas de encabezado de tabla (COD, CARGA, etc.) y no las incluye en el nombre de facultad; regex ampliado para incluir caracteres acentuados (ÁÉÍÓÚÜÑ)
- **PDF**: lectura correcta de materias desde archivos PDF comprobada con formato tabular UNAM/FCEQyN
- **Frontend**: esquema de colores rediseñado — paleta ámbar sobre fondo oscuro, sin gradientes genéricos, aspecto más limpio y profesional
- **Frontend**: buscador de carreras rediseñado con contenedor integrado, ícono de búsqueda y borde que resalta al enfocar
- **Frontend**: navegación por tecla Enter en formularios de login/register
- **Frontend**: sesión efímera (sessionStorage en lugar de localStorage) — al cerrar la pestaña se requiere login nuevamente

## [2026-06-28] Frontend: rediseño completo

### Realizado
- **HTML**: reestructurado con flujo paso a paso (1. Carrera → 2. Cargar plan → 3. Mis materias → 4. Avance)
- **HTML**: tabs para alternar entre métodos de carga (PDF / Texto / Manual)
- **HTML**: sección de vista previa editable con botones Confirmar y Cancelar
- **HTML**: contenedor de toasts para notificaciones
- **CSS**: tema oscuro con gradientes y paleta de colores definida en variables CSS
- **CSS**: tarjetas de materias con borde izquierdo según estado (promocionado, aprobado, regular, cursando, no_cursada)
- **CSS**: barras de progreso animadas (general y por año)
- **CSS**: toasts animados con auto-dismiss
- **CSS**: diseño responsive adaptable a mobile
- **JS**: sistema de notificaciones toast (info, success, warning, error)
- **JS**: spinners en botones durante operaciones asíncronas
- **JS**: manejo de errores con `try/catch` en todas las llamadas a la API
- **JS**: tabs funcionales con toggle de paneles
- **JS**: vista previa editable (nombre, año, semestre, correlativas)
- **JS**: confirmar envía materias al backend, cancelar descarta

## [2026-06-28] Parser: soporte para formato UNAM/FCEQyN

### Realizado
- **Parser**: nuevo `parse_faculty_table()` para formato tabular con años en palabras (PRIMERO, SEGUNDO, TERCERO)
- **Parser**: detección automática del formato mediante `looks_like_faculty_table()`
- **Parser**: extracción de materias con nombre partido en líneas de continuación (pre-text + data row + continuación)
- **Parser**: detección de semestre desde marcadores `(1º C)` y `(2º C)` en el nombre
- **Parser**: mapeo de códigos romanos (I, II, III...) a nombres de materias para resolver correlativas
- **Parser**: soporte para líneas de continuación de correlativas (p.ej. `XIV- XVI-` en líneas separadas)
- **Parser**: deduplicación de materias con mismo nombre en distintos años (agrega " (N° Año)")
- **Parser**: legacy parser intacto como fallback

## [2026-06-28] Sistema de usuarios + autenticación JWT

### Realizado
- **Backend/auth.py**: módulo de autenticación con JWT (PyJWT), hasheo de contraseñas con pbkdf2_hmac, dependencias `get_current_user` y `require_admin`
- **Backend/models.py**: nuevos modelos `User` (username, password_hash, role) y `UserSubject` (user_id, subject_id, status); eliminado `status` de `Subject` (pasa a ser por usuario)
- **Backend/main.py**: endpoints `/api/auth/register` (primer usuario = admin), `/api/auth/login`, `/api/auth/me`; todos los endpoints protegidos con JWT; creación/edición de carreras solo para admin; status de materias por usuario (se crea UserSubject automáticamente al primer acceso)
- **Backend/schemas.py**: schemas de auth (AuthRegister, AuthLogin, AuthOut, UserOut)
- **Backend/requirements.txt**: agregado `pyjwt`
- **Frontend/index.html**: pantalla de login/register con tabs + contenedor main-app, reemplaza el inicio directo de la app
- **Frontend/app.js**: estado de sesión (token en localStorage), headers de auth en todas las llamadas, cierre de sesión, badge de usuario con indicador de admin, controles admin visibles solo para rol admin
- **Frontend/style.css**: estilos para auth-tabs, header-row con usuario, botón de logout

### Pendiente
- Test end-to-end con PDF real de plan de estudios (formato UNAM)
- Agregar edición/eliminación de materias individuales desde la sección "Mis materias"
- Endpoints de admin para eliminar usuarios o cambiar roles
