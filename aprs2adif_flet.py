import flet as ft
import re
import os
from datetime import datetime, timedelta

def convertir_aprs_a_adif(archivo_entrada, archivo_salida, mi_indicativo, solo_mensajes, offset_utc, banda_seleccionada):
    # Captura el encabezado: Fecha, Hora y Remitente (quien transmite el paquete)
    patron_log = re.compile(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}).*?(?:[RT]\s*:\s*)?([A-Z0-9]+(?:-\d{1,2})?)>')
    # NUEVO: Captura el destinatario dentro del payload de un mensaje de texto APRS
    patron_msg = re.compile(r'::([A-Z0-9\-]{1,9})\s*:')
    
    qsos_procesados = {}
    lineas_procesadas = 0
    primer_tiempo = None
    ultimo_tiempo = None

    if banda_seleccionada == "VHF":
        banda = "2m"
        frecuencia = "144.390"
    else:
        banda = "70cm"
        frecuencia = "430.930"

    # Nos aseguramos de comparar solo los indicativos base (sin SSIDs como -9 o -7)
    mi_ind_base = mi_indicativo.upper().split('-')[0]

    try:
        with open(archivo_entrada, 'r', encoding='utf-8', errors='ignore') as f:
            for linea in f:
                match_log = patron_log.search(linea)
                if match_log:
                    fecha_str, hora_str, indicativo_crudo = match_log.groups()
                    
                    tiempo_local = datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M:%S")
                    tiempo_utc = tiempo_local + timedelta(hours=offset_utc)
                    
                    if primer_tiempo is None:
                        primer_tiempo = tiempo_utc
                    ultimo_tiempo = tiempo_utc
                    lineas_procesadas += 1

                    remitente_base = indicativo_crudo.split('-')[0]
                    contacto_final = None

                    if solo_mensajes:
                        # Buscar si la línea tiene el formato de un mensaje dirigido
                        match_msg = patron_msg.search(linea)
                        if match_msg:
                            destinatario_base = match_msg.group(1).split('-')[0]
                            
                            # Lógica estricta de QSO:
                            if remitente_base == mi_ind_base:
                                # Yo envié el mensaje -> Anoto al destinatario
                                contacto_final = destinatario_base
                            elif destinatario_base == mi_ind_base:
                                # Yo recibí el mensaje -> Anoto al remitente
                                contacto_final = remitente_base
                            else:
                                # Mensaje entre terceros que mi radio simplemente escuchó
                                continue
                        else:
                            # No es un mensaje (es una baliza, telemetría, etc.)
                            continue
                    else:
                        # Si el usuario NO marcó la casilla de "Solo mensajes" (guarda todo lo que escucha)
                        if remitente_base == mi_ind_base:
                            continue # Ignorar mis propias balizas
                        contacto_final = remitente_base
                    
                    # Si superó los filtros y tenemos un contacto válido
                    if contacto_final:
                        adif_fecha = tiempo_utc.strftime("%Y%m%d")
                        adif_hora = tiempo_utc.strftime("%H%M")

                        clave_qso = (contacto_final, adif_fecha)
                        if clave_qso not in qsos_procesados:
                            qsos_procesados[clave_qso] = adif_hora

        if lineas_procesadas == 0:
            return False, "No se encontraron registros de APRS válidos en el archivo."

        if not qsos_procesados:
            return True, f"Se procesaron {lineas_procesadas} registros, pero ninguno es un QSO contigo."

        with open(archivo_salida, 'w', encoding='utf-8') as out:
            out.write("Generado por convertidor APRSdroid (Flet)\n")
            out.write("<EOH>\n\n")

            contactos = 0
            for (call, fecha), hora in qsos_procesados.items():
                linea_adif = (
                    f"<CALL:{len(call)}>{call} "
                    f"<QSO_DATE:8>{fecha} "
                    f"<TIME_ON:4>{hora} "
                    f"<BAND:{len(banda)}>{banda} "
                    f"<FREQ:{len(frecuencia)}>{frecuencia} "
                    f"<MODE:3>PKT " 
                    f"<EOR>\n"
                )
                out.write(linea_adif)
                contactos += 1

        str_inicio = primer_tiempo.strftime("%Y-%m-%d %H:%M:%S UTC")
        str_fin = ultimo_tiempo.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        mensaje_final = (
            f"¡Conversión exitosa!\n\n"
            f"• Registros procesados (Log): {lineas_procesadas}\n"
            f"• Fecha/Hora inicial: {str_inicio}\n"
            f"• Fecha/Hora final: {str_fin}\n"
            f"• Contactos ADIF generados: {contactos}\n\n"
            f"Archivo guardado correctamente."
        )

        return True, mensaje_final
        
    except Exception as e:
        return False, f"Ocurrió un error:\n{str(e)}"

