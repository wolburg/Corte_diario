import pandas as pd
import re
import requests
import plotly.express as px
import streamlit as st
from datetime import datetime
import io
import streamlit_authenticator as stauth

credentials = {
    "usernames": {
        "admin": {
            "name":     "Administrador",
            "password": "$2b$12$E46pgxE/rBVImEtNGusoGuLWxpOMdCTvOhH9l1D3KTrlwIbA5ry5q",
            "role":     "admin",
            "asesor":   None,
        },
        "ximena": {
            "name":     "XIMENA MUÑOZ MORA",
            "password": "$2b$12$Yuo1ScckF73h7MMWgdVgFeX/G9Pv8DegESIZCFUkuQ/QNtYz8VC0e",
            "role":     "asesor",
            "asesor":   "XIMENA MUÑOZ MORA",
        },
        "andrea": {
            "name":     "ANDREA DÁVILA TREJO",
            "password": "$2b$12$IXpzyHRki.yyc6mhpmE3g.gPMNu6Pzl42g/4tJjUTHWrMlzA/c3Pq",
            "role":     "asesor",
            "asesor":   "ANDREA DÁVILA TREJO",
        },
        "jorge": {
            "name":     "JORGE ANTONIO OROZCO LOPEZ",
            "password": "$2b$12$HH8yosRAWrL2yNamp1ihS.btTpf9lNE8vYBuyxqNRRP2OeATANNz2",
            "role":     "asesor",
            "asesor":   "JORGE ANTONIO OROZCO LOPEZ",
        },
        "marco": {
            "name":     "MARCO ANTONIO OCHOA CARDENAS",
            "password": "$2b$12$lMraAxgSV8nVlPptiv/8weL6qn/hedFu9NTjdq085M0KINQybHpe.",
            "role":     "asesor",
            "asesor":   "MARCO ANTONIO OCHOA CARDENAS",
        },
        "eduardo": {
            "name":     "EDUARDO JAQUEZ BORREGO",
            "password": "$2b$12$PK80dZ38KPHe7XMB8IsIxuNY.g.igWVLfivjI9aiThH.XKiasn4Ji",
            "role":     "asesor",
            "asesor":   "EDUARDO JAQUEZ BORREGO",
        },
    }
}

authenticator = stauth.Authenticate(
    credentials,
    cookie_name        = "corte_diario",
    key         = "clave_secreta_finarq_2026",
    cookie_expiry_days = 1,
)




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

#Cargar catalogo sheets
@st.cache_data(ttl=600000,show_spinner="Leyendo catálogo...")
def get_sheet():
    url = "https://docs.google.com/spreadsheets/d/1Li6A3vVrxj3U6stsJG9lsjre0lkeynJR/export?format=csv&gid=736741268"
    return pd.read_csv(url)

#Cargar sheets asesores
@st.cache_data(ttl=600000,show_spinner="Leyendo sheets de asesores...")
def get_asesores():
    url = "https://docs.google.com/spreadsheets/d/1Li6A3vVrxj3U6stsJG9lsjre0lkeynJR/export?format=csv&gid=618953566"
    df = pd.read_csv(url)
    df.columns = ["Nombre", "Asesor"]
    return df


#Iniciar sesion
st.set_page_config(page_title="Corte Diario Promotor", page_icon="📊", layout="wide")

authenticator.login("Login", location="main")

if not st.session_state.get("authentication_status"):
    st.title("📊 Corte Diario Promotor")
    if st.session_state.get("authentication_status") is False:
        st.error("Usuario o contraseña incorrectos")
    else:
        st.info("Ingresa tus credenciales para continuar.")
    st.stop()

usuario_actual = st.session_state["username"]
rol_actual     = credentials["usernames"][usuario_actual]["role"]
asesor_actual  = credentials["usernames"][usuario_actual]["asesor"]

if rol_actual == "admin":
    st.title("📊 Corte Diario Promotor — Admin")
