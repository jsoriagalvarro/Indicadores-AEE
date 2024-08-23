import streamlit as st
import pyodbc
import pandas as pd
import plotly.graph_objs as go
from io import BytesIO

# Obtener credenciales desde Streamlit secrets
db_config = st.secrets["database"]

# Función para conectarse a la base de datos
def get_db_connection():
    conn = pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={db_config["server"]};'
        f'DATABASE={db_config["database"]};'
        f'UID={db_config["username"]};'
        f'PWD={db_config["password"]};'
        'TrustServerCertificate=yes;'
        'Encrypt=yes;'
    )
    return conn

# Función para obtener los datos de la base de datos
def get_data(country_id, indicator_ids):
    if not indicator_ids:
        return pd.DataFrame()  # Devolver un DataFrame vacío si no hay indicadores seleccionados

    conn = get_db_connection()
    query = f"""
    SELECT Date, Value, IndicatorID 
    FROM EconomicData 
    WHERE CountryID = {country_id} 
    AND IndicatorID IN ({','.join(map(str, indicator_ids))})
    ORDER BY Date
    """
    data = pd.read_sql(query, conn)
    conn.close()
    return data

# Función para obtener indicadores disponibles según el país seleccionado
def get_available_indicators(country_id):
    conn = get_db_connection()
    query = f"""
    SELECT DISTINCT i.IndicatorName, i.IndicatorID
    FROM EconomicData e
    JOIN Indicators i ON e.IndicatorID = i.IndicatorID
    WHERE e.CountryID = {country_id}
    """
    indicators = pd.read_sql(query, conn)
    conn.close()
    return indicators

# Función para descargar datos en formato Excel
def download_excel(data):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        data.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    return output

# Configuración de la página de Streamlit
st.set_page_config(page_title="Interfaz - AEE", layout="wide")

# Sidebar para seleccionar opciones
st.sidebar.title("Configuración")
page = st.sidebar.radio("Seleccione una página:", ["Home", "Mesa de trabajo Económica"])

# Ruta del logo
logo_path = "estrellafon_transparent.png"

# Página Home
if page == "Home":
    col1, col2 = st.columns([1, 8])
    with col1:
        st.image(logo_path, width=80)
    with col2:
        st.markdown("<h1 style='text-align: left;'>Mesa Económica - AEE</h1>", unsafe_allow_html=True)

    st.markdown("""
    ## Bienvenido
    
    Esta aplicación está diseñada para proporcionar acceso interactivo a indicadores económicos 
    clave de diversos países. Puedes explorar datos históricos, personalizar gráficos, y descargar 
    tanto los datos como las visualizaciones para un análisis más detallado.

    ### Funcionalidades Principales:
    - **Selección de Países:** Filtra y visualiza datos económicos por país.
    - **Indicadores Personalizables:** Elige entre múltiples indicadores económicos para generar gráficos personalizados.
    - **Opciones de Visualización:** Explora diferentes tipos de gráficos, incluyendo líneas, barras, y áreas apiladas.
    - **Descargas Fáciles:** Exporta datos y gráficos en formato Excel y PNG para su uso fuera de la aplicación.

    ### Cómo Usar la Aplicación:
    1. Selecciona la opción "Mesa de trabajo Económica" en el menú lateral.
    2. Escoge un país de interés.
    3. Selecciona los indicadores que deseas analizar.
    4. Personaliza el tipo de gráfico y otros parámetros.
    5. Descarga los datos o la visualización si es necesario.

    
    
    """)
    
    st.write("Explora los datos y descubre insights económicos clave de una manera interactiva y fácil de usar.")


