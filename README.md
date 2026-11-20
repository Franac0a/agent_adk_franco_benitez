# agent_adk_franco_benitez — Gestor de Gastos Personales

Agente de inteligencia artificial desarrollado con **Python** y **Google Agent Development Kit (ADK)** que ayuda a llevar el control de los gastos personales. El modelo se conecta mediante **LiteLLM**, por lo que puede usarse con Gemini, Groq, Ollama u otro proveedor compatible.

No es un chatbot que solo genera texto: el agente interpreta lo que pide el usuario, decide qué herramienta(s) usar, las ejecuta sobre los datos guardados y arma la respuesta a partir de los resultados.

## Problema que resuelve

Anotar gastos y saber en qué se va la plata suele ser tedioso. Con este agente el usuario puede escribir en lenguaje natural, por ejemplo *"ayer gasté 12000 en el cine"* o *"¿cómo voy con un presupuesto de 400000 este mes?"*, y el agente registra, busca, resume o controla el presupuesto según corresponda.

## Herramientas

| Herramienta | Responsabilidad | Parámetros |
|---|---|---|
| `registrar_gasto` | Guarda un nuevo gasto | `descripcion`, `monto`, `categoria`, `fecha` (opcional, AAAA-MM-DD; por defecto hoy) |
| `buscar_gastos` | Lista/filtra gastos | `categoria`, `desde`, `hasta`, `texto` (todos opcionales) |
| `resumen_gastos` | Estadísticas: total, promedio, total y % por categoría, gasto más alto | `mes` (opcional, AAAA-MM) |
| `verificar_presupuesto` | Compara lo gastado contra un presupuesto e indica estado `dentro` / `alerta` (≥80%) / `excedido` | `presupuesto`, `mes`, `categoria` (opcional) |
| `eliminar_gasto` | Borra un gasto por su id | `gasto_id` |

Categorías válidas: `alimentacion`, `transporte`, `vivienda`, `servicios`, `salud`, `educacion`, `ocio`, `ropa`, `otros`.

Los gastos se guardan en `gestor_gastos/data/gastos.json`.

### Validaciones

Todas las herramientas devuelven un diccionario con `status`:

- `success`: la operación se realizó correctamente.
- `error` + `error_message`: argumentos inválidos (monto negativo o no numérico, categoría inexistente, fecha con formato incorrecto o futura, rango de fechas invertido, id inexistente, presupuesto ≤ 0, etc.).
- `empty`: la consulta no encontró resultados (sin gastos en ese período o con esos filtros).

El agente tiene instrucciones para explicar los errores en lenguaje simple y sugerir cómo corregirlos, y para no inventar datos que no provengan de una herramienta.

## Instrucciones del agente

Definidas en `gestor_gastos/agent.py`:

- **Rol:** asistente financiero personal "Gestor de Gastos".
- **Objetivo:** registrar, consultar y analizar gastos, y controlar presupuestos.
- **Restricciones:** no inventar montos ni totales; usar solo las categorías válidas; pedir los datos obligatorios que falten; no responder temas ajenos (por ejemplo, inversiones).
- **Comportamiento:** responder en español, breve y claro; manejar los estados `error` y `empty`; encadenar herramientas cuando hace falta (ej.: buscar un gasto antes de eliminarlo).

## Estructura

```
agent_adk_franco_benitez/
├── gestor_gastos/            # paquete del agente (lo detecta `adk web`)
│   ├── __init__.py
│   ├── agent.py              # root_agent: modelo, instrucciones y herramientas
│   ├── tools.py              # las 5 herramientas + validaciones
│   ├── .env.example          # configuración del modelo
│   └── data/
│       └── gastos_ejemplo.json
├── tests/test_tools.py       # pruebas de las herramientas
├── cargar_ejemplo.py         # carga datos de ejemplo
└── requirements.txt
```

## Instalación y uso

1. Clonar el repositorio y crear un entorno virtual:

   ```bash
   git clone https://github.com/Franac0a/agent_adk_franco_benitez.git
   cd agent_adk_franco_benitez
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux / macOS
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Configurar el modelo: copiar `gestor_gastos/.env.example` a `gestor_gastos/.env` y completar la API key.

   ```env
   MODEL=gemini/gemini-2.5-flash
   GEMINI_API_KEY=tu_api_key
   ```

   También se puede usar `groq/llama-3.3-70b-versatile` (con `GROQ_API_KEY`) o un modelo local con Ollama (`ollama_chat/llama3.1`).

3. (Opcional) Cargar datos de ejemplo:

   ```bash
   python cargar_ejemplo.py
   ```

4. Ejecutar la interfaz web de ADK desde la carpeta raíz del proyecto:

   ```bash
   adk web
   ```

   Abrir http://localhost:8000 y seleccionar el agente **gestor_gastos**. En la pestaña *Events* se puede ver qué herramienta eligió el agente y con qué argumentos.

   Alternativa por consola: `adk run gestor_gastos`.

5. Ejecutar las pruebas de las herramientas (no necesitan API key):

   ```bash
   python -m unittest discover tests -v
   ```

## Ejemplos de uso (selección de herramientas)

| Mensaje del usuario | Herramienta(s) que usa el agente |
|---|---|
| "Hoy gasté 8500 en la farmacia" | `registrar_gasto` (infiere categoría `salud`) |
| "Mostrame los gastos de transporte de noviembre" | `buscar_gastos` |
| "¿En qué gasté más este mes?" | `resumen_gastos` |
| "Tengo un presupuesto de 150000 para noviembre, ¿cómo voy?" | `verificar_presupuesto` |
| "Borrá el gasto del cine" | `buscar_gastos` → `eliminar_gasto` |
| "Gasté -500 en ropa" | `registrar_gasto` → devuelve error y el agente lo explica |
| "Resumen de enero 2020" | `resumen_gastos` → `empty`, el agente informa que no hay datos |

## Autor

Franco Benitez
