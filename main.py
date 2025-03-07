import time
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configuración
PREFIJOS = ["+595"]  # Prefijo de Paraguay
SECTORES = [
    # Firmas de inversión y capital privado
    "inversiones paraguay",
    "private equity paraguay",
    "fondo de inversión paraguay",
    "family office paraguay",
    # Empresas inmobiliarias
    "inmobiliaria paraguay",
    "desarrolladora inmobiliaria paraguay",
    "real estate paraguay",
    "constructora paraguay",
    # Agronegocios
    "agribusiness paraguay",
    "agronegocios paraguay",
    "empresa agrícola paraguay",
    "agricultural company paraguay",
    "agroexportadora paraguay",
    # Retail y comercio
    "retail paraguay",
    "cadena comercial paraguay",
    "franquicia paraguay",
    "mayorista paraguay",
    "distribuidor paraguay"
]

class LeadsExtractor:
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-allow-origins=*")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        try:
            # Intentar inicializar el driver directamente
            self.driver = webdriver.Chrome(options=options)
            print("✅ Navegador iniciado correctamente")
        except Exception as e:
            print(f"❌ Error al inicializar Chrome directamente: {str(e)}")
            try:
                # Si falla, intentar con ChromeDriverManager
                driver_path = ChromeDriverManager().install()
                service = Service(executable_path=driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
                print("✅ Navegador iniciado con ChromeDriverManager")
            except Exception as e:
                print(f"❌ Error al inicializar Chrome con ChromeDriverManager: {str(e)}")
                raise
        
        self.data = []

    def extraer_info_adicional(self, descripcion):
        email = re.findall(r'[\w\.-]+@[\w\.-]+', descripcion)
        # Adaptamos la búsqueda de direcciones para Paraguay
        direccion = re.findall(r'(?:Calle|Avenida|Ruta|Boulevard).*?(?=\s{2,}|$)', descripcion)
        return {
            'email': email[0] if email else '',
            'direccion': direccion[0] if direccion else '',
            'pais': 'Paraguay'  # Siempre será Paraguay
        }

    def detectar_pais(self, texto):
        return 'Paraguay'  # Siempre retornamos Paraguay ya que es nuestro foco

    def manejar_recaptcha(self):
        try:
            # Buscar el checkbox del reCAPTCHA
            recaptcha = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.recaptcha-checkbox-border"))
            )
            if (recaptcha and recaptcha.is_displayed()):
                print("Marcando reCAPTCHA...")
                recaptcha.click()
                time.sleep(2)  # Esperar a que se procese el reCAPTCHA
                return True
        except Exception as e:
            print("No se encontró reCAPTCHA o no fue necesario marcarlo")
        return False

    def normalizar_numero_paraguay(self, numero):
        """Normaliza un número de teléfono al formato paraguayo (+595)"""
        # Eliminar espacios y caracteres especiales
        numero = re.sub(r'[\s\-\(\)]', '', numero)
        
        # Si empieza con 0595, convertir a +595
        if numero.startswith('0595'):
            return '+' + numero[1:]
        
        # Si empieza con 595, añadir +
        elif numero.startswith('595'):
            return '+' + numero
            
        # Si es un número local (empieza con 0), añadir prefijo país
        elif numero.startswith('0'):
            return '+595' + numero[1:]
            
        # Si es un número local sin 0, añadir prefijo país
        else:
            return '+595' + numero

    def es_numero_paraguay_valido(self, numero):
        """Verifica si un número es un número de Paraguay válido"""
        numero_limpio = re.sub(r'[\s\-\(\)]', '', numero)
        # Patrón para números paraguayos: +595 seguido de 9 dígitos
        patron = r'^\+595\d{9}$'
        return bool(re.match(patron, numero_limpio))

    def extraer_numeros_paraguay(self, texto):
        """Extrae números de teléfono paraguayos del texto"""
        # Patrones más específicos para capturar números paraguayos
        patrones = [
            r'(?:tel[eé]fono|tel|phone|movil|móvil|celular|contact|fijo|fax)?\s*:?\s*(?:\+595|595|0)[\s\-\(\)]*(?:\d[\s\-\(\)]*){8,}',  # Números con prefijo país
            r'(?:\+595|595|0)[\s\-\(\)]*(?:\d[\s\-\(\)]*){8,}',  # Números sin etiqueta
            r'\b(?:0|9)[\s\-\(\)]*(?:\d[\s\-\(\)]*){7,}'  # Números locales
        ]
        
        numeros_encontrados = []
        texto = texto.lower()  # Convertir a minúsculas para mejor búsqueda
        
        for patron in patrones:
            matches = re.findall(patron, texto, re.IGNORECASE)
            for match in matches:
                # Limpiar y normalizar el número
                numero_limpio = re.sub(r'[^\d\+]', '', match)  # Mantener solo dígitos y +
                if numero_limpio.startswith('0'):
                    numero_limpio = numero_limpio[1:]  # Quitar el 0 inicial
                if not numero_limpio.startswith('+'):
                    if numero_limpio.startswith('595'):
                        numero_limpio = '+' + numero_limpio
                    else:
                        numero_limpio = '+595' + numero_limpio
                
                # Verificar longitud válida (código país + 9 dígitos)
                if len(re.sub(r'[^\d]', '', numero_limpio)) == 12:
                    numeros_encontrados.append(numero_limpio)
        
        return list(set(numeros_encontrados))  # Eliminar duplicados

    def buscar_numeros(self, consulta):
        print(f"\n🔍 Iniciando búsqueda para: {consulta}")
        self.driver.get("https://www.google.com")
        time.sleep(2)

        try:
            # Aceptar cookies de Google si aparece el cartel
            try:
                accept_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.QS5gu.sy4vM"))
                )
                accept_button.click()
                print("✅ Cookies aceptadas")
                time.sleep(1)
            except Exception as e:
                print("ℹ️ No se encontró el cartel de cookies o ya fue aceptado")

            # Manejar reCAPTCHA si aparece
            if self.manejar_recaptcha():
                print("✅ reCAPTCHA manejado correctamente")

            # Esperar a que el cuadro de búsqueda esté disponible
            search_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "q"))
            )
            search_box.clear()
            # Quitamos el site:py y mejoramos la consulta
            search_box.send_keys(consulta)
            search_box.send_keys(Keys.RETURN)
            time.sleep(3)

            leads_en_pagina_actual = 0
            # Procesar 5 páginas de resultados
            for pagina in range(5):
                print(f"\n📄 Procesando página {pagina + 1} de 5...")

                try:
                    # Esperar a que los resultados estén disponibles - usando selector más amplio
                    resultados = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.g, div.hlcw0c"))
                    )
                    
                    print(f"📊 Analizando {len(resultados)} resultados en esta página")
                    leads_en_pagina_actual = 0
                    
                    for i, resultado in enumerate(resultados, 1):
                        try:
                            # Extraer título y enlace
                            try:
                                titulo_elem = resultado.find_element(By.CSS_SELECTOR, "h3")
                                titulo = titulo_elem.text
                                print(f"\n🔍 Analizando: {titulo[:100]}")
                            except:
                                titulo = "Sin título"
                                print("\n🔍 Analizando resultado sin título")
                            
                            try:
                                enlace_elem = resultado.find_element(By.CSS_SELECTOR, "a")
                                enlace = enlace_elem.get_attribute("href")
                            except:
                                enlace = ""
                            
                            # Extraer todo el texto del resultado
                            texto_completo = ""
                            
                            # Intentar extraer texto de diferentes elementos
                            selectores = [
                                "div.VwiC3b",        # Descripción principal
                                "div.kb0PBd",        # Información adicional
                                "div.dVsXxc",        # Contenedor de detalles
                                "div.B1uW2d",        # Datos de contacto
                                "div.YrbPuc",        # Información de la empresa
                                "div.X7NTVe",        # Detalles adicionales
                                "span"               # Cualquier otro texto
                            ]
                            
                            for selector in selectores:
                                try:
                                    elementos = resultado.find_elements(By.CSS_SELECTOR, selector)
                                    for elem in elementos:
                                        texto = elem.text.strip()
                                        if texto:
                                            texto_completo += " " + texto
                                except:
                                    continue
                            
                            if texto_completo:
                                print(f"📝 Texto extraído: {texto_completo[:150]}...")
                                
                                # Buscar números de teléfono
                                numeros = self.extraer_numeros_paraguay(texto_completo)
                                
                                if numeros:
                                    print(f"✅ Encontrado(s) {len(numeros)} número(s):")
                                    for numero in numeros:
                                        info_adicional = self.extraer_info_adicional(texto_completo)
                                        nuevo_lead = [
                                            titulo,
                                            enlace,
                                            numero,
                                            info_adicional['email'],
                                            info_adicional['direccion'],
                                            'Paraguay',
                                            consulta,
                                            time.strftime("%Y-%m-%d")
                                        ]
                                        
                                        self.data.append(nuevo_lead)
                                        leads_en_pagina_actual += 1
                                        
                                        print(f"  📞 Número: {numero}")
                                        if info_adicional['email']:
                                            print(f"  📧 Email: {info_adicional['email']}")
                                        
                                        # Guardar inmediatamente
                                        self.guardar_datos_incrementalmente()
                                else:
                                    print("❌ No se encontraron números en este resultado")
                            else:
                                print("⚠️ No se pudo extraer texto del resultado")
                            
                        except Exception as e:
                            print(f"⚠️ Error al procesar resultado: {str(e)}")
                            continue

                    print(f"\n✨ Página {pagina + 1} completada")
                    print(f"📊 Leads encontrados en esta página: {leads_en_pagina_actual}")
                    print(f"📈 Total de leads acumulados: {len(self.data)}")

                    if pagina < 4:  # No intentar ir a siguiente en la última página
                        try:
                            # Actualizar selector para el botón "Siguiente"
                            siguiente = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'oeN89d')]"))
                            )
                            siguiente.click()
                            print("➡️ Navegando a la siguiente página...")
                            time.sleep(3)
                        except Exception as e:
                            print(f"⚠️ No se pudo navegar a la siguiente página: {str(e)}")
                            break

                        # Verificar si aparece reCAPTCHA después de la navegación
                        if self.manejar_recaptcha():
                            print("✅ reCAPTCHA manejado después de cambio de página")

                except Exception as e:
                    print(f"❌ Error al procesar la página {pagina + 1}: {str(e)}")
                    print(f"Detalles del error: {str(e)}")

                # Pequeña pausa entre páginas para evitar bloqueos
                time.sleep(2)

        except Exception as e:
            print(f"❌ Error general al buscar {consulta}: {str(e)}")

    def guardar_datos_incrementalmente(self):
        """Guarda los datos en el Excel después de cada nuevo lead encontrado"""
        try:
            if not self.data:  # Si no hay datos, no intentar guardar
                return
                
            df = pd.DataFrame(self.data, columns=[
                "Empresa",
                "Enlace",
                "Teléfono",
                "Email",
                "Dirección",
                "País",
                "Sector",
                "Fecha Extracción"
            ])
            
            # Eliminar duplicados basados en el número de teléfono
            df = df.drop_duplicates(subset=['Teléfono'], keep='first')
            
            # Guardar en Excel con formato
            with pd.ExcelWriter('leads_empresas.xlsx', engine='openpyxl', mode='w') as writer:
                df.to_excel(writer, index=False, sheet_name='Leads')
                workbook = writer.book
                worksheet = writer.sheets['Leads']
                
                # Dar formato a las columnas
                for column in worksheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
            
            print(f"💾 Base de datos actualizada - Total: {len(df)} leads únicos")
            
        except Exception as e:
            print(f"❌ Error al guardar datos: {str(e)}")

    def ejecutar(self):
        print("\n🚀 Iniciando extracción de leads...")
        print(f"📱 Buscando números con prefijo: {PREFIJOS[0]}")
        print(f"🎯 Total de sectores a buscar: {len(SECTORES)}")
        
        try:
            total_leads = 0
            for i, sector in enumerate(SECTORES, 1):
                print(f"\n📊 Progreso: Sector {i}/{len(SECTORES)}")
                query = f'"{sector}" AND ("contacto" OR "teléfono" OR "telefono" OR "contact") AND "{PREFIJOS[0]}"'
                self.buscar_numeros(query)
                
                # Actualizar contador total
                if len(self.data) > total_leads:
                    nuevos_leads = len(self.data) - total_leads
                    print(f"✨ Encontrados {nuevos_leads} nuevos leads en este sector")
                    total_leads = len(self.data)
                
                print(f"⏳ Esperando antes de la siguiente búsqueda...")
                time.sleep(5)

            if total_leads == 0:
                print("\n⚠️ No se encontraron resultados")
            else:
                print(f"\n✅ Proceso finalizado exitosamente")
                print(f"📊 Total de leads únicos encontrados: {total_leads}")
                print("📁 Datos guardados en 'leads_empresas.xlsx'")
        
        except Exception as e:
            print(f"\n❌ Error durante la ejecución: {str(e)}")
        
        finally:
            print("\n👋 Cerrando el navegador...")
            self.driver.quit()

if __name__ == "__main__":
    extractor = LeadsExtractor()
    extractor.ejecutar()
