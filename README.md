# 📊 Corte Diario Promotor

Herramienta web para analizar portafolios de inversión de Mercado de Dinero a partir del corte diario de Valmer. Extrae posiciones por cliente, consulta tasas de referencia de Banxico en tiempo real y despliega la composición del portafolio con gráficas interactivas.

---

## ¿Qué hace?

- Carga el Excel del corte diario (formato Valmer) y extrae automáticamente todas las posiciones de Mercado de Dinero por cliente
- Consulta la **TIIE 28 días** y la **TIIE de Fondeo** directamente de la API del Banco de México
- Lee un catálogo de emisoras desde Google Sheets con fechas de emisión, vencimiento y spread sobre tasa de referencia
- Calcula la **tasa total** de cada instrumento (spread + TIIE correspondiente)
- Muestra para cada cliente su portafolio, valor total de cartera, días a vencimiento y composición en gráfica de pie
- Permite descargar el resultado completo en Excel

---

## Estructura del repositorio

```
corte-diario-promotor/
├── Corte_diario.py      # App principal
├── requirements.txt     # Dependencias
└── README.md
```

---

## Instalación local

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/corte-diario-promotor.git
cd corte-diario-promotor

# Instalar dependencias
pip install -r requirements.txt

# Correr la app
streamlit run Corte_diario.py
```

---

## Uso

1. Abre la app (local o en Streamlit Cloud)
2. Sube el archivo Excel del corte diario en el panel izquierdo
3. Las tasas de Banxico se cargan automáticamente
4. Selecciona un cliente en el menú desplegable
5. Consulta su portafolio, tasa total y composición
6. Descarga el resultado en Excel si lo necesitas

---

## Fuentes de datos

| Fuente | Qué provee | Actualización |
|---|---|---|
| Excel Valmer | Posiciones, valuación, VTC por cliente | Manual (se sube cada día) |
| API Banxico SIE | TIIE 28 días (`SF60648`) y TIIE Fondeo (`SF331451`) | Caché 24 horas |
| Google Sheets | Catálogo de emisoras: fechas, spread, tipo de tasa | Caché 10 minutos |

---

## Caché

Las tasas de Banxico se almacenan en caché por **24 horas** y el catálogo de Google Sheets por **10 minutos**. Esto evita llamadas repetidas a las APIs externas cada vez que el usuario interactúa con la app.

---

## Requisitos

```
streamlit
pandas
openpyxl
requests
plotly
```

---

## Deploy en Streamlit Cloud

1. Haz fork o sube este repositorio a tu cuenta de GitHub
2. Entra a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu cuenta de GitHub
4. Selecciona el repositorio y en **Main file path** escribe `Corte_diario.py`
5. Clic en **Deploy**

---

## Notas

- El Excel debe ser el formato estándar del corte diario de Valmer (promotor)
- El catálogo de Google Sheets debe estar compartido como "cualquier persona con el enlace puede ver"
- El token de Banxico está incluido en el código — si caduca, solicita uno nuevo en [banxico.org.mx](https://www.banxico.org.mx/SieAPIRest/service/v1/token)
