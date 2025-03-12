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
PREFIJOS = ["+595", "+598"]  # Prefijos de Paraguay y Uruguay
SECTORES = [
    # Términos relacionados a Paraguay
    "residencia fiscal paraguay",
    "ciudadanía paraguay",
    "abogados migratorios paraguay",
    "firma contable paraguay",
    "asesoría fiscal paraguay",
    "consultoría migratoria paraguay",
    "family office paraguay",
    "expatriados paraguay",
    "banca privada paraguay",
    "offshore paraguay",
    # Términos relacionados a Uruguay
    "residencia fiscal uruguay",
    "ciudadanía uruguay",
    "abogados migratorios uruguay",
    "firma contable uruguay",
    "asesoría fiscal uruguay",
    "consultoría migratoria uruguay",
    "family office uruguay",
    "expatriados uruguay",
    "banca privada uruguay",
    "offshore uruguay"
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
        # Adaptamos la búsqueda de direcciones para incluir formatos de ambos países
        direccion = re.findall(r'(?:Calle|Avenida|Ruta|Boulevard|Av\.|Dr\.|Camino).*?(?=\s{2,}|$)', descripcion)
        
        # Detectar país
        pais = self.detectar_pais(descripcion)
        
        return {
            'email': email[0] if email else '',
            'direccion': direccion[0] if direccion else '',
            'pais': pais
        }

    def detectar_pais(self, texto):
        """Detecta si el texto está relacionado con Paraguay o Uruguay"""
        texto = texto.lower()
        if any(keyword in texto for keyword in ["paraguay", "asunción", "asuncion", "py", "paraguayo", "paraguaya"]):
            return "Paraguay"
        elif any(keyword in texto for keyword in ["uruguay", "montevideo", "uy", "uruguayo", "uruguaya"]):
            return "Uruguay"
        
        # Si no hay palabras clave, intentamos detectar por prefijos telefónicos
        if "+595" in texto or "0595" in texto:
            return "Paraguay"
        elif "+598" in texto or "0598" in texto:
            return "Uruguay"
        
        # Si no podemos determinar, usamos el término de búsqueda
        return None  # Lo determinaremos por el término de búsqueda

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

    def normalizar_numero_telefono(self, numero, prefijo_pais):
        """Normaliza un número de teléfono al formato internacional correspondiente"""
        # Eliminar espacios y caracteres especiales
        numero = re.sub(r'[\s\-\(\)]', '', numero)
        
        # Si ya tiene formato internacional correcto, retornarlo
        if numero.startswith(prefijo_pais):
            return numero
        
        # Si empieza con 0 + el prefijo sin +
        if numero.startswith('0' + prefijo_pais[1:]):
            return '+' + numero[1:]
        
        # Si empieza con el prefijo sin +
        elif numero.startswith(prefijo_pais[1:]):
            return '+' + numero
            
        # Si es un número local (empieza con 0), añadir prefijo país
        elif numero.startswith('0'):
            return prefijo_pais + numero[1:]
            
        # Si es un número local sin 0, añadir prefijo país
        else:
            return prefijo_pais + numero

    def es_numero_valido(self, numero, prefijo_pais):
        """Verifica si un número es válido para el país indicado"""
        numero_limpio = re.sub(r'[\s\-\(\)]', '', numero)
        # Verificar formato internacional y longitud
        if prefijo_pais == "+595":  # Paraguay
            patron = r'^\+595\d{9}$'  # +595 seguido de 9 dígitos
        elif prefijo_pais == "+598":  # Uruguay
            patron = r'^\+598\d{8}$'  # +598 seguido de 8 dígitos
        return bool(re.match(patron, numero_limpio))

    def extraer_numeros_telefono(self, texto, consulta):
        """Extrae números de teléfono del texto según el país de la consulta"""
        # Determinar el país por la consulta
        pais_consulta = "Paraguay" if "paraguay" in consulta.lower() else "Uruguay"
        prefijo_pais = "+595" if pais_consulta == "Paraguay" else "+598"
        
        # Patrones de búsqueda según el país
        if pais_consulta == "Paraguay":
            patrones = [
                r'(?:tel[eé]fono|tel|phone|movil|móvil|celular|contact|fijo|fax|whatsapp|wsp|wa)?\s*:?\s*(?:\+595|595|0)[\s\-\(\)]*(?:\d[\s\-\(\)]*){8,}',
                r'(?:\+595|595|0)[\s\-\(\)]*(?:\d[\s\-\(\)]*){8,}',
                r'\b(?:0|9)[\s\-\(\)]*(?:\d[\s\-\(\)]*){7,}'
            ]
            long_numero = 12  # +595 + 9 dígitos
        else:  # Uruguay
            patrones = [
                r'(?:tel[eé]fono|tel|phone|movil|móvil|celular|contact|fijo|fax|whatsapp|wsp|wa)?\s*:?\s*(?:\+598|598|0)[\s\-\(\)]*(?:\d[\s\-\(\)]*){7,}',
                r'(?:\+598|598|0)[\s\-\(\)]*(?:\d[\s\-\(\)]*){7,}',
                r'\b(?:0|9)[\s\-\(\)]*(?:\d[\s\-\(\)]*){6,}'
            ]
            long_numero = 11  # +598 + 8 dígitos
        
        numeros_encontrados = []
        texto = texto.lower()  # Convertir a minúsculas para mejor búsqueda
        
        for patron in patrones:
            matches = re.findall(patron, texto, re.IGNORECASE)
            for match in matches:
                # Limpiar y normalizar el número
                numero_limpio = re.sub(r'[^\d\+]', '', match)  # Mantener solo dígitos y +
                numero_normalizado = self.normalizar_numero_telefono(numero_limpio, prefijo_pais)
                
                # Verificar longitud válida
                if len(re.sub(r'[^\d]', '', numero_normalizado)) == long_numero:
                    numeros_encontrados.append(numero_normalizado)
        
        return list(set(numeros_encontrados))  # Eliminar duplicados

    def extraer_whatsapp(self, texto):
        """Extrae específicamente menciones a WhatsApp"""
        texto = texto.lower()
        # Buscar patrones específicos de WhatsApp
        patrones_whatsapp = [
            r'(?:whatsapp|wsp|wa|whats app)[\s\:]*(?:\+?[0-9][\s\-\(\)]*){7,}',
            r'(?:contacto|contactar|escribir)(?:\s\w+){0,3}\s(?:al|por)\s(?:whatsapp|wsp|wa)',
            r'(?:escríbenos|escribenos|contáctenos|contactenos)(?:\s\w+){0,3}\s(?:whatsapp|wsp|wa)'
        ]
        
        es_whatsapp = False
        for patron in patrones_whatsapp:
            if re.search(patron, texto, re.IGNORECASE):
                es_whatsapp = True
                break
                
        return es_whatsapp

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
            # Mejorar la consulta para encontrar contactos
            search_query = f'{consulta} AND ("contacto" OR "teléfono" OR "telefono" OR "contact" OR "WhatsApp" OR "correo" OR "email")'
            search_box.send_keys(search_query)
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
                                numeros = self.extraer_numeros_telefono(texto_completo, consulta)
                                
                                # Extraer información adicional
                                info_adicional = self.extraer_info_adicional(texto_completo)
                                if not info_adicional['pais']:
                                    info_adicional['pais'] = "Paraguay" if "paraguay" in consulta.lower() else "Uruguay"
                                
                                # Determinar si algún número es WhatsApp
                                es_whatsapp = self.extraer_whatsapp(texto_completo)
                                
                                if numeros or info_adicional['email']:
                                    print(f"✅ Encontrado(s) {len(numeros)} número(s) y/o email:")
                                    
                                    # Si hay email pero no números, agregar un registro con el email
                                    if info_adicional['email'] and not numeros:
                                        nuevo_lead = [
                                            titulo,
                                            enlace,
                                            "",  # No hay número
                                            info_adicional['email'],
                                            info_adicional['direccion'],
                                            info_adicional['pais'],
                                            consulta,
                                            "Sí" if es_whatsapp else "No",
                                            time.strftime("%Y-%m-%d")
                                        ]
                                        
                                        self.data.append(nuevo_lead)
                                        leads_en_pagina_actual += 1
                                        print(f"  📧 Email: {info_adicional['email']}")
                                    
                                    # Para cada número encontrado, crear un registro
                                    for numero in numeros:
                                        nuevo_lead = [
                                            titulo,
                                            enlace,
                                            numero,
                                            info_adicional['email'],
                                            info_adicional['direccion'],
                                            info_adicional['pais'],
                                            consulta,
                                            "Sí" if es_whatsapp else "No",
                                            time.strftime("%Y-%m-%d")
                                        ]
                                        
                                        self.data.append(nuevo_lead)
                                        leads_en_pagina_actual += 1
                                        
                                        print(f"  📞 Número: {numero} {'(WhatsApp)' if es_whatsapp else ''}")
                                        if info_adicional['email']:
                                            print(f"  📧 Email: {info_adicional['email']}")
                                        
                                        # Guardar inmediatamente
                                        self.guardar_datos_incrementalmente()
                                else:
                                    print("❌ No se encontraron números ni emails en este resultado")
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
                "Empresa/Entidad",
                "Enlace",
                "Teléfono",
                "Email",
                "Dirección",
                "País",
                "Sector",
                "WhatsApp",
                "Fecha Extracción"
            ])
            
            # Eliminar duplicados basados en el número de teléfono y email
            df = df.drop_duplicates(subset=['Teléfono', 'Email'], keep='first')
            
            # Guardar en Excel con formato
            with pd.ExcelWriter('leads_contactos.xlsx', engine='openpyxl', mode='w') as writer:
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
        print(f"🌎 Países objetivo: Paraguay (+595) y Uruguay (+598)")
        print(f"🎯 Total de términos a buscar: {len(SECTORES)}")
        
        try:
            total_leads = 0
            for i, sector in enumerate(SECTORES, 1):
                print(f"\n📊 Progreso: Término {i}/{len(SECTORES)}")
                
                # Simplificamos la query para ser más directa
                self.buscar_numeros(sector)
                
                # Actualizar contador total
                if len(self.data) > total_leads:
                    nuevos_leads = len(self.data) - total_leads
                    print(f"✨ Encontrados {nuevos_leads} nuevos leads en esta búsqueda")
                    total_leads = len(self.data)
                
                print(f"⏳ Esperando antes de la siguiente búsqueda...")
                time.sleep(5)

            if total_leads == 0:
                print("\n⚠️ No se encontraron resultados")
            else:
                print(f"\n✅ Proceso finalizado exitosamente")
                print(f"📊 Total de leads únicos encontrados: {total_leads}")
                print("📁 Datos guardados en 'leads_contactos.xlsx'")
        
        except Exception as e:
            print(f"\n❌ Error durante la ejecución: {str(e)}")
        
        finally:
            print("\n👋 Cerrando el navegador...")
            self.driver.quit()

if __name__ == "__main__":
    extractor = LeadsExtractor()
    extractor.ejecutar()
