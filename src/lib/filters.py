import cv2
import numpy as np
import pytesseract
import json
import re

try:
    from PIL import Image
except ImportError:
    import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'


# get grayscale image
def get_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


# noise removal
def remove_noise(image):
    return cv2.medianBlur(image, 5)


# thresholding
def thresholding(image):
    return cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]


# dilation
def dilate(image):
    kernel = np.ones((5, 5), np.uint8)
    return cv2.dilate(image, kernel, iterations=1)


# erosion
def erode(image):
    kernel = np.ones((5, 5), np.uint8)
    return cv2.erode(image, kernel, iterations=1)


# opening - erosion followed by dilation
def opening(image):
    kernel = np.ones((5, 5), np.uint8)
    return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)


# canny edge detection
def canny(image):
    return cv2.Canny(image, 100, 200)


# skew correction
def correct_skew(image):
    """Corrige la inclinación de la imagen usando transformación de perspectiva"""
    gray = get_grayscale(image) if len(image.shape) == 3 else image
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
    
    if lines is not None and len(lines) > 0:
        angles = []
        for line in lines[:10]:
            # Handle both formats: [[rho, theta]] and [rho, theta]
            if len(line.shape) > 1:
                rho, theta = line[0]
            else:
                rho, theta = line
            angle = np.degrees(theta) - 90
            angles.append(angle)
        
        median_angle = np.median(angles)
        if abs(median_angle) > 1:  # Solo corregir si hay una inclinación significativa
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            return cv2.warpAffine(image, rotation_matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return image


# enhanced plate preprocessing
def enhanced_preprocessing(image):
    """Aplica múltiples filtros para mejorar la detección de texto"""
    # Convertir a escala de grises si es necesario
    if len(image.shape) == 3:
        gray = get_grayscale(image)
    else:
        gray = image.copy()
    
    # Corregir inclinación
    corrected = correct_skew(gray)
    
    # Aplicar desenfoque gaussiano para reducir ruido
    blurred = cv2.GaussianBlur(corrected, (3, 3), 0)
    
    # Ecualización de histograma para mejorar contraste
    equalized = cv2.equalizeHist(blurred)
    
    # Umbralización adaptativa
    adaptive_thresh = cv2.adaptiveThreshold(
        equalized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Operaciones morfológicas para limpiar la imagen
    kernel = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(adaptive_thresh, cv2.MORPH_CLOSE, kernel)
    
    return cleaned


# detect license plate region
def detect_plate_contours(image):
    """Detecta automáticamente la región de la placa usando contornos"""
    gray = get_grayscale(image) if len(image.shape) == 3 else image
    
    # Aplicar filtro bilateral para reducir ruido manteniendo bordes
    bilateral = cv2.bilateralFilter(gray, 11, 17, 17)
    
    # Detectar bordes
    edges = cv2.Canny(bilateral, 30, 200)
    
    # Encontrar contornos
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filtrar contornos que podrían ser placas
    plate_candidates = []
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 1000:  # Filtrar contornos muy pequeños
            # Aproximar el contorno
            epsilon = 0.018 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Si tiene 4 vértices (rectángulo)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / h
                
                # Verificar proporciones típicas de una placa
                if 2.0 <= aspect_ratio <= 5.5 and w > 100 and h > 30:
                    plate_candidates.append((x, y, w, h, area))
    
    # Ordenar por área y tomar la más grande
    if plate_candidates:
        plate_candidates.sort(key=lambda x: x[4], reverse=True)
        return plate_candidates[0][:4]  # Retornar x, y, w, h
    
    return None


# extract text with confidence
def extract_text_with_confidence(image, config):
    """Extrae texto usando OCR y retorna el texto con su nivel de confianza"""
    try:
        # Obtener datos detallados del OCR
        data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
        
        # Filtrar solo texto con confianza alta
        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
        texts = [data['text'][i] for i, conf in enumerate(data['conf']) if int(conf) > 0]
        
        if confidences and texts:
            # Combinar textos y calcular confianza promedio
            combined_text = ' '.join(texts).strip()
            avg_confidence = sum(confidences) / len(confidences)
            
            # Limpiar el texto (remover caracteres no deseados)
            cleaned_text = re.sub(r'[^A-Z0-9\-]', '', combined_text.upper())
            
            return cleaned_text, avg_confidence
        
        return "", 0
    except Exception as e:
        print(f"Error en OCR: {e}")
        return "", 0


# validate plate format
def validate_plate_format(plate_text):
    """Valida si el texto extraído tiene formato de placa boliviana"""
    if not plate_text or len(plate_text) < 4:
        return False

    # Usar la función detect_plate_format que ya reconoce ambos órdenes (L3N4 y N4L3)
    fmt, _ = detect_plate_format(plate_text)
    return fmt is not None


def get_plate_last_digit(plate_text):
    """Extrae el último dígito numérico de una placa boliviana.

    Intenta normalizar a '1234 ABC' y extraer el último dígito. Si no es
    posible normalizar, busca el último dígito disponible en la cadena.
    Devuelve un int o None.
    """
    if not plate_text:
        return None

    # Intentar normalizar y extraer
    normalized = normalize_plate_to_bolivian(plate_text)
    if normalized:
        return get_plate_last_digit_from_normalized(normalized)

    # Fallback: extraer cualquier dígito
    clean_plate = re.sub(r'[^A-Z0-9\-]', '', plate_text.upper())
    digits = re.findall(r'\d', clean_plate)
    return int(digits[-1]) if digits else None


def detect_plate_format(plate_text):
    """Detecta formato de placa boliviana. 
    Acepta varios patrones: ABC1234, 1234ABC, BRA2E19, 1825B0L, etc.
    Retorna (format, cleaned_text) donde format indica el tipo detectado.
    """
    if not plate_text:
        return None, None

    clean = re.sub(r'[^A-Z0-9\-\s]', '', plate_text.upper()).strip()
    
    # Patrones bolivianos estándar
    # 3 letras + 4 números (ABC-1234 o ABC1234)
    if re.match(r'^[A-Z]{3}[- ]?\d{4}$', clean):
        return 'L3N4', clean
    # 4 números + 3 letras (1234 ABC or 1234ABC)
    if re.match(r'^\d{4}[- ]?[A-Z]{3}$', clean):
        return 'N4L3', clean
    
    # Patrones mixtos bolivianos (como BRA2E19, 1825B0L)
    # Debe tener exactamente 7 caracteres con mix de letras y números
    if len(clean.replace('-', '').replace(' ', '')) == 7:
        clean_no_sep = clean.replace('-', '').replace(' ', '')
        # Debe contener al menos 3 letras y 3 números
        letter_count = len(re.findall(r'[A-Z]', clean_no_sep))
        number_count = len(re.findall(r'\d', clean_no_sep))
        
        if letter_count >= 3 and number_count >= 3:
            return 'MIXED', clean_no_sep
    
    return None, clean


def normalize_plate_to_bolivian(plate_text):
    """Normaliza la placa a formato consistente si es boliviana válida.
    Para formatos estándar: normaliza a '1234 ABC'
    Para formatos mixtos: mantiene el formato original limpio
    Retorna string normalizado o None si no es formato boliviano.
    """
    fmt, clean = detect_plate_format(plate_text)
    if not fmt:
        return None

    if fmt == 'L3N4':
        # ABC1234 -> 1234 ABC
        m = re.match(r'^([A-Z]{3})[- ]?(\d{4})$', clean)
        if m:
            letters, numbers = m.group(1), m.group(2)
            return f"{numbers} {letters}"
    elif fmt == 'N4L3':
        # 1234ABC -> 1234 ABC
        m = re.match(r'^(\d{4})[- ]?([A-Z]{3})$', clean)
        if m:
            numbers, letters = m.group(1), m.group(2)
            return f"{numbers} {letters}"
    elif fmt == 'MIXED':
        # Formatos mixtos como BRA2E19, 1825B0L - mantener formato original
        return clean

    return None


def get_plate_last_digit_from_normalized(normalized_plate):
    """Extrae el último dígito de una placa normalizada o formato mixto"""
    if not normalized_plate:
        return None
    
    # Para formato estándar '1234 ABC'
    match = re.match(r'^(\d+)\s+[A-Z]+$', normalized_plate)
    if match:
        numbers = match.group(1)
        return int(numbers[-1]) if numbers else None
    
    # Para formatos mixtos (BRA2E19, 1825B0L, etc.)
    # Extraer todos los dígitos y tomar el último
    digits = re.findall(r'\d', normalized_plate)
    return int(digits[-1]) if digits else None


def is_restricted_today(plate_text, current_datetime=None):
    """Verifica si una placa está restringida hoy según el sistema boliviano"""
    import datetime
    
    if current_datetime is None:
        current_datetime = datetime.datetime.now()
    
    # Obtener el último dígito de la placa
    last_digit = get_plate_last_digit(plate_text)
    if last_digit is None:
        return False, "No se pudo determinar el último dígito"
    
    # Obtener día de la semana (0=Lunes, 6=Domingo)
    weekday = current_datetime.weekday()
    day_names = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    
    # Definir restricciones por día (dígitos restringidos)
    restrictions = {
        0: [1, 2],  # Lunes: terminación 1 y 2
        1: [3, 4],  # Martes: terminación 3 y 4  
        2: [5, 6],  # Miércoles: terminación 5 y 6
        3: [7, 8],  # Jueves: terminación 7 y 8
        4: [9, 0],  # Viernes: terminación 9 y 0
        5: [],      # Sábado: sin restricción
        6: [],      # Domingo: sin restricción
    }
    
    restricted_digits = restrictions.get(weekday, [])
    
    if last_digit in restricted_digits:
        return True, f"Restringido {day_names[weekday]} (terminación {last_digit})"
    else:
        return False, f"Permitido {day_names[weekday]} (terminación {last_digit})"


def is_restricted_time(current_datetime=None):
    """Verifica si estamos en horario de restricción"""
    import datetime
    
    if current_datetime is None:
        current_datetime = datetime.datetime.now()
    
    current_time = current_datetime.time()
    
    # Horarios de restricción en Bolivia (generalmente)
    morning_start = datetime.time(7, 0)   # 7:00 AM
    morning_end = datetime.time(9, 0)     # 9:00 AM
    evening_start = datetime.time(17, 0)  # 5:00 PM
    evening_end = datetime.time(20, 0)    # 8:00 PM
    
    is_morning_restriction = morning_start <= current_time <= morning_end
    is_evening_restriction = evening_start <= current_time <= evening_end
    
    if is_morning_restriction:
        return True, "Horario de restricción matutino (7:00-9:00)"
    elif is_evening_restriction:
        return True, "Horario de restricción vespertino (17:00-20:00)"
    else:
        return False, "Fuera de horario de restricción"
