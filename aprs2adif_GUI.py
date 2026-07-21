import tkinter as tk
from tkinter import filedialog, messagebox
import re
import os
from datetime import datetime, timedelta

def convertir_aprs_a_adif(archivo_entrada, archivo_salida, mi_indicativo, solo_mensajes, offset_utc, banda_seleccionada):
    patron_log = re.compile(r'(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}).*?(?:[RT]\s*:\s*)?([A-Z0-9]+(?:-\d{1,2})?)>')
    qsos_procesados = {}
    
    lineas_procesadas = 0
    primer_tiempo = None
    ultimo_tiempo = None

    # Asignar banda y frecuencia según la selección
    if banda_seleccionada == "VHF":
        banda = "2m"
        frecuencia = "144.390"
    else:
        banda = "70cm"
        frecuencia = "430.930"

    if not archivo_entrada or not os.path.exists(archivo_entrada):
        return False, "Error: Selecciona un archivo de entrada válido."
    if not archivo_salida:
        return False, "Error: Especifica un archivo de salida válido."
    if not mi_indicativo:
        return False, "Error: Debes ingresar tu indicativo."

    try:
        with open(archivo_entrada, 'r', encoding='utf-8', errors='ignore') as f:
            for linea in f:
                match = patron_log.search(linea)
                if match:
                    fecha_str, hora_str, indicativo_crudo = match.groups()
                    
                    tiempo_local = datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M:%S")
                    tiempo_utc = tiempo_local + timedelta(hours=offset_utc)
                    
                    if primer_tiempo is None:
                        primer_tiempo = tiempo_utc
                    ultimo_tiempo = tiempo_utc
                    lineas_procesadas += 1

                    if solo_mensajes and "::" not in linea:
                        continue
                    
                    if indicativo_crudo.startswith(mi_indicativo.upper()):
                        continue
                    
                    # --- NUEVO: Remover el SSID ---
                    # Ej: "LU1ABC-9" se convierte en "LU1ABC"
                    indicativo_base = indicativo_crudo.split('-')[0]
                    
                    adif_fecha = tiempo_utc.strftime("%Y%m%d")
                    adif_hora = tiempo_utc.strftime("%H%M")

                    clave_qso = (indicativo_base, adif_fecha)
                    if clave_qso not in qsos_procesados:
                        qsos_procesados[clave_qso] = adif_hora

        if lineas_procesadas == 0:
            return False, "No se encontraron registros de APRS válidos en el archivo."

        if not qsos_procesados:
            return True, f"Se procesaron {lineas_procesadas} registros, pero ninguno cumplió los criterios para ser exportado."

        with open(archivo_salida, 'w', encoding='utf-8') as out:
            out.write("Generado por convertidor APRS2ADIF by LU9DUV local\n")
            out.write("<EOH>\n\n")

            contactos = 0
            for (call, fecha), hora in qsos_procesados.items():
                # --- NUEVO: Se agregan campos BAND y FREQ dinámicos ---
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
            f"Banda: {banda} ({frecuencia} MHz)\n"
            f"Archivo guardado en:\n{archivo_salida}"
        )

        return True, mensaje_final
        
    except Exception as e:
        return False, f"Ocurrió un error inesperado:\n{str(e)}"

# --- Lógica de la Interfaz Gráfica ---

class ConversorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("APRSdroid a ADIF Converter")
        self.root.geometry("500x380") # Ventana ligeramente más alta
        self.root.resizable(False, False)

        self.var_entrada = tk.StringVar()
        self.var_salida = tk.StringVar()
        self.var_indicativo = tk.StringVar(value="LU")
        self.var_offset = tk.IntVar(value=3)
        self.var_solo_msj = tk.BooleanVar(value=False)
        self.var_banda = tk.StringVar(value="VHF") # Variable para la banda seleccionada

        self.crear_widgets()

    def crear_widgets(self):
        padding = {'padx': 10, 'pady': 5}

        tk.Label(self.root, text="Archivo Log (Entrada):").grid(row=0, column=0, sticky='w', **padding)
        tk.Entry(self.root, textvariable=self.var_entrada, width=40).grid(row=0, column=1, **padding)
        tk.Button(self.root, text="Buscar", command=self.buscar_entrada).grid(row=0, column=2, **padding)

        tk.Label(self.root, text="Archivo ADIF (Salida):").grid(row=1, column=0, sticky='w', **padding)
        tk.Entry(self.root, textvariable=self.var_salida, width=40).grid(row=1, column=1, **padding)
        tk.Button(self.root, text="Guardar", command=self.buscar_salida).grid(row=1, column=2, **padding)

        tk.Label(self.root, text="Mi Indicativo:").grid(row=2, column=0, sticky='w', **padding)
        tk.Entry(self.root, textvariable=self.var_indicativo, width=15).grid(row=2, column=1, sticky='w', **padding)

        tk.Label(self.root, text="Horas a sumar para UTC:").grid(row=3, column=0, sticky='w', **padding)
        tk.Spinbox(self.root, from_=-12, to=14, textvariable=self.var_offset, width=5).grid(row=3, column=1, sticky='w', **padding)

        # --- NUEVO: Selección de Banda/Frecuencia ---
        tk.Label(self.root, text="Banda / Frecuencia:").grid(row=4, column=0, sticky='w', **padding)
        frame_bandas = tk.Frame(self.root)
        frame_bandas.grid(row=4, column=1, sticky='w', **padding)
        tk.Radiobutton(frame_bandas, text="VHF (144.390 MHz)", variable=self.var_banda, value="VHF").pack(side=tk.LEFT)
        tk.Radiobutton(frame_bandas, text="UHF (430.930 MHz)", variable=self.var_banda, value="UHF").pack(side=tk.LEFT)

        tk.Checkbutton(self.root, text="Exportar solo mensajes directos (QSOs reales)", variable=self.var_solo_msj).grid(row=5, column=0, columnspan=2, sticky='w', **padding)

        tk.Button(self.root, text="Convertir a ADIF", command=self.ejecutar_conversion, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), height=2).grid(row=6, column=0, columnspan=3, pady=20)

    def buscar_entrada(self):
        archivo = filedialog.askopenfilename(title="Seleccionar Log de APRSdroid", filetypes=[("Text/Log Files", "*.txt *.log"), ("All Files", "*.*")])
        if archivo:
            self.var_entrada.set(archivo)

    def buscar_salida(self):
        archivo = filedialog.asksaveasfilename(title="Guardar archivo ADIF", defaultextension=".adi", filetypes=[("ADIF Files", "*.adi"), ("All Files", "*.*")])
        if archivo:
            self.var_salida.set(archivo)

    def ejecutar_conversion(self):
        entrada = self.var_entrada.get()
        salida = self.var_salida.get()
        indicativo = self.var_indicativo.get().strip()
        solo_msj = self.var_solo_msj.get()
        banda_sel = self.var_banda.get()
        
        try:
            offset = self.var_offset.get()
        except tk.TclError:
            messagebox.showerror("Error", "El valor de ajuste UTC debe ser un número entero.")
            return

        exito, mensaje = convertir_aprs_a_adif(entrada, salida, indicativo, solo_msj, offset, banda_sel)

        if exito:
            messagebox.showinfo("Resumen de Conversión", mensaje)
        else:
            messagebox.showerror("Error", mensaje)

if __name__ == "__main__":
    root = tk.Tk()
    app = ConversorApp(root)
    root.mainloop()