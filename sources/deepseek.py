from sources.common.common import logger, processControl, writeLog

import asyncio
import json
import pandas as pd
from playwright.async_api import async_playwright
import time
from datetime import datetime
import csv


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
        # Verifica si ya estás logueado
        await page.goto(self.base_url)
        await page.wait_for_timeout(3000)

        # Si hay campo de login, completa con tus credenciales
        # Ajusta según la página actual de DeepSeek
        login_input = page.locator('input[type="email"], input[type="text"]').first
        if await login_input.is_visible():
            await login_input.fill("ega364620916@proton.me")
            await page.locator('input[type="password"]').fill("barcelona92")
            await page.locator('button:has-text("Log in"), button:has-text("登录"), button:has-text("Sign in"), button:has-text("Iniciar sesión")').first.click()
            await page.wait_for_timeout(5000)

    async def send_prompt(self, page, prompt, wait_time=30):
        """Envía un prompt y recoge la respuesta"""
        try:
            # Localiza el textarea/input para el prompt
            # (Ajusta estos selectores según la interfaz actual)
            textarea = page.locator('textarea, [contenteditable="true"], .prompt-input')
            await textarea.wait_for(state='visible')
            await textarea.click()
            await textarea.fill(prompt)

            # Envía el prompt (Enter o botón Send)
            await textarea.press('Enter')

            # Espera a que la respuesta esté completa
            # Busca el último mensaje de respuesta
            await page.wait_for_timeout(wait_time * 1000)

            # Extrae la respuesta (ajusta el selector)
            response_locator = page.locator('.message-content, .ds-scroll-area .ds-markdown, [data-testid="message"]').last
            response = await response_locator.text_content()

            return {
                'prompt': prompt,
                'response': response.strip() if response else '',
                'timestamp': datetime.now().isoformat(),
                'wait_time': wait_time
            }

        except Exception as e:
            print(f"Error procesando prompt: {e}")
            return None

    async def run_questionnaire(self, questions, output_file="resultados.csv"):
        """Ejecuta un cuestionario completo"""
        playwright, browser, page = await self.setup_browser()

        try:
            # Navega a la página
            await self.login_if_needed(page)
            await page.wait_for_timeout(5000)

            # Procesa cada pregunta
            for i, question in enumerate(questions):
                print(f"Procesando pregunta {i + 1}/{len(questions)}: {question[:50]}...")

                result = await self.send_prompt(page, question)
                if result:
                    self.results.append(result)
                    print(f"✓ Respuesta obtenida ({len(result['response'])} caracteres)")

                # Espera entre preguntas para evitar rate limiting
                await page.wait_for_timeout(5000)

            # Guarda resultados
            self.save_results(output_file)
            print(f"\n✅ Cuestionario completado. Resultados en {output_file}")

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

        return df


# Ejemplo de uso
async def main():
    # Lista de preguntas/prompts
    questions = [
        "Explícame la teoría de la relatividad en términos simples",
        "¿Cuáles son las ventajas de Python sobre otros lenguajes?",
    ]

    automator = DeepSeekAutomator()

    # Opción 1: Ejecutar cuestionario completo
    await automator.run_questionnaire(
        questions=questions,
        output_file="deepseek_responses.csv"
    )

    # Opción 2: Modo interactivo para debugging
    # playwright, browser, page = await automator.setup_browser()
    # await automator.login_if_needed(page)
    # resultado = await automator.send_prompt(page, "Hola, ¿cómo estás?")
    # print(resultado)


def processAI():
    asyncio.run(main())


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
            "delay_between_prompts": 3,
            "output_formats": ["csv", "json", "excel"]
        }
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        except FileNotFoundError:
            pass
        return default_config

    async def send_prompt_with_retry(self, page, prompt, attempt=1):
        """Envía prompt con reintentos"""
        try:
            result = await self.send_prompt(
                page,
                prompt,
                wait_time=self.config["timeout"]
            )
            return result
        except Exception as e:
            if attempt < self.config["retry_attempts"]:
                print(f"Reintentando ({attempt}/{self.config['retry_attempts']})...")
                await page.wait_for_timeout(5000)
                return await self.send_prompt_with_retry(page, prompt, attempt + 1)
            else:
                print(f"Error después de {attempt} intentos: {e}")
                return None

    async def batch_processing(self, questions_batch, batch_size=5):
        """Procesa preguntas en lotes con pausas"""
        results = []

        for i in range(0, len(questions_batch), batch_size):
            batch = questions_batch[i:i + batch_size]
            print(f"\nProcesando lote {i // batch_size + 1}/{(len(questions_batch) + batch_size - 1) // batch_size}")

            for question in batch:
                result = await self.send_prompt_with_retry(question)
                if result:
                    results.append(result)

            # Pausa entre lotes para evitar rate limiting
            if i + batch_size < len(questions_batch):
                print(f"Pausa de 60 segundos...")
                await asyncio.sleep(60)

        return results


# Cargar preguntas desde archivo
def load_questions_from_file(filename):
    """Carga preguntas desde diferentes formatos"""
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


# Script principal mejorado
async def enhanced_main():
    # Cargar preguntas desde archivo
    questions = load_questions_from_file("preguntas.txt")

    # O crear dinámicamente
    if not questions:
        questions = [
            f"Explica el concepto de {concept} en 3 líneas"
            for concept in ["blockchain", "quantum computing", "neural networks", "docker"]
        ]

    # Configurar automator
    automator = EnhancedDeepSeekAutomator()

    # Procesar
    await automator.run_questionnaire(
        questions=questions,
        output_file="resultados_completos.csv"
    )

    # Análisis básico
    if automator.results:
        df = pd.DataFrame(automator.results)
        print(f"\n📊 Estadísticas:")
        print(f"- Total respuestas: {len(df)}")
        print(f"- Longitud promedio respuesta: {df['response'].str.len().mean():.0f} caracteres")
        print(f"- Tiempo total estimado: {len(df) * 35 / 60:.1f} minutos")