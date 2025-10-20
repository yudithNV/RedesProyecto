# 🇧🇴 Sistema de Control de Restricción Vehicular - Bolivia

Sistema inteligente de reconocimiento de placas vehiculares y verificación de restricción de circulación basado en el sistema boliviano de "Pico y Placa".

## 🚀 Características Principales

### ✨ Reconocimiento de Placas
- **Detección automática** de placas en imágenes
- **OCR avanzado** usando Tesseract
- **Múltiples filtros** de imagen para mejor precisión
- **Validación de formato** de placas bolivianas

### 📅 Sistema de Restricción
- **Verificación por día** de la semana según último dígito
- **Control de horarios** (7:00-9:00 y 17:00-20:00)
- **Simulación** para diferentes fechas y horas
- **Estados claros**: Restricción Activa, Restringido Inactivo, Permitido



## 🛠️ Instalación

### 1. Dependencias de Python
```bash
pip install opencv-python pytesseract colorama numpy
```

### 2. Tesseract OCR
- **Windows**: Descargar desde [GitHub Tesseract](https://github.com/tesseract-ocr/tesseract)
- **Linux**: `sudo apt install tesseract-ocr`
- **macOS**: `brew install tesseract`

### 3. Configuración
Asegúrate de que Tesseract esté en el PATH o actualiza la ruta en `src/lib/filters.py`:
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'
```

## 📋 Sistema de Restricción Boliviano

### 📅 Restricciones por Día
| Día | Dígitos Restringidos |
|-----|---------------------|
| 🟡 Lunes | 1, 2 |
| 🔵 Martes | 3, 4 |
| 🟢 Miércoles | 5, 6 |
| 🟠 Jueves | 7, 8 |
| 🔴 Viernes | 9, 0 |
| ⚪ Sábado/Domingo | Sin restricción |

### ⏰ Horarios de Restricción
- **🌅 Matutino**: 07:00 - 09:00
- **🌆 Vespertino**: 17:00 - 20:00

## 🎯 Uso del Sistema

### 1. Sistema Completo Interactivo
```bash
cd src
python sistema_bolivia_final.py
```

### 2. Versión Simplificada
```bash
cd src
python bolivia_simple.py
```

### 3. Sistema Original (sin restricción)
```bash
cd src
python app.py
```

## 📁 Estructura del Proyecto

```
license-plate-recognition/
├── src/
│   ├── sistema_bolivia_final.py    # Sistema interactivo completo
│   ├── bolivia_simple.py           # Versión simplificada
│   ├── app.py                      # Sistema original
│   ├── config.json                 # Configuración del sistema
│   ├── utils.py                    # Utilidades adicionales
│   └── lib/
│       ├── filters.py              # Filtros y procesamiento OCR
│       └── format_output.py        # Formateo de salida
├── images/                         # Imágenes a procesar
└── README.md                       # Este archivo
```

## 💡 Ejemplos de Uso

### Estados de Vehículos
- **🚫 RESTRICCIÓN ACTIVA**: No puede circular (día restringido + horario activo)
- **⚠️ RESTRINGIDO (fuera de horario)**: Día restringido pero horario libre
- **✅ PERMITIDO CIRCULAR**: Puede circular libremente

## 🔧 Configuración

Para personalizar horarios, editar en el código:
```python
self.horario_restriccion = {
    'matutino': (datetime.time(7, 0), datetime.time(9, 0)),
    'vespertino': (datetime.time(17, 0), datetime.time(20, 0))
}
```
