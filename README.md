# APRSDroid-to-ADIF
This project aims to filter real qso's from the APRSDroid logs and convert them into ADIF to be loaded in QRZ/LOTW/LDA/etc.

The code is in Phyton and the UI is pretty rough. 
Only spanish as of now. More on that later

Pre-Requisitos : Phyton instalado en la computadora

Lógica de Conversión
Un archivo de registro (log) de APRSdroid generalmente contiene líneas de texto con marcas de tiempo (timestamp) seguidas del paquete TNC2 en bruto. Por ejemplo:
2026-07-20 14:30:25 R: LU1ABC-9>APDR15,TCPIP*,qAC,T2ARG:=...

Para convertir el log de APRSDROID a un registro válido en formato ADIF, el programa hace lo siguiente:

Extracción (Parsing): Leer el archivo línea por línea y usar Expresiones Regulares (Regex) para capturar tres datos clave: la fecha, la hora y la señal distintiva (Callsign) de la estación emisora.

Filtrado de Mensajes (Opcional pero recomendado): En APRS, la mayoría de los paquetes son balizas de posición. En radioafición, escuchar una baliza no suele considerarse un "QSO bidireccional" válido para QRZ. Los verdaderos QSOs en APRS se dan mediante el intercambio de mensajes de texto. El código incluye un filtro opcional para registrar solo estaciones que enviaron un mensaje (:: en el payload).

Deduplicación: APRS transmite el mismo paquete múltiples veces por redundancia. Si no filtras, generarás cientos de contactos duplicados con la misma estación. El programa usará un diccionario para guardar un solo contacto por estación, por día.

Formateo ADIF: El estándar ADIF requiere etiquetas que especifican el nombre del campo y la longitud del dato. Por ejemplo, para el indicativo "LU1ABC" (6 caracteres), el formato exacto es <CALL:6>LU1ABC.

Hora Local vs UTC: El programa permite especificar una diferencia entre la hora de los registros y la hora UTC para el caso en que los registros estén en hora local y se deseen levantar a algún log online en hora utc.

Remoción de SSID: El programa remueve la SSID para dejar la licencia limpia. Ej. LU9DUV-5 se reduce a LU9DUV. 

Cómo usarlo
Asegúrate de tener guardado el código en un archivo con extensión .py. Por ejemplo aprs2adif_gui.py

Desde la terminal o ventana de comandos, ejecútalo escribiendo: python aprs2adif_gui.py (o dependiendo de tu instalación, puedes hacerle doble clic al archivo).

Aparecerá una ventana. Usa los botones Buscar y Guardar para elegir de dónde leer y dónde escribir.

El offset por defecto en 3 asumiendo que la hora local es UTC-3 (como en Argentina). Si el log dice 20:00, el ADIF registrará 23:00 de forma automática.

Selecciona la frecuencia en que van a registrarse los contactos (por ahora 144.390 y 430.930)

Haz clic en Convertir a ADIF y verás un mensaje emergente confirmando cuántos contactos se guardaron.

Al finalizar la ejecución, aparece una ventana emergente con el resumen de registros leídos y QSO convertidos