else:
    st.title(f"📊 Mi Cartera — {st.session_state['name']}")

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuración")
    st.write(f"👤 {st.session_state['name']}")
    authenticator.logout("Cerrar sesión", location="sidebar")
    st.divider()
    archivo = st.file_uploader("Sube el Excel del corte", type=["xlsx"])
    st.divider()
    tasas = get_tasas_banxico()
    if tasas:
        st.metric("TIIE 28 días", f"{tasas['tiie_28']:.4f}%",  tasas['tiie_28_fecha'])
        st.metric("TIIE Fondeo",  f"{tasas['tiie_fondeo']:.4f}%", tasas['tiie_fondeo_fecha'])
    st.divider()

    # Botones solo para admin
    if rol_actual == "admin":
        if st.button("🔄 Actualizar catálogo"):
            get_sheet.clear()
            st.rerun()
        if st.button("🔄 Actualizar tasas"):
            get_tasas_banxico.clear()
            st.rerun()
        if st.button("🔄 Actualizar Asesores"):
            get_asesores.clear()
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
nombres_por_contrato = {}
saldo_efectivo_por_contrato = {} 

#Rregistrar accion
registros_acciones = []
en_acciones = False

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
        en_acciones     = False  # ← resetear
        if contrato_actual not in vtc_por_contrato:
            vtc_por_contrato[contrato_actual] = 0.0
        nombres_por_contrato[contrato_actual] = nombre_actual
        continue

    if val_a == 'Valor Total de la Cartera':
        vtc_por_contrato[contrato_actual] = float(fila[1]) if pd.notna(fila[1]) else 0.0
        continue
    if val_a == 'Saldo de Efectivo Hoy':
        saldo_efectivo_por_contrato[contrato_actual] = float(fila[1]) if pd.notna(fila[1]) else 0.0
        continue

    if val_a == 'Posiciones':
        en_posiciones = True
        en_mdo_dinero = False
        en_emisoras   = False
        en_acciones   = False  # ← resetear
        continue

    if not en_posiciones:
        continue

    # ── Mercado de Dinero ─────────────────────────────────────────────────────
    if val_a == 'Mercado de Dinero':
        en_mdo_dinero = True
        en_emisoras   = False
        en_acciones   = False
        continue

    if en_mdo_dinero and en_emisoras and es_seccion_header(val_a):
        en_mdo_dinero = False
        en_emisoras   = False
        if val_a == 'Posiciones':
            en_posiciones = True
        continue

    # ── Mercado Accionario ────────────────────────────────────────────────────
    if val_a == 'Posición de Mercado Accionario' or val_a == 'Mercado Accionario':
        en_acciones   = True
        en_mdo_dinero = False
        en_emisoras   = False
        continue

    # Capturar acciones
    if en_acciones:
        if val_a == 'Emisora':
            continue
        if not val_a or pd.isna(col_a):
            continue
        if es_seccion_header(val_a):
            en_acciones = False
            continue
        ticker_acc, serie_acc = parsear_emisora(val_a)
        if ticker_acc:
            registros_acciones.append({
                'contrato': contrato_actual,
                'nombre':   nombre_actual,
                'ticker':   ticker_acc,
                'serie':    serie_acc,
                'valuacion': col_e if pd.notna(col_e) else None,
            })
        continue

    # ── MdoD emisoras ─────────────────────────────────────────────────────────
    if not en_mdo_dinero:
        continue

    if val_a == 'Emisora':
        en_emisoras = True
        continue

    if not en_emisoras:
        continue

    if not val_a or pd.isna(col_a):
        continue

    if es_seccion_header(val_a):
        en_mdo_dinero = False
        en_emisoras   = False
        if val_a == 'Posiciones':
            en_posiciones = True
        continue

    ticker, serie = parsear_emisora(val_a)
    if not ticker:
        continue

    valuacion = col_e if pd.notna(col_e) else None
    registros.append({
        'contrato': contrato_actual,
        'nombre':   nombre_actual,
        'ticker':   ticker,
        'serie':    serie,
        'valuacion': valuacion, 
    })


df_resultado = pd.DataFrame(registros)
df_vtc = pd.DataFrame([
    {
        'contrato':            k,
        'nombre':              nombres_por_contrato.get(k, ''),
        'valor_total_cartera': v,
        'saldo_efectivo':      saldo_efectivo_por_contrato.get(k, 0.0),
    }
    for k, v in vtc_por_contrato.items()
])

df_todos_clientes = df_vtc.copy()
df_resultado = df_resultado.merge(
    df_vtc[['contrato', 'valor_total_cartera', "saldo_efectivo"]],
    on='contrato', how='left')

# Vista rápida: pares (ticker, serie) únicos
pares_unicos = (
    df_resultado[['ticker', 'serie']]
    .drop_duplicates()
    .sort_values(['ticker', 'serie'])
    .reset_index(drop=True)
)

