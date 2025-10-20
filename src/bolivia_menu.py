#!/usr/bin/env python3
"""
Sistema interactivo de placas bolivianas - Menú principal
"""

import os
import cv2
import datetime
import re
from pathlib import Path
from lib.filters import (
    get_grayscale,
    thresholding,
    remove_noise,
    pytesseract,
    detect_plate_contours
)

def normalize_bolivian_plate(plate_text):
    """Normaliza placa boliviana a formato consistente"""
    if not plate_text:
        return None
    
    # Limpiar entrada
    clean = re.sub(r'[^A-Z0-9\-\s]', '', plate_text.upper()).strip()
    clean_no_sep = clean.replace('-', '').replace(' ', '')
    
    # Verificar si es placa boliviana válida (7 caracteres, mix de letras y números)
    if len(clean_no_sep) == 7:
        letter_count = len(re.findall(r'[A-Z]', clean_no_sep))
        number_count = len(re.findall(r'[0-9]', clean_no_sep))
        
        if letter_count >= 3 and number_count >= 3:
            # Patrones estándar
            if re.match(r'^[A-Z]{3}[0-9]{4}$', clean_no_sep):
                # ABC1234 -> 1234 ABC
                return f"{clean_no_sep[3:]} {clean_no_sep[:3]}"
            elif re.match(r'^[0-9]{4}[A-Z]{3}$', clean_no_sep):
                # 1234ABC -> 1234 ABC  
                return f"{clean_no_sep[:4]} {clean_no_sep[4:]}"
            else:
                # Formatos mixtos como BRA2E19, 1825B0L - mantener original
                return clean_no_sep
    
    return None

def get_last_digit(plate_text):
    """Extrae el último dígito de cualquier formato de placa"""
    if not plate_text:
        return None
    # Extraer todos los dígitos y tomar el último
    digits = re.findall(r'\d', plate_text)
    return int(digits[-1]) if digits else None

def correct_ocr_errors(text):
    """Corrige errores comunes de OCR en placas bolivianas"""
    if not text:
        return text
    
    # Correcciones específicas de OCR
    corrections = {
        'I': '1',  # I confundida con 1
        'O': '0',  # O confundida con 0  
        'S': '5',  # S confundida con 5 (en posición de número)
        'G': '6',  # G confundida con 6 (en posición de número)
        'B': '8',  # B confundida con 8 (en posición de número)
        'Z': '2',  # Z confundida con 2 (en posición de número)
    }
    
    result = text.upper()
    
    # Aplicar correcciones solo en las primeras 4 posiciones (números)
    if len(result) >= 4:
        # Corregir caracteres en posiciones de números (0-3)
        number_part = result[:4]
        letter_part = result[4:]
        
        corrected_numbers = ""
        for char in number_part:
            corrected_numbers += corrections.get(char, char)
        
        # Para las letras (posiciones 4-6), hacer correcciones inversas si es necesario
        corrected_letters = ""
        for char in letter_part:
            # Corregir números que deberían ser letras
            if char == '0':
                corrected_letters += 'O'
            elif char == '1':
                corrected_letters += 'I'
            elif char == '5':
                corrected_letters += 'S'
            elif char == '6':
                corrected_letters += 'G'
            elif char == '8':
                corrected_letters += 'B'
            elif char == '2':
                corrected_letters += 'Z'
            else:
                corrected_letters += char
        
        result = corrected_numbers + corrected_letters
    
    return result

