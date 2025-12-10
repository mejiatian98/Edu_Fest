                                #################################
                                #                               #
                                #           EVENT-SOFT          #
                                #       GESTION DE EVENTOS      #
                                #                               #
                                #################################




# Integrantes
- Juan David Cardona Rivera
- Michel Dahiana Rivera Cradona
- Sebastian Mejia Carmona
- Maria Jose Rodriguez Quintero

--------------------------------------------------------------------------------------------------------

# Descripcion del proyecto 

El presente trabajo tuvo como propósito desarrollar una solución de software orientada a mejorar la Gestión de Eventos, respondiendo a la necesidad identificada en el SENA. El proyecto se fundamentó en la carencia de herramientas digitales eficientes que permitieran optimizar tiempos, reducir errores y facilitar la toma de decisiones.

Para alcanzar este objetivo se implementó una metodología de desarrollo ágil, específicamente Scrum, que permitió iterar sobre los requerimientos y asegurar la participación activa de los usuarios finales. El sistema se construyó utilizando Django, MySQL y fue sometido a pruebas de validación funcional y de usabilidad.

Como resultado, se obtuvo una aplicación que cumple con los requerimientos planteados, mejora los tiempos de respuesta en un 100% efectiva y facilita la interacción entre usuarios y procesos. Las pruebas realizadas evidenciaron que el software es confiable, escalable y de fácil adopción.

En conclusión, el proyecto contribuye a la modernización de [campo de aplicación] y demuestra la pertinencia de integrar metodologías ágiles en el desarrollo de soluciones tecnológicas con impacto real en el entorno organizacional.

Palabras clave: desarrollo de software, metodología ágil, sistema de información, implementación.


# Roles

- Asistente: El Asistente es quien simplemente asiste al evento como público. Va a observar, escuchar o disfrutar del evento, sin participar activamente ni exponer nada.
- Expositor: El Expositor es quien presenta, muestra o explica algo durante el evento. Por ejemplo, si alguien tiene un stand, un proyecto o una charla, esa persona es un expositor.
- Evaluador: El evaluador es quien evalua a los expositores, proporcionando retroalimentación y puntuaciones.
- Administrador de eventos: persona encargada de crear eventos y su objetivo es garantizar que el evento se desarrolle de manera eficiente, ordenada y exitosa.
- super admin: Es el usuario con el nivel de acceso más alto dentro del sistema. Tiene control total sobre la plataforma. Su función es supervisar, administrar y asegurar el correcto funcionamiento general del sistema.

# Funcionalidades Principales

- Preinscripcion
- Inscipcion
- Certificacion
- Calificacion
- Descarga de documentos 
- Administracion de eventos
- Creacion de eventos

------------------------------------------------------------------------------------------------------------

# Repositorio de la aplicacion: https://github.com/mejiatian98/Edu_Fest.git

1- Clonar repositorio: git clone https://github.com/mejiatian98/Edu_Fest.git  
2- Entrar a la caperta :cd Edu_Fest
3- Instalar entorno virtrual: python -m venv venv
4- Activar entorno virtual: venv\Scripts\activate 
5- Instalar depencias del proyecto : pip install -r .\requirements.txt
6- Instalar migraciones: py .\manage.py migrate
7- Crear super usuario: py .\manage.py createsuperuser "rellenar campos" 
8- correr servidor: py .\manage.py runserver

------------------------------------------------------------------------------------------------------------

# Despliegue

- La aplicación está desplegada en Render.
- Los archivos estáticos están almacenados en Cloudinary.
- El envío de correos se realiza mediante Brevo (SendinBlue).|