#df de acciones
df_acciones = pd.DataFrame(registros_acciones)

if not df_acciones.empty:
    df_acciones = df_acciones.merge(
        df_vtc[['contrato', 'valor_total_cartera']],
        on='contrato', how='left'
    )
    df_acciones.columns = ['contrato', 'Nombre', 'Ticker', 'Serie', 
                           'Valuación', 'Valor Total de la Cartera']
    df_acciones["Emisora"] = df_acciones["Ticker"] + " " + df_acciones["Serie"]

# ─────────────────────────────────────────────────────────────────────────────
# DATAFRAME FINAL
# ─────────────────────────────────────────────────────────────────────────────

df_final = df_resultado[[
    'contrato',
    'nombre',
    'ticker',
    'serie',
    'valuacion',
    "valor_total_cartera",
    'saldo_efectivo'
]].copy()


df_final.columns = [
    '# Contrato',
    'Nombre',
    'Ticker',
    'Serie',
    'Valuación',
    'Valor Total de la Cartera',
    'Saldo Efectivo'
]


df_final["Emisora"] = df_final["Ticker"] + " " + df_final["Serie"]


df_final = df_final[[
   '# Contrato', 'Nombre',"Ticker",'Serie' , 'Valuación','Emisora',"Valor Total de la Cartera", "Saldo Efectivo"]]


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

df_asesores = get_asesores()

df_final = df_final.merge(
    df_asesores,
    left_on="Nombre",
    right_on="Nombre",
    how="left"
)

if rol_actual == "admin":
    df_vista = df_final.copy()
else:
    df_vista = df_final[df_final["Asesor"] == asesor_actual].copy()
    st.info(f"👤 Cartera de {st.session_state['name']} — {df_vista['# Contrato'].nunique()} clientes")

#Warning de asesores
sin_asesor = df_final[df_final["Asesor"].isna()]["Nombre"].drop_duplicates()
if not sin_asesor.empty:
    st.warning(f"⚠️ {len(sin_asesor)} cliente(s) sin asesor asignado:")
    for nombre in sin_asesor:
        st.caption(f"• {nombre}")



#Alarms de dias a vencer 
proximos = df_vista[
    (df_vista["Dias a vencimiento"] >= 0) &
    (df_vista["Dias a vencimiento"] <= 30)][["# Contrato", "Nombre", "Emisora", "Valuación", "Saldo Efectivo", "Valor Total de la Cartera", "Dias a vencimiento"]].drop_duplicates().sort_values("Dias a vencimiento").copy()

proximos["% Liquidez"] = (proximos["Saldo Efectivo"] / proximos["Valor Total de la Cartera"] * 100).round(2)


if not proximos.empty:
    st.warning(f"⚠️ {len(proximos)} posición(es) vencen en los próximos 30 días")
    st.dataframe(
        proximos.style.format({
            "Valuación": "${:,.2f}",
            "Saldo Efectivo": "${:,.2f}",
            "Valor Total de la Cartera": "${:,.2f}",
            "% Liquidez": "{:.2f}%",
            "Dias a vencimiento": "{:.0f} días",
        }),
        use_container_width=True,
        hide_index=True,
    )

#Grafica de pastel emisora 
st.subheader("📅 Emisoras próximas a vencer")
proximos_cliente = df_vista[
    df_vista["Dias a vencimiento"].notna() &
    (df_vista["Dias a vencimiento"] >= 0) &
    (df_vista["Dias a vencimiento"] <= 30)].groupby("Emisora")["Valuación"].sum().reset_index()

if proximos_cliente.empty:
    st.info("No hay emisoras próximas a vencer en los próximos 30 días.")
else:
    fig2 = px.pie(
        proximos_cliente,
        names="Emisora",
        values="Valuación",
        title="Emisoras que vencen en 30 días",
        hole=0.35,
        color_discrete_sequence=px.colors.qualitative.Set1,
    )
    fig2.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
    )
    st.plotly_chart(fig2, use_container_width=True)

## Alerta de liquidez 
st.subheader("🚨 Alerta de Liquidez para Comisión")