def quick_plate_scan(image):
    """Escaneo de placa simplificado"""
    
    # Estrategias básicas
    strategies = []
    
    # 1. Original procesado
    gray = get_grayscale(image)
    processed = remove_noise(thresholding(gray))
    strategies.append(processed)
    
    # 2. Imagen ampliada para mejorar detalles
    try:
        enlarged = cv2.resize(image, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        enlarged_gray = get_grayscale(enlarged)
        enlarged_processed = remove_noise(thresholding(enlarged_gray))
        strategies.append(enlarged_processed)
    except:
        pass
    
    # 3. Región detectada si es posible
    try:
        plate_region = detect_plate_contours(image)
        if plate_region:
            x, y, w, h = plate_region
            margin = 15
            x_m = max(0, x - margin)
            y_m = max(0, y - margin)
            w_m = min(image.shape[1] - x_m, w + 2*margin)
            h_m = min(image.shape[0] - y_m, h + 2*margin)
            
            if w_m > 50 and h_m > 20:
                cropped = image[y_m:y_m+h_m, x_m:x_m+w_m]
                cropped_gray = get_grayscale(cropped)
                cropped_processed = remove_noise(thresholding(cropped_gray))
                strategies.append(cropped_processed)
    except:
        pass
    
    # Configuraciones OCR optimizadas
    configs = [
        '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
        '--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', 
        '--psm 6 -c tessedit_char_blacklist=|@#$%^&*()+={}[]\\:";\'<>?,./~`'
    ]
    
    best_result = None
    best_score = 0
    
    for img_variant in strategies:
        for config in configs:
            try:
                raw_text = pytesseract.image_to_string(img_variant, config=config).strip()
                
                if not raw_text or len(raw_text) < 3:
                    continue
                
                # Procesar líneas
                lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                
                for line in lines:
                    # Filtrar texto no-placa
                    if any(word in line.upper() for word in ['BOLIVIA', 'ESTADO', 'PLURINACIONAL']):
                        continue
                    
                    # Limpiar y aplicar correcciones
                    clean_line = re.sub(r'[^A-Z0-9]', '', line.upper())
                    corrected_line = correct_ocr_errors(clean_line)
                    
                    if len(corrected_line) >= 6 and len(corrected_line) <= 8:
                        # Verificar si contiene letras y números
                        if re.search(r'[A-Z]', corrected_line) and re.search(r'[0-9]', corrected_line):
                            
                            # Scoring simple
                            score = 0
                            
                            # Longitud ideal
                            if len(corrected_line) == 7:
                                score += 10
                            
                            # Verificar patrones bolivianos
                            letter_count = len(re.findall(r'[A-Z]', corrected_line))
                            number_count = len(re.findall(r'[0-9]', corrected_line))
                            
                            if letter_count >= 3 and number_count >= 3:
                                score += 15
                            
                            if score > best_score:
                                best_score = score
                                best_result = corrected_line
                                
            except Exception:
                continue
    
    return best_result

def is_restricted_day(plate_text):
    """Verifica restricción por día"""
    last_digit = get_last_digit(plate_text)
    if last_digit is None:
        return False, "No se pudo determinar el último dígito"
    
    current_time = datetime.datetime.now()
    weekday = current_time.weekday()  # 0=Lunes
    
    # Sábados y domingos sin restricción
    if weekday in [5, 6]:
        return False, "Sin restricción los fines de semana"
    
    # Restricciones por día
    restrictions = {
        0: [1, 2],  # Lunes
        1: [3, 4],  # Martes
        2: [5, 6],  # Miércoles  
        3: [7, 8],  # Jueves
        4: [9, 0],  # Viernes
    }
    
    day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
    
    if last_digit in restrictions[weekday]:
        return True, f"Restringido los {day_names[weekday]}s (terminación {last_digit})"
    else:
        return False, f"Permitido circular los {day_names[weekday]}s"

def is_restricted_time():
    """Verifica restricción por horario según reglamento oficial de La Paz"""
    current_time = datetime.datetime.now().time()
    
    # Horario oficial de La Paz: 07:00 - 20:00 (todo el día)
    restriction_start = datetime.time(7, 0)   # 7:00 AM
    restriction_end = datetime.time(20, 0)    # 8:00 PM
    
    if restriction_start <= current_time <= restriction_end:
        return True, "Horario de restricción (07:00-20:00)"
    else:
        return False, "Fuera de horario de restricción (20:01-06:59)"

def show_restrictions_info():
    """Muestra información de las restricciones"""
    print("\n" + "="*60)
    print("RESTRICCIÓN VEHICULAR EN LA PAZ, BOLIVIA")
    print("="*60)
    print("\nRESTRICCIONES POR TERMINACIÓN DE PLACA:")
    print("  Lunes: 1, 2")
    print("  Martes: 3, 4") 
    print("  Miércoles: 5, 6")
    print("  Jueves: 7, 8")
    print("  Viernes: 9, 0")
    print("  Sábados y Domingos: SIN RESTRICCIÓN")
    print("\nHORARIO DE RESTRICCIÓN:")
    print("  Lunes a Viernes: 07:00 - 20:00")
    print("\nNOTAS:")
    print("  - Solo para transporte público y privado")
    print("  - La restricción se basa en el último dígito de la placa")
    print("  - Formato de placa boliviana: 4 números + 3 letras")
    print("="*60)

def detect_plates():
    """Detecta placas de las imágenes"""
    print("\n" + "="*60)
    print("DETECCIÓN DE PLACAS BOLIVIANAS")
    print("="*60)
    
    images_dir = Path("../images")
    image_files = []
    
    for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
        image_files.extend(images_dir.glob(f"*{ext}"))
    
    # Eliminar duplicados por nombre base
    unique_files = {}
    for img_path in image_files:
        base_name = img_path.stem.lower()
        if base_name not in unique_files:
            unique_files[base_name] = img_path
    
    image_files = sorted(unique_files.values(), key=lambda x: x.name.lower())
    
    if not image_files:
        print("\nNo se encontraron imágenes para procesar.")
        return
    
    print(f"\nProcesando {len(image_files)} imágenes...\n")
    
    results = []
    
    for img_path in image_files:
        print(f"Imagen: {img_path.name}")
        
        try:
            # Cargar imagen
            image = cv2.imread(str(img_path))
            if image is None:
                print("  Error: No se pudo cargar la imagen\n")
                continue
            
            # Detectar placa
            detected_plate = quick_plate_scan(image)
            
            if not detected_plate:
                print("  Error: No se detectó placa\n")
                continue
            
            # Normalizar
            normalized = normalize_bolivian_plate(detected_plate)
            
            if not normalized:
                print(f"  Error: Formato no válido para Bolivia: {detected_plate}\n")
                continue
            
            print(f"  Detectada: {detected_plate}")
            print(f"  Normalizada: {normalized}")
            
            # Verificar restricciones
            day_restricted, day_msg = is_restricted_day(detected_plate)
            time_restricted, time_msg = is_restricted_time()
            
            if day_restricted and time_restricted:
                status = "RESTRINGIDO"
            elif day_restricted:
                status = "RESTRINGIDO (fuera de horario)"
            else:
                status = "PERMITIDO"
            
            print(f"  Estado: {status}")
            print(f"  Día: {day_msg}")
            print(f"  Horario: {time_msg}\n")
            
            results.append({
                'file': img_path.name,
                'detected': detected_plate,
                'normalized': normalized,
                'status': status
            })
            
        except Exception as e:
            print(f"  Error: {e}\n")
    
    # Resumen final
    if results:
        print("-" * 60)
        print("RESUMEN")
        print("-" * 60)
        for r in results:
            print(f"{r['file']}: {r['normalized']} -> {r['status']}")
        
        print(f"\nTotal procesadas: {len(results)}/{len(image_files)}")
    else:
        print("No se procesaron placas exitosamente.")

def show_menu():
    """Muestra el menú principal"""
    print("\n" + "="*60)
    print("SISTEMA DE PLACAS BOLIVIANAS")
    print("="*60)
    print("\nOPCIONES:")
    print("1. Ver información de restricciones")
    print("2. Detectar placas de las imágenes")
    print("3. Salir")
    print("="*60)

def main():
    """Función principal con menú interactivo"""
    while True:
        show_menu()
        
        try:
            opcion = input("\nSeleccione una opción (1-3): ").strip()
            
            if opcion == '1':
                show_restrictions_info()
            
            elif opcion == '2':
                detect_plates()
            
            elif opcion == '3':
                print("\nGracias por usar el sistema de placas bolivianas.")
                break
            
            else:
                print("\nOpción inválida. Por favor seleccione 1, 2 o 3.")
            
            input("\nPresione Enter para continuar...")
                
        except KeyboardInterrupt:
            print("\n\nSistema interrumpido. Hasta luego!")
            break
        except Exception as e:
            print(f"\nError: {e}")

if __name__ == "__main__":
    main()