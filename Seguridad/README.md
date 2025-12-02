# 🔐 Módulo de Seguridad - Autenticación Multifactor (MFA)

## 🧠 Descripción

Este módulo implementa un **sistema de autenticación multifactor (MFA)** robusto para el ecosistema CIPROBA. Proporciona una capa adicional de seguridad mediante verificación en dos pasos utilizando códigos de 6 dígitos enviados por correo electrónico.

El sistema está diseñado como un Blueprint de Flask, ofreciendo una interfaz web elegante y funcionalidad de redirección inteligente para proteger el acceso a las aplicaciones críticas del sistema.

---

## 📁 Estructura de archivos

```
Seguridad/
├── mfa.py                                # Blueprint principal MFA con lógica de verificación
├── __init__.py                          # Inicialización del módulo
├── templates/
│   ├── verificar_codigo.html           # Plantilla principal de verificación MFA
│   └── verificar_codigo copy.html      # Versión respaldo de la plantilla
├── static/
│   ├── css/
│   │   ├── verificar_codigo.css        # Estilos principales con identidad CIPROBA
│   │   ├── verificar_codigo copy.css   # Versión respaldo de estilos
│   │   └── verificar_codigo copy 2.css # Versión adicional de respaldo
│   └── js/                             # Directorio para JavaScript (futuro)
└── __pycache__/                        # Cache de Python compilado
```

---

## ⚙️ Configuración

### 🔗 Dependencias
- **Flask**: Framework web principal
- **utils**: Módulo para envío de correos (`enviar_codigo_verificacion`)
- **Log_Ciproba**: Sistema de logging centralizado
- **datetime**: Manejo de expiración de códigos
- **random**: Generación de códigos aleatorios

### 🗄️ Sesión requerida
El sistema requiere las siguientes variables en la sesión Flask:
- `correo_usuario`: Email del usuario para envío del código
- `nombre_usuario`: Nombre del usuario para personalización
- `destino_post_mfa`: Ruta de redirección después de verificación exitosa

---

## 🚀 Funcionalidades principales

### 🔐 Blueprint MFA (`mfa.py`)

**Funcionalidad central**: Gestión completa del flujo de autenticación multifactor

#### Ruta principal: `/verificar-codigo`
```python
@bp_mfa.route("/verificar-codigo", methods=["GET", "POST"])
def verificar_codigo():
```

#### Características del sistema:

**📧 Generación y envío de códigos (GET)**:
- Genera código aleatorio de 6 dígitos (100000-999999)
- Almacena código en sesión con expiración de 5 minutos
- Envía código por correo usando `enviar_codigo_verificacion()`
- Logging detallado de operaciones de seguridad

**✅ Validación de códigos (POST)**:
- Verifica código ingresado vs código esperado en sesión
- Valida expiración temporal (5 minutos)
- Manejo de errores con mensajes Flash
- Redirección inteligente post-verificación

**🔄 Sistema de redirección inteligente**:
- Soporte para rutas con parámetros GET
- Preservación del destino original en `destino_post_mfa`
- Reconstrucción completa de URLs con query strings
- Fallback a ruta base en caso de error

#### Variables de sesión manejadas:
- `codigo_mfa`: Código generado para verificación
- `mfa_expira`: Timestamp de expiración del código
- `mfa_verificado`: Estado de verificación (Boolean)
- `destino_post_mfa`: Objeto con ruta y parámetros de destino

---

## 🎨 Interfaz de usuario

### 🖼️ Plantilla de verificación (`verificar_codigo.html`)

**Diseño**: Interfaz elegante con identidad visual CIPROBA

#### Características de UX:
- **Personalización**: Saludo con nombre del usuario
- **Información clara**: Muestra email de destino del código
- **Feedback visual**: Mensajes Flash para errores y éxito
- **Accesibilidad**: Input con patrones de validación y autofocus
- **Responsive**: Adaptable a dispositivos móviles

#### Elementos clave:
- Input con validación de 6 dígitos numéricos
- Indicador de expiración (5 minutos)
- Iconografía intuitiva (🔐 para seguridad, ⏳ para tiempo)
- Botón de verificación con estados visuales

### 🎨 Estilos CSS (`verificar_codigo.css`)

**Identidad visual**: Colores verdes institucionales CIPROBA