# Clientes con posiciones
clientes_con_posiciones = (
    df_vista.groupby(["# Contrato", "Nombre"])
    .agg(
        valuacion_total=("Valuación", "sum"),
        valor_total_cartera=("Valor Total de la Cartera", "first"),
        saldo_efectivo=("Saldo Efectivo", "first"),
    )
    .reset_index()
)

contratos_con_pos = set(clientes_con_posiciones["# Contrato"].unique())

# Clientes sin posiciones (en el corte pero sin emisoras)
if rol_actual == "admin":
    clientes_base = df_todos_clientes
else:
    nombres_asesor = set(df_asesores[df_asesores["Asesor"] == asesor_actual]["Nombre"])
    clientes_base  = df_todos_clientes[df_todos_clientes["nombre"].isin(nombres_asesor)]

clientes_sin_posiciones = pd.DataFrame([
    {
        "# Contrato":          row["contrato"],
        "Nombre":              row["nombre"],
        "valuacion_total":     0.0,
        "valor_total_cartera": row["valor_total_cartera"],
        "saldo_efectivo":      row["saldo_efectivo"],
    }
    for _, row in clientes_base.iterrows()
    if row["contrato"] not in contratos_con_pos
])

# Unir ambos grupos
resumen_clientes = pd.concat(
    [clientes_con_posiciones, clientes_sin_posiciones],
    ignore_index=True
)

# Calcular comisión y liquidez usando Saldo Efectivo
resumen_clientes["Comisión mensual"] = resumen_clientes["valor_total_cartera"] * 0.01 / 12
resumen_clientes["Liquidez"]         = resumen_clientes["saldo_efectivo"]
resumen_clientes["Cubre comisión"]   = (
    (resumen_clientes["valor_total_cartera"] > 0) &
    (resumen_clientes["Liquidez"] >= resumen_clientes["Comisión mensual"])
)

# Separar los que no cubren
sin_liquidez = resumen_clientes[~resumen_clientes["Cubre comisión"]].sort_values("Liquidez")

# Métricas de la alerta
a1, a2, a3 = st.columns(3)
a1.metric("Total clientes",          len(resumen_clientes))
a2.metric("Cubren comisión",         resumen_clientes["Cubre comisión"].sum())
a3.metric("Sin liquidez suficiente", len(sin_liquidez))

if sin_liquidez.empty:
    st.success("✅ Todos los clientes tienen liquidez suficiente para cubrir la comisión.")
else:
    st.error(f"❌ {len(sin_liquidez)} cliente(s) sin liquidez suficiente para cubrir la comisión mensual")
    st.dataframe(
        sin_liquidez[[
            "# Contrato", "Nombre",
            "valuacion_total", "valor_total_cartera",
            "Comisión mensual", "Liquidez"
        ]].rename(columns={
            "valuacion_total":     "Valuación MdoD",
            "valor_total_cartera": "Valor Total Cartera",
        }).style.format({
            "Valuación MdoD":      "${:,.2f}",
            "Valor Total Cartera": "${:,.2f}",
            "Comisión mensual":    "${:,.2f}",
            "Liquidez":            "${:,.2f}",
        }).map(
            lambda v: "color: red" if isinstance(v, (int, float)) and v < 0 else "",
            subset=["Liquidez"]
        ),
        use_container_width=True,
        hide_index=True,
    )

st.divider()
# ─────────────────────────────────────────────────────────────────────────────
# EXPORTAR A EXCEL
# ─────────────────────────────────────────────────────────────────────────────

buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as w:
    df_vista.to_excel(w, sheet_name="Posiciones", index=False)
    pares_unicos_vista = (
        df_vista[['Ticker', 'Serie']]
        .drop_duplicates()
        .sort_values(['Ticker', 'Serie'])
        .reset_index(drop=True)
    )
    pares_unicos_vista.to_excel(w, sheet_name="Tickers Únicos", index=False)