# Página Mesa de trabajo Económica
if page == "Mesa de trabajo Económica":
    col1, col2 = st.columns([1, 8])
    with col1:
        st.image(logo_path, width=80)
    with col2:
        st.markdown("<h1 style='text-align: left;'>Mesa de trabajo Económica</h1>", unsafe_allow_html=True)

    # Selección de país
    country_options = {
        "Argentina": 1,
        "Bolivia": 2,
        "Brasil": 3,
        "Uruguay": 4,
        "Paraguay": 5
    }
    country = st.sidebar.selectbox("Seleccione el país:", options=list(country_options.keys()))
    country_id = country_options[country]

    # Obtener los indicadores disponibles para el país seleccionado
    available_indicators = get_available_indicators(country_id)
    indicator_options = {row['IndicatorName']: row['IndicatorID'] for index, row in available_indicators.iterrows()}

    # Selección de indicadores
    selected_indicators = st.sidebar.multiselect("Seleccione los indicadores:", options=list(indicator_options.keys()))
    indicator_ids = [indicator_options[indicator] for indicator in selected_indicators]

    if indicator_ids:
        # Obtener los datos sin filtrar por fechas
        data = get_data(country_id, indicator_ids)

        if not data.empty:
            # Selección de tipo de gráfico por indicador
            chart_type_by_indicator = {}
            chart_type_options = ["Línea", "Área", "Barras agrupadas", "Barras apiladas", "Scatter", "Histograma", "Áreas apiladas"]  # Agregada opción "Áreas apiladas"
            for indicator in selected_indicators:
                chart_type_by_indicator[indicator] = st.sidebar.selectbox(
                    f"Seleccione el tipo de gráfico para {indicator}:",
                    options=chart_type_options,
                    key=f"chart_type_{indicator}"
                )

            # Selección de colores para cada serie
            colors = {}
            for indicator in selected_indicators:
                colors[indicator] = st.sidebar.color_picker(f"Seleccione el color para {indicator}:", "#D80026")

            # Opción para mostrar etiquetas de datos
            show_data_labels = st.sidebar.checkbox("Mostrar etiquetas de datos")

            # Asignación de eje Y (izquierda o derecha) para cada indicador
            y_axis_by_indicator = {}
            for indicator in selected_indicators:
                y_axis_by_indicator[indicator] = st.sidebar.selectbox(
                    f"Seleccione el eje Y para {indicator}:",
                    options=["Izquierda", "Derecha"],
                    key=f"y_axis_{indicator}"
                )

            # Input para el título del gráfico
            chart_title = st.sidebar.text_input("Título del gráfico", value="Gráfico de Indicadores Económicos")

            # Determinar el rango de fechas disponible
            min_date = data["Date"].min()
            max_date = data["Date"].max()

            # Sección para mostrar el gráfico
            fig = go.Figure()
            placeholder = st.empty()

            def update_chart(start_date, end_date):
                filtered_data = data[(data["Date"] >= start_date) & (data["Date"] <= end_date)]

                fig.data = []  # Limpiar datos existentes en el gráfico

                for indicator in selected_indicators:
                    indicator_id = indicator_options[indicator]
                    indicator_data = filtered_data[filtered_data["IndicatorID"] == indicator_id]

                    chart_type = chart_type_by_indicator[indicator]
                    yaxis = "y2" if y_axis_by_indicator[indicator] == "Derecha" else "y"

                    # Obtener el último valor para la etiqueta de datos
                    if not indicator_data.empty:
                        last_value = indicator_data.iloc[-1]["Value"]
                        last_date = indicator_data.iloc[-1]["Date"]
                    else:
                        last_value = None
                        last_date = None

                    if chart_type == "Línea":
                        fig.add_trace(go.Scatter(
                            x=indicator_data["Date"],
                            y=indicator_data["Value"],
                            mode="lines+markers" if show_data_labels else "lines",
                            name=indicator,
                            line=dict(color=colors[indicator], shape="spline"),
                            yaxis=yaxis,
                            text=[f"{last_value:.2f}" if d == last_date else "" for d in indicator_data["Date"]],
                            textposition="top right" if show_data_labels else None
                        ))
                    elif chart_type == "Área":
                        fig.add_trace(go.Scatter(
                            x=indicator_data["Date"],
                            y=indicator_data["Value"],
                            mode="lines+markers" if show_data_labels else "lines",
                            fill="tozeroy",
                            name=indicator,
                            line=dict(color=colors[indicator]),
                            yaxis=yaxis,
                            text=[f"{last_value:.2f}" if d == last_date else "" for d in indicator_data["Date"]],
                            textposition="top right" if show_data_labels else None
                        ))
                    elif chart_type == "Barras agrupadas":
                        fig.add_trace(go.Bar(
                            x=indicator_data["Date"],
                            y=indicator_data["Value"],
                            name=indicator,
                            marker=dict(color=colors[indicator]),
                            text=[f"{last_value:.2f}" if d == last_date else "" for d in indicator_data["Date"]],
                            textposition='auto' if show_data_labels else None,
                            yaxis=yaxis
                        ))
                    elif chart_type == "Barras apiladas":
                        fig.add_trace(go.Bar(
                            x=indicator_data["Date"],
                            y=indicator_data["Value"],
                            name=indicator,
                            marker=dict(color=colors[indicator]),
                            text=[f"{last_value:.2f}" if d == last_date else "" for d in indicator_data["Date"]],
                            textposition='auto' if show_data_labels else None,
                            yaxis=yaxis
                        ))
                        fig.update_layout(barmode='stack')
                    elif chart_type == "Áreas apiladas":
                        fig.add_trace(go.Scatter(
                            x=indicator_data["Date"],
                            y=indicator_data["Value"],
                            mode="lines+markers" if show_data_labels else "lines",
                            fill="tonexty",
                            name=indicator,
                            line=dict(color=colors[indicator]),
                            yaxis=yaxis,
                            text=[f"{last_value:.2f}" if d == last_date else "" for d in indicator_data["Date"]],
                            textposition="top right" if show_data_labels else None
                        ))
                        fig.update_layout(barmode='stack')
                    elif chart_type == "Scatter":
                        fig.add_trace(go.Scatter(
                            x=indicator_data["Date"],
                            y=indicator_data["Value"],
                            mode="markers",
                            name=indicator,
                            marker=dict(color=colors[indicator]),
                            yaxis=yaxis,
                            text=[f"{last_value:.2f}" if d == last_date else "" for d in indicator_data["Date"]],
                            textposition="top right" if show_data_labels else None
                        ))
                    elif chart_type == "Histograma":
                        fig.add_trace(go.Histogram(
                            x=indicator_data["Value"],
                            name=indicator,
                            marker=dict(color=colors[indicator]),
                            yaxis=yaxis
                        ))

                # Configuración de los ejes Y, diseño general y hovermode
                fig.update_layout(
                    yaxis=dict(
                        showgrid=True,
                        zeroline=True,
                        titlefont=dict(family="Segoe UI", size=12)
                    ),
                    yaxis2=dict(
                        overlaying="y",
                        side="right",
                        showgrid=False,
                        zeroline=False,
                        titlefont=dict(family="Segoe UI", size=12)
                    ),
                    title={
                        'text': chart_title,
                        'y': 0.9,
                        'x': 0.5,
                        'xanchor': 'center',
                        'yanchor': 'top',
                        'font': dict(size=24, family="Segoe UI")
                    },
                    xaxis=dict(showgrid=False, titlefont=dict(family="Segoe UI", size=12)),
                    legend=dict(
                        font=dict(family="Segoe UI", size=10),
                        orientation="h",
                        yanchor="top",
                        y=-0.2,  # Coloca la leyenda debajo del gráfico
                        xanchor="center",
                        x=0.5
                    ),
                    hovermode='x unified',  # Hovermode agregado
                    width=1000,
                    height=600,
                    plot_bgcolor='rgba(0,0,0,0)',  # Fondo transparente
                    paper_bgcolor='rgba(0,0,0,0)'  # Fondo transparente
                )

                # Renderizar el gráfico en Streamlit
                placeholder.plotly_chart(fig, use_container_width=True)

            # Agregar slider de fechas debajo del gráfico
            start_date, end_date = st.slider(
                "Seleccione el rango de fechas:",
                min_value=min_date,
                max_value=max_date,
                value=(min_date, max_date),
                format="YYYY-MM-DD"
            )

            # Actualizar el gráfico en tiempo real
            update_chart(start_date, end_date)

            # Opción para descargar los datos como Excel
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Descargar datos en Excel",
                    data=download_excel(data[(data["Date"] >= start_date) & (data["Date"] <= end_date)]),
                    file_name="datos_indicadores.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            with col2:
                # Opción para descargar la imagen del gráfico
                image_buffer = BytesIO()
                fig.write_image(image_buffer, format='png', engine='kaleido')
                st.download_button(
                    label="Descargar gráfico como imagen",
                    data=image_buffer,
                    file_name="grafico_indicadores.png",
                    mime="image/png"
                )

        else:
            st.warning("No hay datos disponibles para los indicadores seleccionados.")
    else:
        st.warning("Por favor seleccione al menos un indicador.")
