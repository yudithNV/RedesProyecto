import colorama
import json
import datetime
from colorama import Fore, Style, Back

colorama.init()

header = ['Image', 'Plate', 'Status']
enhanced_header = ['Imagen', 'Placa', 'Confianza', 'Estado', 'Propietario', 'Método']


def fixed_length(text, length):
    if len(text) > length:
        text = text[:length]
    elif len(text) < length:
        text = (text + " " * length)[:length]
    return text


def format_output(data):
    """Formato original mantenido para compatibilidad"""
    print("━" * 70)
    print("┃", end=" ")
    for column in header:
        print(fixed_length(column, 20), end=" ┃ ")
    print()
    print("━" * 70)

    for row in data:
        print("┃", end=" ")
        for column in row:
            if column == 'AUTHORIZED':
                print(Fore.GREEN + fixed_length(column, 20) + Style.RESET_ALL, end=" ┃ ")
            elif column == 'NOT AUTHORIZED':
                print(Fore.RED + fixed_length(column, 20) + Style.RESET_ALL, end=" ┃ ")
            else:
                print(fixed_length(column, 20), end=" ┃ ")
        print()
    print("━" * 70)


def get_status_color(status):
    """Retorna el color apropiado para cada estado"""
    status_colors = {
        'AUTHORIZED': Fore.GREEN,
        'NOT AUTHORIZED': Fore.RED,
        'EXPIRED': Fore.YELLOW,
        'LOW CONFIDENCE': Fore.MAGENTA,
        'NOT DETECTED': Fore.CYAN,
        'PROCESSING ERROR': Fore.RED + Back.YELLOW,
        'ERROR': Fore.RED
    }
    return status_colors.get(status, Fore.WHITE)


def format_enhanced_output(results, output_config):
    """Formato mejorado con más información"""
    if not results:
        print("❌ No hay resultados para mostrar")
        return
    
    print("\n🚗 RESULTADOS DEL RECONOCIMIENTO DE PLACAS")
    print("=" * 120)
    
    # Encabezado
    print("┃", end=" ")
    widths = [20, 15, 12, 18, 25, 20]
    headers = ['Imagen', 'Placa', 'Confianza %', 'Estado', 'Propietario', 'Método']
    
    for i, header in enumerate(headers):
        print(fixed_length(header, widths[i]), end=" ┃ ")
    print()
    print("━" * 120)
    
    # Datos
    for result in results:
        print("┃", end=" ")
        
        # Imagen
        print(fixed_length(result['filename'], widths[0]), end=" ┃ ")
        
        # Placa
        plate_text = result['plate_text'] if result['plate_text'] else 'N/A'
        print(fixed_length(plate_text, widths[1]), end=" ┃ ")
        
        # Confianza
        if output_config.get('show_confidence', True):
            confidence_text = f"{result['confidence']}%" if result['confidence'] > 0 else "N/A"
            if result['confidence'] >= 80:
                confidence_color = Fore.GREEN
            elif result['confidence'] >= 60:
                confidence_color = Fore.YELLOW
            else:
                confidence_color = Fore.RED
            print(confidence_color + fixed_length(confidence_text, widths[2]) + Style.RESET_ALL, end=" ┃ ")
        else:
            print(fixed_length("N/A", widths[2]), end=" ┃ ")
        
        # Estado
        status_color = get_status_color(result['status'])
        status_text = result['status']
        print(status_color + fixed_length(status_text, widths[3]) + Style.RESET_ALL, end=" ┃ ")
        
        # Propietario
        if output_config.get('show_owner_info', True) and result.get('owner_info'):
            owner_name = result['owner_info'].get('owner', 'Desconocido')
            vehicle_type = result['owner_info'].get('vehicle_type', '')
            owner_text = f"{owner_name} ({vehicle_type})" if vehicle_type else owner_name
        else:
            owner_text = "N/A"
        print(fixed_length(owner_text, widths[4]), end=" ┃ ")
        
        # Método de procesamiento
        method = result.get('processing_method', 'Standard')
        print(fixed_length(method, widths[5]), end=" ┃ ")
        
        print()
    
    print("━" * 120)
    
    # Mostrar información adicional para placas autorizadas
    if output_config.get('show_owner_info', True):
        authorized_results = [r for r in results if r['status'] == 'AUTHORIZED' and r.get('owner_info')]
        if authorized_results:
            print("\n📋 DETALLES DE PLACAS AUTORIZADAS:")
            print("-" * 60)
            for result in authorized_results:
                owner_info = result['owner_info']
                print(f"🚗 Placa: {result['plate_text']}")
                print(f"   👤 Propietario: {owner_info.get('owner', 'N/A')}")
                print(f"   🚙 Vehículo: {owner_info.get('vehicle_type', 'N/A')}")
                print(f"   📅 Válida hasta: {owner_info.get('authorized_until', 'N/A')}")
                print(f"   🎯 Confianza: {result['confidence']}%")
                print()


