import pandas as pd
import re
import requests
import plotly.express as px
import streamlit as st
from datetime import datetime
import io


BANXICO_TOKEN = "5b4940077ca974bf7d505dcf537701c924ed3c8264499dec142fc79f65c5cf72"

SERIES_BANXICO = {
    'tiie_28':     'SF60648',   
    'tiie_fondeo': 'SF331451', 
}

@st.cache_data(ttl=86400,show_spinner="Consultando tasas Banxico...")
def get_tasas_banxico() -> dict:
    
    ids = ','.join(SERIES_BANXICO.values())
    
   
    url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{ids}/datos/oportuno"
    
    headers = {
        'Bmx-Token': BANXICO_TOKEN,
        'Accept':    'application/json'}
    
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    
    series = resp.json()['bmx']['series']
    
    resultado = {}
    id_to_nombre = {v: k for k, v in SERIES_BANXICO.items()}
    
    for s in series:
        nombre = id_to_nombre[s['idSerie']]
        datos  = s.get('datos', [])
        if datos:
            ultimo = datos[-1]
            resultado[nombre]         = float(ultimo['dato'])
            resultado[nombre + '_fecha'] = ultimo['fecha']
    
    return resultado

@st.cache_data(ttl=600000,show_spinner="Leyendo catálogo...")
def get_sheet():
    url = "https://docs.google.com/spreadsheets/d/1Li6A3vVrxj3U6stsJG9lsjre0lkeynJR/export?format=csv&gid=736741268"
    return pd.read_csv(url)

st.set_page_config(page_title="Corte Diario Promotor", page_icon="📊", layout="wide")
st.title("📊 Corte Diario Promotor")

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuración")
    archivo = st.file_uploader("Sube el Excel del corte", type=["xlsx"])
    st.divider()
    tasas = get_tasas_banxico()
    if tasas:
        st.metric("TIIE 28 días",  f"{tasas['tiie_28']:.4f}%",  tasas['tiie_28_fecha'])
        st.metric("TIIE Fondeo",   f"{tasas['tiie_fondeo']:.4f}%", tasas['tiie_fondeo_fecha'])
    st.divider()
    if st.button("🔄 Actualizar catálogo"):
        get_sheet.clear()
        st.rerun()

if not archivo:
    st.info("👆 Sube el archivo Excel del corte diario para comenzar.")
    st.stop()

# Reemplaza ARCHIVO_EXCEL por archivo (el objeto subido)
df_raw = pd.read_excel(archivo, header=None, engine="openpyxl")

# FUNCIONES DE PARSEO

def es_contrato(valor):
    # Detecta si una celda es un número de contrato
    return bool(re.match(r'^\d{5,8}$', str(valor).strip()))


def parsear_emisora(emisora_raw):
    """
    Formato esperado
    """
    partes = [p.strip() for p in str(emisora_raw).split(' - ')]
    if len(partes) >= 2:
        ticker = partes[0].strip()
        serie  = partes[1].strip()
        return ticker, serie
    return None, None


def es_seccion_header(valor):
    # Detecta encabezados de sección que indican fin de datos de emisoras
    secciones = [
        'Mercado de Dinero (Garantía)',
        'Mercado Accionario',
        'Inversiones Bancarias',
        'Movimientos',
        'Posiciones',
        'Deuda',
        'SIC',
        'Notas Estructuradas',
    ]
    v = str(valor).strip()
    return any(v == s for s in secciones) or es_contrato(v)

# EXTRACCIÓN PRINCIPAL

registros = []

# Estado del parser
contrato_actual = None
nombre_actual   = None
en_posiciones   = False
en_mdo_dinero   = False
en_emisoras     = False
vtc_por_contrato = {} 

