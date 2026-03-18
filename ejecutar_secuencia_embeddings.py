#!/usr/bin/env python3
"""
Script orquestador que ejecuta los scripts de embeddings en secuencia
y apaga la computadora al finalizar.
"""

import subprocess
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SCRIPTS = [
    "script_embeddings_segob_55.py",
    "script_embeddings_basic_55.py",
    "script_embeddings_fce_55.py",
    "script_embeddings_transp_55.py",
    "script_embeddings_3p_55.py",
]

def ejecutar_script(script_path):
    """Ejecuta un script y retorna True si fue exitoso."""
    print(f"\n{'='*70}")
    print(f"Ejecutando: {script_path}")
    print(f"{'='*70}\n")
    
    try:
        resultado = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            check=False
        )
        if resultado.returncode == 0:
            print(f"✅ {script_path} completado exitosamente.")
            return True
        else:
            print(f"❌ {script_path} falló con código {resultado.returncode}.")
            return False
    except Exception as e:
        print(f"❌ Error ejecutando {script_path}: {e}")
        return False

def main():
    print("="*70)
    print("🔄 Iniciando secuencia de embeddings")
    print("="*70)
    
    resultados = {}
    
    for script in SCRIPTS:
        script_path = BASE_DIR / script
        if not script_path.exists():
            print(f"❌ Archivo no encontrado: {script_path}")
            resultados[script] = False
        else:
            resultados[script] = ejecutar_script(script_path)
    
    # Resumen final
    print(f"\n{'='*70}")
    print("📊 RESUMEN DE EJECUCIÓN")
    print(f"{'='*70}")
    for script, exito in resultados.items():
        estado = "✅ ÉXITO" if exito else "❌ FALLO"
        print(f"{estado} - {script}")
    
    print(f"\n{'='*70}")
    print("🔌 Apagando sistema en 10 segundos...")
    print(f"{'='*70}\n")
    
    import time
    time.sleep(10)
    
    # Apagar sistema
    sistema = sys.platform
    try:
        if sistema.startswith('linux'):
            os.system('shutdown -h now')
        elif sistema == 'darwin':
            os.system('osascript -e "tell app \\\"System Events\\\" to shut down"')
        elif sistema.startswith('win'):
            os.system('shutdown /s /t 0')
    except Exception as e:
        print(f"⚠️  No se pudo apagar automáticamente: {e}")
        print("Por favor, apaga manualmente el sistema.")

if __name__ == "__main__":
    main()