def save_results_to_file(results, filename):
    """Guarda los resultados en un archivo JSON"""
    try:
        output_data = {
            'scan_date': datetime.datetime.now().isoformat(),
            'total_images': len(results),
            'results': results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Resultados guardados en: {filename}")
        
    except Exception as e:
        print(f"❌ Error guardando resultados: {e}")


def display_welcome_message():
    """Muestra mensaje de bienvenida mejorado"""
    print(Fore.CYAN + """
╔══════════════════════════════════════════════════════════════════╗
║                🚗 SISTEMA DE RECONOCIMIENTO DE PLACAS 🚗        ║
║                           Versión Mejorada                       ║
╠══════════════════════════════════════════════════════════════════╣
║  ✨ Características:                                             ║
║  • Detección automática de placas                                ║
║  • Múltiples filtros de imagen                                   ║
║  • Base de datos de placas autorizadas                           ║
║  • Análisis de confianza del OCR                                 ║
║  • Logging y estadísticas detalladas                             ║
║  • Configuración flexible                                        ║
╚══════════════════════════════════════════════════════════════════╝
    """ + Style.RESET_ALL)


def format_bolivia_output(results):
    """Formato específico para el sistema boliviano de restricción vehicular"""
    if not results:
        print("❌ No hay resultados para mostrar")
        return
    
    print("\n🚗 RESULTADOS DEL CONTROL DE RESTRICCIÓN VEHICULAR")
    print("═" * 110)
    
    # Encabezado
    headers = ['Imagen', 'Placa', 'Dígito', 'Confianza', 'Estado', 'Horario', 'Observaciones']
    widths = [18, 12, 8, 10, 20, 15, 25]
    
    print("┃", end=" ")
    for i, header in enumerate(headers):
        print(fixed_length(header, widths[i]), end=" ┃ ")
    print()
    print("═" * 110)
    
    # Datos
    for result in results:
        print("┃", end=" ")
        
        # Imagen
        print(fixed_length(result['filename'], widths[0]), end=" ┃ ")
        
        # Placa
        plate_text = result['plate_text'] if result['plate_text'] else 'N/A'
        print(fixed_length(plate_text, widths[1]), end=" ┃ ")
        
        # Último dígito
        digit_text = str(result.get('last_digit', 'N/A'))
        if result.get('last_digit') is not None:
            if result.get('is_restricted'):
                digit_color = Fore.RED
            else:
                digit_color = Fore.GREEN
            print(digit_color + fixed_length(digit_text, widths[2]) + Style.RESET_ALL, end=" ┃ ")
        else:
            print(fixed_length(digit_text, widths[2]), end=" ┃ ")
        
        # Confianza
        confidence_text = f"{result['confidence']}%" if result['confidence'] > 0 else "N/A"
        if result['confidence'] >= 80:
            confidence_color = Fore.GREEN
        elif result['confidence'] >= 60:
            confidence_color = Fore.YELLOW
        else:
            confidence_color = Fore.RED
        
        if result['confidence'] > 0:
            print(confidence_color + fixed_length(confidence_text, widths[3]) + Style.RESET_ALL, end=" ┃ ")
        else:
            print(fixed_length(confidence_text, widths[3]), end=" ┃ ")
        
        # Estado general
        status = result.get('overall_status', 'N/A')
        if 'RESTRICCIÓN ACTIVA' in status:
            status_color = Fore.RED + Back.YELLOW
        elif 'RESTRINGIDO' in status:
            status_color = Fore.YELLOW
        elif 'PERMITIDO' in status:
            status_color = Fore.GREEN
        else:
            status_color = Fore.CYAN
        
        print(status_color + fixed_length(status, widths[4]) + Style.RESET_ALL, end=" ┃ ")
        
        # Horario
        current_time = result.get('current_time', 'N/A')
        if result.get('time_restricted'):
            time_color = Fore.RED
        else:
            time_color = Fore.GREEN
        print(time_color + fixed_length(current_time, widths[5]) + Style.RESET_ALL, end=" ┃ ")
        
        # Observaciones
        if result.get('restriction_reason'):
            obs_text = result['restriction_reason']
        elif result.get('time_reason'):
            obs_text = result['time_reason']
        else:
            obs_text = "N/A"
        
        print(fixed_length(obs_text, widths[6]), end=" ┃ ")
        print()
    
    print("═" * 110)
    
    # Resumen por estados
    print("\n📊 RESUMEN:")
    print("-" * 50)
    
    status_counts = {}
    for result in results:
        status = result.get('overall_status', 'N/A')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in status_counts.items():
        if 'RESTRICCIÓN ACTIVA' in status:
            color = Fore.RED
            icon = "🚫"
        elif 'RESTRINGIDO' in status:
            color = Fore.YELLOW  
            icon = "⚠️"
        elif 'PERMITIDO' in status:
            color = Fore.GREEN
            icon = "✅"
        else:
            color = Fore.CYAN
            icon = "ℹ️"
        
        print(f"{icon} {color}{status}: {count}{Style.RESET_ALL}")


def display_processing_animation():
    """Muestra animación de procesamiento"""
    import time
    import sys
    
    animation = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    for i in range(20):
        sys.stdout.write(f"\r🔍 Procesando imágenes {animation[i % len(animation)]}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * 30 + "\r")
    sys.stdout.flush()
