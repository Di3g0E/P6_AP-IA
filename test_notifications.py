#!/usr/bin/env python3
"""
Script para probar el sistema de notificaciones del P6_AP-IA.

Uso:
    python test_notifications.py

Este script permite probar:
1. Notificaciones por Telegram (requiere TELEGRAM_BOT_TOKEN en .env)
2. Notificaciones por WhatsApp (requiere pywhatkit y sesión activa)
3. Diferentes tipos de eventos: register, login, finance_anomaly, goal_threshold
4. Niveles de privacidad: redacted (default) vs full

Requisitos:
- Configurar .env con TELEGRAM_BOT_TOKEN
- Obtener tu chat_id de Telegram (habla con @userinfobot)
- Opcional: tener WhatsApp Web abierto para probar WhatsApp
"""

import os
import sys
from pathlib import Path

# Añadir src al path para importar módulos del proyecto
sys.path.insert(0, str(Path(__file__).parent / "src"))

from utils.notifications import (
    UserNotificationConfig,
    notify_register,
    notify_login,
    notify_finance_anomaly,
    notify_goal_threshold,
    get_notification_message,
)

def print_banner():
    print("=" * 60)
    print("🔔 SISTEMA DE NOTIFICACIONES P6_AP-IA - TEST")
    print("=" * 60)

def get_test_config():
    """
    Configuración de prueba. Modifica estos valores según tus necesidades.
    """
    # OBTENER TU CHAT_ID: habla con @userinfobot en Telegram
    # IMPORTANTE: El chat_id debe ser positivo (sin el signo -)
    telegram_chat_id = input("Introduce tu Telegram Chat ID (sin signo -, o presiona Enter para omitir): ").strip()
    
    # Formato internacional: +34600000000
    whatsapp_phone = input("Introduce tu número WhatsApp (formato +34..., o presiona Enter para omitir): ").strip()
    
    notification_level = input("Nivel de detalle (redacted/full, default=redacted): ").strip() or "redacted"
    
    # Convertir chat_id a positivo si es negativo
    if telegram_chat_id and telegram_chat_id.startswith('-'):
        telegram_chat_id = telegram_chat_id[1:]
        print(f"ℹ️  Chat ID convertido a positivo: {telegram_chat_id}")
    
    config = UserNotificationConfig(
        user_id="test-user-001",
        notifications_enabled=True,
        telegram_chat_id=telegram_chat_id if telegram_chat_id else None,
        whatsapp_phone=whatsapp_phone if whatsapp_phone else None,
        notification_level=notification_level if notification_level in ["redacted", "full"] else "redacted"
    )
    
    return config

def test_message_preview():
    """Muestra vistas previas de mensajes sin enviar."""
    print("\n📝 VISTAS PREVIAS DE MENSAJES:")
    print("-" * 40)
    
    # Test register
    msg1 = get_notification_message("register", level="redacted", user_id="test-user-001")
    print("🔹 REGISTER:")
    print(msg1)
    print()
    
    # Test login success
    msg2 = get_notification_message("login", level="redacted", success=True, 
                                  user_id="test-user-001", similarity=0.85, liveness=0.92)
    print("🔹 LOGIN SUCCESS:")
    print(msg2)
    print()
    
    # Test login failed
    msg3 = get_notification_message("login", level="redacted", success=False,
                                  user_id="test-user-001", message="Biometría no coincide")
    print("🔹 LOGIN FAILED:")
    print(msg3)
    print()
    
    # Test finance anomaly
    msg4 = get_notification_message("finance_anomaly", level="redacted",
                                  user_id="test-user-001", amount="1500.00€",
                                  area="Restaurante", type="gasto", date="2025-05-01",
                                  reasons=["Cantidad inusualmente alta", "Fuera de horario habitual"])
    print("🔹 FINANCE ANOMALY:")
    print(msg4)
    print()
    
    # Test goal threshold
    msg5 = get_notification_message("goal_threshold", level="redacted",
                                  user_id="test-user-001", area="Restaurantes",
                                  current="450€", limit="500€", pct=0.9)
    print("🔹 GOAL THRESHOLD:")
    print(msg5)
    print()

