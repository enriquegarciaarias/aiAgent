from sources.common.common import processControl, writeLog, logger
import os
import json
import time
import shutil
import re
import unicodedata

class configLoader:
    def __init__(self, config_path='./sources/common/config.json'):
        #realConfigPath = os.path.join(processControl.env['realPath'], config_path)
        realConfigPath = os.path.realpath(config_path)
        self.config = self.load_config(realConfigPath)

    def load_config(self, realConfigPath):
        """Carga el archivo de configuración JSON."""
        with open(realConfigPath, 'r') as config_file:
            return json.load(config_file)

    def get_environment(self):
        """Devuelve el valor de environment."""
        return self.config.get("environment", None)

    def get_uid(self):
        """Devuelve el valor de environment."""
        return self.config.get("uid", 'test')

    def getStorageProcesses(self):
        return self.config.get("storage", {}).get("processes", {})

    def getDefaults(self):
        return self.config.get("defaults", {})


# Ejemplo de uso en otro script:
# from utils import ConfigLoader
# config = ConfigLoader('config.json')
# print(config.get_num_distinct_words())



def dbTimestamp():
    timestamp = int(time.time())
    # Format it as "YYYYMMDDHHMMSS"
    formatted_timestamp = str(time.strftime("%Y%m%d%H%M%S", time.gmtime(timestamp)))
    return formatted_timestamp

def deleteFilesPath(folderPath):
    for filename in os.listdir(folderPath):
        filePath = os.path.join(folderPath, filename)
        if os.path.isfile(filePath):
            os.remove(filePath)


def unzipToDestination(zipFile, destinationPath):
    try:
        # Create the 'working' directory if it doesn't exist
        if not os.path.exists(destinationPath):
            os.makedirs(destinationPath)
        # Unzip the file using shutil
        shutil.unpack_archive(f'{zipFile}.zip', destinationPath)
    except Exception as e:
        raise e

    return True


def sanitizar_nombre_archivo(nombre):
    """
    Convierte un string en un nombre de archivo válido
    """
    # Normalizar caracteres Unicode (ej: ñ -> n, á -> a)
    nombre = unicodedata.normalize('NFKD', nombre)
    nombre = nombre.encode('ASCII', 'ignore').decode('ASCII')

    # Eliminar caracteres inválidos
    nombre = re.sub(r'[<>:"/\\|?*]', '', nombre)

    # Eliminar espacios al inicio y final
    nombre = nombre.strip()

    # Reemplazar espacios múltiples por uno solo
    nombre = re.sub(r'\s+', ' ', nombre)

    # Reemplazar espacios por guiones bajos
    nombre = nombre.replace(' ', '_')

    # Limitar longitud (255 caracteres máximo típicamente)
    nombre = nombre[:255]

    # Asegurar que no empiece con punto o espacio
    nombre = nombre.lstrip('. ')

    return nombre


def preparaDirectorio(ruta):
    """Versión más compacta"""
    try:
        # Eliminar directorio si existe (con todo su contenido)
        if os.path.exists(ruta):
            shutil.rmtree(ruta)

        # Crear directorio vacío
        os.makedirs(ruta, exist_ok=True)
        writeLog("info", logger, f"✓ Directorio '{ruta}' preparado y vacío")
        return True

    except Exception as e:
        writeLog("error", logger, f"✗ Error con '{ruta}': {e}")
        return False