#### Características de diseño:
- **Gradientes**: Fondo suave con verdes institucionales (#e7f8eb, #f4fff9, #e4f5e9)
- **Animaciones**: Efectos fade-in y elevación para mejor UX
- **Card principal**: Diseño moderno con sombras y bordes redondeados
- **Responsive**: Adaptación completa a diferentes tamaños de pantalla
- **Estados interactivos**: Hover y focus con transiciones suaves

#### Paleta de colores:
- Verde principal: `#6fbb44`
- Verde oscuro: `#39952b` 
- Verde texto: `#436c28`
- Fondo suave: `#f8fff7`
- Bordes: `#b3ddb0`

---

## 🔒 Seguridad implementada

### 🛡️ Características de seguridad

#### Validación temporal:
- **Expiración**: Códigos válidos por 5 minutos únicamente
- **Verificación de timestamp**: Comparación precisa con timezone handling
- **Invalidación automática**: Códigos expirados rechazados automáticamente

#### Protección de sesión:
- **Estado de verificación**: Flag `mfa_verificado` para control de acceso
- **Limpieza de sesión**: Eliminación del destino después de redirección
- **Validación de parámetros**: Verificación de variables de sesión requeridas

#### Logging de seguridad:
- **Eventos registrados**: Generación, verificación y fallos de códigos
- **Información auditada**: Email, timestamps y resultados de verificación
- **Integración**: Uso del sistema `Log_Ciproba` centralizado

---

## 🧪 Flujo de funcionamiento

### 📊 Proceso completo MFA

1. **Inicio de sesión**: Usuario accede a ruta protegida
2. **Redirecto a MFA**: Sistema redirecciona a `/verificar-codigo`
3. **Generación de código**: Sistema genera código aleatorio 6 dígitos
4. **Envío por correo**: Código enviado al email registrado del usuario
5. **Presentación de formulario**: Interfaz solicita ingreso del código
6. **Validación**: Sistema verifica código y expiración
7. **Redirección**: Acceso permitido a destino original o error mostrado

### 🔄 Estados del sistema

#### Estado inicial (GET):
```python
session["codigo_mfa"] = "123456"
session["mfa_expira"] = datetime + 5_minutos
session["mfa_verificado"] = False
```

#### Estado post-verificación (POST exitoso):
```python
session["mfa_verificado"] = True
# Redirección a destino_post_mfa
```

#### Estado de error:
```python
flash("❌ Código inválido o expirado")
# Permanece en formulario de verificación
```

---

## 🛠️ Integración con el ecosistema

### 🔗 Dependencias del sistema
- **Sistema de correos**: Utiliza `utils.enviar_codigo_verificacion()`
- **Logging centralizado**: Integración con `Log_Ciproba`
- **Sesiones Flask**: Manejo de estado de usuario y verificación
- **Rutas protegidas**: Integración con otros módulos del sistema

### 📡 Blueprint registration
```python
# En aplicación principal Flask
from Seguridad.mfa import bp_mfa
app.register_blueprint(bp_mfa)
```

### 🎯 Uso típico en rutas protegidas
```python
def ruta_protegida():
    if not session.get('mfa_verificado'):
        session['destino_post_mfa'] = {
            'ruta': request.path,
            'params': dict(request.args)
        }
        return redirect(url_for('mfa.verificar_codigo'))
    # Lógica de la ruta protegida...
```

---

## 🔮 Funcionalidades futuras

### Mejoras planificadas
1. **Múltiples canales**: SMS, WhatsApp, aplicaciones autenticadoras
2. **Códigos QR**: Integración con Google Authenticator/Authy
3. **Biometría**: Soporte para reconocimiento facial/huella
4. **Tokens hardware**: Compatibilidad con llaves de seguridad FIDO2
5. **Análisis de riesgo**: MFA adaptativo basado en contexto de acceso
6. **Dashboard de seguridad**: Panel de control para administradores

### Optimizaciones técnicas
1. **Cache de códigos**: Redis para mejor performance en múltiples instancias
2. **Rate limiting**: Protección contra ataques de fuerza bruta
3. **Métricas de seguridad**: Telemetría de intentos de acceso
4. **API REST**: Endpoints para integración con aplicaciones móviles

---

## 📚 Dependencias técnicas

### Principales
- `Flask`: Framework web con soporte para Blueprints
- `datetime`: Manejo de timestamps y expiración
- `random`: Generación criptográficamente segura de códigos
- `utils`: Módulo interno para envío de correos

### Integración interna
- `Log_Ciproba`: Sistema de logging del ecosistema CIPROBA
- Sesiones Flask para persistencia de estado
- Sistema de templates Jinja2 para renderizado

---

## 👥 Contribuidores

- **Carlos Andrés Jiménez Sarmiento (CJ)**: Arquitecto y desarrollador principal

---

## 📄 Licencia

Uso interno CIPROBA - Todos los derechos reservados

---

*Última actualización: Enero 2025 - Documentación basada en análisis de código real*