for idx, fila in df_raw.iterrows():
    col_a = fila[0]  
    col_b = fila[1]  
    col_e = fila[4]   

    val_a = str(col_a).strip() if pd.notna(col_a) else ""

    # Detectar nuevo contrato 
    if es_contrato(val_a) and pd.notna(col_b):
        contrato_actual = val_a
        nombre_actual   = str(col_b).strip()
        en_posiciones   = False
        en_mdo_dinero   = False
        en_emisoras     = False
        continue
    #VTC
    if val_a == 'Valor Total de la Cartera':
        vtc_por_contrato[contrato_actual] = float(fila[1]) if pd.notna(fila[1]) else 0.0
        continue

    # Detectar sección 'Posiciones'
    if val_a == 'Posiciones':
        en_posiciones = True
        en_mdo_dinero = False
        en_emisoras   = False
        continue

    if not en_posiciones:
        continue

    # Detectar 'Mercado de Dinero' 
    if val_a == 'Mercado de Dinero':
        en_mdo_dinero = True
        en_emisoras   = False
        continue

    # Fin de Mercado de Dinero principal al encontrar otra sub-sección
    if en_mdo_dinero and en_emisoras and es_seccion_header(val_a):
        en_mdo_dinero = False
        en_emisoras   = False
        if val_a == 'Posiciones':
            en_posiciones = True
        continue

    if not en_mdo_dinero:
        continue

    # Detectar 'Emisora'
    if val_a == 'Emisora':
        en_emisoras = True
        continue

    if not en_emisoras:
        continue

    # Fila de datos de emisora 
    # Terminamos si la celda A está vacía (fila de subtotales) o es un header
    if not val_a or pd.isna(col_a):
        continue

    # Saltar si empieza una nueva sub-sección dentro de Posiciones
    if es_seccion_header(val_a):
        en_mdo_dinero = False
        en_emisoras   = False
        if val_a == 'Posiciones':
            en_posiciones = True
        continue

    # Parsear emisora
    ticker, serie = parsear_emisora(val_a)
    if not ticker:
        continue

    valuacion = col_e if pd.notna(col_e) else None

    registros.append({
        'contrato'       : contrato_actual,
        'nombre'         : nombre_actual,
        'ticker'         : ticker,
        'serie'          : serie,
        'valuacion'      : valuacion, 
    })

df_resultado = pd.DataFrame(registros)
df_vtc = pd.DataFrame([
    {'contrato': k, 'valor_total_cartera': v}
    for k, v in vtc_por_contrato.items()
])

df_resultado = df_resultado.merge(df_vtc, on='contrato', how='left')


# Vista rápida: pares (ticker, serie) únicos
pares_unicos = (
    df_resultado[['ticker', 'serie']]
    .drop_duplicates()
    .sort_values(['ticker', 'serie'])
    .reset_index(drop=True)
)

# ─────────────────────────────────────────────────────────────────────────────
# DATAFRAME FINAL
# ─────────────────────────────────────────────────────────────────────────────

df_final = df_resultado[[
    'contrato',
    'nombre',
    'ticker',
    'serie',
    'valuacion',
    "valor_total_cartera"
]].copy()


df_final.columns = [
    '# Contrato',
    'Nombre',
    'Ticker',
    'Serie',
    'Valuación',
    'Valor Total de la Cartera'
]


df_final["Emisora"] = df_final["Ticker"] + " " + df_final["Serie"]


df_final = df_final[[
   '# Contrato', 'Nombre',"Ticker",'Serie' , 'Valuación','Emisora',"Valor Total de la Cartera"]]



df_final["% Cartera"]= df_final["Valuación"] / df_final["Valor Total de la Cartera"] * 100


df_sheet = get_sheet()


tiie_28   = tasas['tiie_28']      
tiie_fondeo = tasas['tiie_fondeo']


def calcular_tasa_total(row):
    if row['Tipo tasa'] == 'TIIE28':
        return row['Tasa'] + tiie_28
    elif row['Tipo tasa'] == 'TIIE FONDEO':
        return row['Tasa'] + tiie_fondeo
    else:
        return row['Tasa']  

df_sheet['tasa_total'] = df_sheet.apply(calcular_tasa_total, axis=1)

df_final = df_final.merge(
    df_sheet[['Emisora', 'Fecha de emisión','Fecha de vencimiento', 'tasa_total']],
    on="Emisora",
    how='left'  
)

emisoras_en_catalogo = set(df_sheet["Emisora"].dropna().unique())

emisoras_sin_catalogo = (
    df_final[~df_final["Emisora"].isin(emisoras_en_catalogo)]["Emisora"]
    .drop_duplicates()
    .sort_values()
    .reset_index(drop=True)
)

if not emisoras_sin_catalogo.empty:
    with st.sidebar:
        st.divider()
        st.warning(f"⚠️ {len(emisoras_sin_catalogo)} emisora(s) sin catálogo")
        st.dataframe(
            emisoras_sin_catalogo.rename("Emisora faltante"),
            hide_index=True,
            use_container_width=True,
        )
        st.caption("Agrégalas al Google Sheet para ver su tasa.")

