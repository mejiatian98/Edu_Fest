                                #################################
                                #                               #
                                #           EVENT-SOFT          #
                                #       GESTIÓN DE EVENTOS      #
                                #                               #
                                #################################







----------------------------------------------------------------------------------------------------


# Integrantes

- Juan David Cardona Rivera
- Michel Dahiana Rivera Cardona
- Sebastián Mejía Carmona
- Maria Jose Rodríguez Quintero


---------------------------------------------------------------------------------------------------------


# Descripción del proyecto 

El presente trabajo tuvo como propósito desarrollar una solución de software orientada a mejorar la Gestión de Eventos, respondiendo a la necesidad identificada en el SENA. El proyecto se fundamentó en la carencia de herramientas digitales eficientes que permitieran optimizar tiempos, reducir errores y facilitar la toma de decisiones.
Para alcanzar este objetivo se implementó una metodología de desarrollo ágil, específicamente Scrum, que permitió iterar sobre los requerimientos y asegurar la participación activa de los usuarios finales. El sistema se construyó utilizando Django, MySQL y fue sometido a pruebas de validación funcional y de usabilidad.
Como resultado, se obtuvo una aplicación que cumple con los requerimientos planteados, mejora los tiempos de respuesta en un 100% efectiva y facilita la interacción entre usuarios y procesos. Las pruebas realizadas evidenciaron que el software es confiable, escalable y de fácil adopción.

En conclusión, el proyecto contribuye a la modernización de [campo de aplicación] y demuestra la pertinencia de integrar metodologías ágiles en el desarrollo de soluciones tecnológicas con impacto real en el entorno organizacional.

Palabras clave: desarrollo de software, metodología ágil, sistema de información, implementación.

---------------------------------------------------------------------------------------------------------
 

# Roles

- Asistente: El Asistente es quien simplemente asiste al evento como público. Va a observar, escuchar o disfrutar del evento, sin participar activamente ni exponer nada.
- Expositor: El Expositor es quien presenta, muestra o explica algo durante el evento. Por ejemplo, si alguien tiene un stand, un proyecto o una charla, esa persona es un expositor.
- Evaluador: El evaluador es quien evalúa a los expositores, proporcionando retroalimentación y puntuaciones.
- Administrador de eventos: persona encargada de crear eventos y su objetivo es garantizar que el evento se desarrolle de manera eficiente, ordenada y exitosa.
- súper admin: Es el usuario con el nivel de acceso más alto dentro del sistema. Tiene control total sobre la plataforma. Su función es supervisar, administrar y asegurar el correcto funcionamiento general del sistema.

---------------------------------------------------------------------------------------------------------


# Funcionalidades Principales


- Preinscripción
- Inscripción
- Certificación
- Calificación
- Descarga de documentos 
- Administración de eventos
- Creación de eventos

------------------------------------------------------------------------------------------------------------


# Pasos correr la aplicación en entorno local

1- Clonar repositorio: git cloné https://github.com/mejiatian98/Edu_Fest.git  
2- Entrar a la caperta:cd Edu_Fest
3- Instalar entorno virtual: python -m venv venv
4- Activar entorno virtual: venv\Scripts\activate 
5- Instalar dependías del proyecto: pip install -r .\requirements.txt
6- Instalar migraciones: py .\manage.py migrate
7- Crear superusuario: py .\manage.py createsuperuser "rellenar campos" 
8- Crear archivo variable de entorno .env en la raiz del proyecto que contenga lo siguiente:


----- DJANGO -----

- SECRET_KEY=tu_clave_secreta_super_segura
- DEBUG=True


--------- BASE DATOS LOCAL --------

- DB_NAME= nombre_de_la_base_de_datos
- DB_USER=root
- DB_PASSWORD=****
- DB_HOST=localhost
- DB_PORT=3306


----- CORREO GMAIL lOCAL -----
- EMAIL_HOST_USER=tucorreoaqui@gmail.com
- EMAIL_HOST_PASSWORD=**** **** **** ****
- DEFAULT_FROM_EMAIL="Event-Soft <tucorreoaqui@gmail.com>"


----- EMAIL (BREVO) -----

- USE_BREVO=False
- BREVO_API_KEY=******************************************
- DEFAULT_FROM_EMAIL="Event-Soft <tucorreoaqui@gmail.com>"


----- AWS S3 (solo necesario en producción) -----

- AWS_ACCESS_KEY_ID =****************
- AWS_SECRET_ACCESS_KEY =***********************************
- AWS_STORAGE_BUCKET_NAME =Nombre-Bucket-AWS-S3
- AWS_S3_REGION_NAME =us-east-#


----- CORREO SUPERUSER -----

- SUPERADMIN_EMAIL =Super-User-Even-Soft<halosniper04@gmail.com>


9- correr servidor: py .\manage.py runserver


---------------------------------------------------------------------------------------------------------


# Despliegue

- La aplicación está desplegada en Render al igual que la db postgrest
Acá la configuracion de ambiente en Render

![alt text](image.png)


- Los archivos media estan configurados en AWS S3.

- PASO 1 crear una cuenta en [AWS S3](https://aws.amazon.com/s3/) 
- PASO 2 crear un Bucket
- PASO 3 Dar permisos al bukcet, poner lo siguiente:

{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowPublicRead",
            "Effect": "Allow",
            "Principal": {
                "AWS": "*"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::evensotf-bucket/*"
        }
    ]
}

- PASO 4 Entrar a IAM y crear un usuario
- PASO 5 Dar politicas de permiso, por defecto seleccionar AmazonS3FullAccess
- PASO 6 Crear Clave de acceso en este mismo apartado del usuario usuario previamente creado
- PASO 7 copiar y pegar en entorno virtual de render la siguiente con su respectivo valor

AWS_ACCESS_KEY_ID =****************

AWS_SECRET_ACCESS_KEY =***********************************

AWS_STORAGE_BUCKET_NAME =Nombre-Bucket-AWS-S3

AWS_S3_REGION_NAME =us-east-#



- El envío de correos se realiza mediante Brevo.

- PASO 1 Crear una cuenta de [Brevo](https://www.brevo.com/es/)
- PASO 2 Ir a configuracion y entrar a SMTP Y API 
- PASO 3 Generar una clave API y MCP
- PASO 4 copiar y pegar en el entorno virtual de render

USE_BREVO=False

BREVO_API_KEY=******************************************

DEFAULT_FROM_EMAIL="Event-Soft <tucorreoaqui@gmail.com>"



NOTA IMPORTANTE

Debe tener un correo verificado en Brevo el cual sera el DEFAULT_FROM_EMAIL



------------------------------------------------------------------------------------------------------------


# Documentación de Event-Soft

La documentación está en la raíz del proyecto [Documentos_eventsoft](Documentos_eventsoft)
se alojan, los manuales de usuario, tecnico, las historias de usuario, sprint backlogs, Diagramas y documentación de proyecto formativo.

---------------------------------------------------------------------------------------------------------

