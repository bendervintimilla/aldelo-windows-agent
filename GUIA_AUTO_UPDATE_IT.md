# Guía para IT: Auto-Update de Agentes Windows

## Resumen
Cada vez que se haga un push a GitHub, los agentes de Windows se actualizarán automáticamente (cada hora).

---

## Instalación (UNA VEZ por computadora)

### Paso 1: Abrir carpeta del agente
Cada tienda tiene su carpeta, ejemplo:
- `C:\AldeloBIAgent\windows-agent-molldelrio\`
- `C:\AldeloBIAgent\windows-agent-lacreme\`

### Paso 2: Ejecutar como Administrador
1. Click derecho en `SETUP_AUTO_UPDATE.bat`
2. Seleccionar **"Ejecutar como administrador"**
3. Esperar mensaje de confirmación

### Paso 3: Verificar
El script creará una tarea programada llamada `AldeloBIAgentAutoUpdate` que:
- Se ejecuta **cada hora**
- Hace `git pull` automático
- Reinicia el servicio si hay cambios

---

## Verificar que funciona

### Ver logs de actualización:
```
update_log.txt
```
Este archivo está en la misma carpeta del agente y muestra:
- Fecha/hora de cada verificación
- Si se encontraron actualizaciones
- Si hubo errores

### Ver tarea programada:
1. Abrir **Task Scheduler** (Programador de tareas)
2. Buscar tarea: `AldeloBIAgentAutoUpdate`
3. Verificar que esté habilitada

---

## Desactivar auto-update
Si necesitas desactivar:
```cmd
schtasks /delete /tn "AldeloBIAgentAutoUpdate" /f
```

---

## Troubleshooting

| Problema | Solución |
|----------|----------|
| "Git not found" | Instalar Git para Windows |
| No se actualiza | Verificar conexión a internet |
| Servicio no reinicia | Verificar que el servicio "AldeloBIAgent" existe |
| Permisos denegados | Ejecutar como Administrador |

---

## Contacto
Si hay problemas, revisar el archivo `update_log.txt` y enviar captura.
