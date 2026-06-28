# Gestor de Correlativas

Sistema web para gestionar el avance en carreras universitarias. Permite cargar planes de estudio (PDF, texto o manualmente), hacer seguimiento del estado de cada materia por usuario, visualizar el progreso general y por año, y controlar correlativas.

---

## Características

### Autenticación multiusuario
- Registro e inicio de sesión con JWT
- El primer usuario registrado obtiene rol **admin** automáticamente
- Cada usuario tiene su propio estado de materias (promocionado, aprobado, regular, cursando, no cursada)
- Indicador visual del rol (admin/user) en la interfaz
- Sesión persistente (token en localStorage)

### Carga de planes de estudio
Tres métodos para cargar materias:

| Método | Descripción |
|--------|-------------|
| **PDF** | Subí un archivo PDF del plan de estudios. El sistema extrae las materias usando `pdfminer.six`. |
| **Texto** | Pegá el texto copiado del PDF o página web. Ideal cuando el PDF no se procesa bien. |
| **Manual** | Agregá materias una por una o cargá un JSON con todas las materias. |

### Parseo inteligente de planes
El sistema detecta automáticamente el formato del plan de estudios:

- **Formato tabular UNAM/FCEQyN** — tablas con años en palabras (PRIMERO, SEGUNDO, TERCERO), códigos romanos (I, II, III...), régimen (Anual/Cuatrimestral), carga horaria, correlativas en código romano y modalidad. Soporta nombres partidos en múltiples líneas (pre-texto + fila de datos + continuación).
- **Formato texto libre** — planes descriptivos con años, semestres y correlativas en texto plano.
- **Detección automática de facultad** — extrae el nombre de la universidad/facultad del encabezado del plan.
- **Resolución de correlativas** — convierte códigos romanos a nombres de materias automáticamente.
- **Vista previa editable** — antes de guardar, se pueden corregir nombres, años, semestres y correlativas.

### Seguimiento de materias
- Vista de todas las materias organizadas por año
- Estado visual por tarjeta con color de borde:
  - 🟢 Promocionado
  - 🔵 Aprobado
  - 🟣 Regular
  - 🟡 Cursando
  - ⚪ No cursada
- **Bloqueo por correlativas** — las materias con correlativas pendientes se muestran bloqueadas (🔒) hasta aprobar los requisitos. Se puede cambiar el estado igualmente con confirmación.
- Selector de estado en cada tarjeta con actualización instantánea.

### Visualización de progreso
- Barra de progreso general con porcentaje
- Estadísticas desglosadas por estado
- Progreso por año académico
- Texto del porcentaje superpuesto sin recortes (incluso en barras angostas)

### Búsqueda de carreras
- Filtro en tiempo real por nombre de carrera o facultad
- Interfaz con ícono de búsqueda integrado

### Interfaz de usuario
- Tema oscuro con gradientes
- Diseño responsive (adaptable a mobile)
- Notificaciones toast animadas con auto-dismiss
- Spinners en botones durante operaciones
- Navegación por tecla Enter en formularios de autenticación
- Flujo paso a paso: Carrera → Cargar plan → Mis materias → Avance

---

## Stack tecnológico

### Backend
| Tecnología | Versión | Uso |
|---|---|---|
| **Python** | 3.14+ | Lenguaje |
| **FastAPI** | Última | Framework web |
| **Uvicorn** | Última | Servidor ASGI |
| **SQLAlchemy** | Última | ORM y base de datos |
| **Pydantic** | Última | Validación de datos |
| **SQLite** | — | Base de datos |
| **PyJWT** | Última | Tokens de autenticación |
| **pdfminer.six** | Última | Extracción de texto de PDFs |

### Frontend
| Tecnología | Uso |
|---|---|
| **HTML5** | Estructura |
| **CSS3** | Estilos con variables CSS, flexbox, grid |
| **JavaScript (Vanilla)** | Lógica de aplicación, fetch API |

---

## Instalación y ejecución

### Requisitos
- Python 3.14 o superior
- pip

### Backend

```bash
cd backend
pip install --break-system-packages -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

El servidor arranca en `http://localhost:8000`.

### Frontend

Abrí `frontend/index.html` en tu navegador (o servilo con cualquier servidor HTTP estático).

> El frontend está configurado para conectar con `http://localhost:8000/api`. Si el backend corre en otro puerto, actualizá la constante `API` en `frontend/js/app.js`.

---

## API endpoints

### Autenticación
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/auth/register` | Registra nuevo usuario (el primero es admin) |
| POST | `/api/auth/login` | Inicia sesión, devuelve JWT |
| GET | `/api/auth/me` | Obtiene datos del usuario actual |

### Carreras
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/careers` | Lista todas las carreras |
| POST | `/api/careers` | Crea nueva carrera |
| GET | `/api/careers/{id}` | Obtiene carrera con materias |
| DELETE | `/api/careers/{id}` | Elimina carrera (solo admin) |
| POST | `/api/careers/{id}/subjects` | Agrega materias a una carrera |
| GET | `/api/careers/{id}/progress` | Progreso del usuario en la carrera |

### Materias
| Método | Ruta | Descripción |
|---|---|---|
| PUT | `/api/subjects/{id}` | Actualiza estado de una materia |

### Parseo
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/parse-pdf` | Sube PDF y extrae materias |
| POST | `/api/parse-text` | Envía texto y extrae materias |

---

## Estructura del proyecto

```
.
├── backend/
│   ├── main.py           # Servidor FastAPI, endpoints REST
│   ├── parser.py         # Parseo de PDF y texto (faculty table + legacy)
│   ├── auth.py           # Autenticación JWT, hash de contraseñas
│   ├── models.py         # Modelos SQLAlchemy (User, Career, Subject, UserSubject)
│   ├── schemas.py        # Schemas Pydantic para request/response
│   ├── database.py       # Conexión SQLite, sesión SQLAlchemy
│   └── requirements.txt  # Dependencias Python
├── frontend/
│   ├── index.html        # Página web principal
│   ├── css/
│   │   └── style.css     # Estilos (tema oscuro, responsive)
│   └── js/
│       └── app.js        # Lógica frontend (auth, API, UI)
├── ejemplo_plan.json     # Ejemplo de plan de estudios en JSON
├── changelog.md          # Registro de cambios
└── README.md             # Este archivo
```

---

## Formatos de plan de estudios soportados

### Formato tabular UNAM/FCEQyN
```
COD.    ASIGNATURA            RÉGIMEN     CARGA   CARGA   CORRELATIVAS    MODALIDAD
                                          HORARIA HORARIA
                                          SEMANAL TOTAL

PRIMERO
        Álgebra
  I                          Anual        5       80      -               Presencial
        Geometría Analítica
 II                          Anual        5       80      I               Presencial

III     Cálculo Diferencial  Cuatrimestral 4      64      -               Presencial
```

Características:
- Años en palabras: PRIMERO, SEGUNDO, TERCERO...
- Materias identificadas por números romanos (I, II, III, IV, V...)
- El nombre puede estar en la misma línea del código romano o en líneas separadas
- Continuaciones de nombre en líneas siguientes con mayor indentación
- Correlativas expresadas como códigos romanos (I, I-II, XIV-, etc.)

### Formato texto libre
```
Año 1 - Semestre 1:
- Análisis Matemático I
- Álgebra (correlativa: -)

Año 1 - Semestre 2:
- Análisis Matemático II (correlativa: Análisis Matemático I)
```

---

## Licencia

Este proyecto fue desarrollado como trabajo práctico para la materia Ingeniería de Software III.
