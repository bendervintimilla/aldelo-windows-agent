# 🚀 Instalación Rápida - BENDRIX BI Smart Agent v2.0

## Instalación en 1 Minuto

### Paso Único:

1. **Descargar** la carpeta `windows-agent` al computador del local
2. **Doble clic** en `INSTALAR.bat`
3. **Ingresar** el ID de tienda cuando lo pida (ej: `molldelrio`)
4. **¡Listo!** El agente está corriendo

---

## ¿Qué hace el instalador automático?

✅ Instala Python si no existe  
✅ Instala todas las dependencias  
✅ Configura el archivo config.json  
✅ Crea tarea para iniciar con Windows  
✅ Inicia el agente inmediatamente  

---

## Verificar que Funciona

### Opción 1: Dashboard Web
- Ve a https://aldelo-bi-production.up.railway.app
- Login → Manager Tools → Pestaña "Agentes"
- Deberías ver tu tienda como "Online"

### Opción 2: Logs Locales
- Abre la carpeta `windows-agent\logs\`
- Revisa el archivo `agent_YYYYMMDD.log`

---

## Solución de Problemas

### El agente no inicia
```
cd C:\ruta\windows-agent
python smart_agent.py
```
Ver el error en la consola.

### Error de base de datos
1. Verificar que Aldelo esté instalado
2. Revisar que el archivo .mdb exista

### Error de conexión
1. Verificar conexión a internet
2. Los datos se guardan localmente y sincronizan después

---

## Características v2.0

| Característica | Descripción |
|---------------|-------------|
| 📦 Buffer Local | Guarda datos si no hay internet |
| 🔄 Reintentos | Reintenta automáticamente con backoff |
| 💓 Heartbeat | Reporta estado cada 5 minutos |
| 📊 Monitoreo | Visible en dashboard central |
| 📝 Logs | Logs estructurados por día |

---

## Archivos Importantes

```
windows-agent/
├── INSTALAR.bat       ← Instalador de un clic
├── smart_agent.py     ← Agente principal v2.0
├── config.json        ← Configuración (se crea automático)
├── sync_buffer.db     ← Buffer local SQLite
└── logs/              ← Logs diarios
    └── agent_YYYYMMDD.log
```

---

## Contacto Soporte

Si hay problemas, enviar:
1. Screenshot del error
2. Archivo de log más reciente
3. Store ID

---

*Última actualización: Febrero 2026*