st.download_button(
    "⬇️ Descargar Excel completo",
    data=buf.getvalue(),
    file_name="resultado_corte_diario.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

#Descargar Base completa
buf_clientes =  io.BytesIO()

df_descarga = resumen_clientes[[
    "# Contrato", "Nombre",
    "valuacion_total", "valor_total_cartera",
    "Comisión mensual", "Liquidez", "Cubre comisión"
]].rename(columns={
    "valuacion_total":     "Valuación MdoD",
    "valor_total_cartera": "Valor Total Cartera",
}).sort_values("Valor Total Cartera", ascending=False)

with pd.ExcelWriter(buf_clientes, engine="openpyxl") as w:
    df_descarga.to_excel(w, sheet_name="Clientes", index=False)

st.download_button(
    "⬇️ Descargar base completa de clientes",
    data=buf_clientes.getvalue(),
    file_name="base_clientes_comision.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)



# ─────────────────────────────────────────────────────────────────────────────
# RESUMEN ESTADÍSTICO
# ─────────────────────────────────────────────────────────────────────────────
st.subheader("🔍 Consulta por cliente")

clientes = (
    df_vista[["# Contrato", "Nombre"]]
    .drop_duplicates()
    .assign(label=lambda d: d["# Contrato"] + " — " + d["Nombre"])
    .sort_values("Nombre")
)

sel = st.selectbox("Selecciona un cliente", clientes["label"].tolist())
contrato_sel = sel.split(" — ")[0]

df_cli = df_vista[df_vista["# Contrato"] == contrato_sel].copy()
nombre_cli   = df_cli["Nombre"].iloc[0]
vtc_cli      = df_cli["Valor Total de la Cartera"].iloc[0]
liquidez     = df_cli["Saldo Efectivo"].iloc[0]
pct_liquidez = (liquidez / vtc_cli * 100) if vtc_cli > 0 else 0


# Promedio ponderado de vencimiento
df_con_fecha = df_cli[df_cli["Dias a vencimiento"].notna() & (df_cli["Dias a vencimiento"] >= 0)]

if not df_con_fecha.empty:
    prom_ponderado = (
        (df_con_fecha["Dias a vencimiento"] * df_con_fecha["Valuación"]).sum()
        / df_con_fecha["Valuación"].sum()
    )
else:
    prom_ponderado = 0

#Tasa promedio ponderada 
df_con_tasa = df_cli[df_cli["tasa_total"].notna()]

if not df_con_tasa.empty:
    prom_tasa = (
        (df_con_tasa["tasa_total"] * df_con_tasa["Valuación"]).sum()
        / df_con_tasa["Valuación"].sum()
    )
else:
    prom_tasa = 0

st.markdown(f"### {nombre_cli}")

#  Posición de Mercado Accionario 
if not df_acciones.empty:
    df_acc_cli = df_acciones[df_acciones["contrato"] == contrato_sel].copy()
    if not df_acc_cli.empty:
        st.subheader("Posición de Mercado Accionario")
        df_acc_cli["% Cartera"] = df_acc_cli["Valuación"] / vtc_cli * 100
        st.dataframe(
            df_acc_cli[["Emisora", "Valuación", "% Cartera"]].style.format({
                "Valuación":  "${:,.2f}",
                "% Cartera":  "{:.2f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )


# ── Info ──────────────────────────────────────────────────────────────────────
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    </style>
""", unsafe_allow_html=True)

c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
c1.metric("Contrato",            contrato_sel)
c2.metric("Valor Total Cartera", f"${vtc_cli:,.2f}")
c3.metric("Posiciones",          len(df_cli))
c4.metric("Valuacion Total",     f"${df_cli['Valuación'].sum():,.2f}")
c5.metric("Liquidez total",      f"${liquidez:,.2f}")
c6.metric("% Liquidez",          f"{pct_liquidez:.2f}%")
c7.metric("Días prom. venc.",    f"{prom_ponderado:.0f} días")
c8.metric("Tasa prom. pond.",    f"{prom_tasa:.4f}%")


# ── Filtros ───────────────────────────────────────────────────────────────────
with st.expander("🔎 Filtros", expanded=False):
    f1, f2, f3 = st.columns(3)

    emisoras_disponibles = ["Todas"] + sorted(df_cli["Emisora"].unique().tolist())
    filtro_emisora = f1.selectbox("Emisora", emisoras_disponibles)

    fechas_validas = df_cli["Fecha de vencimiento"].dropna()
    if not fechas_validas.empty:
        fecha_min = fechas_validas.min()
        fecha_max = fechas_validas.max()
        filtro_fechas = f2.date_input(
            "Rango de vencimiento",
            value=(fecha_min, fecha_max),
            min_value=fecha_min,
            max_value=fecha_max,
        )
    else:
        filtro_fechas = None

    filtro_dias = f3.selectbox(
        "Días a vencimiento",
        ["Todos", "Vencidos", "0-30 días", "31-90 días", "91-180 días", "más de 180 días"]
    )

# ── Aplicar filtros ───────────────────────────────────────────────────────────
df_filtrado = df_cli.copy()

if filtro_emisora != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Emisora"] == filtro_emisora]

if filtro_fechas and len(filtro_fechas) == 2:
    fecha_ini, fecha_fin = filtro_fechas
    df_filtrado = df_filtrado[
        df_filtrado["Fecha de vencimiento"].notna() &
        (df_filtrado["Fecha de vencimiento"] >= fecha_ini) &
        (df_filtrado["Fecha de vencimiento"] <= fecha_fin)
    ]
    
if filtro_dias != "Todos":
    if filtro_dias == "Vencidos":
        df_filtrado = df_filtrado[df_filtrado["Dias a vencimiento"] < 0]
    elif filtro_dias == "0-30 días":
        df_filtrado = df_filtrado[
            df_filtrado["Dias a vencimiento"].notna() &
            (df_filtrado["Dias a vencimiento"] >= 0) &
            (df_filtrado["Dias a vencimiento"] <= 30)
        ]
    elif filtro_dias == "31-90 días":
        df_filtrado = df_filtrado[
            df_filtrado["Dias a vencimiento"].notna() &
            (df_filtrado["Dias a vencimiento"] > 30) &
            (df_filtrado["Dias a vencimiento"] <= 90)
        ]
    elif filtro_dias == "91-180 días":
        df_filtrado = df_filtrado[
            df_filtrado["Dias a vencimiento"].notna() &
            (df_filtrado["Dias a vencimiento"] > 90) &
            (df_filtrado["Dias a vencimiento"] <= 180)
        ]
    elif filtro_dias == "más de 180 días":
        df_filtrado = df_filtrado[df_filtrado["Dias a vencimiento"] > 180]


total_mdo = df_filtrado["Valuación"].sum()
df_filtrado = df_filtrado.copy()
df_filtrado.loc[:, "% Cartera"] = df_filtrado["Valuación"] / total_mdo * 100


# ── cols y formato ────────────────────────────────────────────────────────────
cols = [c for c in ["Emisora","Valuación","% Cartera","tasa_total",
                     "Fecha de vencimiento","Dias a vencimiento"] if c in df_filtrado.columns]
fmt = {"Valuación":"${:,.2f}", "% Cartera":"{:.2f}%", "tasa_total":"{:.4f}%"}
if "Dias a vencimiento" in cols:
    fmt["Dias a vencimiento"] = "{:.0f}"

df_tabla = df_filtrado[cols].copy()

# ── Tabla ─────────────────────────────────────────────────────────────────────
styled = df_tabla.style.format(fmt, na_rep="—")
if "Dias a vencimiento" in cols:
    styled = styled.map(
        lambda v: "color: red" if isinstance(v, (int, float)) and v < 0 else "",
        subset=["Dias a vencimiento"]
    )
st.dataframe(styled, use_container_width=True, hide_index=True)

# ── Gráfica de pastel ─────────────────────────────────────────────────────────
st.subheader("Composición del portafolio")

df_pie = df_filtrado[["Emisora", "Valuación"]].copy()
fig = px.pie(
    df_pie,
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

## Vista general Finarq 
if rol_actual == "admin":
    st.subheader("🏢 Vista General Finarq")
    resumen_emisoras = (
        df_vista.groupby("Emisora")["Valuación"]
        .sum()
        .reset_index()
        .sort_values("Valuación", ascending=False)
    )
    total_general = df_vista["Valuación"].sum()
    resumen_emisoras["% del Total"] = resumen_emisoras["Valuación"] / total_general * 100

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total General",      f"${total_general:,.2f}")
    m2.metric("Clientes",           df_vista["# Contrato"].nunique())
    m3.metric("Emisoras únicas",    resumen_emisoras["Emisora"].nunique())
    m4.metric("Posiciones totales", len(df_vista))

    st.dataframe(
        resumen_emisoras.style.format({
            "Valuación":   "${:,.2f}",
            "% del Total": "{:.2f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )

    fig_global = px.pie(
        resumen_emisoras,
        names="Emisora",
        values="Valuación",
        title=f"Distribución total por emisora — ${total_general:,.2f}",
        hole=0.35,
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig_global.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>",
    )
    st.plotly_chart(fig_global, use_container_width=True)
    st.divider()

