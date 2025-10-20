#!/usr/bin/env python3
"""
Diagnóstico específico para placa8.jpeg
"""

import cv2
import os
from pathlib import Path
from lib.filters import pytesseract, get_grayscale, thresholding, remove_noise

def diagnose_placa8():
    """Diagnóstico detallado de placa8.jpeg"""
    
    image_path = Path("../images/placa8.jpeg")
    
    if not image_path.exists():
        print("❌ No se encuentra placa8.jpeg en ../images/")
        return
    
    print("🔍 DIAGNÓSTICO DETALLADO DE PLACA8.JPEG")
    print("="*50)
    
    # Cargar imagen
    image = cv2.imread(str(image_path))
    if image is None:
        print("❌ No se pudo cargar la imagen")
        return
    
    print(f"📏 Dimensiones: {image.shape[1]}x{image.shape[0]} píxeles")
    
    # Procesar imagen
    gray = get_grayscale(image)
    thresh = thresholding(gray)
    clean = remove_noise(thresh)
    
    # Probar diferentes configuraciones OCR
    configs = [
        ('PSM 6 (bloque)', '--psm 6'),
        ('PSM 7 (línea)', '--psm 7'),  
        ('PSM 8 (palabra)', '--psm 8'),
        ('PSM 13 (línea raw)', '--psm 13'),
        ('Solo números', '--psm 8 -c tessedit_char_whitelist=0123456789'),
        ('Solo letras', '--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
        ('Números+Letras', '--psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    ]
    
    print("\n📋 RESULTADOS OCR:")
    print("-" * 50)
    
    for name, config in configs:
        try:
            result = pytesseract.image_to_string(clean, config=config).strip()
            lines = [line.strip() for line in result.split('\n') if line.strip()]
            
            print(f"{name:15}: {lines}")
            
        except Exception as e:
            print(f"{name:15}: ERROR - {e}")
    
    print("\n🎯 ANÁLISIS:")
    print("- Esperado: 4143FZP")
    print("- Si aparece ALA3RLP, hay confusión de caracteres")
    print("- Si aparece vacío, problema de calidad de imagen")
    print("- Si aparece parcial, problema de segmentación")
    
    # Consejos
    print("\n💡 POSIBLES SOLUCIONES:")
    print("1. Mejorar preprocesamiento (contraste, nitidez)")
    print("2. Ampliar más la imagen")
    print("3. Detectar región de placa más precisamente")
    print("4. Ajustar correcciones de OCR para estos caracteres específicos")

if __name__ == "__main__":
    diagnose_placa8()