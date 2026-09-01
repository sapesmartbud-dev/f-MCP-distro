# SAPÉ f-MCP — Data Protection Declaration / Declaración de Protección de Datos

**Language:** English / Español  
**Scope:** This declaration applies exclusively to **SAPÉ f-MCP** (the product), not to SAPÉ (the brand) or any other SAPÉ products.

---

## English

### Data Protection & Privacy Policy

**Last Updated:** 2026-07-29

#### Overview

SAPÉ f-MCP is committed to protecting your privacy and data security. This declaration outlines how your data is (or is not) collected, processed, or stored by installing or using SAPÉ f-MCP.

**Important:** This privacy policy applies only to SAPÉ f-MCP. Other SAPÉ products may have different data protection practices.

#### Core Principle: No Data Collection

**SAPÉ f-MCP collects NO personal data, NO telemetry, and NO user information.**

The application operates entirely on your local Windows machine. It does not:
- Send data to remote servers
- Collect usage statistics
- Track user behavior or activities
- Record file paths, file contents, or operation logs outside your machine
- Report crashes or errors to external services
- Require account creation or login
- Use cookies or tracking mechanisms
- Connect to third-party analytics services

#### Local Operation Only

SAPÉ f-MCP:
- Runs entirely on your computer
- Stores all session logs, permissions, and configuration locally
- Operates offline (no internet connection required)
- Does not require internet connectivity to function
- May optionally use the Model Context Protocol (MCP) to connect to local LLM clients—this communication occurs only on your machine and is not monitored or recorded by SAPÉ f-MCP

#### What SAPÉ f-MCP Does Store Locally

SAPÉ f-MCP maintains the following data **only on your local machine**:
- **Permissions database** (`permissions.db`, next to the application or wherever `--db` points): Your configured file access permissions and rules
- **Session log database** (`~/.sape/log.db`): Records of file operations, for your own audit purposes. The graphical interface deletes this database each time it starts
- **Tool log** (`tool_log.jsonl`, next to `permissions.db`): The same records in append-only form; this file is never truncated by the application and grows without limit
- **Settings file** (`~/.sape/config.json`) and detected installation details (`~/.sape/installation.json`): Your application preferences
- **Staged copies of your own files** (`%TEMP%\sape_download` on Windows, `/tmp/sape_download` elsewhere): the `download` tool copies the file or directory you ask for into the system temporary directory so a client can collect it. **These copies are not deleted afterwards**, they are outside the permission rules, and on Linux and macOS the staging directory is created with default permissions, which usually makes it readable by other accounts on the same machine. Delete that directory periodically if you use `download` on sensitive material

**All of this data remains on your computer.** SAPÉ f-MCP does not upload, transmit, or share this data with anyone.

#### Compliance with GDPR / RGPD

Under the EU General Data Protection Regulation (GDPR) and its Spanish implementation (Reglamento General de Protección de Datos, RGPD):

- SAPÉ f-MCP is **not a data controller** (it does not collect or process personal data)
- SAPÉ f-MCP is **not a data processor** (it does not process data on behalf of third parties)
- SAPÉ f-MCP imposes **no data protection obligations** on users, as no personal data exchange occurs
- Users retain full control of their local data at all times

#### Data Retention

Since no data is collected externally, there is no data to retain or delete. Users control their local data and may delete all SAPÉ f-MCP files and configuration at any time.

#### User Responsibilities

While SAPÉ f-MCP itself collects no data, users should be aware that:
- **Session logs stored locally may contain file paths** you have accessed (e.g., `C:\Users\[username]\Documents\file.txt`)
- These logs are for your audit purposes and remain on your machine
- You are responsible for the security and privacy of your own local data
- If you share your computer or backups, you are responsible for protecting your local SAPÉ f-MCP logs from unauthorized access

#### Third-Party Integrations

SAPÉ f-MCP may be used as an MCP server alongside third-party LLM applications (Claude Desktop, etc.). **SAPÉ f-MCP does not monitor or control what those applications do.** If you use SAPÉ f-MCP with a third-party LLM client:
- Consult that application's privacy policy
- That application's data practices are independent of SAPÉ
- SAPÉ f-MCP does not share data with, or receive data from, external LLM services

#### Contact for Privacy Inquiries

If you have questions about data protection or privacy, contact:

**SAPÉ smart bud**  
Email: info@sapebud.com  
Location: Arenys de Mar, Spain


---

---

## Español

### Declaración de Protección de Datos y Política de Privacidad

**Última actualización:** 2026-07-29

#### Descripción General

SAPÉ f-MCP se compromete a proteger su privacidad y seguridad de datos. Esta declaración describe cómo se recopilan, procesan o almacenan sus datos (o no se recopilan) en SAPÉ f-MCP.

**Importante:** Esta política de privacidad aplica únicamente a SAPÉ f-MCP. Otros productos SAPÉ pueden tener diferentes prácticas de protección de datos.