# --- LÓGICA DE LA INTERFAZ GRÁFICA PARA MÓVIL (Flet) ---
def main(page: ft.Page):
    page.title = "APRSdroid a ADIF"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20
    page.scroll = ft.ScrollMode.ADAPTIVE 

    ruta_entrada = ""
    ruta_salida = ""

    dlg = ft.AlertDialog(title=ft.Text(""), content=ft.Text(""))
    page.dialog = dlg

    def mostrar_mensaje(titulo, mensaje):
        dlg.title.value = titulo
        dlg.content.value = mensaje
        dlg.open = True
        page.update()

    def on_file_picked(e: ft.FilePickerResultEvent):
        nonlocal ruta_entrada
        if e.files:
            ruta_entrada = e.files[0].path
            txt_entrada.value = e.files[0].name
            page.update()

    def on_save_picked(e: ft.FilePickerResultEvent):
        nonlocal ruta_salida
        if e.path:
            ruta_salida = e.path
            txt_salida.value = e.path.split("/")[-1]
            page.update()

    picker_entrada = ft.FilePicker(on_result=on_file_picked)
    picker_salida = ft.FilePicker(on_result=on_save_picked)
    page.overlay.extend([picker_entrada, picker_salida])

    txt_entrada = ft.TextField(label="Log seleccionado", read_only=True, expand=True)
    btn_entrada = ft.ElevatedButton("Buscar Log", icon=ft.icons.FOLDER_OPEN, on_click=lambda _: picker_entrada.pick_files(allow_multiple=False))

    txt_salida = ft.TextField(label="ADIF destino", read_only=True, expand=True)
    btn_salida = ft.ElevatedButton("Guardar", icon=ft.icons.SAVE, on_click=lambda _: picker_salida.save_file(file_name="aprs_export.adi"))

    txt_indicativo = ft.TextField(label="Mi Indicativo", value="LU")
    txt_offset = ft.TextField(label="Horas a sumar para UTC", value="3", keyboard_type=ft.KeyboardType.NUMBER)

    radio_banda = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value="VHF", label="VHF (144.390)"),
            ft.Radio(value="UHF", label="UHF (430.930)")
        ]),
        value="VHF"
    )

    chk_mensajes = ft.Checkbox(label="Exportar solo mensajes directos (QSOs reales)", value=True) # Lo puse en True por defecto por conveniencia

    def ejecutar(e):
        if not ruta_entrada or not ruta_salida:
            mostrar_mensaje("Faltan datos", "Por favor selecciona el archivo de entrada y dónde guardar la salida.")
            return
            
        try:
            offset = int(txt_offset.value)
        except ValueError:
            mostrar_mensaje("Error", "El valor UTC debe ser un número entero.")
            return
            
        if not txt_indicativo.value:
            mostrar_mensaje("Error", "Debes ingresar tu indicativo.")
            return

        exito, msj = convertir_aprs_a_adif(
            ruta_entrada, 
            ruta_salida, 
            txt_indicativo.value.strip(), 
            chk_mensajes.value, 
            offset, 
            radio_banda.value
        )

        titulo = "Éxito" if exito else "Error"
        mostrar_mensaje(titulo, msj)

    btn_convertir = ft.ElevatedButton(
        "Convertir a ADIF", 
        icon=ft.icons.SYNC,
        on_click=ejecutar, 
        bgcolor=ft.colors.GREEN_700, 
        color=ft.colors.WHITE,
        height=50
    )

    page.add(
        ft.Text("Conversor APRS", size=28, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_700),
        ft.Divider(),
        ft.Row([txt_entrada, btn_entrada]),
        ft.Row([txt_salida, btn_salida]),
        txt_indicativo,
        txt_offset,
        ft.Text("Banda / Frecuencia:", weight=ft.FontWeight.W_500),
        radio_banda,
        chk_mensajes,
        ft.Container(height=20),
        ft.Row([btn_convertir], alignment=ft.MainAxisAlignment.CENTER)
    )

ft.app(target=main)