def test_telegram_notifications(config):
    """Prueba de envío de notificaciones por Telegram."""
    if not config.telegram_chat_id:
        print("⚠️  No se configuró Telegram Chat ID - omitiendo pruebas de Telegram")
        return
    
    print("\n📱 PRUEBAS DE TELEGRAM:")
    print("-" * 30)
    
    # Verificar token
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN no encontrado en .env")
        print("   Configura tu token en el archivo .env")
        return
    
    print(f"✅ Token encontrado. Enviando pruebas a {config.telegram_chat_id}")
    
    try:
        print("1. Enviando notificación de registro...")
        notify_register(config)
        
        print("2. Enviando notificación de login exitoso...")
        notify_login(config, success=True, similarity=0.89, liveness=0.94)
        
        print("3. Enviando notificación de login fallido...")
        notify_login(config, success=False, message="Umbral de similitud no superado")
        
        print("4. Enviando alerta de anomalía financiera...")
        notify_finance_anomaly(
            config,
            reasons=["Cantidad anómala", "Ubicación sospechosa"],
            date="2025-05-01",
            amount="2500.00€",
            area="Electrónica",
            type="gasto",
            description="Compra de alta tecnología"
        )
        
        print("5. Enviando alerta de objetivo...")
        notify_goal_threshold(
            config,
            area="Restaurantes",
            current="475€",
            limit="500€",
            pct=0.95
        )
        
        print("✅ Todas las pruebas de Telegram enviadas")
        
    except Exception as e:
        print(f"❌ Error en pruebas de Telegram: {e}")

def test_whatsapp_notifications(config):
    """Prueba de envío de notificaciones por WhatsApp."""
    if not config.whatsapp_phone:
        print("⚠️  No se configuró número de WhatsApp - omitiendo pruebas de WhatsApp")
        return
    
    print("\n💬 PRUEBAS DE WHATSAPP:")
    print("-" * 30)
    
    print("ℹ️  WhatsApp requiere:")
    print("   - pywhatkit instalado")
    print("   - WhatsApp Web abierto y logueado en esta máquina")
    print("   - Conexión a internet estable")
    
    confirm = input("¿Deseas continuar con pruebas de WhatsApp? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Pruebas de WhatsApp omitidas")
        return
    
    try:
        print("1. Enviando mensaje de prueba básico...")
        notify_login(config, success=True, message="Test desde P6_AP-IA")
        print("✅ Prueba de WhatsApp enviada (revisa tu WhatsApp)")
        
    except Exception as e:
        print(f"❌ Error en pruebas de WhatsApp: {e}")
        print("   Asegúrate de tener WhatsApp Web abierto")

def main():
    print_banner()
    
    # Verificar entorno
    print("🔍 Verificando entorno...")
    
    # Verificar .env
    if not os.path.exists(".env"):
        print("❌ Archivo .env no encontrado")
        print("   Copia .env.example a .env y configúralo")
        return
    
    # Verificar token de Telegram
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if token:
        print("✅ TELEGRAM_BOT_TOKEN configurado")
    else:
        print("⚠️  TELEGRAM_BOT_TOKEN no configurado (Telegram no funcionará)")
    
    # Mostrar vistas previas
    print("\n¿Deseas ver vistas previas de mensajes? (Y/n): ", end="")
    if input().strip().lower() != 'n':
        test_message_preview()
    
    # Obtener configuración de prueba
    config = get_test_config()
    
    print(f"\n📋 Configuración de prueba:")
    print(f"   Usuario ID: {config.user_id}")
    print(f"   Telegram: {'✅' if config.telegram_chat_id else '❌'}")
    print(f"   WhatsApp: {'✅' if config.whatsapp_phone else '❌'}")
    print(f"   Nivel detalle: {config.notification_level}")
    
    # Ejecutar pruebas
    test_telegram_notifications(config)
    test_whatsapp_notifications(config)
    
    print("\n🎯 Pruebas completadas")
    print("   Revisa tus notificaciones en Telegram/WhatsApp")
    print("   Revisa los logs en logs/app.log para más detalles")

if __name__ == "__main__":
    main()