#### Principio Fundamental: Sin Recopilación de Datos

**SAPÉ f-MCP NO recopila datos personales, NO telemetría y NO información de usuarios.**

La aplicación funciona completamente en su máquina Windows local. No:
- Envía datos a servidores remotos
- Recopila estadísticas de uso
- Rastrea el comportamiento o actividades del usuario
- Registra rutas de archivos, contenidos de archivos u operaciones fuera de su máquina
- Informa de fallos o errores a servicios externos
- Requiere creación de cuenta o inicio de sesión
- Utiliza cookies o mecanismos de seguimiento
- Se conecta a servicios de análisis de terceros

#### Operación Local Únicamente

SAPÉ f-MCP:
- Se ejecuta completamente en su ordenador
- Almacena todos los registros de sesión, permisos y configuración localmente
- Funciona sin conexión (no requiere conexión a Internet)
- No requiere conectividad a Internet para funcionar
- Puede conectarse opcionalmente al Protocolo de Contexto de Modelo (MCP) para conectarse a clientes LLM locales—esta comunicación ocurre solo en su máquina y no es monitoreada ni grabada por SAPÉ f-MCP

#### Qué Almacena SAPÉ f-MCP Localmente

SAPÉ f-MCP mantiene los siguientes datos **solo en su máquina local**:
- **Base de datos de permisos** (`permissions.db`, junto a la aplicación o donde apunte `--db`): Sus permisos y reglas de acceso a archivos configurados
- **Base de datos de registros de sesión** (`~/.sape/log.db`): Registros de operaciones de archivos, para sus propósitos de auditoría. La interfaz gráfica borra esta base de datos cada vez que se inicia
- **Registro de herramientas** (`tool_log.jsonl`, junto a `permissions.db`): Los mismos registros en forma de solo-anexado; la aplicación nunca trunca este archivo y crece sin límite
- **Archivo de configuración** (`~/.sape/config.json`) y datos de la instalación detectada (`~/.sape/installation.json`): Sus preferencias de aplicación
- **Copias temporales de sus propios archivos** (`%TEMP%\sape_download` en Windows, `/tmp/sape_download` en el resto): la herramienta `download` copia el archivo o directorio solicitado al directorio temporal del sistema para que un cliente pueda recogerlo. **Estas copias no se eliminan después**, quedan fuera de las reglas de permisos y, en Linux y macOS, el directorio se crea con permisos predeterminados, lo que habitualmente lo hace legible por otras cuentas de la misma máquina. Borre ese directorio periódicamente si usa `download` con material sensible

**Todos estos datos permanecen en su ordenador.** SAPÉ f-MCP no carga, transmite ni comparte estos datos con nadie.

#### Cumplimiento de RGPD

Bajo el Reglamento General de Protección de Datos de la UE (GDPR) y su implementación española (RGPD):

- SAPÉ f-MCP **no es un responsable del tratamiento** (no recopila ni procesa datos personales)
- SAPÉ f-MCP **no es un procesador de datos** (no procesa datos en nombre de terceros)
- SAPÉ f-MCP **no impone obligaciones de protección de datos** a los usuarios, ya que no se realiza intercambio de datos personales
- Los usuarios retienen el control total de sus datos locales en todo momento

#### Retención de Datos

Como no se recopilan datos externamente, no hay datos para retener o eliminar. Los usuarios controlan sus datos locales y pueden eliminar todos los archivos y configuración de SAPÉ f-MCP en cualquier momento.

#### Responsabilidades del Usuario

Aunque SAPÉ f-MCPf-MCP no recopila datos externamente, los usuarios deben ser conscientes de que:
- **Los registros de sesión almacenados localmente pueden contener rutas de archivos** a las que ha accedido (por ejemplo, `C:\Users\[nombre de usuario]\Documentos\archivo.txt`)
- Estos registros son para sus propósitos de auditoría y permanecen en su máquina
- Usted es responsable de la seguridad y privacidad de sus propios datos locales
- Si comparte su ordenador o copias de seguridad, usted es responsable de proteger sus registros locales de SAPÉ f-MCP del acceso no autorizado

#### Integraciones de Terceros

SAPÉ f-MCP puede usarse como servidor MCP junto con aplicaciones LLM de terceros (Claude Desktop, etc.). **SAPÉ f-MCP no monitorea ni controla lo que hacen esas aplicaciones.** Si usa SAPÉ f-MCP con un cliente LLM de terceros:
- Consulte la política de privacidad de esa aplicación
- Las prácticas de datos de esa aplicación son independientes de SAPÉ f-MCP
- SAPÉ f-MCP no comparte datos con, ni recibe datos de, servicios LLM externos

#### Contacto para Consultas de Privacidad

Si tiene preguntas sobre protección de datos o privacidad, contacte a:

**SAPÉ smart bud**  
Email: info@sapebud.com  
Ubicación: Arenys de Mar, España