hoy = pd.Timestamp.today().normalize()

df_final["Fecha de vencimiento"] = pd.to_datetime(df_final["Fecha de vencimiento"], dayfirst=True, errors='coerce')
df_final["Fecha de emisión"]     = pd.to_datetime(df_final["Fecha de emisión"],     dayfirst=True, errors='coerce')
df_final["Dias a vencimiento"]   = (df_final["Fecha de vencimiento"] - hoy).dt.days
df_final["Fecha de vencimiento"] = df_final["Fecha de vencimiento"].dt.date
df_final["Fecha de emisión"]     = df_final["Fecha de emisión"].dt.date

#Alarms de dias a vencer 
proximos = df_final[
    (df_final["Dias a vencimiento"] >= 0) &
    (df_final["Dias a vencimiento"] <= 10)][["# Contrato", "Nombre", "Emisora", "Valuación", "Dias a vencimiento"]].drop_duplicates().sort_values("Dias a vencimiento")

if not proximos.empty:
    st.warning(f"⚠️ {len(proximos)} posición(es) vencen en los próximos 10 días")
    st.dataframe(
        proximos.style.format({
            "Valuación": "${:,.2f}",
            "Dias a vencimiento": "{:.0f} días",
        }),
        use_container_width=True,
        hide_index=True,
    )
# ─────────────────────────────────────────────────────────────────────────────
# EXPORTAR A EXCEL
# ─────────────────────────────────────────────────────────────────────────────

buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as w:
    df_final.to_excel(w, sheet_name="Posiciones", index=False)
    pares_unicos.to_excel(w, sheet_name="Tickers Únicos", index=False)

st.download_button(
    "⬇️ Descargar Excel completo",
    data=buf.getvalue(),
    file_name="resultado_corte_diario.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)


# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN ESTADÍSTICO
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🔍 Consulta por cliente")

clientes = (
    df_final[["# Contrato", "Nombre"]]
    .drop_duplicates()
    .assign(label=lambda d: d["# Contrato"] + " — " + d["Nombre"])
    .sort_values("Nombre")
)

sel = st.selectbox("Selecciona un cliente", clientes["label"].tolist())
contrato_sel = sel.split(" — ")[0]

df_cli = df_final[df_final["# Contrato"] == contrato_sel].copy()
nombre_cli = df_cli["Nombre"].iloc[0]
vtc_cli    = df_cli["Valor Total de la Cartera"].iloc[0]

# ── Info ──────────────────────────────────────────────────────────────────────
st.markdown(f"### {nombre_cli}")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Contrato",            contrato_sel)
c2.metric("Valor Total Cartera", f"${vtc_cli:,.2f}")
c3.metric("Posiciones",          len(df_cli))
c4.metric("Valuacion Total",     f"${df_cli['Valuación'].sum():,.2f}")
c5.metric("Liquidez total",      f"${df_cli["Valot Total de la Cartera"] - df_cli["Valuación"]}")

# ── Tabla ────────────────────────────────────────────────────────────────────
cols = [c for c in ["Emisora","Valuación","% Cartera","tasa_total",
                     "Fecha de vencimiento","Dias a vencimiento"] if c in df_cli.columns]
fmt = {"Valuación":"${:,.2f}", "% Cartera":"{:.2f}%", "tasa_total":"{:.4f}%"}
if "Dias a vencimiento" in cols:
    fmt["Dias a vencimiento"] = "{:.0f}"

styled = df_cli[cols].style.format(fmt)
if "Dias a vencimiento" in cols:
    styled = styled.map(
        lambda v: "color: red" if isinstance(v, (int, float)) and v < 0 else "",
        subset=["Dias a vencimiento"]
    )
st.dataframe(styled, use_container_width=True, hide_index=True)

# ── Gráfica de pastel ─────────────────────────────────────────────────────────
st.subheader("Composición del portafolio")
fig = px.pie(
    df_cli,
    names="Emisora",
    values="Valuación",
    title=f"Portafolio de {nombre_cli}",
    hole=0.35,
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.update_traces(
    textposition="inside",
    textinfo="percent+label",
    hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
)
st.plotly_chart(fig, use_container_width=True)

