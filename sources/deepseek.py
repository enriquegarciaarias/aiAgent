from sources.common.common import logger, processControl, writeLog
import asyncio
import json
import pandas as pd
from playwright.async_api import async_playwright
import time
from datetime import datetime
import csv
import os


class DeepSeekAutomator:
    def __init__(self):
        self.results = []
        self.base_url = "https://chat.deepseek.com"

    async def setup_browser(self):
        """Configura el navegador"""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=False,  # Cambiar a True para producción
            args=['--no-sandbox']
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()
        return playwright, browser, page

    async def login_if_needed(self, page):
        """Maneja login si es necesario"""
        await page.goto(self.base_url)
        await page.wait_for_timeout(3000)

        login_input = page.locator('input[type="email"], input[type="text"]').first
        if await login_input.is_visible():
            await login_input.fill("ega364620916@proton.me")
            await page.locator('input[type="password"]').fill("barcelona92")
            await page.locator(
                'button:has-text("Log in"), button:has-text("登录"), button:has-text("Sign in"), button:has-text("Iniciar sesión")').first.click()
            await page.wait_for_timeout(5000)

    async def upload_pdf(self, page, pdf_path):
        """Sube un archivo PDF a la conversación"""
        try:
            # Esperar a que el botón de adjuntar archivo esté disponible
            # Los selectores pueden variar - probar diferentes opciones
            upload_selectors = [
                'button[aria-label*="upload"]',
                'div.ds-icon-button--sizing-container',
                'button.ds-icon-button--sizing-container',
                'div[class*="ds-icon-button--sizing-container"]',
                'button[class*="ds-icon-button--sizing-container"]'
            ]


            # Primero intentar encontrar directamente el input file
            file_input = page.locator('input[type="file"]')
            if await file_input.count() > 0:
                writeLog("info", logger, "file input found")
                await file_input.set_input_files(pdf_path)
                await page.wait_for_timeout(3000)
                print(f"✓ PDF subido directamente: {os.path.basename(pdf_path)}")
                return True            



            # Si no, buscar botón de upload
            upload_button = None
            for selector in upload_selectors:
                if await page.locator(selector).count() > 0:
                    writeLog("info", logger, "file selector locator found")
                    upload_button = page.locator(selector).first
                    break

            if upload_button and await upload_button.is_visible():
                await upload_button.click()
                await page.wait_for_timeout(1000)

                # Ahora debería aparecer el input file
                file_input = page.locator('input[type="file"]')
                if await file_input.count() > 0:
                    await file_input.set_input_files(pdf_path)
                    await page.wait_for_timeout(3000)
                    print(f"✓ PDF subido: {os.path.basename(pdf_path)}")

                    # Esperar a que se complete la carga (verificar que aparece en la conversación)
                    await page.wait_for_timeout(10000)
                    return True
                else:
                    # Si no aparece input, intentar con diálogo nativo
                    async with page.expect_file_chooser() as fc_info:
                        await upload_button.click()
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(pdf_path)
                    await page.wait_for_timeout(3000)
                    print(f"✓ PDF subido mediante diálogo: {os.path.basename(pdf_path)}")
                    return True

            print("⚠ No se encontró el botón de subida de archivos")
            return False

        except Exception as e:
            print(f"✗ Error subiendo PDF: {e}")
            return False

    async def send_prompt(self, page, prompt, pdf_path=None, wait_time=30):
        """Envía un prompt y recoge la respuesta, opcionalmente con PDF adjunto"""
        try:
            # Subir PDF primero si se especifica
            if pdf_path and os.path.exists(pdf_path):
                print(f"Subiendo PDF: {pdf_path}")
                upload_success = await self.upload_pdf(page, pdf_path)
                if not upload_success:
                    print("⚠ Continuando sin el PDF...")
                await page.wait_for_timeout(50000)  # Esperar después de subir

            # Localizar el textarea/input para el prompt
            textarea_selectors = [
                'textarea[placeholder*="Message"]',
                'textarea[placeholder*="mensaje"]',
                'textarea[placeholder*="escribe"]',
                'div[contenteditable="true"]',
                '.prompt-input',
                'input[type="text"]',
                '[role="textbox"]',
                '[data-testid="message-input"]'
            ]

            textarea = None
            for selector in textarea_selectors:
                if await page.locator(selector).count() > 0:
                    textarea = page.locator(selector).first
                    break

            if not textarea:
                # Último recurso: cualquier textarea
                textarea = page.locator('textarea').first

            await textarea.wait_for(state='visible', timeout=5000)
            await textarea.click()
            await textarea.fill(prompt)

            # Enviar el prompt
            await textarea.press('Enter')
            print(f"✓ Prompt enviado")

            # Esperar a que la respuesta esté completa
            await page.wait_for_timeout(wait_time * 1000)

            # Extraer la respuesta - selectores comunes para respuestas
            response_selectors = [
                '.message-content',
                '.ds-markdown',
                '.prose',
                '[data-testid="message"]',
                '.chat-message',
                '.response-content',
                'div.markdown'
            ]

            response = None
            for selector in response_selectors:
                elements = page.locator(selector)
                if await elements.count() > 0:
                    # Tomar el último elemento (la respuesta más reciente)
                    response_locator = elements.last
                    response = await response_locator.text_content(timeout=5000)
                    if response and len(response.strip()) > 10:  # Validar que tenga contenido
                        break

            if not response:
                # Intentar selector más genérico
                all_messages = page.locator('.message, .chat-message, [class*="message"]')
                count = await all_messages.count()
                if count > 0:
                    response_locator = all_messages.last
                    response = await response_locator.text_content(timeout=5000)

            return {
                'prompt': prompt,
                'pdf': os.path.basename(pdf_path) if pdf_path else None,
                'response': response.strip() if response else '',
                'timestamp': datetime.now().isoformat(),
                'wait_time': wait_time
            }

        except Exception as e:
            print(f"Error procesando prompt: {e}")
            return None

    async def run_questionnaire(self, questions, pdf_files=None, output_file="resultados.csv"):
        """Ejecuta un cuestionario completo con posibilidad de adjuntar PDFs"""
        playwright, browser, page = await self.setup_browser()

        try:
            # Navegar a la página
            await self.login_if_needed(page)
            await page.wait_for_timeout(5000)

            for pdf_path in pdf_files:

                # Procesar cada pregunta
                for i, question in questions.items():
                    resultData = []
                    print(f"\n{'=' * 60}")
                    print(f"Procesando pregunta {i}")
                    print(f"Pregunta: {question[:80]}...")

                    result = await self.send_prompt(
                        page,
                        question,
                        pdf_path=pdf_path,
                        wait_time=35  # Más tiempo si hay PDF
                    )

                    if result:
                        resultData.append(
                            {i: result['response']}
                        )
                        char_count = len(result['response'])
                        print(f"✓ Respuesta obtenida ({char_count} caracteres)")

                        # Guardar progreso incrementalmente
                        if i % 3 == 0:  # Cada 3 preguntas
                            self.save_results(f"progress_{output_file}")

                    # Esperar entre preguntas
                    await page.wait_for_timeout(7000)  # Más tiempo entre preguntas

                self.results.append(
                    {
                    "file": os.path.basename(pdf_path),
                    "data": resultData,
                    }
                )

            # Guardar resultados finales
            self.save_results(output_file)
            print(f"\n{'=' * 60}")
            print(f"✅ Cuestionario completado. Resultados en {output_file}")

        except Exception as e:
            print(f"Error en run_questionnaire: {e}")
            # Guardar resultados obtenidos hasta ahora
            if self.results:
                self.save_results(f"partial_{output_file}")
        finally:
            await browser.close()
            await playwright.stop()

    def save_results(self, filename):
        """Guarda resultados en diferentes formatos"""
        if not self.results:
            return

        df = pd.DataFrame(self.results)

        # CSV
        df.to_csv(filename, index=False, encoding='utf-8')

        # JSON
        json_file = filename.replace('.csv', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        # Excel
        excel_file = filename.replace('.csv', '.xlsx')
        df.to_excel(excel_file, index=False)

        print(f"📁 Resultados guardados en {filename}")
        return df


class EnhancedDeepSeekAutomator(DeepSeekAutomator):
    def __init__(self, config_file="config.json"):
        super().__init__()
        self.config = self.load_config(config_file)

    def load_config(self, config_file):
        """Carga configuración desde JSON"""
        default_config = {
            "headless": True,
            "timeout": 45,
            "retry_attempts": 3,
            "delay_between_prompts": 7,
            "output_formats": ["csv", "json", "excel"],
            "max_pdf_size_mb": 10
        }
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        except FileNotFoundError:
            pass
        return default_config

    async def send_prompt_with_retry(self, page, prompt, pdf_path=None, attempt=1):
        """Envía prompt con reintentos"""
        try:
            result = await self.send_prompt(
                page,
                prompt,
                pdf_path=pdf_path,
                wait_time=self.config["timeout"]
            )
            return result
        except Exception as e:
            if attempt < self.config["retry_attempts"]:
                print(f"Reintentando ({attempt}/{self.config['retry_attempts']})...")
                await page.wait_for_timeout(5000)
                return await self.send_prompt_with_retry(
                    page, prompt, pdf_path, attempt + 1
                )
            else:
                print(f"Error después de {attempt} intentos: {e}")
                return None


# Funciones auxiliares
def validate_pdf_path(pdf_path):
    """Valida que el PDF exista y tenga el tamaño adecuado"""
    if not os.path.exists(pdf_path):
        print(f"✗ El archivo no existe: {pdf_path}")
        return False

    if not pdf_path.lower().endswith('.pdf'):
        print(f"✗ El archivo no es un PDF: {pdf_path}")
        return False

    # Verificar tamaño (ejemplo: máximo 10MB)
    file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # MB
    if file_size > 10:
        print(f"✗ PDF demasiado grande ({file_size:.1f}MB > 10MB)")
        return False

    return True

def listaPdfFiles():
    files_path = processControl.env.get("input", "")
    lista_pdfs = []

    # Verificar si la ruta existe
    if not os.path.exists(files_path):
        print(f"Error: La ruta '{files_path}' no existe.")
        return lista_pdfs

    # Recorrer directorio y subdirectorios
    for root, dirs, files in os.walk(files_path):
        for file in files:
            # Verificar si es un archivo PDF (por extensión)
            if file.lower().endswith('.pdf'):
                # Obtener ruta completa del archivo
                pdf_path = os.path.join(root, file)
                lista_pdfs.append(pdf_path)
                print(f"PDF encontrado: {pdf_path}")

    # Mostrar resumen
    writeLog("info", logger, f"\nTotal de PDFs encontrados: {len(lista_pdfs)}")
    return lista_pdfs


def leer_json_simple(ruta_archivo):
    """
    Lee un archivo JSON y retorna su contenido como diccionario o lista.

    Args:
        ruta_archivo (str): Ruta del archivo JSON

    Returns:
        dict or list: Contenido del JSON
    """
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            datos = json.load(archivo)
        return datos
    except FileNotFoundError:
        print(f"Error: El archivo '{ruta_archivo}' no existe.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: El archivo '{ruta_archivo}' no es un JSON válido.")
        print(f"Detalles: {e}")
        return None
    except Exception as e:
        print(f"Error inesperado: {e}")
        return None


async def main():

    jsonPrompt = os.path.join(processControl.env.get("input", ""), "preguntasPrompt.json")
    questions = leer_json_simple(jsonPrompt)
    pdf_files = listaPdfFiles()

    automator = DeepSeekAutomator()

    # Ejecutar con PDFs
    await automator.run_questionnaire(
        questions=questions,
        pdf_files=pdf_files,
        output_file="deepseek_responses_con_pdfs.csv"
    )


def processAI():
    """Función principal para ejecutar el proceso"""
    asyncio.run(main())


# Script principal mejorado
async def enhanced_main():
    """Versión mejorada que carga configuraciones desde archivos"""

    # Cargar preguntas desde archivo
    questions = load_questions_from_file("preguntas.txt")

    # Cargar PDFs desde configuración o lista
    pdf_config = load_pdf_config("pdf_config.json")

    automator = EnhancedDeepSeekAutomator()

    await automator.run_questionnaire(
        questions=questions,
        pdf_files=pdf_config.get("pdf_files", []),
        output_file="resultados_completos_con_pdfs.csv"
    )

    # Análisis
    if automator.results:
        df = pd.DataFrame(automator.results)
        print(f"\n📊 Estadísticas:")
        print(f"- Total respuestas: {len(df)}")
        print(f"- PDFs utilizados: {df['pdf'].notna().sum()}")
        print(f"- Longitud promedio respuesta: {df['response'].str.len().mean():.0f} caracteres")


def load_pdf_config(filename):
    """Carga configuración de PDFs desde JSON"""
    default_config = {"pdf_files": []}
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return default_config


# También mantener la función existente para cargar preguntas
def load_questions_from_file(filename):
    """Carga preguntas desde diferentes formatos"""
    if not os.path.exists(filename):
        return []

    if filename.endswith('.txt'):
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    elif filename.endswith('.csv'):
        df = pd.read_csv(filename)
        return df['pregunta'].tolist() if 'pregunta' in df.columns else df.iloc[:, 0].tolist()
    elif filename.endswith('.json'):
        with open(filename, 'r') as f:
            data = json.load(f)
            return data.get('questions', [])
    return []


