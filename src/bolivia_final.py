#!/usr/bin/env python3
"""
Sistema de detección de placas bolivianas - Solo formato 4números+3letras
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
        
        # Para las letras (posiciones 4-6), hacer correcciones inversas
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

def normalize_bolivian_plate(plate_text):
    """Normaliza placa boliviana al formato estricto 1234 ABC"""
    if not plate_text:
        return None
    
    # Limpiar entrada
    clean = re.sub(r'[^A-Z0-9]', '', plate_text.upper()).strip()
    
    # Aplicar correcciones de OCR
    corrected = correct_ocr_errors(clean)
    
    # Verificar formato boliviano estricto: exactamente 7 caracteres
    if len(corrected) != 7:
        return None
    
    # Verificar patrón boliviano: 4 dígitos + 3 letras
    if re.match(r'^\d{4}[A-Z]{3}$', corrected):
        # Ya está en formato correcto, solo agregar espacio
        return f"{corrected[:4]} {corrected[4:]}"
    
    return None

def get_last_digit(plate_text):
    """Extrae el último dígito de placa boliviana (siempre en posición 3)"""
    if not plate_text:
        return None
    
    # Para placas bolivianas normalizadas "1234 ABC"
    normalized = normalize_bolivian_plate(plate_text)
    if normalized:
        # El último dígito está en la posición 3 de los primeros 4 números
        numbers = normalized[:4]
        return int(numbers[3]) if len(numbers) >= 4 else None
    
    return None

def advanced_ocr_scan(image):
    """Escaneo OCR avanzado específicamente para placas bolivianas"""
    #print("  🔍 Escaneo avanzado para Bolivia...")
    
    best_result = None
    best_score = 0
    
    # Estrategias optimizadas para placas bolivianas
    strategies = []
    
    # 1. Original procesado
    gray = get_grayscale(image)
    processed = remove_noise(thresholding(gray))
    strategies.append(("original", processed))
    
    # 2. Imagen ampliada x2.5 para mayor claridad en números
    try:
        enlarged = cv2.resize(image, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        enlarged_gray = get_grayscale(enlarged)
        enlarged_processed = remove_noise(thresholding(enlarged_gray))
        strategies.append(("enlarged", enlarged_processed))
    except:
        pass
    
    # 3. Región de placa detectada automáticamente
    try:
        plate_region = detect_plate_contours(image)
        if plate_region:
            x, y, w, h = plate_region
            margin = 20  # Margen más generoso
            x_m = max(0, x - margin)
            y_m = max(0, y - margin)
            w_m = min(image.shape[1] - x_m, w + 2*margin)
            h_m = min(image.shape[0] - y_m, h + 2*margin)
            
            if w_m > 50 and h_m > 20:
                cropped = image[y_m:y_m+h_m, x_m:x_m+w_m]
                cropped_gray = get_grayscale(cropped)
                cropped_processed = remove_noise(thresholding(cropped_gray))
                strategies.append(("region", cropped_processed))
    except:
        pass
    
    # 4. Procesamiento con ecualización de histograma
    try:
        from lib.filters import enhanced_preprocessing
        enhanced = enhanced_preprocessing(gray)
        strategies.append(("enhanced", enhanced))
    except:
        pass
    
    #print(f"  📊 Probando {len(strategies)} estrategias...")
    
    # Configuraciones OCR específicas para números y letras
    configs = [
        # Configuración optimizada para 4 números + 3 letras
        '--psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        '--psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        '--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ',
        '--psm 13 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    ]
    
    candidates = []
    
    for strategy_name, img_variant in strategies:
        for config in configs:
            try:
                raw_text = pytesseract.image_to_string(img_variant, config=config).strip()
                
                if not raw_text or len(raw_text) < 3:
                    continue
                
                # Procesar líneas
                lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                
                for line in lines:
                    # Filtrar texto no-placa
                    if any(word in line.upper() for word in ['BOLIVIA', 'ESTADO', 'PLURINACIONAL', 'DEPARTAMENTO']):
                        continue
                    
                    # Limpiar y aplicar correcciones
                    clean_line = re.sub(r'[^A-Z0-9]', '', line.upper())
                    corrected_line = correct_ocr_errors(clean_line)
                    
                    # Verificar longitud y formato boliviano
                    if len(corrected_line) == 7:
                        if re.match(r'^\d{4}[A-Z]{3}$', corrected_line):
                            
                            # Scoring para placas bolivianas
                            score = 50  # Base alta para formato perfecto
                            
                            # Bonificaciones por estrategia
                            if strategy_name == "region":
                                score += 10
                            elif strategy_name == "enlarged":
                                score += 8
                            elif strategy_name == "enhanced":
                                score += 5
                            
                            # Bonificación si no requirió muchas correcciones
                            if clean_line == corrected_line:
                                score += 15  # Sin correcciones necesarias
                            
                            candidates.append((corrected_line, score, strategy_name, line))
                            
                            if score > best_score:
                                best_score = score
                                best_result = corrected_line
                                
            except Exception as e:
                continue
    
    #print(f"  📋 {len(candidates)} candidatos encontrados")
    if best_result:
        #print(f"  🏆 Mejor: {best_result} (score: {best_score})")
        # Mostrar correcciones aplicadas si las hubo
        for candidate, score, strategy, original in candidates:
            if candidate == best_result and candidate != original.replace(' ', '').replace('-', '').upper():
                print(f"  🔧 Corregido de: {original} → {best_result}")
                break
    
    return best_result

def is_restricted_day(plate_text):
    """Verifica restricción por día para placa boliviana"""
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
    
    # Horario oficial: 07:00 - 20:00 (todo el día)
    restriction_start = datetime.time(7, 0)   # 7:00 AM
    restriction_end = datetime.time(20, 0)    # 8:00 PM
    
    if restriction_start <= current_time <= restriction_end:
        return True, "Horario de restricción (07:00-20:00)"
    else:
        return False, "Fuera de horario de restricción (20:01-06:59)"

def main():
    """Sistema optimizado para placas bolivianas únicamente"""
    print("🇧🇴 SISTEMA DE RESTRICCIÓN VEHICULAR - LA PAZ, BOLIVIA")
    print("="*70)
    print("📋 RESTRICCIONES POR TERMINACIÓN DE PLACA:")
    print("   🟢 Lunes: 1, 2")
    print("   🔴 Martes: 3, 4") 
    print("   🟡 Miércoles: 5, 6")
    print("   🔵 Jueves: 7, 8")
    print("   🟠 Viernes: 9, 0")
    print("   ⚪ Sábados y Domingos: SIN RESTRICCIÓN")
    print()
    print("🕐 HORARIO DE RESTRICCIÓN: 07:00 - 20:00")
    print("="*70)
    
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
    
    print(f"🔍 Procesando {len(image_files)} placas bolivianas...\n")
    
    results = []
    
    for img_path in image_files:
        print(f"📷 {img_path.name}")
        
        try:
            # Cargar imagen
            image = cv2.imread(str(img_path))
            if image is None:
                print(f"  ❌ No se pudo cargar la imagen\n")
                continue
            
            # Detectar placa
            detected_plate = advanced_ocr_scan(image)
            
            if not detected_plate:
                print(f"  ❌ No se detectó placa boliviana\n")
                continue
            
            # Normalizar
            normalized = normalize_bolivian_plate(detected_plate)
            
            if not normalized:
                print(f"  ❌ Formato no válido para Bolivia: {detected_plate}\n")
                continue
            
            print(f"  🎯 Detectada: {detected_plate}")
            print(f"  ✅ Normalizada: {normalized}")
            
            # Verificar restricciones
            day_restricted, day_msg = is_restricted_day(detected_plate)
            time_restricted, time_msg = is_restricted_time()
            
            if day_restricted and time_restricted:
                status = "🚫 RESTRINGIDO"
            elif day_restricted:
                status = "⚠️ RESTRINGIDO (fuera de horario)"
            else:
                status = "✅ PERMITIDO"
            
            print(f"  📋 Estado: {status}")
            print(f"  📅 Día: {day_msg}")
            print(f"  🕐 Horario: {time_msg}\n")
            
            results.append({
                'file': img_path.name,
                'detected': detected_plate,
                'normalized': normalized,
                'status': status
            })
            
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
    
    # Resumen final
    if results:
        print("🎯 RESUMEN FINAL - PLACAS BOLIVIANAS")
        print("="*70)
        for r in results:
            print(f"📋 {r['file']}: {r['normalized']} → {r['status']}")
        
        print(f"\n📊 Placas bolivianas procesadas: {len(results)}/{len(image_files)}")
        print(f"📈 Tasa de éxito: {len(results)*100/len(image_files):.1f}%")
    else:
        print("❌ No se detectaron placas bolivianas válidas")

if __name__ == "__main__":
    main()